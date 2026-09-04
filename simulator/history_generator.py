"""
Generates historical checkout journeys for synthetic customers.

Historical journeys are generated only from information that existed
before the current prediction point. Payment attempts and interventions
are added by later simulator components.
"""

from datetime import datetime, timedelta

from simulator.config import SimulatorConfig
from simulator.models import (
    HistoricalJourney,
    PaymentAttempt,
    PaymentStatus,
    SyntheticCustomer,
)
from simulator.random_source import RandomSource
from simulator.method_selector import PaymentMethodSelector
from simulator.order_behavior import OrderBehaviorModel


class HistoricalJourneyGenerator:
    """
    Generates past checkout journeys for synthetic customers.

    Checkout counts follow the customer's checkout rate and tenure.
    Historical Order amounts vary around the customer's typical value.
    """

    def __init__(
        self,
        config: SimulatorConfig,
        random_source: RandomSource,
        reference_time: datetime,
    ):
        self.order_behavior = OrderBehaviorModel(
            config=config,
            random_source=random_source,
        )

        self.method_selector = PaymentMethodSelector(
            config=config,
            random_source=random_source,
        )
        self.config = config
        self.random = random_source
        self.reference_time = reference_time

    def generate_history(
        self,
        customer: SyntheticCustomer,
    ) -> list[HistoricalJourney]:
        """
        Generate historical checkout journeys for one customer.

        The expected checkout count equals the customer's annual checkout
        rate multiplied by the fraction of a year they have existed.
        """

        tenure_years = (
            customer.created_at_days_ago / 365.0
        )

        expected_checkout_count = (
            customer.checkout_rate_per_year
            * tenure_years
        )

        checkout_count = self.random.poisson(
            expected_checkout_count
        )

        if checkout_count == 0:
            return []

        checkout_times = self._generate_checkout_times(
            customer=customer,
            checkout_count=checkout_count,
        )

        journeys = []

        for journey_number, checkout_time in enumerate(
            checkout_times,
            start=1,
        ):
            amount_minor = self._generate_order_amount(
                customer
            )

            base_order_motivation = (
                self.order_behavior.sample_base_motivation()
            )

            latent_order_propensity = (
                self.order_behavior.calculate_propensity(
                    customer=customer,
                    amount_minor=amount_minor,
                    base_motivation=base_order_motivation,
                )
            )

            initial_method = (
                self.method_selector.choose_initial_method(
                    customer=customer,
                    amount_minor=amount_minor,
                )
            )

            first_attempt = PaymentAttempt(
                payment_id=(
                    f"{customer.customer_id}_P"
                    f"{journey_number:04d}_01"
                ),
                attempt_number=1,
                method=initial_method,
                attempted_at=checkout_time,
                status=PaymentStatus.CREATED,
            )

            journey = HistoricalJourney(
                journey_id=(
                    f"{customer.customer_id}_J"
                    f"{journey_number:04d}"
                ),
                order_id=(
                    f"{customer.customer_id}_O"
                    f"{journey_number:04d}"
                ),
                customer_id=customer.customer_id,
                created_at=checkout_time,
                amount_minor=amount_minor,

                base_order_motivation=base_order_motivation,
                latent_order_propensity=latent_order_propensity,

                initial_method=initial_method,
                payment_attempts=[first_attempt],
            )

            journeys.append(journey)

        return journeys

    def _generate_checkout_times(
        self,
        customer: SyntheticCustomer,
        checkout_count: int,
    ) -> list[datetime]:
        """
        Generate historical checkout times within the customer's tenure.

        Conditional on the number of events, uniformly distributed event
        times are consistent with a homogeneous Poisson process.
        """

        tenure_seconds = (
            customer.created_at_days_ago
            * 24
            * 60
            * 60
        )

        seconds_after_creation = self.random.uniform_array(
            low=0.0,
            high=float(tenure_seconds),
            size=checkout_count,
        )

        seconds_after_creation.sort()

        customer_created_at = (
            self.reference_time
            - timedelta(
                days=customer.created_at_days_ago
            )
        )

        return [
            customer_created_at
            + timedelta(seconds=float(seconds))
            for seconds in seconds_after_creation
        ]

    def _generate_order_amount(
        self,
        customer: SyntheticCustomer,
    ) -> int:
        """
        Generate one Order amount around the customer's normal spend.

        A median-one log-normal multiplier gives modest variation while
        retaining occasional larger Orders.
        """

        multiplier = self.random.lognormal(
            mean=0.0,
            sigma=self.config.within_customer_order_sigma,
        )

        amount_minor = round(
            customer.typical_order_value_minor
            * multiplier
        )

        return max(amount_minor, 1)

    