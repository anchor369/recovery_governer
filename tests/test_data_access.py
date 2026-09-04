import uuid
from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from backend.db import (
    get_connection,
)

from backend.data_access.payments import (
    create_customer,
    create_order,
    create_payment,
    get_customer,
    get_order,
    get_payments_for_order,
    get_prior_orders_for_customer,
    get_payment_events_for_order_before_time,
    record_payment_event,
)


@pytest.fixture
def test_ids():
    """
    Generate unique IDs for every test run.

    This prevents repeated pytest runs from
    colliding with old database rows.
    """

    suffix = uuid.uuid4().hex[:10]

    ids = {
        "customer_id":
            f"C_DATA_{suffix}",

        "order_id":
            f"O_DATA_{suffix}",

        "second_order_id":
            f"O_DATA_SECOND_{suffix}",

        "payment_id":
            f"P_DATA_{suffix}",

        "provider_event_id":
            f"EV_DATA_{suffix}",
    }

    yield ids

    # Cleanup happens even if a test fails.
    #
    # Delete children before parents because
    # PostgreSQL foreign keys require this order.
    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                DELETE FROM payment_events
                WHERE payment_id = %s;
                """,
                (
                    ids["payment_id"],
                ),
            )

            cursor.execute(
                """
                DELETE FROM payments
                WHERE payment_id = %s;
                """,
                (
                    ids["payment_id"],
                ),
            )

            cursor.execute(
                """
                DELETE FROM orders
                WHERE order_id IN (%s, %s);
                """,
                (
                    ids["order_id"],
                    ids["second_order_id"],
                ),
            )

            cursor.execute(
                """
                DELETE FROM customers
                WHERE customer_id = %s;
                """,
                (
                    ids["customer_id"],
                ),
            )


def test_create_and_read_customer(
    test_ids,
):
    customer_id = (
        test_ids["customer_id"]
    )

    create_customer(
        customer_id=customer_id,
        contact_consent=True,
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
        is True
    )

    assert (
        customer["created_at"]
        is not None
    )


def test_create_and_read_order(
    test_ids,
):
    customer_id = (
        test_ids["customer_id"]
    )

    order_id = (
        test_ids["order_id"]
    )

    create_customer(
        customer_id=customer_id,
    )

    create_order(
        order_id=order_id,
        customer_id=customer_id,
        amount_minor=150_000,
        currency="INR",
        status="CREATED",
    )

    order = get_order(
        order_id
    )

    assert order is not None

    assert (
        order["order_id"]
        == order_id
    )

    assert (
        order["customer_id"]
        == customer_id
    )

    assert (
        order["amount_minor"]
        == 150_000
    )

    assert (
        order["currency"]
        == "INR"
    )

    assert (
        order["status"]
        == "CREATED"
    )


def test_create_and_read_payment(
    test_ids,
):
    customer_id = (
        test_ids["customer_id"]
    )

    order_id = (
        test_ids["order_id"]
    )

    payment_id = (
        test_ids["payment_id"]
    )

    create_customer(
        customer_id=customer_id,
    )

    create_order(
        order_id=order_id,
        customer_id=customer_id,
        amount_minor=150_000,
    )

    create_payment(
        payment_id=payment_id,
        order_id=order_id,
        method="UPI",
        status="FAILED",
        failure_reason=(
            "AUTHENTICATION_FAILURE"
        ),
    )

    payments = (
        get_payments_for_order(
            order_id
        )
    )

    assert len(payments) == 1

    payment = payments[0]

    assert (
        payment["payment_id"]
        == payment_id
    )

    assert (
        payment["order_id"]
        == order_id
    )

    assert (
        payment["method"]
        == "UPI"
    )

    assert (
        payment["status"]
        == "FAILED"
    )

    assert (
        payment["failure_reason"]
        == "AUTHENTICATION_FAILURE"
    )


def test_payment_event_can_be_read_before_time(
    test_ids,
):
    customer_id = (
        test_ids["customer_id"]
    )

    order_id = (
        test_ids["order_id"]
    )

    payment_id = (
        test_ids["payment_id"]
    )

    provider_event_id = (
        test_ids["provider_event_id"]
    )

    create_customer(
        customer_id=customer_id,
    )

    create_order(
        order_id=order_id,
        customer_id=customer_id,
        amount_minor=150_000,
    )

    create_payment(
        payment_id=payment_id,
        order_id=order_id,
        method="NETBANKING",
        status="FAILED",
        failure_reason=(
            "TECHNICAL_FAILURE"
        ),
    )

    now = datetime.now(
        timezone.utc
    )

    event_time = (
        now
        - timedelta(seconds=5)
    )

    record_payment_event(
        payment_id=payment_id,
        provider_event_id=(
            provider_event_id
        ),
        event_type="FAILED",
        event_time=event_time,
    )

    # Future cutoff ensures both:
    #
    # event_time < before_time
    # received_at < before_time
    before_time = (
        datetime.now(
            timezone.utc
        )
        + timedelta(seconds=5)
    )

    events = (
        get_payment_events_for_order_before_time(
            order_id=order_id,
            before_time=before_time,
        )
    )

    assert len(events) == 1

    event = events[0]

    assert (
        event["payment_id"]
        == payment_id
    )

    assert (
        event["provider_event_id"]
        == provider_event_id
    )

    assert (
        event["event_type"]
        == "FAILED"
    )

    assert (
        event["method"]
        == "NETBANKING"
    )


def test_prior_orders_are_read_without_current_order(
    test_ids,
):
    customer_id = (
        test_ids["customer_id"]
    )

    prior_order_id = (
        test_ids["order_id"]
    )

    current_order_id = (
        test_ids["second_order_id"]
    )

    create_customer(
        customer_id=customer_id,
    )

    create_order(
        order_id=prior_order_id,
        customer_id=customer_id,
        amount_minor=100_000,
    )

    create_order(
        order_id=current_order_id,
        customer_id=customer_id,
        amount_minor=150_000,
    )

    before_time = (
        datetime.now(
            timezone.utc
        )
        + timedelta(seconds=5)
    )

    prior_orders = (
        get_prior_orders_for_customer(
            customer_id=customer_id,
            before_time=before_time,
            exclude_order_id=(
                current_order_id
            ),
        )
    )

    returned_ids = {
        order["order_id"]
        for order in prior_orders
    }

    assert (
        prior_order_id
        in returned_ids
    )

    assert (
        current_order_id
        not in returned_ids
    )