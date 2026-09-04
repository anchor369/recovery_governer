from datetime import datetime, timezone

from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.history_generator import HistoricalJourneyGenerator
from simulator.models import PaymentStatus
from simulator.payment_engine import PaymentEngine
from simulator.payment_environment import (
    PaymentEnvironmentGenerator,
)
from simulator.random_source import RandomSource
from dataclasses import replace

from simulator.models import (
    FailureCategory,
    IncidentMode,
    PaymentAttempt,
    PaymentStatus,
)
from simulator.payment_environment import PaymentEnvironment

REFERENCE_TIME = datetime(
    2026,
    9,
    4,
    tzinfo=timezone.utc,
)


def build_attempt(seed: int = 42):
    config = SimulatorConfig()
    random_source = RandomSource(seed)

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
        return build_attempt(seed + 1)

    journey = history[0]
    attempt = journey.payment_attempts[0]

    environment_generator = (
        PaymentEnvironmentGenerator(
            config,
            random_source,
        )
    )

    environment = (
        environment_generator.get_environment(
            attempt.method,
            attempt.attempted_at,
        )
    )

    engine = PaymentEngine(
        config,
        random_source,
    )

    return (
        customer,
        journey,
        attempt,
        environment,
        engine,
    )


def test_processed_attempt_does_not_remain_created():
    customer, journey, attempt, environment, engine = (
        build_attempt()
    )

    engine.process_attempt(
        customer,
        journey,
        attempt,
        environment,
    )

    assert attempt.status != PaymentStatus.CREATED


def test_captured_payment_has_no_failure_information():
    for seed in range(100, 500):
        (
            customer,
            journey,
            attempt,
            environment,
            engine,
        ) = build_attempt(seed)

        engine.process_attempt(
            customer,
            journey,
            attempt,
            environment,
        )

        if attempt.status == PaymentStatus.CAPTURED:
            assert attempt.failure_category is None
            assert attempt.failure_detail is None
            assert attempt.failure_source is None
            assert attempt.failure_step is None


def test_failed_payment_has_failure_category():
    failure_found = False

    for seed in range(100, 1000):
        (
            customer,
            journey,
            attempt,
            environment,
            engine,
        ) = build_attempt(seed)

        engine.process_attempt(
            customer,
            journey,
            attempt,
            environment,
        )

        if attempt.status == PaymentStatus.FAILED:
            failure_found = True
            assert attempt.failure_category is not None

    assert failure_found

def test_nearby_attempts_share_payment_environment():
    config = SimulatorConfig()
    random_source = RandomSource(42)

    environment_generator = (
        PaymentEnvironmentGenerator(
            config,
            random_source,
        )
    )

    from simulator.models import PaymentMethod

    first_time = datetime(
        2026,
        9,
        4,
        18,
        31,
        tzinfo=timezone.utc,
    )

    second_time = datetime(
        2026,
        9,
        4,
        18,
        34,
        tzinfo=timezone.utc,
    )

    first = environment_generator.get_environment(
        PaymentMethod.UPI,
        first_time,
    )

    second = environment_generator.get_environment(
        PaymentMethod.UPI,
        second_time,
    )

    assert first == second

def test_insufficient_funds_can_persist_on_same_method_retry():
    config = replace(
        SimulatorConfig(),
        insufficient_funds_persistence=1.0,
    )

    random_source = RandomSource(42)

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

    first_attempt = journey.payment_attempts[0]

    first_attempt.status = PaymentStatus.FAILED
    first_attempt.failure_category = (
        FailureCategory.INSUFFICIENT_FUNDS
    )
    first_attempt.failure_detail = (
        "INSUFFICIENT_BANK_BALANCE"
    )
    first_attempt.failure_source = (
        "CUSTOMER_BANK"
    )
    first_attempt.failure_step = (
        "PAYMENT_PROCESSING"
    )

    second_attempt = PaymentAttempt(
        payment_id=f"{journey.order_id}_P02",
        attempt_number=2,
        method=first_attempt.method,
        attempted_at=first_attempt.attempted_at,
    )

    journey.payment_attempts.append(
        second_attempt
    )

    environment = PaymentEnvironment(
        method=second_attempt.method,
        true_health=1.0,
        observed_health=1.0,
        incident_mode=IncidentMode.NONE,
    )

    engine = PaymentEngine(
        config,
        random_source,
    )

    engine.process_attempt(
        customer=customer,
        journey=journey,
        attempt=second_attempt,
        environment=environment,
    )

    assert (
        second_attempt.status
        == PaymentStatus.FAILED
    )

    assert (
        second_attempt.failure_category
        == FailureCategory.INSUFFICIENT_FUNDS
    )