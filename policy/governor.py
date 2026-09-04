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

from simulator.action_codec import (
    action_to_label,
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

@dataclass(frozen=True)
class ActionPolicyCheck:
    allowed: bool
    reason: str | None = None


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
                action_to_label(
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

    def check_action_policy(
        self,
        state: RecoveryDecisionState,
        action: RecoveryAction,
    ) -> ActionPolicyCheck:

        if (
            action.action_type
            == ActionType.NO_ACTION
        ):
            return ActionPolicyCheck(
                allowed=True,
            )

        if (
            state.attempt_count
            >= self.max_payment_attempts
        ):
            return ActionPolicyCheck(
                allowed=False,
                reason=(
                    "MAX_PAYMENT_ATTEMPTS_REACHED"
                ),
            )

        if (
            action.action_type
            == ActionType.NUDGE
        ):
            if not state.contact_consent:
                return ActionPolicyCheck(
                    allowed=False,
                    reason=(
                        "CONTACT_CONSENT_MISSING"
                    ),
                )

            if state.customer_active:
                return ActionPolicyCheck(
                    allowed=False,
                    reason=(
                        "CUSTOMER_STILL_ACTIVE"
                    ),
                )

            return ActionPolicyCheck(
                allowed=True,
            )

        if (
            action.action_type
            == ActionType.SWITCH_METHOD
        ):
            target = (
                action.target_method
            )

            if target is None:
                return ActionPolicyCheck(
                    allowed=False,
                    reason=(
                        "TARGET_METHOD_MISSING"
                    ),
                )

            if (
                target
                == state.current_method
            ):
                return ActionPolicyCheck(
                    allowed=False,
                    reason=(
                        "TARGET_EQUALS_CURRENT_METHOD"
                    ),
                )

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

            if not availability[target]:
                return ActionPolicyCheck(
                    allowed=False,
                    reason=(
                        "TARGET_METHOD_UNAVAILABLE"
                    ),
                )

            return ActionPolicyCheck(
                allowed=True,
            )

        if (
            action.action_type
            == ActionType.APPROVED_OFFER
        ):
            discount = (
                action.discount_percent
            )

            if (
                discount is None
                or discount <= 0.0
            ):
                return ActionPolicyCheck(
                    allowed=False,
                    reason=(
                        "INVALID_DISCOUNT"
                    ),
                )

            if (
                discount
                > self.economics
                .merchant_offer_cap_percent
            ):
                return ActionPolicyCheck(
                    allowed=False,
                    reason=(
                        "MERCHANT_OFFER_CAP_EXCEEDED"
                    ),
                )

            return ActionPolicyCheck(
                allowed=True,
            )

        return ActionPolicyCheck(
            allowed=False,
            reason="UNKNOWN_ACTION_TYPE",
        )

    def _is_allowed(
        self,
        state: RecoveryDecisionState,
        action: RecoveryAction,
    ) -> bool:

        return self.check_action_policy(
            state=state,
            action=action,
        ).allowed

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