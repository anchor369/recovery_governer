from simulator.models import (
    ActionType,
    PaymentMethod,
    RecoveryAction,
    RecoveryDecisionState,
)


DEFAULT_ALLOWED_OFFER_PERCENTAGES = (
    5.0,
    10.0,
)


def build_structural_candidates(
    state: RecoveryDecisionState,
    allowed_offer_percentages=(
        DEFAULT_ALLOWED_OFFER_PERCENTAGES
    ),
) -> list[RecoveryAction]:
    """
    Create actions that are structurally possible
    for this recovery state.

    Deterministic policy and economic filtering
    happen later in the Recovery Governor.
    """

    candidates = [
        RecoveryAction(
            action_type=ActionType.NO_ACTION,
        ),
        RecoveryAction(
            action_type=ActionType.NUDGE,
        ),
    ]

    method_availability = {
        PaymentMethod.UPI:
            state.available_upi,

        PaymentMethod.CREDIT_CARD:
            state.available_credit_card,

        PaymentMethod.DEBIT_CARD:
            state.available_debit_card,

        PaymentMethod.NETBANKING:
            state.available_netbanking,
    }

    for method, available in (
        method_availability.items()
    ):
        if not available:
            continue

        if method == state.current_method:
            continue

        candidates.append(
            RecoveryAction(
                action_type=(
                    ActionType.SWITCH_METHOD
                ),
                target_method=method,
            )
        )

    for discount_percent in (
        allowed_offer_percentages
    ):
        if discount_percent <= 0:
            continue

        candidates.append(
            RecoveryAction(
                action_type=(
                    ActionType.APPROVED_OFFER
                ),
                discount_percent=(
                    float(discount_percent)
                ),
            )
        )

    return candidates