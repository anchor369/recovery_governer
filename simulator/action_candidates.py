"""
Creates possible recovery actions for one failed payment state.

This component only creates structurally possible action candidates.
Economic and policy filtering is applied later by the Governor.
"""

from simulator.config import SimulatorConfig
from simulator.method_selector import PaymentMethodSelector
from simulator.models import (
    ActionType,
    HistoricalJourney,
    PaymentStatus,
    RecoveryAction,
    SyntheticCustomer,
)


class ActionCandidateGenerator:
    """Creates recovery-action candidates after a confirmed failure."""

    def __init__(
        self,
        config: SimulatorConfig,
        method_selector: PaymentMethodSelector,
    ):
        self.config = config
        self.method_selector = method_selector

    def generate_candidates(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
    ) -> list[RecoveryAction]:
        """
        Return candidate actions for the latest confirmed payment failure.
        """

        latest_attempt = journey.payment_attempts[-1]

        if latest_attempt.status != PaymentStatus.FAILED:
            return []

        candidates = [
            RecoveryAction(
                action_type=ActionType.NO_ACTION,
            ),
            RecoveryAction(
                action_type=ActionType.NUDGE,
            ),
        ]

        available_methods = (
            self.method_selector.get_available_methods(
                customer
            )
        )

        for method in available_methods:
            if method == latest_attempt.method:
                continue

            candidates.append(
                RecoveryAction(
                    action_type=ActionType.SWITCH_METHOD,
                    target_method=method,
                )
            )

        for discount_percent in (
            self.config.allowed_offer_percentages
        ):
            candidates.append(
                RecoveryAction(
                    action_type=ActionType.APPROVED_OFFER,
                    discount_percent=discount_percent,
                )
            )

        return candidates