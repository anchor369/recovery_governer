from datetime import (
    datetime,
    timezone,
)

import uuid

from backend.data_access.payments import (
    create_customer,
    create_order,
)

from backend.data_access.recovery import (
    create_recovery_case,
    create_recovery_decision,
)

from backend.services import (
    recovery_execution,
)

from simulator.models import (
    ActionType,
    RecoveryAction,
)


def build_pending_nudge_action():
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
        action_type=(
            ActionType.NUDGE
        ),
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
        build_pending_nudge_action()
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
        build_pending_nudge_action()
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


def test_paid_order_blocks_action_before_execution(
    monkeypatch,
):
    order_id, action = (
        build_pending_nudge_action()
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


def test_uncertain_payment_state_blocks_action(
    monkeypatch,
):
    order_id, action = (
        build_pending_nudge_action()
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