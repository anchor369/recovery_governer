"""
Payment-safe economic Recovery Governor.

The Governor scores only policy-eligible actions using the learned
counterfactual recovery model and chooses the action with the highest
positive incremental merchant value.
"""

from dataclasses import asdict, dataclass

import pandas as pd

from policy.economics import (
    MerchantEconomics,
    expected_merchant_value_minor,
)
from simulator.models import (
    ActionType,
    PaymentMethod,
    RecoveryAction,
    RecoveryDecisionState,
)


@dataclass(frozen=True)
class ScoredRecoveryAction:
    action: RecoveryAction

    predicted_recovery_probability: float

    expected_value_minor: float
    incremental_utility_minor: float


@dataclass(frozen=True)
class GovernorDecision:
    chosen_action: RecoveryAction
    scores: tuple[ScoredRecoveryAction, ...]


class RecoveryGovernor:
    """
    Combine causal recovery predictions, economics and deterministic policy.
    """

    def __init__(
        self,
        learner,
        economics: MerchantEconomics,
        max_payment_attempts: int = 6,
        minimum_incremental_utility_minor: float = 0.0,
    ):
        self.learner = learner
        self.economics = economics
        self.minimum_incremental_utility_minor = (minimum_incremental_utility_minor)
        self.max_payment_attempts = (
            max_payment_attempts
        )

    def decide(
        self,
        state: RecoveryDecisionState,
        candidates: list[RecoveryAction],
    ) -> GovernorDecision:
        """
        Score eligible actions and choose positive incremental utility.
        """

        eligible_actions = [
            action
            for action in candidates
            if self._is_allowed(
                state=state,
                action=action,
            )
        ]

        no_action = next(
            (
                action
                for action in eligible_actions
                if action.action_type
                == ActionType.NO_ACTION
            ),
            None,
        )

        if no_action is None:
            raise ValueError(
                "NO_ACTION must always be available."
            )

        state_frame = self._state_frame(
            state
        )

        preliminary_scores = []

        for action in eligible_actions:

            treatment = (
                self._action_label(
                    action
                )
            )

            probability = float(
                self.learner.predict_treatment(
                    dataframe=state_frame,
                    treatment=treatment,
                )[0]
            )

            expected_value = (
                expected_merchant_value_minor(
                    state=state,
                    action=action,
                    recovery_probability=probability,
                    economics=self.economics,
                )
            )

            preliminary_scores.append(
                (
                    action,
                    probability,
                    expected_value,
                )
            )

        no_action_expected_value = next(
            expected_value
            for (
                action,
                _,
                expected_value,
            )
            in preliminary_scores
            if action.action_type
            == ActionType.NO_ACTION
        )

        scored_actions = []

        for (
            action,
            probability,
            expected_value,
        ) in preliminary_scores:

            incremental_utility = (
                expected_value
                - no_action_expected_value
            )

            scored_actions.append(
                ScoredRecoveryAction(
                    action=action,
                    predicted_recovery_probability=(
                        probability
                    ),
                    expected_value_minor=(
                        expected_value
                    ),
                    incremental_utility_minor=(
                        incremental_utility
                    ),
                )
            )

        best_score = max(
            scored_actions,
            key=lambda score:
                score.incremental_utility_minor,
        )

        # NO_ACTION has utility exactly zero relative to itself.
        # Therefore negative-value interventions can never win.
        if (
            best_score.incremental_utility_minor
            <= self.minimum_incremental_utility_minor
        ):
            chosen_action = no_action
        else:
            chosen_action = (
                best_score.action
            )

        return GovernorDecision(
            chosen_action=chosen_action,
            scores=tuple(
                scored_actions
            ),
        )

    def _is_allowed(
        self,
        state: RecoveryDecisionState,
        action: RecoveryAction,
    ) -> bool:
        """Apply deterministic payment and merchant policy constraints."""

        if (
            action.action_type
            == ActionType.NO_ACTION
        ):
            return True

        if (
            state.attempt_count
            >= self.max_payment_attempts
        ):
            return False

        if (
            action.action_type
            == ActionType.NUDGE
        ):
            return (
                state.contact_consent
                and not state.customer_active
            )

        if (
            action.action_type
            == ActionType.SWITCH_METHOD
        ):
            target = (
                action.target_method
            )

            if (
                target is None
                or target == state.current_method
            ):
                return False

            availability = {
                PaymentMethod.UPI:
                    state.available_upi,

                PaymentMethod.CREDIT_CARD:
                    state.available_credit_card,

                PaymentMethod.DEBIT_CARD:
                    state.available_debit_card,

                PaymentMethod.NETBANKING:
                    state.available_netbanking,
            }

            return availability[
                target
            ]

        if (
            action.action_type
            == ActionType.APPROVED_OFFER
        ):
            discount = (
                action.discount_percent
            )

            return (
                discount is not None
                and discount > 0.0
                and discount
                <= self.economics
                .merchant_offer_cap_percent
            )

        return False

    @staticmethod
    def _state_frame(
        state: RecoveryDecisionState,
    ) -> pd.DataFrame:
        """Convert observable decision state into model input."""

        row = asdict(
            state
        )

        row[
            "current_method"
        ] = state.current_method.value

        row[
            "failure_category"
        ] = state.failure_category.value

        return pd.DataFrame(
            [row]
        )

    @staticmethod
    def _action_label(
        action: RecoveryAction,
    ) -> str:

        if (
            action.action_type
            == ActionType.SWITCH_METHOD
        ):
            return (
                "SWITCH_"
                + action.target_method.value
            )

        if (
            action.action_type
            == ActionType.APPROVED_OFFER
        ):
            return (
                "OFFER_"
                + str(
                    int(
                        action.discount_percent
                    )
                )
            )

        return action.action_type.value