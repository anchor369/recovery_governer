import numpy as np

from policy.economics import MerchantEconomics
from policy.governor import RecoveryGovernor
from simulator.models import (
    ActionType,
    FailureCategory,
    PaymentMethod,
    RecoveryAction,
    RecoveryDecisionState,
)


class StubLearner:
    """Return deterministic probabilities for Governor unit tests."""

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


def build_state(
    consent=True,
    active=False,
):

    return RecoveryDecisionState(
        customer_tenure_days=250,

        prior_checkout_count=5,
        prior_success_count=4,
        prior_failure_count=1,
        prior_success_rate=0.8,

        prior_upi_count=3,
        prior_credit_card_count=1,
        prior_debit_card_count=1,
        prior_netbanking_count=0,

        available_upi=True,
        available_credit_card=True,
        available_debit_card=True,
        available_netbanking=True,

        current_amount_minor=100000,
        amount_ratio=1.0,

        current_method=PaymentMethod.UPI,

        failure_category=(
            FailureCategory.ISSUER_DECLINED
        ),

        attempt_count=1,

        observed_rail_health=0.95,

        contact_consent=consent,
        customer_active=active,
    )


def test_governor_can_choose_no_action_when_intervention_value_is_negative():

    learner = StubLearner(
        {
            "NO_ACTION": 0.60,
            "NUDGE": 0.602,
            "SWITCH_DEBIT_CARD": 0.601,
            "OFFER_5": 0.61,
        }
    )

    governor = RecoveryGovernor(
        learner=learner,
        economics=MerchantEconomics(),
    )

    candidates = [
        RecoveryAction(
            action_type=ActionType.NO_ACTION,
        ),

        RecoveryAction(
            action_type=ActionType.NUDGE,
        ),

        RecoveryAction(
            action_type=ActionType.SWITCH_METHOD,
            target_method=PaymentMethod.DEBIT_CARD,
        ),

        RecoveryAction(
            action_type=ActionType.APPROVED_OFFER,
            discount_percent=5.0,
        ),
    ]

    decision = governor.decide(
        state=build_state(),
        candidates=candidates,
    )

    assert (
        decision.chosen_action.action_type
        == ActionType.NO_ACTION
    )


def test_governor_chooses_high_value_nudge():

    learner = StubLearner(
        {
            "NO_ACTION": 0.60,
            "NUDGE": 0.72,
        }
    )

    governor = RecoveryGovernor(
        learner=learner,
        economics=MerchantEconomics(),
    )

    candidates = [
        RecoveryAction(
            action_type=ActionType.NO_ACTION,
        ),

        RecoveryAction(
            action_type=ActionType.NUDGE,
        ),
    ]

    decision = governor.decide(
        state=build_state(),
        candidates=candidates,
    )

    assert (
        decision.chosen_action.action_type
        == ActionType.NUDGE
    )


def test_governor_blocks_nudge_without_consent():

    learner = StubLearner(
        {
            "NO_ACTION": 0.50,
            "NUDGE": 0.99,
        }
    )

    governor = RecoveryGovernor(
        learner=learner,
        economics=MerchantEconomics(),
    )

    candidates = [
        RecoveryAction(
            action_type=ActionType.NO_ACTION,
        ),

        RecoveryAction(
            action_type=ActionType.NUDGE,
        ),
    ]

    decision = governor.decide(
        state=build_state(
            consent=False,
        ),
        candidates=candidates,
    )

    assert (
        decision.chosen_action.action_type
        == ActionType.NO_ACTION
    )