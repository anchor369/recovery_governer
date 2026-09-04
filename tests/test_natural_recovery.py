from datetime import datetime, timezone

from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.history_generator import HistoricalJourneyGenerator
from simulator.journey_processor import JourneyProcessor
from simulator.models import PaymentStatus
from simulator.random_source import RandomSource


REFERENCE_TIME = datetime(
    2026,
    9,
    4,
    tzinfo=timezone.utc,
)


def test_natural_recovery_never_exceeds_attempt_limit():
    config = SimulatorConfig()
    random_source = RandomSource(42)

    customer_generator = CustomerGenerator(
        config=config,
        random_source=random_source,
    )

    history_generator = HistoricalJourneyGenerator(
        config=config,
        random_source=random_source,
        reference_time=REFERENCE_TIME,
    )

    processor = JourneyProcessor(
        config=config,
        random_source=random_source,
    )

    for _ in range(1000):

        customer = (
            customer_generator.generate_customer()
        )

        history = history_generator.generate_history(
            customer
        )

        for journey in history:

            processor.process_initial_attempt(
                customer,
                journey,
            )

            if (
                journey.payment_attempts[0].status
                != PaymentStatus.FAILED
            ):
                continue

            processor.process_natural_recovery(
                customer,
                journey,
            )

            assert (
                len(journey.payment_attempts)
                <= config.max_payment_attempts
            )


def test_natural_recovery_does_not_act_on_uncertain_payment():
    config = SimulatorConfig()
    random_source = RandomSource(50)

    customer = CustomerGenerator(
        config,
        random_source,
    ).generate_customer()

    history = HistoricalJourneyGenerator(
        config,
        random_source,
        REFERENCE_TIME,
    ).generate_history(customer)

    if not history:
        return

    journey = history[0]

    journey.payment_attempts[0].status = (
        PaymentStatus.UNCERTAIN
    )

    original_attempt_count = len(
        journey.payment_attempts
    )

    processor = JourneyProcessor(
        config,
        random_source,
    )

    processor.process_natural_recovery(
        customer,
        journey,
    )

    assert (
        len(journey.payment_attempts)
        == original_attempt_count
    )