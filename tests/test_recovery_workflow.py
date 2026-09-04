from datetime import (
    datetime,
    timezone,
)

from types import (
    SimpleNamespace,
)

from backend.services import (
    recovery_engine,
)


class FakeDecisionService:
    def __init__(self):
        self.called = False
        self.call_count = 0

        # Real RecoveryDecisionService has this.
        self.governor = object()

    def decide_for_order(
        self,
        current_order_id,
        decision_time,
        runtime_signals,
    ):
        self.called = True
        self.call_count += 1

        # The workflow now expects:
        #
        # decision
        #   .governor_decision
        #   .chosen_action
        #
        # SimpleNamespace lets us imitate
        # that structure without running ML.
        return SimpleNamespace(
            governor_decision=(
                SimpleNamespace(
                    chosen_action=(
                        "FAKE_CHOSEN_ACTION"
                    )
                )
            )
        )


def fake_persist_operational_decision(
    recovery_case_id,
    prediction_time,
    operational_decision,
    governor,
):
    return {
        "decision": {
            "decision_id": "D_TEST",
        },
        "scores": [],
    }


def fake_create_pending_recovery_action(
    decision_id,
    chosen_action,
):
    return {
        "action_id": "A_TEST",
        "decision_id": decision_id,
        "action_type": "NUDGE",
        "execution_status": "PENDING",
        "blocked_reason": None,
        "executed_at": None,
    }


def fake_execute_recovery_action(
    order_id,
    action,
):
    return {
        **action,
        "execution_status": "EXECUTED",
        "executed_at": (
            datetime.now(
                timezone.utc
            )
        ),
    }


def test_paid_order_stops_before_decision(
    monkeypatch,
):
    decision_service = (
        FakeDecisionService()
    )

    def fake_open(order_id):
        return {
            "opened": False,
            "reason": (
                "ORDER_ALREADY_PAID"
            ),
            "case": None,
        }

    monkeypatch.setattr(
        recovery_engine,
        "open_recovery_case_if_eligible",
        fake_open,
    )

    result = (
        recovery_engine
        .run_recovery_workflow(
            order_id="O_TEST",
            decision_time=(
                datetime.now(
                    timezone.utc
                )
            ),
            runtime_signals=None,
            decision_service=(
                decision_service
            ),
        )
    )

    assert (
        result.workflow_state
        == "STOP"
    )

    assert (
        decision_service.called
        is False
    )

    assert result.audit is None
    assert result.action is None


def test_uncertain_order_waits_before_decision(
    monkeypatch,
):
    decision_service = (
        FakeDecisionService()
    )

    def fake_open(order_id):
        return {
            "opened": False,
            "reason": (
                "PAYMENT_STATE_UNCERTAIN"
            ),
            "case": None,
        }

    monkeypatch.setattr(
        recovery_engine,
        "open_recovery_case_if_eligible",
        fake_open,
    )

    result = (
        recovery_engine
        .run_recovery_workflow(
            order_id="O_TEST",
            decision_time=(
                datetime.now(
                    timezone.utc
                )
            ),
            runtime_signals=None,
            decision_service=(
                decision_service
            ),
        )
    )

    assert (
        result.workflow_state
        == "WAIT_FOR_TRUTH"
    )

    assert (
        decision_service.called
        is False
    )

    assert result.audit is None
    assert result.action is None


def test_first_failure_allows_natural_retry(
    monkeypatch,
):
    decision_service = (
        FakeDecisionService()
    )

    def fake_open(order_id):
        return {
            "opened": False,
            "reason": (
                "ALLOW_NATURAL_RETRY"
            ),
            "case": None,
        }

    monkeypatch.setattr(
        recovery_engine,
        "open_recovery_case_if_eligible",
        fake_open,
    )

    result = (
        recovery_engine
        .run_recovery_workflow(
            order_id="O_TEST",
            decision_time=(
                datetime.now(
                    timezone.utc
                )
            ),
            runtime_signals=None,
            decision_service=(
                decision_service
            ),
        )
    )

    assert (
        result.workflow_state
        == "ALLOW_NATURAL_RETRY"
    )

    assert (
        decision_service.called
        is False
    )

    assert result.audit is None
    assert result.action is None


def test_eligible_order_runs_full_decision_and_execution_flow(
    monkeypatch,
):
    decision_service = (
        FakeDecisionService()
    )

    fake_case = {
        "recovery_case_id": "RC_TEST",
        "order_id": "O_TEST",
        "status": "OPEN",
    }

    def fake_open(order_id):
        return {
            "opened": True,
            "reason": (
                "RECOVERY_CASE_OPENED"
            ),
            "case": fake_case,
        }

    monkeypatch.setattr(
        recovery_engine,
        "open_recovery_case_if_eligible",
        fake_open,
    )

    monkeypatch.setattr(
        recovery_engine,
        "persist_operational_decision",
        fake_persist_operational_decision,
    )

    monkeypatch.setattr(
        recovery_engine,
        "create_pending_recovery_action",
        fake_create_pending_recovery_action,
    )

    monkeypatch.setattr(
        recovery_engine,
        "execute_recovery_action",
        fake_execute_recovery_action,
    )

    result = (
        recovery_engine
        .run_recovery_workflow(
            order_id="O_TEST",
            decision_time=(
                datetime.now(
                    timezone.utc
                )
            ),
            runtime_signals=(
                "TEST_SIGNALS"
            ),
            decision_service=(
                decision_service
            ),
        )
    )

    assert (
        result.workflow_state
        == "DECIDED"
    )

    assert (
        result.reason
        == "RECOVERY_DECISION_CREATED"
    )

    assert (
        result.case
        == fake_case
    )

    assert (
        decision_service.called
        is True
    )

    assert (
        decision_service.call_count
        == 1
    )

    assert (
        result.audit[
            "decision"
        ][
            "decision_id"
        ]
        == "D_TEST"
    )

    assert (
        result.action[
            "action_id"
        ]
        == "A_TEST"
    )

    assert (
        result.action[
            "decision_id"
        ]
        == "D_TEST"
    )

    assert (
        result.action[
            "execution_status"
        ]
        == "EXECUTED"
    )

    assert (
        result.action[
            "executed_at"
        ]
        is not None
    )