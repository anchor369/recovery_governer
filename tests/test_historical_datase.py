from datetime import datetime, timezone

from simulator.config import SimulatorConfig
from simulator.historical_dataset import (
    HistoricalDatasetGenerator,
)
from simulator.random_source import RandomSource


REFERENCE_TIME = datetime(
    2026,
    9,
    4,
    tzinfo=timezone.utc,
)


def generate_small_dataset():
    config = SimulatorConfig()

    generator = HistoricalDatasetGenerator(
        config=config,
        random_source=RandomSource(42),
        reference_time=REFERENCE_TIME,
    )

    return generator.generate_rows(
        target_rows=25
    )


def test_hidden_simulator_variables_do_not_leak_into_rows():
    rows = generate_small_dataset()

    hidden_variables = {
        "merchant_affinity",
        "retry_persistence",
        "method_flexibility",
        "price_sensitivity",
        "latent_order_propensity",
        "base_order_motivation",
        "true_rail_health",
    }

    for row in rows:
        assert hidden_variables.isdisjoint(
            row.keys()
        )


def test_observational_row_contains_one_valid_treatment():
    rows = generate_small_dataset()

    for row in rows:
        assert row["treatment"]
        assert row["action_type"]

        assert (
            0.0
            < row["behavior_policy_probability"]
            <= 1.0
        )


def test_recovered_is_binary():
    rows = generate_small_dataset()

    for row in rows:
        assert row["recovered"] in {
            0,
            1,
        }