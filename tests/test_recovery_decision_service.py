import numpy as np

from backend.services.recovery_decision import (
    RecoveryDecisionService,
)

from simulator.models import (
    ActionType,
    FailureCategory,
    PaymentMethod,
    RecoveryDecisionState,
)

import uuid

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from backend.data_access.payments import (
    create_customer,
    create_order,
    create_payment,
    record_payment_event,
)

from backend.services.recovery_state import (
    RuntimeRecoverySignals,
)


class StubLearner:
    def __init__(
        self,
        probabilities,
    ):
        self.probabilities = (
            probabilities
        )

    def predict_treatment(
        self,
        dataframe,
        treatment,
    ):
        return np.array(
            [
                self.probabilities[
                    treatment
                ]
            ]
        )


def build_test_state():
    return RecoveryDecisionState(
        customer_tenure_days=100,

        prior_checkout_count=3,
        prior_success_count=2,
        prior_failure_count=1,
        prior_success_rate=(2 / 3),

        prior_upi_count=2,
        prior_credit_card_count=1,
        prior_debit_card_count=0,
        prior_netbanking_count=0,

        prior_upi_attempt_count=2,
        prior_upi_success_count=1,
        prior_upi_success_rate=0.5,

        prior_credit_card_attempt_count=1,
        prior_credit_card_success_count=1,
        prior_credit_card_success_rate=1.0,

        prior_debit_card_attempt_count=0,
        prior_debit_card_success_count=0,
        prior_debit_card_success_rate=0.0,

        prior_netbanking_attempt_count=0,
        prior_netbanking_success_count=0,
        prior_netbanking_success_rate=0.0,

        available_upi=True,
        available_credit_card=True,
        available_debit_card=False,
        available_netbanking=True,

        current_amount_minor=100_000,
        amount_ratio=1.2,

        current_method=PaymentMethod.UPI,

        failure_category=(
            FailureCategory.TECHNICAL_FAILURE
        ),

        attempt_count=2,

        observed_rail_health=0.8,

        contact_consent=True,
        customer_active=False,
    )

def test_decision_service_connects_candidates_and_governor():

    learner = StubLearner(
        {
            "NO_ACTION": 0.60,
            "NUDGE": 0.72,

            "SWITCH_CREDIT_CARD":
                0.64,

            "SWITCH_NETBANKING":
                0.63,

            "OFFER_5": 0.61,
            "OFFER_10": 0.62,
        }
    )

    service = RecoveryDecisionService(
        learner=learner,
    )

    result = service.decide_from_state(
        build_test_state()
    )

    assert (
        result.governor_decision
        .chosen_action
        .action_type
        == ActionType.NUDGE
    )

    assert len(
        result.candidates
    ) == 6


def test_decide_for_order_builds_state_from_database():
    suffix = uuid.uuid4().hex[:8]

    customer_id = (
        f"C_DECISION_{suffix}"
    )

    prior_order_id = (
        f"O_DECISION_PRIOR_{suffix}"
    )

    current_order_id = (
        f"O_DECISION_CURRENT_{suffix}"
    )

    prior_payment_id = (
        f"P_DECISION_PRIOR_{suffix}"
    )

    current_payment_1 = (
        f"P_DECISION_CURRENT_1_{suffix}"
    )

    current_payment_2 = (
        f"P_DECISION_CURRENT_2_{suffix}"
    )

    create_customer(
        customer_id=customer_id,
        contact_consent=True,
    )

    create_order(
        order_id=prior_order_id,
        customer_id=customer_id,
        amount_minor=100_000,
    )

    create_order(
        order_id=current_order_id,
        customer_id=customer_id,
        amount_minor=150_000,
    )

    create_payment(
        payment_id=prior_payment_id,
        order_id=prior_order_id,
        method="UPI",
        status="CAPTURED",
    )

    create_payment(
        payment_id=current_payment_1,
        order_id=current_order_id,
        method="UPI",
        status="FAILED",
        failure_reason=(
            "AUTHENTICATION_FAILURE"
        ),
    )

    create_payment(
        payment_id=current_payment_2,
        order_id=current_order_id,
        method="NETBANKING",
        status="FAILED",
        failure_reason=(
            "TECHNICAL_FAILURE"
        ),
    )

    now = datetime.now(
        timezone.utc
    )

    record_payment_event(
        payment_id=prior_payment_id,
        provider_event_id=(
            f"EV_DECISION_PRIOR_{suffix}"
        ),
        event_type="CAPTURED",
        event_time=(
            now
            - timedelta(minutes=30)
        ),
    )

    record_payment_event(
        payment_id=current_payment_1,
        provider_event_id=(
            f"EV_DECISION_CURRENT_1_{suffix}"
        ),
        event_type="FAILED",
        event_time=(
            now
            - timedelta(minutes=10)
        ),
    )

    record_payment_event(
        payment_id=current_payment_2,
        provider_event_id=(
            f"EV_DECISION_CURRENT_2_{suffix}"
        ),
        event_type="FAILED",
        event_time=(
            now
            - timedelta(minutes=5)
        ),
    )

    learner = StubLearner(
        {
            "NO_ACTION": 0.60,
            "NUDGE": 0.72,

            "SWITCH_UPI":
                0.64,

            "SWITCH_CREDIT_CARD":
                0.63,

            "OFFER_5": 0.61,
            "OFFER_10": 0.62,
        }
    )

    service = RecoveryDecisionService(
        learner=learner,
    )

    signals = RuntimeRecoverySignals(
        available_upi=True,
        available_credit_card=True,
        available_debit_card=False,
        available_netbanking=True,
        observed_rail_health=0.8,
        customer_active=False,
    )

    result = service.decide_for_order(
        current_order_id=current_order_id,
        decision_time=(
            now
            + timedelta(seconds=5)
        ),
        runtime_signals=signals,
    )

    assert (
        result.state.attempt_count
        == 2
    )

    assert (
        result.state.current_method
        == PaymentMethod.NETBANKING
    )

    assert (
        result.state.prior_success_count
        == 1
    )

    assert (
        result.governor_decision
        .chosen_action
        .action_type
        == ActionType.NUDGE
    )