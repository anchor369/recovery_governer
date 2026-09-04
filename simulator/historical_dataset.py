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
    PaymentStatus,
)
from simulator.random_source import RandomSource
from simulator.action_codec import (
    action_to_label,
)
from simulator.state_codec import (
    decision_state_to_model_row,
)

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

        state_features = (
            decision_state_to_model_row(
                state
            )
        )

        return {
            # Metadata used for audit / splitting.
            "decision_id": (
                f"D{self.decision_counter:07d}"
            ),

            "customer_id":
                customer.customer_id,

            "order_id":
                journey.order_id,

            "prediction_time": (
                first_attempt
                .attempted_at
                .isoformat()
            ),

            # Canonical observable model state.
            **state_features,

            # Historical treatment.
            "treatment":
                action_to_label(
                    action
                ),

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
                    observed_result
                    .payment_attempts
                ),

            "final_payment_status":
                final_attempt.status.value,
        }