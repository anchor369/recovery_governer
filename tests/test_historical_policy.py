from simulator.historical_policy import (
    HistoricalRecoveryPolicy,
)
from simulator.models import (
    ActionType,
    FailureCategory,
    PaymentMethod,
    RecoveryAction,
    RecoveryDecisionState,
)
from simulator.random_source import RandomSource


def build_state(
    consent=True,
    active=False,
):

    return RecoveryDecisionState(
        customer_tenure_days=300,

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

        current_amount_minor=200000,
        amount_ratio=1.3,

        current_method=PaymentMethod.UPI,

        failure_category=(
            FailureCategory.INSUFFICIENT_FUNDS
        ),

        attempt_count=1,

        observed_rail_health=0.95,

        contact_consent=consent,
        customer_active=active,
    )


def build_candidates():

    return [
        RecoveryAction(
            action_type=ActionType.NO_ACTION,
        ),

        RecoveryAction(
            action_type=ActionType.NUDGE,
        ),

        RecoveryAction(
            action_type=ActionType.SWITCH_METHOD,
            target_method=PaymentMethod.CREDIT_CARD,
        ),

        RecoveryAction(
            action_type=ActionType.APPROVED_OFFER,
            discount_percent=5.0,
        ),
    ]


def test_policy_probabilities_sum_to_one():

    policy = HistoricalRecoveryPolicy(
        RandomSource(42)
    )

    results = policy.action_probabilities(
        build_state(),
        build_candidates(),
    )

    total = sum(
        probability
        for _, probability
        in results
    )

    assert abs(
        total - 1.0
    ) < 1e-9


def test_nudge_is_blocked_without_consent():

    policy = HistoricalRecoveryPolicy(
        RandomSource(42)
    )

    results = policy.action_probabilities(
        build_state(
            consent=False,
        ),
        build_candidates(),
    )

    assert all(
        action.action_type
        != ActionType.NUDGE
        for action, _
        in results
    )


def test_nudge_is_blocked_for_active_customer():

    policy = HistoricalRecoveryPolicy(
        RandomSource(42)
    )

    results = policy.action_probabilities(
        build_state(
            active=True,
        ),
        build_candidates(),
    )

    assert all(
        action.action_type
        != ActionType.NUDGE
        for action, _
        in results
    )


def test_chosen_action_has_positive_behavior_probability():

    policy = HistoricalRecoveryPolicy(
        RandomSource(42)
    )

    action, probability = (
        policy.choose_action(
            build_state(),
            build_candidates(),
        )
    )

    assert action in build_candidates()
    assert probability > 0.0
    assert probability <= 1.0