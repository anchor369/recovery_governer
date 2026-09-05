from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class DemoPreset(StrEnum):
    TWO_FAILURES = "two_failures"
    TECHNICAL_FAILURE = "technical_failure"
    WRONG_PIN = "wrong_pin"
    NO_CONTACT_CONSENT = "no_contact_consent"
    ACTIVE_CUSTOMER = "active_customer"
    PAYMENT_UNCERTAIN = "payment_uncertain"
    ALREADY_PAID = "already_paid"
    NATURAL_RETRY = "natural_retry"


class DemoCustomerProfile(StrEnum):
    NEW_CUSTOMER = "new_customer"
    LOYAL_RETURNING = "loyal_returning"
    MIXED_HISTORY = "mixed_history"


class DemoScenarioRequest(BaseModel):
    preset: DemoPreset = DemoPreset.TWO_FAILURES
    customer_profile: DemoCustomerProfile = DemoCustomerProfile.NEW_CUSTOMER


class DemoScenarioResponse(BaseModel):
    preset: DemoPreset
    customer_profile: DemoCustomerProfile
    customer_id: str
    order_id: str
    payment_ids: list[str]
    journey: dict[str, Any]
    metadata: dict[str, Any]
