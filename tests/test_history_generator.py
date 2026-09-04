from datetime import datetime, timezone, timedelta

import numpy as np

from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.history_generator import (
    HistoricalJourneyGenerator,
)
from simulator.random_source import RandomSource
from simulator.method_selector import PaymentMethodSelector

REFERENCE_TIME = datetime(
    2026,
    9,
    4,
    0,
    0,
    tzinfo=timezone.utc,
)


def build_customer_and_history(seed: int = 42):
    config = SimulatorConfig()
    random_source = RandomSource(seed)

    customer_generator = CustomerGenerator(
        config=config,
        random_source=random_source,
    )

    customer = customer_generator.generate_customer()

    history_generator = HistoricalJourneyGenerator(
        config=config,
        random_source=random_source,
        reference_time=REFERENCE_TIME,
    )

    history = history_generator.generate_history(
        customer
    )

    return customer, history


def test_historical_times_are_before_reference_time():
    customer, history = build_customer_and_history()

    for journey in history:
        assert journey.created_at < REFERENCE_TIME


def test_historical_times_are_sorted():
    customer, history = build_customer_and_history()

    timestamps = [
        journey.created_at
        for journey in history
    ]

    assert timestamps == sorted(timestamps)


def test_historical_times_do_not_precede_customer_creation():
    customer, history = build_customer_and_history()

    customer_created_at = (
        REFERENCE_TIME
        - timedelta(
            days=customer.created_at_days_ago
        )
    )

    for journey in history:
        assert journey.created_at >= customer_created_at


def test_order_amounts_are_positive():
    customer, history = build_customer_and_history()

    for journey in history:
        assert journey.amount_minor > 0


def test_population_checkout_count_matches_expected_rate():
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

    customers = [
        customer_generator.generate_customer()
        for _ in range(10000)
    ]

    actual_counts = []
    expected_counts = []

    for customer in customers:
        history = history_generator.generate_history(
            customer
        )

        actual_counts.append(len(history))

        expected_counts.append(
            customer.checkout_rate_per_year
            * customer.created_at_days_ago
            / 365.0
        )

    assert abs(
        np.mean(actual_counts)
        - np.mean(expected_counts)
    ) < 0.20


def test_historical_amounts_center_around_customer_typical_value():
    config = SimulatorConfig()

    random_source = RandomSource(91)

    customer_generator = CustomerGenerator(
        config=config,
        random_source=random_source,
    )

    history_generator = HistoricalJourneyGenerator(
        config=config,
        random_source=random_source,
        reference_time=REFERENCE_TIME,
    )

    amount_ratios = []

    for _ in range(5000):
        customer = customer_generator.generate_customer()

        history = history_generator.generate_history(
            customer
        )

        for journey in history:
            amount_ratios.append(
                journey.amount_minor
                / customer.typical_order_value_minor
            )

    median_ratio = np.median(amount_ratios)

    assert 0.97 <= median_ratio <= 1.03

def test_each_historical_journey_starts_with_one_payment_attempt():
    customer, history = build_customer_and_history()

    for journey in history:
        assert len(journey.payment_attempts) == 1

        first_attempt = journey.payment_attempts[0]

        assert first_attempt.attempt_number == 1
        assert (
            first_attempt.method
            == journey.initial_method
        )


def test_initial_payment_method_is_available_to_customer():
    config = SimulatorConfig()
    random_source = RandomSource(42)

    customer_generator = CustomerGenerator(
        config,
        random_source,
    )

    method_selector = PaymentMethodSelector(
        config,
        random_source,
    )

    history_generator = HistoricalJourneyGenerator(
        config,
        random_source,
        REFERENCE_TIME,
    )

    for _ in range(1000):
        customer = (
            customer_generator.generate_customer()
        )

        available_methods = (
            method_selector.get_available_methods(
                customer
            )
        )

        history = history_generator.generate_history(
            customer
        )

        for journey in history:
            assert (
                journey.initial_method
                in available_methods
            )

def test_each_historical_journey_starts_with_one_payment_attempt():
    customer, history = build_customer_and_history()

    for journey in history:
        assert len(journey.payment_attempts) == 1

        first_attempt = journey.payment_attempts[0]

        assert first_attempt.attempt_number == 1
        assert (
            first_attempt.method
            == journey.initial_method
        )