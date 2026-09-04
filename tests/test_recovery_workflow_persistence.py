"""Database regressions for durable recovery-workflow boundaries."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np
import pytest

from backend.data_access.payments import (
    create_customer,
    create_order,
    create_payment,
    record_payment_event,
)
from backend.data_access.recovery import (
    close_recovery_case_for_workflow_failure,
    create_recovery_decision_audit_bundle,
    create_recovery_case,
    get_recovery_decision,
    get_active_recovery_case_for_order,
)
from backend.db import get_connection
from backend.services import recovery_engine
from backend.services.recovery_decision import RecoveryDecisionService
from backend.services.recovery_outcome import record_recovered_payment
from backend.services.recovery_state import RuntimeRecoverySignals


class FailingDecisionService:
    governor = object()

    def __init__(self, error):
        self.error = error

    def decide_for_order(self, **kwargs):
        raise self.error


class SuccessfulDecisionService:
    governor = object()

    def decide_for_order(self, **kwargs):
        return SimpleNamespace(
            governor_decision=SimpleNamespace(
                chosen_action="TEST_ACTION",
            )
        )


class StubLearner:
    def __init__(self, probabilities):
        self.probabilities = probabilities

    def predict_treatment(self, dataframe, treatment):
        return np.array([self.probabilities[treatment]])


def create_order_record(prefix):
    suffix = uuid.uuid4().hex[:10]
    customer_id = f"C_{prefix}_{suffix}"
    order_id = f"O_{prefix}_{suffix}"

    create_customer(customer_id=customer_id)
    create_order(
        order_id=order_id,
        customer_id=customer_id,
        amount_minor=150_000,
    )

    return order_id, suffix


def get_cases_for_order(order_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    recovery_case_id,
                    status,
                    closure_reason,
                    closed_at
                FROM recovery_cases
                WHERE order_id = %s
                ORDER BY opened_at;
                """,
                (order_id,),
            )
            return cursor.fetchall()


def test_failed_case_is_queryable_and_does_not_block_future_case(
    monkeypatch,
):
    order_id, suffix = create_order_record("WORKFLOW_FAIL")
    original_error = RuntimeError("decision failed")

    monkeypatch.setattr(
        recovery_engine,
        "evaluate_recovery_eligibility",
        lambda order_id: {
            "eligible": True,
            "reason": "MULTIPLE_CONFIRMED_FAILURES",
        },
    )

    with pytest.raises(RuntimeError) as raised:
        recovery_engine.run_recovery_workflow(
            order_id=order_id,
            decision_time=datetime.now(timezone.utc),
            runtime_signals=None,
            decision_service=FailingDecisionService(original_error),
        )

    assert raised.value is original_error
    assert get_active_recovery_case_for_order(order_id) is None

    failed_case = get_cases_for_order(order_id)[0]
    assert failed_case[1] == "CLOSED"
    assert failed_case[2] == "DECISION_FAILED"
    assert failed_case[3] is not None

    # Closing the failed case releases the existing partial unique index;
    # the safety constraint itself remains unchanged.
    replacement = create_recovery_case(
        recovery_case_id=f"RC_RETRY_{suffix}",
        order_id=order_id,
    )
    assert replacement["status"] == "OPEN"

    close_recovery_case_for_workflow_failure(
        recovery_case_id=replacement["recovery_case_id"],
        closure_reason="DECISION_FAILED",
    )


def test_action_creation_failure_preserves_committed_audit(
    monkeypatch,
):
    order_id, suffix = create_order_record("ACTION_FAIL")
    decision_id = f"D_ACTION_FAIL_{suffix}"
    original_error = RuntimeError("action creation failed")

    monkeypatch.setattr(
        recovery_engine,
        "evaluate_recovery_eligibility",
        lambda order_id: {
            "eligible": True,
            "reason": "MULTIPLE_CONFIRMED_FAILURES",
        },
    )

    def persist_audit(recovery_case_id, prediction_time, **kwargs):
        return create_recovery_decision_audit_bundle(
            decision_data={
                "decision_id": decision_id,
                "recovery_case_id": recovery_case_id,
                "prediction_time": prediction_time,
                "model_version": "test-model",
                "proposed_action": "NUDGE",
                "feature_snapshot": {"attempt_count": 2},
                "explanation": "Committed before action creation.",
            },
            score_rows=[
                {
                    "decision_id": decision_id,
                    "action_type": "NO_ACTION",
                    "is_eligible": True,
                    "ineligible_reason": None,
                    "predicted_success_probability": 0.5,
                    "uplift": 0.0,
                    "expected_incremental_utility_minor": 0,
                    "payment_processing_cost_minor": 0,
                    "action_cost_minor": 0,
                    "discount_cost_minor": 0,
                    "expected_merchant_value_minor": 75_000,
                }
            ],
        )

    monkeypatch.setattr(
        recovery_engine,
        "persist_operational_decision",
        persist_audit,
    )

    def fail_action_creation(**kwargs):
        raise original_error

    monkeypatch.setattr(
        recovery_engine,
        "create_pending_recovery_action",
        fail_action_creation,
    )

    with pytest.raises(RuntimeError) as raised:
        recovery_engine.run_recovery_workflow(
            order_id=order_id,
            decision_time=datetime.now(timezone.utc),
            runtime_signals=None,
            decision_service=SuccessfulDecisionService(),
        )

    assert raised.value is original_error
    assert get_recovery_decision(decision_id) is not None

    failed_case = get_cases_for_order(order_id)[0]
    assert failed_case[1] == "CLOSED"
    assert failed_case[2] == "ACTION_CREATION_FAILED"

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM decision_action_scores "
                "WHERE decision_id = %s;",
                (decision_id,),
            )
            score_count = cursor.fetchone()[0]
            cursor.execute(
                "SELECT count(*) FROM recovery_actions "
                "WHERE decision_id = %s;",
                (decision_id,),
            )
            action_count = cursor.fetchone()[0]

    assert score_count == 1
    assert action_count == 0


def test_successful_workflow_still_reaches_recovered_closed():
    order_id, suffix = create_order_record("WORKFLOW_SUCCESS")
    now = datetime.now(timezone.utc)

    for attempt, method in ((1, "UPI"), (2, "NETBANKING")):
        payment_id = f"P_WORKFLOW_FAIL_{attempt}_{suffix}"
        create_payment(
            payment_id=payment_id,
            order_id=order_id,
            method=method,
            status="CREATED",
            failure_reason="TECHNICAL_FAILURE",
        )
        record_payment_event(
            payment_id=payment_id,
            provider_event_id=f"EV_WORKFLOW_FAIL_{attempt}_{suffix}",
            event_type="FAILED",
            event_time=now - timedelta(minutes=3 - attempt),
        )

    learner = StubLearner(
        {
            "NO_ACTION": 0.50,
            "NUDGE": 0.80,
            "SWITCH_UPI": 0.55,
            "SWITCH_CREDIT_CARD": 0.55,
            "SWITCH_DEBIT_CARD": 0.55,
            "SWITCH_NETBANKING": 0.55,
            "OFFER_5": 0.54,
            "OFFER_10": 0.53,
        }
    )
    decision_service = RecoveryDecisionService(learner=learner)
    signals = RuntimeRecoverySignals(
        available_upi=True,
        available_credit_card=True,
        available_debit_card=True,
        available_netbanking=True,
        observed_rail_health=0.9,
        customer_active=False,
    )

    workflow = recovery_engine.run_recovery_workflow(
        order_id=order_id,
        decision_time=now + timedelta(seconds=1),
        runtime_signals=signals,
        decision_service=decision_service,
    )

    assert workflow.workflow_state == "DECIDED"
    assert workflow.action["execution_status"] == "EXECUTED"

    recovery_payment_id = f"P_WORKFLOW_RECOVERED_{suffix}"
    create_payment(
        payment_id=recovery_payment_id,
        order_id=order_id,
        method="UPI",
        status="CREATED",
    )
    record_payment_event(
        payment_id=recovery_payment_id,
        provider_event_id=f"EV_WORKFLOW_RECOVERED_{suffix}",
        event_type="CAPTURED",
        event_time=datetime.now(timezone.utc),
    )

    outcome = record_recovered_payment(
        recovery_case_id=workflow.case["recovery_case_id"],
        action_id=workflow.action["action_id"],
        payment_id=recovery_payment_id,
    )

    assert outcome["outcome"]["outcome_type"] == "RECOVERED"
    assert outcome["case"]["status"] == "CLOSED"
    assert outcome["case"]["closure_reason"] == "RECOVERED"
