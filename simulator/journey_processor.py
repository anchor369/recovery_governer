"""
Runs payment mechanics for synthetic checkout journeys.

This layer connects generated journeys with infrastructure state and the
payment engine without mixing those responsibilities into the generators.
"""

from simulator import random_source
from simulator.config import SimulatorConfig
from simulator.models import (
    HistoricalJourney,
    SyntheticCustomer,
)
from simulator.payment_engine import PaymentEngine
from simulator.payment_environment import (
    PaymentEnvironment,
    PaymentEnvironmentGenerator,
)
from simulator.random_source import RandomSource

from simulator.natural_recovery import NaturalRecoveryEngine
from simulator.models import PaymentStatus


class JourneyProcessor:
    """Processes payment attempts belonging to synthetic journeys."""

    def __init__(
        self,
        config: SimulatorConfig,
        random_source: RandomSource,
    ):
        self.config = config
        self.random = random_source

        self.environment_generator = (
            PaymentEnvironmentGenerator(
                config=config,
                random_source=random_source,
            )
        )

        self.payment_engine = PaymentEngine(
            config=config,
            random_source=random_source,
        )

        self.natural_recovery = NaturalRecoveryEngine(
            config=config,
            random_source=random_source,
        )

    def process_initial_attempt(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
    ) -> PaymentEnvironment:
        """
        Process the first payment attempt of a historical journey.

        Returns the hidden environment only for simulator evaluation and
        debugging. It must not become an ML feature.
        """

        if not journey.payment_attempts:
            raise ValueError(
                "Journey does not contain a payment attempt."
            )

        first_attempt = journey.payment_attempts[0]

        return self.process_attempt(
            customer=customer,
            journey=journey,
            attempt=first_attempt,
        )

    def process_natural_recovery(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
    ) -> None:
        """
        Continue an unpaid journey without merchant intervention.

        This represents the NO_ACTION counterfactual.
        """

        while True:

            latest_attempt = (
                journey.payment_attempts[-1]
            )

            if (
                latest_attempt.status
                == PaymentStatus.CAPTURED
            ):
                if latest_attempt.attempt_number > 1:
                    journey.naturally_recovered = True

                return

            if (
                latest_attempt.status
                == PaymentStatus.UNCERTAIN
            ):
                # Recovery must wait for authoritative truth.
                return

            action = (
                self.natural_recovery.choose_next_action(
                    customer=customer,
                    journey=journey,
                )
            )

            next_attempt = (
                self.natural_recovery.create_next_attempt(
                    customer=customer,
                    journey=journey,
                    action=action,
                )
            )

            if next_attempt is None:
                return

            elapsed_seconds = (
                next_attempt.attempted_at
                - journey.created_at
            ).total_seconds()

            if (
                elapsed_seconds
                > self.config.natural_recovery_window_seconds
            ):
                journey.abandoned = True
                return

            environment = (
                self.environment_generator.get_environment(
                    method=next_attempt.method,
                    attempted_at=next_attempt.attempted_at,
                )
            )

            self.payment_engine.process_attempt(
                customer=customer,
                journey=journey,
                attempt=next_attempt,
                environment=environment,
            )

    def process_attempt(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
        attempt,
    ):
        """
        Process any payment attempt using the infrastructure state at its time.
        """

        environment = (
            self.environment_generator.get_environment(
                method=attempt.method,
                attempted_at=attempt.attempted_at,
            )
        )

        self.payment_engine.process_attempt(
            customer=customer,
            journey=journey,
            attempt=attempt,
            environment=environment,
        )

        return environment