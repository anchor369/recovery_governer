"""
Biased stochastic historical recovery policy.

This represents the kind of imperfect policy that could have generated
observational treatment data before the learned Recovery Governor existed.
"""

import math

from simulator.models import (
    ActionType,
    FailureCategory,
    PaymentMethod,
    RecoveryAction,
    RecoveryDecisionState,
)
from simulator.random_source import RandomSource


class HistoricalRecoveryPolicy:
    """Chooses one observable action using biased stochastic rules."""

    def __init__(
        self,
        random_source: RandomSource,
    ):
        self.random = random_source

    def choose_action(
        self,
        state: RecoveryDecisionState,
        candidates: list[RecoveryAction],
    ) -> tuple[RecoveryAction, float]:
        """
        Choose one historical action and return its behaviour probability.
        """

        eligible_candidates = [
            action
            for action in candidates
            if self._is_eligible(
                state=state,
                action=action,
            )
        ]

        if not eligible_candidates:
            raise ValueError(
                "Historical policy has no eligible actions."
            )

        scores = [
            self._score_action(
                state=state,
                action=action,
            )
            for action in eligible_candidates
        ]

        probabilities = self._softmax(
            scores
        )

        probabilities = self._add_exploration_floor(
            probabilities
        )

        chosen_action = self.random.choice(
            eligible_candidates,
            probabilities,
        )

        chosen_index = (
            eligible_candidates.index(
                chosen_action
            )
        )

        behavior_probability = (
            probabilities[
                chosen_index
            ]
        )

        return (
            chosen_action,
            behavior_probability,
        )

    def action_probabilities(
        self,
        state: RecoveryDecisionState,
        candidates: list[RecoveryAction],
    ) -> list[
        tuple[RecoveryAction, float]
    ]:
        """Expose policy probabilities for testing and diagnostics."""

        eligible_candidates = [
            action
            for action in candidates
            if self._is_eligible(
                state,
                action,
            )
        ]

        scores = [
            self._score_action(
                state,
                action,
            )
            for action in eligible_candidates
        ]

        probabilities = (
            self._add_exploration_floor(
                self._softmax(scores)
            )
        )

        return list(
            zip(
                eligible_candidates,
                probabilities,
            )
        )

    def _is_eligible(
        self,
        state: RecoveryDecisionState,
        action: RecoveryAction,
    ) -> bool:
        """Apply basic historical policy eligibility."""

        if action.action_type == ActionType.NO_ACTION:
            return True

        if action.action_type == ActionType.NUDGE:

            return (
                state.contact_consent
                and not state.customer_active
            )

        if action.action_type == ActionType.SWITCH_METHOD:

            return (
                action.target_method
                is not None
                and action.target_method
                != state.current_method
            )

        if (
            action.action_type
            == ActionType.APPROVED_OFFER
        ):
            return (
                action.discount_percent
                is not None
            )

        return False

    def _score_action(
        self,
        state: RecoveryDecisionState,
        action: RecoveryAction,
    ) -> float:
        """Assign an intentionally imperfect observable rule score."""

        if action.action_type == ActionType.NO_ACTION:

            score = 0.80

            if (
                state.failure_category
                == FailureCategory.AUTHENTICATION_FAILURE
            ):
                score += 0.70

            if state.customer_active:
                score += 0.45

            if state.attempt_count <= 1:
                score += 0.25

            return score

        if action.action_type == ActionType.NUDGE:

            score = 0.55

            score += (
                0.60
                * state.prior_success_rate
            )

            if state.amount_ratio > 1.5:
                score += 0.20

            return score

        if (
            action.action_type
            == ActionType.SWITCH_METHOD
        ):
            score = 0.30

            if state.failure_category in {
                FailureCategory.TECHNICAL_FAILURE,
                FailureCategory.BANK_OR_PROVIDER_UNAVAILABLE,
                FailureCategory.INSTRUMENT_UNAVAILABLE,
                FailureCategory.INSUFFICIENT_FUNDS,
                FailureCategory.LIMIT_EXCEEDED,
            }:
                score += 1.10

            if (
                state.failure_category
                == FailureCategory.AUTHENTICATION_FAILURE
            ):
                score -= 0.40

            score += (
                0.25
                * self._target_familiarity(
                    state=state,
                    target_method=(
                        action.target_method
                    ),
                )
            )

            if (
                state.observed_rail_health
                < 0.75
            ):
                score += 0.40

            return score

        if (
            action.action_type
            == ActionType.APPROVED_OFFER
        ):
            score = -0.10

            # An intentionally simplistic historical policy:
            # large Orders get offered discounts more often.
            if state.amount_ratio > 1.25:
                score += 0.45

            if state.amount_ratio > 2.0:
                score += 0.45

            if state.prior_failure_count > 1:
                score += 0.20

            if (
                action.discount_percent
                == 10.0
            ):
                score -= 0.15

            return score

        raise ValueError(
            f"Unsupported action {action.action_type}"
        )

    @staticmethod
    def _target_familiarity(
        state: RecoveryDecisionState,
        target_method: PaymentMethod,
    ) -> float:

        counts = {
            PaymentMethod.UPI:
                state.prior_upi_count,

            PaymentMethod.CREDIT_CARD:
                state.prior_credit_card_count,

            PaymentMethod.DEBIT_CARD:
                state.prior_debit_card_count,

            PaymentMethod.NETBANKING:
                state.prior_netbanking_count,
        }

        total = sum(
            counts.values()
        )

        if total == 0:
            return 0.0

        return (
            counts[target_method]
            / total
        )

    @staticmethod
    def _softmax(
        scores: list[float],
    ) -> list[float]:

        max_score = max(scores)

        exponentials = [
            math.exp(
                score - max_score
            )
            for score in scores
        ]

        denominator = sum(
            exponentials
        )

        return [
            value / denominator
            for value in exponentials
        ]

    @staticmethod
    def _add_exploration_floor(
        probabilities: list[float],
    ) -> list[float]:
        """
        Preserve treatment overlap so uncommon actions remain observable.
        """

        exploration = 0.05

        action_count = len(
            probabilities
        )

        uniform_probability = (
            1.0 / action_count
        )

        return [
            (
                (1.0 - exploration)
                * probability
                + exploration
                * uniform_probability
            )
            for probability
            in probabilities
        ]