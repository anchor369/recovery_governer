import uuid
from datetime import datetime, timedelta, timezone
from statistics import median

from backend.api.schemas.demo import DemoCustomerProfile, DemoPreset
from backend.data_access.payments import (
    create_customer,
    create_order,
    create_payment,
    get_customer,
    get_order,
    get_payment_events_for_order_before_time,
    get_payments_for_order,
    get_prior_orders_for_customer,
    record_payment_event,
)
from backend.data_access.recovery_cases import get_active_recovery_case_for_order
from backend.services.payment_truth import evaluate_order_truth_at_time
from backend.services.recovery_eligibility import evaluate_recovery_eligibility
from backend.services.recovery_history import (
    build_customer_order_features,
    build_prior_order_summary,
)
from backend.services.recovery_method_history import build_payment_method_summary


PROFILE_LABELS = {
    DemoCustomerProfile.NEW_CUSTOMER: "New customer",
    DemoCustomerProfile.LOYAL_RETURNING: "Loyal returning customer",
    DemoCustomerProfile.MIXED_HISTORY: "Mixed payment history",
}

PROFILE_HISTORY = {
    DemoCustomerProfile.NEW_CUSTOMER: [],
    DemoCustomerProfile.LOYAL_RETURNING: [
        (120, 120_000, "UPI", "CAPTURED", None),
        (90, 140_000, "CREDIT_CARD", "CAPTURED", None),
        (60, 160_000, "UPI", "CAPTURED", None),
        (30, 180_000, "DEBIT_CARD", "CAPTURED", None),
    ],
    DemoCustomerProfile.MIXED_HISTORY: [
        (120, 120_000, "UPI", "CAPTURED", None),
        (90, 180_000, "CREDIT_CARD", "FAILED", "ISSUER_DECLINED"),
        (60, 150_000, "NETBANKING", "CAPTURED", None),
        (30, 210_000, "DEBIT_CARD", "FAILED", "TECHNICAL_FAILURE"),
    ],
}


def _create_historical_orders(customer_id, suffix, profile, now):
    for index, (days_ago, amount, method, status, reason) in enumerate(
        PROFILE_HISTORY[profile], start=1
    ):
        order_time = now - timedelta(days=days_ago)
        order_id = f"O_DEMO_H{index}_{suffix}"
        payment_id = f"P_DEMO_H{index}_{suffix}"
        create_order(
            order_id,
            customer_id,
            amount_minor=amount,
            created_at=order_time,
        )
        create_payment(
            payment_id,
            order_id,
            method=method,
            status="CREATED",
            failure_reason=reason,
            created_at=order_time + timedelta(minutes=1),
        )
        record_payment_event(
            payment_id=payment_id,
            provider_event_id=f"EV_DEMO_H{index}_{suffix}",
            event_type=status,
            event_time=order_time + timedelta(minutes=2),
            raw_payload={"source": "demo_history", "profile": profile.value},
        )


def _current_events_for_preset(preset):
    if preset == DemoPreset.PAYMENT_UNCERTAIN:
        return [("UPI", "AUTHORIZED", None)]
    if preset == DemoPreset.ALREADY_PAID:
        return [("UPI", "CAPTURED", None)]
    if preset == DemoPreset.NATURAL_RETRY:
        return [("UPI", "FAILED", "TECHNICAL_FAILURE")]

    final_reason = (
        "AUTHENTICATION_FAILURE"
        if preset == DemoPreset.WRONG_PIN
        else "TECHNICAL_FAILURE"
    )
    return [
        ("UPI", "FAILED", final_reason),
        ("NETBANKING", "FAILED", final_reason),
    ]


def _build_journey(customer_id, order_id, profile, decision_time):
    customer = get_customer(customer_id)
    order = get_order(order_id)
    payments = get_payments_for_order(order_id)
    payment_events = get_payment_events_for_order_before_time(
        order_id=order_id,
        before_time=decision_time,
    )
    latest_event_by_payment = {
        event["payment_id"]: event for event in payment_events
    }
    attempts = []
    for attempt_number, payment in enumerate(payments, start=1):
        event = latest_event_by_payment.get(payment["payment_id"]) or {}
        attempts.append({
            "attempt_number": attempt_number,
            "payment_id": payment["payment_id"],
            "method": payment["method"],
            "status": event.get("event_type", payment["status"]),
            "failure_reason": payment["failure_reason"],
            "created_at": payment["created_at"],
            "event_time": event.get("event_time"),
        })

    prior_orders = get_prior_orders_for_customer(
        customer_id=customer_id,
        before_time=decision_time,
        exclude_order_id=order_id,
    )
    prior_summary = build_prior_order_summary(
        customer_id=customer_id,
        current_order_id=order_id,
        decision_time=decision_time,
    )
    customer_features = build_customer_order_features(
        customer_id=customer_id,
        current_order_id=order_id,
        decision_time=decision_time,
    )
    method_summary = build_payment_method_summary(
        customer_id=customer_id,
        current_order_id=order_id,
        decision_time=decision_time,
    )
    eligibility = evaluate_recovery_eligibility(order_id)

    return {
        "customer": {
            "customer_id": customer["customer_id"],
            "profile": profile.value,
            "profile_label": PROFILE_LABELS[profile],
            "contact_consent": customer["contact_consent"],
            "created_at": customer["created_at"],
            "tenure_days": customer_features["customer_tenure_days"],
        },
        "order": {
            "order_id": order["order_id"],
            "amount_minor": order["amount_minor"],
            "currency": order["currency"],
            "created_at": order["created_at"],
            "financial_truth": evaluate_order_truth_at_time(
                order_id=order_id,
                before_time=decision_time,
            ),
        },
        "current_payment_attempts": attempts,
        "history": {
            **prior_summary,
            "prior_uncertain_count": (
                prior_summary["prior_checkout_count"]
                - prior_summary["prior_success_count"]
                - prior_summary["prior_failure_count"]
            ),
            "median_prior_amount_minor": (
                median(order["amount_minor"] for order in prior_orders)
                if prior_orders
                else None
            ),
            "amount_ratio": customer_features["amount_ratio"],
            "method_summary": method_summary,
            "orders": [
                {
                    "order_id": prior_order["order_id"],
                    "amount_minor": prior_order["amount_minor"],
                    "currency": prior_order["currency"],
                    "created_at": prior_order["created_at"],
                    "financial_truth": evaluate_order_truth_at_time(
                        order_id=prior_order["order_id"],
                        before_time=decision_time,
                    ),
                }
                for prior_order in prior_orders
            ],
        },
        "recovery_gate": {
            "financial_truth": evaluate_order_truth_at_time(
                order_id=order_id,
                before_time=decision_time,
            ),
            "confirmed_failure_count": sum(
                attempt["status"] == "FAILED" for attempt in attempts
            ),
            "active_recovery_case": (
                get_active_recovery_case_for_order(order_id) is not None
            ),
            "eligible": eligibility["eligible"],
            "reason": eligibility["reason"],
        },
    }


def create_demo_scenario(
    preset,
    customer_profile=DemoCustomerProfile.NEW_CUSTOMER,
):
    preset = DemoPreset(preset)
    customer_profile = DemoCustomerProfile(customer_profile)
    suffix = uuid.uuid4().hex[:10]
    customer_id = f"C_DEMO_{suffix}"
    order_id = f"O_DEMO_{suffix}"
    contact_consent = preset != DemoPreset.NO_CONTACT_CONSENT
    customer_active = preset == DemoPreset.ACTIVE_CUSTOMER
    now = datetime.now(timezone.utc)

    customer_age = (
        timedelta(hours=2)
        if customer_profile == DemoCustomerProfile.NEW_CUSTOMER
        else timedelta(days=180)
    )
    create_customer(
        customer_id,
        contact_consent=contact_consent,
        created_at=now - customer_age,
    )
    _create_historical_orders(customer_id, suffix, customer_profile, now)
    create_order(
        order_id,
        customer_id,
        amount_minor=150_000,
        created_at=now - timedelta(minutes=5),
    )

    events = _current_events_for_preset(preset)
    payment_ids = []
    for attempt, (method, status, reason) in enumerate(events, start=1):
        payment_id = f"P_DEMO_{attempt}_{suffix}"
        payment_ids.append(payment_id)
        payment_time = now - timedelta(minutes=len(events) - attempt + 1)
        create_payment(
            payment_id=payment_id,
            order_id=order_id,
            method=method,
            status="CREATED",
            failure_reason=reason,
            created_at=payment_time - timedelta(seconds=15),
        )
        record_payment_event(
            payment_id=payment_id,
            provider_event_id=f"EV_DEMO_{attempt}_{suffix}",
            event_type=status,
            event_time=payment_time,
            raw_payload={
                "source": "demo",
                "preset": preset.value,
                "customer_profile": customer_profile.value,
            },
        )

    decision_time = datetime.now(timezone.utc)
    return {
        "preset": preset,
        "customer_profile": customer_profile,
        "customer_id": customer_id,
        "order_id": order_id,
        "payment_ids": payment_ids,
        "journey": _build_journey(
            customer_id,
            order_id,
            customer_profile,
            decision_time,
        ),
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
