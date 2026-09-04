"""
Generates observational historical recovery data.

Each row represents one recovery decision after a confirmed payment
failure. The historical policy chooses exactly one action and only the
outcome of that chosen action becomes observable.
"""

from datetime import datetime

from simulator.action_candidates import ActionCandidateGenerator
from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.decision_state import RecoveryDecisionStateBuilder
from simulator.history_generator import HistoricalJourneyGenerator
from simulator.historical_policy import HistoricalRecoveryPolicy
from simulator.intervention_engine import InterventionEngine
from simulator.journey_processor import JourneyProcessor
from simulator.method_selector import PaymentMethodSelector
from simulator.models import (
    ActionType,
    PaymentStatus,
    RecoveryAction,
)
from simulator.random_source import RandomSource


class HistoricalDatasetGenerator:
    """Generate biased observational treatment data for ML training."""

    def __init__(
        self,
        config: SimulatorConfig,
        random_source: RandomSource,
        reference_time: datetime,
    ):
        self.config = config
        self.random = random_source

        self.customer_generator = CustomerGenerator(
            config=config,
            random_source=random_source,
        )

        self.history_generator = (
            HistoricalJourneyGenerator(
                config=config,
                random_source=random_source,
                reference_time=reference_time,
            )
        )

        self.processor = JourneyProcessor(
            config=config,
            random_source=random_source,
        )

        self.state_builder = (
            RecoveryDecisionStateBuilder(
                random_source=random_source,
                method_selector=PaymentMethodSelector(
                    config=config,
                    random_source=random_source,
                ),
            )
        )

        self.candidate_generator = (
            ActionCandidateGenerator(
                config=config,
                method_selector=PaymentMethodSelector(
                    config=config,
                    random_source=random_source,
                ),
            )
        )

        self.policy = HistoricalRecoveryPolicy(
            random_source=random_source,
        )

        self.intervention_engine = (
            InterventionEngine(
                config=config,
                random_source=random_source,
                journey_processor=self.processor,
            )
        )

        self.state_builder = RecoveryDecisionStateBuilder(
            random_source=random_source,
            method_selector=PaymentMethodSelector(
                config=config,
                random_source=random_source,
            ),
        )

        self.decision_counter = 0

    def generate_rows(
        self,
        target_rows: int,
    ) -> list[dict]:
        """
        Generate observational recovery rows until target_rows is reached.
        """

        rows = []

        while len(rows) < target_rows:

            customer = (
                self.customer_generator
                .generate_customer()
            )

            generated_history = (
                self.history_generator
                .generate_history(customer)
            )

            # This contains what actually happened historically.
            observed_history = []

            for journey in generated_history:

                self.processor.process_initial_attempt(
                    customer=customer,
                    journey=journey,
                )

                first_attempt = (
                    journey.payment_attempts[0]
                )

                # No recovery decision required.
                if (
                    first_attempt.status
                    == PaymentStatus.CAPTURED
                ):
                    observed_history.append(
                        journey
                    )
                    continue

                # Financial truth unresolved.
                if (
                    first_attempt.status
                    == PaymentStatus.UNCERTAIN
                ):
                    observed_history.append(
                        journey
                    )
                    continue

                # At this point the first payment is a confirmed failure.
                state = self.state_builder.build(
                    customer=customer,
                    current_journey=journey,
                    prior_journeys=observed_history,
                )

                candidates = (
                    self.candidate_generator
                    .generate_candidates(
                        customer=customer,
                        journey=journey,
                    )
                )

                (
                    chosen_action,
                    behavior_probability,
                ) = self.policy.choose_action(
                    state=state,
                    candidates=candidates,
                )

                observed_result = (
                    self.intervention_engine
                    .simulate_action(
                        customer=customer,
                        journey=journey,
                        action=chosen_action,
                    )
                )

                recovered = any(
                    attempt.status
                    == PaymentStatus.CAPTURED
                    for attempt
                    in observed_result.payment_attempts
                )

                self.decision_counter += 1

                row = self._build_row(
                    customer=customer,
                    journey=journey,
                    state=state,
                    action=chosen_action,
                    behavior_probability=(
                        behavior_probability
                    ),
                    recovered=recovered,
                    observed_result=observed_result,
                )

                rows.append(row)

                # Future journeys must see what ACTUALLY happened under
                # the chosen historical action, not the unused branch.
                observed_history.append(
                    observed_result
                )

                if len(rows) >= target_rows:
                    break

        return rows

    def _build_row(
        self,
        customer,
        journey,
        state,
        action,
        behavior_probability,
        recovered,
        observed_result,
    ) -> dict:
        """Convert one observed decision into a flat ML dataset row."""

        first_attempt = (
            journey.payment_attempts[0]
        )

        final_attempt = (
            observed_result.payment_attempts[-1]
        )

        

        return {
            # Metadata: retain for audit/splitting, not model features.
            "decision_id": (
                f"D{self.decision_counter:07d}"
            ),
            "customer_id": customer.customer_id,
            "order_id": journey.order_id,
            "prediction_time": (
                first_attempt.attempted_at.isoformat()
            ),

            # Observable pre-treatment features.
            "customer_tenure_days":
                state.customer_tenure_days,

            "prior_checkout_count":
                state.prior_checkout_count,

            "prior_success_count":
                state.prior_success_count,

            "prior_failure_count":
                state.prior_failure_count,

            "prior_success_rate":
                state.prior_success_rate,

            "prior_upi_count":
                state.prior_upi_count,

            "prior_credit_card_count":
                state.prior_credit_card_count,

            "prior_debit_card_count":
                state.prior_debit_card_count,

            "prior_netbanking_count":
                state.prior_netbanking_count,

            "available_upi":
                int(state.available_upi),

            "available_credit_card":
                int(state.available_credit_card),

            "available_debit_card":
                int(state.available_debit_card),

            "available_netbanking":
                int(state.available_netbanking),

            "current_amount_minor":
                state.current_amount_minor,

            "amount_ratio":
                state.amount_ratio,

            "current_method":
                state.current_method.value,

            "failure_category":
                state.failure_category.value,

            "attempt_count":
                state.attempt_count,

            "observed_rail_health":
                state.observed_rail_health,

            "contact_consent":
                int(state.contact_consent),

            "customer_active":
                int(state.customer_active),

            # Historical treatment.
            "treatment":
                self._action_label(action),

            "action_type":
                action.action_type.value,

            "target_method": (
                action.target_method.value
                if action.target_method
                is not None
                else ""
            ),

            "discount_percent": (
                action.discount_percent
                if action.discount_percent
                is not None
                else ""
            ),

            "behavior_policy_probability":
                behavior_probability,

            # Post-treatment outcomes.
            "recovered":
                int(recovered),

            "final_attempt_count":
                len(
                    observed_result.payment_attempts
                ),

            "final_payment_status":
                final_attempt.status.value,
        }

    @staticmethod
    def _action_label(
        action: RecoveryAction,
    ) -> str:
        """Create one unique treatment label."""

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