"""
Core data structures used by the synthetic payment simulator.

These objects describe factual synthetic entities and simulator-only
behavioural state. Simulator-only fields must never be exposed directly
to the ML feature pipeline.
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PaymentMethod(str, Enum):
    UPI = "UPI"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    NETBANKING = "NETBANKING"

class PaymentStatus(str, Enum):
    CREATED = "CREATED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    UNCERTAIN = "UNCERTAIN"

class FailureCategory(str, Enum):
    USER_CANCELLED = "USER_CANCELLED"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    INSTRUMENT_UNAVAILABLE = "INSTRUMENT_UNAVAILABLE"
    RISK_DECLINED = "RISK_DECLINED"
    ISSUER_DECLINED = "ISSUER_DECLINED"
    BANK_OR_PROVIDER_UNAVAILABLE = "BANK_OR_PROVIDER_UNAVAILABLE"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"
    OTHER_CONFIRMED_FAILURE = "OTHER_CONFIRMED_FAILURE"


class IncidentMode(str, Enum):
    NONE = "NONE"
    PROCESSING_ERRORS = "PROCESSING_ERRORS"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    LATENCY = "LATENCY"

class NaturalAction(str, Enum):
    RETRY_SAME_METHOD = "RETRY_SAME_METHOD"
    SWITCH_METHOD = "SWITCH_METHOD"
    RETURN_LATER = "RETURN_LATER"
    ABANDON = "ABANDON"

class ActionType(str, Enum):
    NO_ACTION = "NO_ACTION"
    NUDGE = "NUDGE"
    SWITCH_METHOD = "SWITCH_METHOD"
    APPROVED_OFFER = "APPROVED_OFFER"

@dataclass(frozen=True)
class RecoveryAction:
    action_type: ActionType

    target_method: PaymentMethod | None = None
    discount_percent: float | None = None

@dataclass
class BankAccount:
    account_id: str
    bank_id: str

    upi_enabled: bool
    debit_card_available: bool
    netbanking_enabled: bool


@dataclass
class CreditCard:
    card_id: str
    issuer_bank_id: str
    network: str

    active: bool = True
    online_enabled: bool = True


@dataclass
class SyntheticCustomer:
    customer_id: str
    created_at_days_ago: int

    # Simulator-only behavioural state.
    merchant_affinity: float
    retry_persistence: float
    method_flexibility: float
    price_sensitivity: float

    # Simulator-only generative parameters.
    checkout_rate_per_year: float
    typical_order_value_minor: int

    habitual_method: PaymentMethod
    contact_consent: bool

    bank_accounts: list[BankAccount] = field(default_factory=list)
    credit_cards: list[CreditCard] = field(default_factory=list)

@dataclass
class PaymentAttempt:
    payment_id: str
    attempt_number: int

    method: PaymentMethod
    attempted_at: datetime

    status: PaymentStatus = PaymentStatus.CREATED

    failure_category: FailureCategory | None = None
    failure_detail: str | None = None
    failure_source: str | None = None
    failure_step: str | None = None

    observed_rail_health: float | None = None

@dataclass
class HistoricalJourney:
    journey_id: str
    order_id: str
    customer_id: str

    created_at: datetime
    amount_minor: int

    # Simulator-only Order state.
    base_order_motivation: float
    latent_order_propensity: float

    initial_method: PaymentMethod

    payment_attempts: list[PaymentAttempt] = field(
        default_factory=list
    )

    naturally_recovered: bool = False
    abandoned: bool = False



@dataclass
class RecoveryDecisionState:
    customer_tenure_days: int

    prior_checkout_count: int
    prior_success_count: int
    prior_failure_count: int
    prior_success_rate: float

    prior_upi_count: int
    prior_credit_card_count: int
    prior_debit_card_count: int
    prior_netbanking_count: int

    prior_upi_attempt_count: int
    prior_upi_success_count: int
    prior_upi_success_rate: float

    prior_credit_card_attempt_count: int
    prior_credit_card_success_count: int
    prior_credit_card_success_rate: float

    prior_debit_card_attempt_count: int
    prior_debit_card_success_count: int
    prior_debit_card_success_rate: float

    prior_netbanking_attempt_count: int
    prior_netbanking_success_count: int
    prior_netbanking_success_rate: float

    available_upi: bool
    available_credit_card: bool
    available_debit_card: bool
    available_netbanking: bool

    current_amount_minor: int
    amount_ratio: float

    current_method: PaymentMethod
    failure_category: FailureCategory
    attempt_count: int

    observed_rail_health: float

    contact_consent: bool
    customer_active: bool
