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

        prior_upi_attempt_count=0,
        prior_upi_success_count=0,
        prior_upi_success_rate=0.0,

        prior_credit_card_attempt_count=0,
        prior_credit_card_success_count=0,
        prior_credit_card_success_rate=0.0,

        prior_debit_card_attempt_count=0,
        prior_debit_card_success_count=0,
        prior_debit_card_success_rate=0.0,

        prior_netbanking_attempt_count=0,
        prior_netbanking_success_count=0,
        prior_netbanking_success_rate=0.0,

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

def test_policy_check_explains_missing_consent():
    state = build_state()
    state.contact_consent = False

    learner = StubLearner(
        {
            "NO_ACTION": 0.60,
            "NUDGE": 0.70,
        }
    )

    governor = RecoveryGovernor(
        learner=learner,
        economics=MerchantEconomics(),
    )

    action = RecoveryAction(
        action_type=ActionType.NUDGE,
    )

    check = governor.check_action_policy(
        state=state,
        action=action,
    )

    assert check.allowed is False

    assert (
        check.reason
        == "CONTACT_CONSENT_MISSING"
    )

def test_policy_check_explains_offer_cap():
    state = build_state()

    learner = StubLearner(
        {
            "NO_ACTION": 0.60,
        }
    )

    governor = RecoveryGovernor(
        learner=learner,
        economics=MerchantEconomics(
            merchant_offer_cap_percent=5.0
        ),
    )

    action = RecoveryAction(
        action_type=(
            ActionType.APPROVED_OFFER
        ),
        discount_percent=10.0,
    )

    check = governor.check_action_policy(
        state=state,
        action=action,
    )

    assert check.allowed is False

    assert (
        check.reason
        == "MERCHANT_OFFER_CAP_EXCEEDED"
    )


def test_policy_check_blocks_nudge_for_active_customer():
    state = build_state(active=True)
    governor = RecoveryGovernor(
        learner=StubLearner({"NO_ACTION": 0.60}),
        economics=MerchantEconomics(),
    )

    check = governor.check_action_policy(
        state=state,
        action=RecoveryAction(action_type=ActionType.NUDGE),
    )

    assert check.allowed is False
    assert check.reason == "CUSTOMER_STILL_ACTIVE"


def test_policy_check_blocks_actions_at_maximum_attempts():
    state = build_state()
    state.attempt_count = 6
    governor = RecoveryGovernor(
        learner=StubLearner({"NO_ACTION": 0.60}),
        economics=MerchantEconomics(),
        max_payment_attempts=6,
    )

    check = governor.check_action_policy(
        state=state,
        action=RecoveryAction(action_type=ActionType.NUDGE),
    )

    assert check.allowed is False
    assert check.reason == "MAX_PAYMENT_ATTEMPTS_REACHED"


def test_policy_check_blocks_switch_to_current_method():
    state = build_state()
    governor = RecoveryGovernor(
        learner=StubLearner({"NO_ACTION": 0.60}),
        economics=MerchantEconomics(),
    )

    check = governor.check_action_policy(
        state=state,
        action=RecoveryAction(
            action_type=ActionType.SWITCH_METHOD,
            target_method=PaymentMethod.UPI,
        ),
    )

    assert check.allowed is False
    assert check.reason == "TARGET_EQUALS_CURRENT_METHOD"


def test_policy_check_blocks_unavailable_switch_target():
    state = build_state()
    state.available_debit_card = False
    governor = RecoveryGovernor(
        learner=StubLearner({"NO_ACTION": 0.60}),
        economics=MerchantEconomics(),
    )

    check = governor.check_action_policy(
        state=state,
        action=RecoveryAction(
            action_type=ActionType.SWITCH_METHOD,
            target_method=PaymentMethod.DEBIT_CARD,
        ),
    )

    assert check.allowed is False
    assert check.reason == "TARGET_METHOD_UNAVAILABLE"
