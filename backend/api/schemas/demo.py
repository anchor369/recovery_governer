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


class DemoScenarioRequest(BaseModel):
    preset: DemoPreset = DemoPreset.TWO_FAILURES


class DemoScenarioResponse(BaseModel):
    preset: DemoPreset
    customer_id: str
    order_id: str
    payment_ids: list[str]
    metadata: dict[str, Any]
