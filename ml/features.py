"""
Feature definitions shared by recovery models.

Only pre-treatment, observable information is included here.
Identifiers, treatments and post-treatment outcomes must never be features.
"""


NUMERIC_FEATURES = [
    "customer_tenure_days",
    "prior_checkout_count",
    "prior_success_count",
    "prior_failure_count",
    "prior_success_rate",
    "prior_upi_count",
    "prior_credit_card_count",
    "prior_debit_card_count",
    "prior_netbanking_count",
    "available_upi",
    "available_credit_card",
    "available_debit_card",
    "available_netbanking",
    "current_amount_minor",
    "amount_ratio",
    "attempt_count",
    "observed_rail_health",
    "contact_consent",
    "customer_active",
]

METHOD_HISTORY_NUMERIC_FEATURES = [
    "prior_upi_attempt_count",
    "prior_upi_success_count",
    "prior_upi_success_rate",

    "prior_credit_card_attempt_count",
    "prior_credit_card_success_count",
    "prior_credit_card_success_rate",

    "prior_debit_card_attempt_count",
    "prior_debit_card_success_count",
    "prior_debit_card_success_rate",

    "prior_netbanking_attempt_count",
    "prior_netbanking_success_count",
    "prior_netbanking_success_rate",
]

CATEGORICAL_FEATURES = [
    "current_method",
    "failure_category",
]


MODEL_FEATURES = (
    NUMERIC_FEATURES
    + CATEGORICAL_FEATURES
)