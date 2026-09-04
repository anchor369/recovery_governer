from dataclasses import dataclass

from policy.economics import (
    MerchantEconomics,
)

from policy.governor import (
    GovernorDecision,
    RecoveryGovernor,
)

from simulator.models import (
    RecoveryAction,
    RecoveryDecisionState,
)

from backend.services.recovery_candidates import (
    build_structural_candidates,
)

from backend.services.recovery_state import (
    RuntimeRecoverySignals,
    build_recovery_decision_state,
)


@dataclass(frozen=True)
class OperationalRecoveryDecision:
    state: RecoveryDecisionState
    candidates: tuple[RecoveryAction, ...]
    governor_decision: GovernorDecision


class RecoveryDecisionService:
    def __init__(
        self,
        learner,
        economics=None,
        max_payment_attempts=6,
        minimum_incremental_utility_minor=0.0,
    ):
        if economics is None:
            economics = MerchantEconomics()

        self.governor = RecoveryGovernor(
            learner=learner,
            economics=economics,
            max_payment_attempts=(
                max_payment_attempts
            ),
            minimum_incremental_utility_minor=(
                minimum_incremental_utility_minor
            ),
        )

    def decide_from_state(
        self,
        state: RecoveryDecisionState,
        allowed_offer_percentages=(
            5.0,
            10.0,
        ),
    ) -> OperationalRecoveryDecision:

        candidates = (
            build_structural_candidates(
                state=state,
                allowed_offer_percentages=(
                    allowed_offer_percentages
                ),
            )
        )

        governor_decision = (
            self.governor.decide(
                state=state,
                candidates=candidates,
            )
        )

        return OperationalRecoveryDecision(
            state=state,
            candidates=tuple(
                candidates
            ),
            governor_decision=(
                governor_decision
            ),
        )

    def decide_for_order(
        self,
        current_order_id,
        decision_time,
        runtime_signals: RuntimeRecoverySignals,
        allowed_offer_percentages=(
            5.0,
            10.0,
        ),
    ) -> OperationalRecoveryDecision:

        state = build_recovery_decision_state(
            current_order_id=current_order_id,
            decision_time=decision_time,
            runtime_signals=runtime_signals,
        )

        return self.decide_from_state(
            state=state,
            allowed_offer_percentages=(
                allowed_offer_percentages
            ),
        )