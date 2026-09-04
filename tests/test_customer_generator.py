import numpy as np

from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.random_source import RandomSource


def build_population(size: int):
    config = SimulatorConfig()

    random_source = RandomSource(config.random_seed)

    generator = CustomerGenerator(
        config=config,
        random_source=random_source,
    )

    return [
        generator.generate_customer()
        for _ in range(size)
    ]


def test_customer_hidden_traits_stay_between_zero_and_one():
    customers = build_population(5000)

    for customer in customers:
        assert 0.0 <= customer.merchant_affinity <= 1.0
        assert 0.0 <= customer.retry_persistence <= 1.0
        assert 0.0 <= customer.method_flexibility <= 1.0
        assert 0.0 <= customer.price_sensitivity <= 1.0


def test_customer_order_values_respect_configured_bounds():
    config = SimulatorConfig()
    customers = build_population(5000)

    minimum_minor = round(
        config.min_typical_order_rupees * 100
    )

    maximum_minor = round(
        config.max_typical_order_rupees * 100
    )

    for customer in customers:
        assert (
            minimum_minor
            <= customer.typical_order_value_minor
            <= maximum_minor
        )


def test_customer_population_has_expected_trait_means():
    customers = build_population(20000)

    affinity_mean = np.mean([
        customer.merchant_affinity
        for customer in customers
    ])

    retry_mean = np.mean([
        customer.retry_persistence
        for customer in customers
    ])

    flexibility_mean = np.mean([
        customer.method_flexibility
        for customer in customers
    ])

    price_sensitivity_mean = np.mean([
        customer.price_sensitivity
        for customer in customers
    ])

    assert 0.58 <= affinity_mean <= 0.62
    assert 0.43 <= retry_mean <= 0.48
    assert 0.48 <= flexibility_mean <= 0.52
    assert 0.42 <= price_sensitivity_mean <= 0.47


def test_checkout_rate_population_mean_is_reasonable():
    customers = build_population(20000)

    mean_checkout_rate = np.mean([
        customer.checkout_rate_per_year
        for customer in customers
    ])

    assert 4.7 <= mean_checkout_rate <= 5.3


def test_same_seed_generates_same_customers():
    first_population = build_population(20)
    second_population = build_population(20)

    assert first_population == second_population