import uuid
from datetime import (
    datetime,
    timedelta,
    timezone,
)


from backend.data_access.payments import (
    create_customer,
    create_order,
    create_payment,
    get_customer,
    get_prior_orders_for_customer,
    get_payment_events_for_order_before_time,
    record_payment_event,
    get_payments_for_order_before_time,
)


def test_customer_and_prior_order_reads():
    suffix = uuid.uuid4().hex[:8]

    customer_id = f"C_READ_{suffix}"

    old_order_id = f"O_OLD_{suffix}"
    current_order_id = f"O_CURRENT_{suffix}"

    create_customer(
        customer_id=customer_id,
        contact_consent=False,
    )

    create_order(
        order_id=old_order_id,
        customer_id=customer_id,
        amount_minor=80_000,
    )

    create_order(
        order_id=current_order_id,
        customer_id=customer_id,
        amount_minor=150_000,
    )

    customer = get_customer(
        customer_id
    )

    assert customer is not None
    assert (
        customer["customer_id"]
        == customer_id
    )
    assert (
        customer["contact_consent"]
        is False
    )

    decision_time = (
        datetime.now(timezone.utc)
        + timedelta(seconds=1)
    )

    prior_orders = (
        get_prior_orders_for_customer(
            customer_id=customer_id,
            before_time=decision_time,
            exclude_order_id=current_order_id,
        )
    )

    prior_order_ids = {
        order["order_id"]
        for order in prior_orders
    }

    assert old_order_id in prior_order_ids

    assert (
        current_order_id
        not in prior_order_ids
    )

def test_payment_event_history_excludes_future_events():
    suffix = uuid.uuid4().hex[:8]

    customer_id = f"C_EVENT_{suffix}"
    order_id = f"O_EVENT_{suffix}"
    payment_id = f"P_EVENT_{suffix}"

    create_customer(
        customer_id=customer_id,
    )

    create_order(
        order_id=order_id,
        customer_id=customer_id,
        amount_minor=100_000,
    )

    create_payment(
        payment_id=payment_id,
        order_id=order_id,
        method="UPI",
        status="FAILED",
        failure_reason="TECHNICAL_FAILURE",
    )

    now = datetime.now(
        timezone.utc
    )

    past_event_time = (
        now
        - timedelta(minutes=10)
    )

    future_event_time = (
        now
        + timedelta(hours=1)
    )

    record_payment_event(
        payment_id=payment_id,
        provider_event_id=(
            f"EV_PAST_{suffix}"
        ),
        event_type="FAILED",
        event_time=past_event_time,
    )

    record_payment_event(
        payment_id=payment_id,
        provider_event_id=(
            f"EV_FUTURE_{suffix}"
        ),
        event_type="CAPTURED",
        event_time=future_event_time,
    )

    decision_time = (
        now
        + timedelta(seconds=5)
    )

    events = (
        get_payment_events_for_order_before_time(
            order_id=order_id,
            before_time=decision_time,
        )
    )

    event_types = [
        event["event_type"]
        for event in events
    ]

    assert "FAILED" in event_types
    assert "CAPTURED" not in event_types

def test_payment_attempt_read_returns_known_attempts():
    suffix = uuid.uuid4().hex[:8]

    customer_id = f"C_ATTEMPT_{suffix}"
    order_id = f"O_ATTEMPT_{suffix}"

    payment_1 = f"P_ATTEMPT_1_{suffix}"
    payment_2 = f"P_ATTEMPT_2_{suffix}"

    create_customer(
        customer_id=customer_id,
    )

    create_order(
        order_id=order_id,
        customer_id=customer_id,
        amount_minor=100_000,
    )

    create_payment(
        payment_id=payment_1,
        order_id=order_id,
        method="UPI",
        status="FAILED",
        failure_reason="TECHNICAL_FAILURE",
    )

    create_payment(
        payment_id=payment_2,
        order_id=order_id,
        method="NETBANKING",
        status="CAPTURED",
    )

    decision_time = (
        datetime.now(timezone.utc)
        + timedelta(seconds=5)
    )

    payments = (
        get_payments_for_order_before_time(
            order_id=order_id,
            before_time=decision_time,
        )
    )

    payment_ids = [
        payment["payment_id"]
        for payment in payments
    ]

    assert payment_ids == [
        payment_1,
        payment_2,
    ]

    assert payments[0]["method"] == "UPI"

    assert (
        payments[1]["method"]
        == "NETBANKING"
    )