"""
Behaviour model for individual synthetic Orders.

The values produced here are simulator-only latent state. They are used
to generate behaviour but must not be exposed directly as ML features.
"""

import math

from simulator.config import SimulatorConfig
from simulator.models import SyntheticCustomer
from simulator.random_source import RandomSource


class OrderBehaviorModel:
    """
    Generates Order-specific hidden motivation and completion propensity.
    """

    def __init__(
        self,
        config: SimulatorConfig,
        random_source: RandomSource,
    ):
        self.config = config
        self.random = random_source

    def sample_base_motivation(self) -> float:
        """Generate hidden motivation specific to one Order."""

        return self.random.beta(
            self.config.order_motivation_alpha,
            self.config.order_motivation_beta,
        )

    def calculate_propensity(
        self,
        customer: SyntheticCustomer,
        amount_minor: int,
        base_motivation: float,
    ) -> float:
        """
        Calculate hidden completion propensity for one Order.

        The score combines Order-specific motivation, merchant affinity,
        relative price pressure and small unexplained variation.
        """

        amount_ratio = (
            amount_minor
            / customer.typical_order_value_minor
        )

        price_pressure = (
            customer.price_sensitivity
            * math.log(amount_ratio)
        )

        random_noise = self.random.normal(
            mean=0.0,
            standard_deviation=(
                self.config.order_propensity_noise_sigma
            ),
        )

        score = (
            self.config.order_motivation_weight
            * (base_motivation - 0.5)
            + self.config.merchant_affinity_weight
            * (customer.merchant_affinity - 0.5)
            - self.config.price_pressure_weight
            * price_pressure
            + random_noise
        )

        return self._sigmoid(score)

    @staticmethod
    def _sigmoid(value: float) -> float:
        """Convert an unrestricted score into a probability-like value."""

        return 1.0 / (1.0 + math.exp(-value))