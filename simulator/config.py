"""
Configuration values used by the synthetic payment simulator.

The values in this file describe the baseline synthetic world.
They are simulation assumptions unless explicitly documented otherwise.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulatorConfig:
    """
    Stores parameters that define one simulator world.

    Keeping these values together makes it easier to create alternative
    worlds later without changing the simulator logic.
    """

    random_seed: int = 42

    # Customer population
    merchant_affinity_alpha: float = 3.0
    merchant_affinity_beta: float = 2.0

    retry_persistence_alpha: float = 2.5
    retry_persistence_beta: float = 3.0

    method_flexibility_alpha: float = 2.0
    method_flexibility_beta: float = 2.0

    price_sensitivity_alpha: float = 2.0
    price_sensitivity_beta: float = 2.5

    # Checkout frequency
    checkout_rate_shape: float = 2.0
    checkout_rate_scale: float = 2.5

    # Customer-typical order value, stored in INR for generation.
    typical_order_median_rupees: float = 1500.0
    typical_order_sigma: float = 0.65

    min_typical_order_rupees: float = 300.0
    max_typical_order_rupees: float = 20000.0

    # Variation between orders belonging to the same customer.
    within_customer_order_sigma: float = 0.28

    # Safety limit. Normal customer behaviour should usually stop earlier.
    max_payment_attempts: int = 6

    # Customer tenure
    customer_tenure_median_days: float = 240.0
    customer_tenure_sigma: float = 0.90
    min_customer_tenure_days: int = 1
    max_customer_tenure_days: int = 1095

    # Synthetic payment-instrument availability.
    # These are baseline simulator assumptions, not market-share claims.
    second_bank_account_probability: float = 0.35
    credit_card_probability: float = 0.45

    debit_card_probability_per_account: float = 0.80
    netbanking_probability_per_account: float = 0.75

    # Relative habitual-method weights in the baseline synthetic world.
    habitual_upi_weight: float = 0.60
    habitual_credit_card_weight: float = 0.25
    habitual_debit_card_weight: float = 0.10
    habitual_netbanking_weight: float = 0.05

        # Per-Order hidden motivation.
    order_motivation_alpha: float = 3.0
    order_motivation_beta: float = 2.0

    # Contribution of hidden factors to Order completion propensity.
    order_motivation_weight: float = 2.0
    merchant_affinity_weight: float = 0.8
    price_pressure_weight: float = 1.0
    order_propensity_noise_sigma: float = 0.25

    # Initial payment-method selection.
    habitual_method_bias: float = 1.8

    # Larger Orders gradually make Card/Netbanking more plausible.
    upi_high_amount_penalty: float = 0.25
    credit_card_high_amount_boost: float = 0.45
    netbanking_high_amount_boost: float = 0.20

    # Payment infrastructure baseline.
    healthy_environment_probability: float = 0.97
    degraded_environment_probability: float = 0.025

    healthy_health_min: float = 0.90
    healthy_health_max: float = 1.00

    degraded_health_min: float = 0.45
    degraded_health_max: float = 0.80

    severe_health_min: float = 0.10
    severe_health_max: float = 0.40

    technical_baseline_risk: float = 0.005
    technical_severity_multiplier: float = 0.45

    environment_window_minutes: int = 5

     # Natural customer recovery.
    same_method_retry_median_seconds: float = 45.0
    technical_retry_median_seconds: float = 120.0
    delayed_return_median_seconds: float = 1800.0

    retry_delay_sigma: float = 0.65
    delayed_return_sigma: float = 1.0

    natural_recovery_window_seconds: int = 24 * 60 * 60

    max_payment_attempts: int = 6

    # Short-term persistence when the same payment method is retried.
    authentication_failure_persistence: float = 0.25
    insufficient_funds_persistence: float = 0.80
    limit_exceeded_persistence: float = 0.90
    instrument_unavailable_persistence: float = 0.95
    issuer_declined_persistence: float = 0.45
    risk_declined_persistence: float = 0.75

    allowed_offer_percentages: tuple[float, ...] = (
        5.0,
        10.0,
    )

    contact_consent_probability: float = 0.90