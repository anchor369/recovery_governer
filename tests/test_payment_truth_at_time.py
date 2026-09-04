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
    record_payment_event,
)

from backend.services.payment_truth import (
    evaluate_order_truth_at_time,
)


def test_latest_known_payment_event_determines_truth():
    suffix = uuid.uuid4().hex[:8]

    customer_id = f"C_TRUTH_{suffix}"
    order_id = f"O_TRUTH_{suffix}"
    payment_id = f"P_TRUTH_{suffix}"

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

    record_payment_event(
        payment_id=payment_id,
        provider_event_id=(
            f"EV_CREATED_{suffix}"
        ),
        event_type="CREATED",
        event_time=(
            now
            - timedelta(minutes=10)
        ),
    )

    record_payment_event(
        payment_id=payment_id,
        provider_event_id=(
            f"EV_FAILED_{suffix}"
        ),
        event_type="FAILED",
        event_time=(
            now
            - timedelta(minutes=5)
        ),
    )

    decision_time = (
        now
        + timedelta(seconds=5)
    )

    truth = evaluate_order_truth_at_time(
        order_id=order_id,
        before_time=decision_time,
    )

    assert truth == "UNPAID"

def test_later_capture_overrides_earlier_failure():
    suffix = uuid.uuid4().hex[:8]

    customer_id = f"C_CAPTURE_{suffix}"
    order_id = f"O_CAPTURE_{suffix}"
    payment_id = f"P_CAPTURE_{suffix}"

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
        status="CAPTURED",
    )

    now = datetime.now(
        timezone.utc
    )

    record_payment_event(
        payment_id=payment_id,
        provider_event_id=(
            f"EV_FAILED_{suffix}"
        ),
        event_type="FAILED",
        event_time=(
            now
            - timedelta(minutes=10)
        ),
    )

    record_payment_event(
        payment_id=payment_id,
        provider_event_id=(
            f"EV_CAPTURED_{suffix}"
        ),
        event_type="CAPTURED",
        event_time=(
            now
            - timedelta(minutes=5)
        ),
    )

    decision_time = (
        now
        + timedelta(seconds=5)
    )

    truth = evaluate_order_truth_at_time(
        order_id=order_id,
        before_time=decision_time,
    )

    assert truth == "PAID"

def test_no_known_events_means_uncertain():
    suffix = uuid.uuid4().hex[:8]

    customer_id = f"C_NOEVENT_{suffix}"
    order_id = f"O_NOEVENT_{suffix}"
    payment_id = f"P_NOEVENT_{suffix}"

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

    decision_time = datetime.now(
        timezone.utc
    )

    truth = evaluate_order_truth_at_time(
        order_id=order_id,
        before_time=decision_time,
    )

    assert truth == "UNCERTAIN"