"""
Random-number utilities for the simulator.

All stochastic behaviour should use this source instead of creating random
generators independently throughout the project.
"""

import numpy as np


class RandomSource:
    """
    Owns the random-number generator used by one simulator run.

    A fixed seed allows failed simulations and tests to be reproduced.
    """

    def __init__(self, seed: int):
        self.generator = np.random.default_rng(seed)

    def beta(self, alpha: float, beta: float) -> float:
        return float(self.generator.beta(alpha, beta))

    def gamma(self, shape: float, scale: float) -> float:
        return float(self.generator.gamma(shape, scale))

    def lognormal(self, mean: float, sigma: float) -> float:
        return float(self.generator.lognormal(mean, sigma))

    def uniform(self, low: float = 0.0, high: float = 1.0) -> float:
        return float(self.generator.uniform(low, high))

    def poisson(self, rate: float) -> int:
        return int(self.generator.poisson(rate))

    def bernoulli(self, probability: float) -> bool:
        return bool(self.generator.random() < probability)

    def choice(self, values, probabilities=None):
        chosen_index = self.generator.choice(
            len(values),
            p=probabilities,
        )

        return values[int(chosen_index)]

    def integer(self, low: int, high: int) -> int:
        return int(self.generator.integers(low, high))

    def uniform_array(
        self,
        low: float,
        high: float,
        size: int,
    ):
        return self.generator.uniform(
            low,
            high,
            size=size,
        )

    def normal(
        self,
        mean: float = 0.0,
        standard_deviation: float = 1.0,
    ) -> float:
        return float(
            self.generator.normal(
                mean,
                standard_deviation,
            )
        )