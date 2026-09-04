"""
Builds observable recovery-decision state from synthetic factual history.

Hidden simulator variables may influence how observable behaviour is
generated, but they are never copied directly into the decision state.
"""

from simulator.models import (
    HistoricalJourney,
    PaymentMethod,
    PaymentStatus,
    RecoveryDecisionState,
    SyntheticCustomer,
)
from simulator.random_source import RandomSource
from simulator.method_selector import PaymentMethodSelector


class RecoveryDecisionStateBuilder:
    """Creates the observable state available at recovery decision time."""

    def __init__(
        self,
        random_source: RandomSource,
        method_selector: PaymentMethodSelector,
    ):
        self.random = random_source
        self.method_selector = method_selector

    def build(
        self,
        customer: SyntheticCustomer,
        current_journey: HistoricalJourney,
        prior_journeys: list[HistoricalJourney],
    ) -> RecoveryDecisionState:

        current_attempt = (
            current_journey.payment_attempts[-1]
        )

        if current_attempt.status != PaymentStatus.FAILED:
            raise ValueError(
                "Recovery decision state requires a confirmed failure."
            )

        available_methods = (
            self.method_selector.get_available_methods(
                customer
            )
        )

        prior_checkout_count = len(
            prior_journeys
        )

        prior_success_count = sum(
            self._journey_paid(journey)
            for journey in prior_journeys
        )

        prior_failure_count = (
            prior_checkout_count
            - prior_success_count
        )

        if prior_checkout_count == 0:
            prior_success_rate = 0.0
        else:
            prior_success_rate = (
                prior_success_count
                / prior_checkout_count
            )

        method_counts = {
            PaymentMethod.UPI: 0,
            PaymentMethod.CREDIT_CARD: 0,
            PaymentMethod.DEBIT_CARD: 0,
            PaymentMethod.NETBANKING: 0,
        }

        for journey in prior_journeys:

            if not journey.payment_attempts:
                continue

            method = (
                journey.payment_attempts[0].method
            )

            method_counts[method] += 1

        amount_ratio = (
            current_journey.amount_minor
            / customer.typical_order_value_minor
        )

        customer_active = (
            self._sample_customer_activity(
                customer=customer,
                journey=current_journey,
            )
        )
        available_methods = (
            self.method_selector.get_available_methods(
                customer
            )
        )

        return RecoveryDecisionState(
            customer_tenure_days=(
                customer.created_at_days_ago
            ),

            prior_checkout_count=(
                prior_checkout_count
            ),

            prior_success_count=(
                prior_success_count
            ),

            prior_failure_count=(
                prior_failure_count
            ),

            prior_success_rate=(
                prior_success_rate
            ),

            prior_upi_count=(
                method_counts[
                    PaymentMethod.UPI
                ]
            ),

            prior_credit_card_count=(
                method_counts[
                    PaymentMethod.CREDIT_CARD
                ]
            ),

            prior_debit_card_count=(
                method_counts[
                    PaymentMethod.DEBIT_CARD
                ]
            ),

            prior_netbanking_count=(
                method_counts[
                    PaymentMethod.NETBANKING
                ]
            ),

            available_upi=(
                PaymentMethod.UPI
                in available_methods
            ),

            available_credit_card=(
                PaymentMethod.CREDIT_CARD
                in available_methods
            ),

            available_debit_card=(
                PaymentMethod.DEBIT_CARD
                in available_methods
            ),

            available_netbanking=(
                PaymentMethod.NETBANKING
                in available_methods
            ),

            current_amount_minor=(
                current_journey.amount_minor
            ),

            amount_ratio=amount_ratio,

            current_method=(
                current_attempt.method
            ),

            failure_category=(
                current_attempt.failure_category
            ),

            attempt_count=(
                current_attempt.attempt_number
            ),

            observed_rail_health=(
                current_attempt.observed_rail_health
            ),

            contact_consent=(
                customer.contact_consent
            ),

            customer_active=(
                customer_active
            ),
        )

    @staticmethod
    def _journey_paid(
        journey: HistoricalJourney,
    ) -> bool:

        return any(
            attempt.status
            == PaymentStatus.CAPTURED
            for attempt
            in journey.payment_attempts
        )

    def _sample_customer_activity(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
    ) -> bool:
        """
        Generate whether the customer is still visibly active after failure.

        Hidden behaviour generates this observable state, but the hidden
        behaviour itself will not become an ML feature.
        """

        activity_probability = (
            0.20
            + 0.40
            * journey.latent_order_propensity
            + 0.25
            * customer.retry_persistence
        )

        activity_probability = max(
            0.05,
            min(
                0.90,
                activity_probability,
            ),
        )

        return self.random.bernoulli(
            activity_probability
        )