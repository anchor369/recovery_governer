from datetime import datetime, timezone

from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.history_generator import (
    HistoricalJourneyGenerator,
)
from simulator.journey_processor import JourneyProcessor
from simulator.models import PaymentStatus
from simulator.random_source import RandomSource


REFERENCE_TIME = datetime(
    2026,
    9,
    4,
    tzinfo=timezone.utc,
)


def test_journey_processor_resolves_initial_payment_attempt():
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

    processed_attempt_found = False

    for _ in range(100):
        customer = customer_generator.generate_customer()

        history = history_generator.generate_history(
            customer
        )

        if not history:
            continue

        journey = history[0]

        processor.process_initial_attempt(
            customer=customer,
            journey=journey,
        )

        attempt = journey.payment_attempts[0]

        assert attempt.status != PaymentStatus.CREATED
        assert attempt.observed_rail_health is not None

        processed_attempt_found = True
        break

    assert processed_attempt_found