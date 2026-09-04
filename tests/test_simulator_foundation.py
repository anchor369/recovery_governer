from simulator.config import SimulatorConfig
from simulator.random_source import RandomSource


def test_same_seed_produces_same_random_sequence():
    config = SimulatorConfig()

    first_source = RandomSource(config.random_seed)
    second_source = RandomSource(config.random_seed)

    first_values = [
        first_source.beta(3.0, 2.0),
        first_source.gamma(2.0, 2.5),
        first_source.uniform(),
    ]

    second_values = [
        second_source.beta(3.0, 2.0),
        second_source.gamma(2.0, 2.5),
        second_source.uniform(),
    ]

    assert first_values == second_values