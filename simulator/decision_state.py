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

from statistics import median


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

        decision_time = current_attempt.attempted_at

        known_prior_journeys = [
            journey
            for journey in prior_journeys
            if journey.created_at < decision_time
        ]

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
            known_prior_journeys
        )

        prior_success_count = sum(
            self._journey_paid_before(
                journey,
                decision_time,
            )
            for journey in known_prior_journeys
        )

        prior_failure_count = sum(
            self._journey_failed_before(
                journey,
                decision_time,
            )
            for journey in known_prior_journeys
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

        for journey in known_prior_journeys:

            if not journey.payment_attempts:
                continue

            method = (
                journey.payment_attempts[0].method
            )

            method_counts[method] += 1

        method_history = self._build_method_history(
            prior_journeys=known_prior_journeys,
            decision_time=decision_time,
        )

        amount_ratio = self._observable_amount_ratio(
            current_amount_minor=current_journey.amount_minor,
            prior_journeys=known_prior_journeys,
        )

        customer_active = (
            self._sample_customer_activity(
                customer=customer,
                journey=current_journey,
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

            prior_upi_attempt_count=(
                method_history[
                    PaymentMethod.UPI
                ]["attempt_count"]
            ),

            prior_upi_success_count=(
                method_history[
                    PaymentMethod.UPI
                ]["success_count"]
            ),

            prior_upi_success_rate=(
                method_history[
                    PaymentMethod.UPI
                ]["success_rate"]
            ),

            prior_credit_card_attempt_count=(
                method_history[
                    PaymentMethod.CREDIT_CARD
                ]["attempt_count"]
            ),

            prior_credit_card_success_count=(
                method_history[
                    PaymentMethod.CREDIT_CARD
                ]["success_count"]
            ),

            prior_credit_card_success_rate=(
                method_history[
                    PaymentMethod.CREDIT_CARD
                ]["success_rate"]
            ),

            prior_debit_card_attempt_count=(
                method_history[
                    PaymentMethod.DEBIT_CARD
                ]["attempt_count"]
            ),

            prior_debit_card_success_count=(
                method_history[
                    PaymentMethod.DEBIT_CARD
                ]["success_count"]
            ),

            prior_debit_card_success_rate=(
                method_history[
                    PaymentMethod.DEBIT_CARD
                ]["success_rate"]
            ),

            prior_netbanking_attempt_count=(
                method_history[
                    PaymentMethod.NETBANKING
                ]["attempt_count"]
            ),

            prior_netbanking_success_count=(
                method_history[
                    PaymentMethod.NETBANKING
                ]["success_count"]
            ),

            prior_netbanking_success_rate=(
                method_history[
                    PaymentMethod.NETBANKING
                ]["success_rate"]
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
    def _known_attempts_before(
        journey: HistoricalJourney,
        decision_time,
    ):
        return [
            attempt
            for attempt in journey.payment_attempts
            if attempt.attempted_at < decision_time
        ]


    @classmethod
    def _build_method_history(
        cls,
        prior_journeys: list[HistoricalJourney],
        decision_time,
    ):
        method_history = {
            method: {
                "attempt_count": 0,
                "resolved_count": 0,
                "success_count": 0,
                "success_rate": 0.0,
            }
            for method in PaymentMethod
        }

        for journey in prior_journeys:

            known_attempts = cls._known_attempts_before(
                journey,
                decision_time,
            )

            for attempt in known_attempts:

                stats = method_history[
                    attempt.method
                ]

                stats["attempt_count"] += 1

                if attempt.status in (
                    PaymentStatus.CAPTURED,
                    PaymentStatus.FAILED,
                ):
                    stats["resolved_count"] += 1

                if (
                    attempt.status
                    == PaymentStatus.CAPTURED
                ):
                    stats["success_count"] += 1

        for stats in method_history.values():

            if stats["resolved_count"] > 0:
                stats["success_rate"] = (
                    stats["success_count"]
                    / stats["resolved_count"]
                )

        return method_history

    @classmethod
    def _journey_paid_before(
        cls,
        journey: HistoricalJourney,
        decision_time,
    ) -> bool:

        known_attempts = cls._known_attempts_before(
            journey,
            decision_time,
        )

        return any(
            attempt.status == PaymentStatus.CAPTURED
            for attempt in known_attempts
        )

    @classmethod
    def _journey_failed_before(
        cls,
        journey: HistoricalJourney,
        decision_time,
    ) -> bool:

        known_attempts = cls._known_attempts_before(
            journey,
            decision_time,
        )

        if not known_attempts:
            return False

        if any(
            attempt.status == PaymentStatus.CAPTURED
            for attempt in known_attempts
        ):
            return False

        return (
            known_attempts[-1].status
            == PaymentStatus.FAILED
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

    @staticmethod
    def _observable_amount_ratio(
        current_amount_minor: int,
        prior_journeys: list[HistoricalJourney],
    ) -> float:

        if not prior_journeys:
            return 1.0

        prior_amounts = [
            journey.amount_minor
            for journey in prior_journeys
        ]

        historical_median = median(
            prior_amounts
        )

        if historical_median <= 0:
            return 1.0

        return (
            current_amount_minor
            / historical_median
        )