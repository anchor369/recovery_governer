from datetime import (
    datetime,
    timezone,
)
from concurrent.futures import (
    ThreadPoolExecutor,
)
from threading import Barrier

import pytest
import uuid

from backend.data_access import (
    recovery as recovery_data_access,
)

from backend.data_access.payments import (
    create_customer,
    create_order,
)

from backend.data_access.recovery import (
    create_recovery_case,
    create_recovery_decision,
)

from backend.db import get_connection

from backend.services import (
    recovery_execution,
)

from simulator.models import (
    ActionType,
    RecoveryAction,
)


def build_recovery_action(
    action_type=ActionType.NUDGE,
):
    """
    Build the minimum real DB chain required
    before a recovery_action can exist:

    customer
        ↓
    order
        ↓
    recovery_case
        ↓
    recovery_decision
        ↓
    recovery_action
    """

    suffix = uuid.uuid4().hex[:8]

    customer_id = (
        f"C_EXEC_{suffix}"
    )

    order_id = (
        f"O_EXEC_{suffix}"
    )

    recovery_case_id = (
        f"RC_EXEC_{suffix}"
    )

    decision_id = (
        f"D_EXEC_{suffix}"
    )

    create_customer(
        customer_id=customer_id,
    )

    create_order(
        order_id=order_id,
        customer_id=customer_id,
        amount_minor=150_000,
    )

    create_recovery_case(
        recovery_case_id=(
            recovery_case_id
        ),
        order_id=order_id,
    )

    create_recovery_decision(
        decision_id=decision_id,
        recovery_case_id=(
            recovery_case_id
        ),
        prediction_time=(
            datetime.now(
                timezone.utc
            )
        ),
        model_version=(
            "s_learner_corrected_v1"
        ),
        proposed_action="NUDGE",
        feature_snapshot={
            "attempt_count": 2,
        },
        explanation=(
            "Execution test."
        ),
    )

    chosen_action = RecoveryAction(
        action_type=action_type,
    )

    action = (
        recovery_execution
        .create_pending_recovery_action(
            decision_id=decision_id,
            chosen_action=(
                chosen_action
            ),
        )
    )

    return (
        order_id,
        action,
    )


def test_create_pending_nudge_action():
    order_id, action = (
        build_recovery_action()
    )

    assert order_id is not None

    assert (
        action["action_type"]
        == "NUDGE"
    )

    assert (
        action["execution_status"]
        == "PENDING"
    )

    assert (
        action["executed_at"]
        is None
    )

    assert (
        action["blocked_reason"]
        is None
    )

    assert (
        action["policy_checks"][
            "governor_approved"
        ]
        is True
    )


def test_unpaid_order_executes_action(
    monkeypatch,
):
    order_id, action = (
        build_recovery_action()
    )

    def fake_truth(order_id):
        return "UNPAID"

    monkeypatch.setattr(
        recovery_execution,
        "evaluate_order_truth",
        fake_truth,
    )

    executed = (
        recovery_execution
        .execute_recovery_action(
            order_id=order_id,
            action=action,
        )
    )

    assert (
        executed["execution_status"]
        == "EXECUTED"
    )

    assert (
        executed["blocked_reason"]
        is None
    )

    assert (
        executed["executed_at"]
        is not None
    )

    assert executed["transition_applied"] is True
    assert executed["execution_result"] == "EXECUTED_NOW"


def test_paid_order_blocks_action_before_execution(
    monkeypatch,
):
    order_id, action = (
        build_recovery_action()
    )

    def fake_truth(order_id):
        return "PAID"

    monkeypatch.setattr(
        recovery_execution,
        "evaluate_order_truth",
        fake_truth,
    )

    blocked = (
        recovery_execution
        .execute_recovery_action(
            order_id=order_id,
            action=action,
        )
    )

    assert (
        blocked["execution_status"]
        == "BLOCKED"
    )

    assert (
        blocked["blocked_reason"]
        == (
            "ORDER_ALREADY_PAID_"
            "BEFORE_EXECUTION"
        )
    )

    assert (
        blocked["executed_at"]
        is None
    )

    assert blocked["transition_applied"] is True
    assert (
        blocked["execution_result"]
        == "BLOCKED_BY_PAYMENT_TRUTH"
    )


def test_uncertain_payment_state_blocks_action(
    monkeypatch,
):
    order_id, action = (
        build_recovery_action()
    )

    def fake_truth(order_id):
        return "UNCERTAIN"

    monkeypatch.setattr(
        recovery_execution,
        "evaluate_order_truth",
        fake_truth,
    )

    blocked = (
        recovery_execution
        .execute_recovery_action(
            order_id=order_id,
            action=action,
        )
    )

    assert (
        blocked["execution_status"]
        == "BLOCKED"
    )

    assert (
        blocked["blocked_reason"]
        == (
            "PAYMENT_STATE_UNCERTAIN_"
            "BEFORE_EXECUTION"
        )
    )

    assert (
        blocked["executed_at"]
        is None
    )

    assert blocked["transition_applied"] is True
    assert (
        blocked["execution_result"]
        == "BLOCKED_BY_PAYMENT_TRUTH"
    )


def test_not_required_action_remains_untouched(
    monkeypatch,
):
    order_id, action = build_recovery_action(
        action_type=ActionType.NO_ACTION,
    )

    def unexpected_truth_check(order_id):
        raise AssertionError(
            "NOT_REQUIRED must not enter execution."
        )

    monkeypatch.setattr(
        recovery_execution,
        "evaluate_order_truth",
        unexpected_truth_check,
    )

    result = recovery_execution.execute_recovery_action(
        order_id=order_id,
        action=action,
    )

    assert result == action
    assert result["execution_status"] == "NOT_REQUIRED"


def test_terminal_action_returns_already_processed(
    monkeypatch,
):
    order_id, action = build_recovery_action()
    truth_calls = 0

    def unpaid_truth(order_id):
        nonlocal truth_calls
        truth_calls += 1
        return "UNPAID"

    monkeypatch.setattr(
        recovery_execution,
        "evaluate_order_truth",
        unpaid_truth,
    )

    first = recovery_execution.execute_recovery_action(
        order_id=order_id,
        action=action,
    )
    second = recovery_execution.execute_recovery_action(
        order_id=order_id,
        action=first,
    )

    assert truth_calls == 1
    assert second["execution_status"] == "EXECUTED"
    assert second["executed_at"] == first["executed_at"]
    assert second["execution_result"] == "ALREADY_PROCESSED"
    assert second["transition_applied"] is False


def test_two_workers_only_one_transitions_pending_action(
    monkeypatch,
):
    order_id, action = build_recovery_action()
    workers_ready = Barrier(2)

    def synchronized_unpaid_truth(order_id):
        workers_ready.wait(timeout=10)
        return "UNPAID"

    monkeypatch.setattr(
        recovery_execution,
        "evaluate_order_truth",
        synchronized_unpaid_truth,
    )

    def execute():
        return recovery_execution.execute_recovery_action(
            order_id=order_id,
            action=dict(action),
        )

    # Each call reaches the data-access boundary in its own worker and opens
    # its own PostgreSQL connection for the conditional transition.
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: execute(), range(2)))

    winners = [
        result
        for result in results
        if result["transition_applied"]
    ]
    already_processed = [
        result
        for result in results
        if not result["transition_applied"]
    ]

    assert len(winners) == 1
    assert len(already_processed) == 1
    assert winners[0]["execution_result"] == "EXECUTED_NOW"
    assert (
        already_processed[0]["execution_result"]
        == "ALREADY_PROCESSED"
    )
    assert {
        result["execution_status"] for result in results
    } == {"EXECUTED"}
    assert (
        results[0]["executed_at"]
        == results[1]["executed_at"]
    )


def test_pending_transition_rolls_back_on_failure():
    _, action = build_recovery_action()

    with pytest.raises(RuntimeError, match="forced failure"):
        with get_connection() as connection:
            with connection.cursor() as cursor:
                transitioned = (
                    recovery_data_access
                    ._transition_pending_recovery_action(
                        cursor=cursor,
                        action_id=action["action_id"],
                        execution_status="EXECUTED",
                        blocked_reason=None,
                        executed_at=datetime.now(timezone.utc),
                    )
                )
                assert transitioned is not None
                raise RuntimeError("forced failure")

    # The connection context sees the exception and rolls back the actual
    # conditional UPDATE rather than leaving a partially changed action.
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT execution_status, executed_at
                FROM recovery_actions
                WHERE action_id = %s;
                """,
                (action["action_id"],),
            )
            status, executed_at = cursor.fetchone()

    assert status == "PENDING"
    assert executed_at is None
