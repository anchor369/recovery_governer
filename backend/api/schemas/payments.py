from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PaymentEventRequest(BaseModel):
    payment_id: str = Field(min_length=1)
    provider_event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    event_time: datetime
    raw_payload: Any | None = None

    @field_validator("payment_id", "provider_event_id", "event_type")
    @classmethod
    def reject_blank_strings(cls, value):
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("event_time")
    @classmethod
    def require_timezone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event_time must include a timezone")
        return value


class PaymentEventResponse(BaseModel):
    created: bool
    duplicate: bool
    payment_status: str
    event: dict[str, Any]
