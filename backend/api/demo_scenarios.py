import uuid
from datetime import datetime, timedelta, timezone

from backend.api.schemas.demo import DemoPreset
from backend.data_access.payments import (
    create_customer,
    create_order,
    create_payment,
    record_payment_event,
)


def create_demo_scenario(preset):
    suffix = uuid.uuid4().hex[:10]
    customer_id = f"C_DEMO_{suffix}"
    order_id = f"O_DEMO_{suffix}"
    contact_consent = preset != DemoPreset.NO_CONTACT_CONSENT
    customer_active = preset == DemoPreset.ACTIVE_CUSTOMER
    now = datetime.now(timezone.utc)

    create_customer(customer_id, contact_consent=contact_consent)
    create_order(order_id, customer_id, amount_minor=150_000)

    if preset == DemoPreset.PAYMENT_UNCERTAIN:
        events = [("UPI", "AUTHORIZED", None)]
    elif preset == DemoPreset.ALREADY_PAID:
        events = [("UPI", "CAPTURED", None)]
    elif preset == DemoPreset.NATURAL_RETRY:
        events = [("UPI", "FAILED", "TECHNICAL_FAILURE")]
    else:
        final_reason = (
            "AUTHENTICATION_FAILURE"
            if preset == DemoPreset.WRONG_PIN
            else "TECHNICAL_FAILURE"
        )
        events = [
            ("UPI", "FAILED", final_reason),
            ("NETBANKING", "FAILED", final_reason),
        ]

    payment_ids = []
    for attempt, (method, status, reason) in enumerate(events, start=1):
        payment_id = f"P_DEMO_{attempt}_{suffix}"
        payment_ids.append(payment_id)
        create_payment(
            payment_id=payment_id,
            order_id=order_id,
            method=method,
            status="CREATED",
            failure_reason=reason,
        )
        record_payment_event(
            payment_id=payment_id,
            provider_event_id=f"EV_DEMO_{attempt}_{suffix}",
            event_type=status,
            event_time=now - timedelta(minutes=len(events) - attempt + 1),
            raw_payload={"source": "demo", "preset": preset.value},
        )

    return {
        "preset": preset,
        "customer_id": customer_id,
        "order_id": order_id,
        "payment_ids": payment_ids,
        "metadata": {
            "contact_consent": contact_consent,
            "runtime_signals": {
                "available_upi": True,
                "available_credit_card": True,
                "available_debit_card": True,
                "available_netbanking": True,
                "observed_rail_health": 0.9,
                "customer_active": customer_active,
            },
        },
    }
