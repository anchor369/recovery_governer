"""
Synthetic merchant economics used by the Recovery Governor.

Recovery probability alone is insufficient. Actions are valued using
expected merchant contribution after discount and intervention costs.
"""

from dataclasses import dataclass

from simulator.models import (
    ActionType,
    RecoveryAction,
    RecoveryDecisionState,
)


@dataclass(frozen=True)
class MerchantEconomics:
    """
    Merchant-level economic assumptions.

    Values are synthetic benchmark parameters, not Razorpay pricing.
    """

    contribution_margin_rate: float = 0.35

    # Communication cost + a small monetized contact/friction penalty.
    nudge_cost_minor: int = 200

    # Small UX / routing friction proxy.
    switch_cost_minor: int = 50

    offer_execution_cost_minor: int = 0

    merchant_offer_cap_percent: float = 10.0


def expected_merchant_value_minor(
    state: RecoveryDecisionState,
    action: RecoveryAction,
    recovery_probability: float,
    economics: MerchantEconomics,
) -> float:
    """
    Calculate expected contribution value of one candidate action.
    """

    base_contribution = (
        state.current_amount_minor
        * economics.contribution_margin_rate
    )

    discount_cost_if_paid = 0.0
    fixed_action_cost = 0.0

    if action.action_type == ActionType.NUDGE:
        fixed_action_cost = (
            economics.nudge_cost_minor
        )

    elif (
        action.action_type
        == ActionType.SWITCH_METHOD
    ):
        fixed_action_cost = (
            economics.switch_cost_minor
        )

    elif (
        action.action_type
        == ActionType.APPROVED_OFFER
    ):
        discount_percent = (
            action.discount_percent or 0.0
        )

        discount_cost_if_paid = (
            state.current_amount_minor
            * discount_percent
            / 100.0
        )

        fixed_action_cost = (
            economics.offer_execution_cost_minor
        )

    value_if_recovered = (
        base_contribution
        - discount_cost_if_paid
    )

    return (
        recovery_probability
        * value_if_recovered
        - fixed_action_cost
    )