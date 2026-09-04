"""
Generates payment-infrastructure conditions shared by nearby attempts.

Attempts on the same method inside the same time window share one
environment snapshot, creating correlated infrastructure failures.
"""

from dataclasses import dataclass
from datetime import datetime

from simulator.config import SimulatorConfig
from simulator.models import IncidentMode, PaymentMethod
from simulator.random_source import RandomSource


@dataclass(frozen=True)
class PaymentEnvironment:
    method: PaymentMethod

    true_health: float
    observed_health: float

    incident_mode: IncidentMode


class PaymentEnvironmentGenerator:
    """
    Creates and caches infrastructure conditions for payment time windows.
    """

    def __init__(
        self,
        config: SimulatorConfig,
        random_source: RandomSource,
    ):
        self.config = config
        self.random = random_source

        self.environment_cache = {}

    def get_environment(
        self,
        method: PaymentMethod,
        attempted_at: datetime,
    ) -> PaymentEnvironment:
        """Return the shared environment for this method and time window."""

        window_minutes = (
            self.config.environment_window_minutes
        )

        bucket_minute = (
            attempted_at.minute
            // window_minutes
            * window_minutes
        )

        cache_key = (
            method,
            attempted_at.year,
            attempted_at.month,
            attempted_at.day,
            attempted_at.hour,
            bucket_minute,
        )

        if cache_key not in self.environment_cache:
            self.environment_cache[cache_key] = (
                self._generate_environment(method)
            )

        return self.environment_cache[cache_key]

    def _generate_environment(
        self,
        method: PaymentMethod,
    ) -> PaymentEnvironment:
        """Generate one hidden infrastructure state."""

        environment_roll = self.random.uniform()

        healthy_cutoff = (
            self.config.healthy_environment_probability
        )

        degraded_cutoff = (
            healthy_cutoff
            + self.config.degraded_environment_probability
        )

        if environment_roll < healthy_cutoff:
            true_health = self.random.uniform(
                self.config.healthy_health_min,
                self.config.healthy_health_max,
            )

            incident_mode = IncidentMode.NONE

        elif environment_roll < degraded_cutoff:
            true_health = self.random.uniform(
                self.config.degraded_health_min,
                self.config.degraded_health_max,
            )

            incident_mode = self._choose_incident_mode()

        else:
            true_health = self.random.uniform(
                self.config.severe_health_min,
                self.config.severe_health_max,
            )

            incident_mode = self._choose_incident_mode()

        observed_health = (
            true_health
            + self.random.normal(
                mean=0.0,
                standard_deviation=0.08,
            )
        )

        observed_health = max(
            0.0,
            min(1.0, observed_health),
        )

        return PaymentEnvironment(
            method=method,
            true_health=true_health,
            observed_health=observed_health,
            incident_mode=incident_mode,
        )

    def _choose_incident_mode(
        self,
    ) -> IncidentMode:
        """Choose the dominant cause of an infrastructure incident."""

        modes = [
            IncidentMode.PROCESSING_ERRORS,
            IncidentMode.PROVIDER_UNAVAILABLE,
            IncidentMode.LATENCY,
        ]

        return self.random.choice(modes)