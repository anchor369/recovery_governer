from backend.db import get_connection
from psycopg.rows import dict_row


def create_customer(customer_id, contact_consent=True):
    query = """
        INSERT INTO customers (
            customer_id,
            contact_consent
        )
        VALUES (%s, %s);
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (customer_id, contact_consent)
            )

def get_customer(customer_id):
    query = """
        SELECT
            customer_id,
            contact_consent,
            created_at
        FROM customers
        WHERE customer_id = %s;
    """

    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            cursor.execute(
                query,
                (customer_id,)
            )

            return cursor.fetchone()
def create_order(
        order_id,
        customer_id,
        amount_minor,
        status="CREATED",
        currency="INR"
    ):
    query = """
        INSERT INTO orders (
            order_id,
            customer_id,
            amount_minor,
            currency,
            status
        )
        VALUES (%s, %s, %s, %s, %s);
    """

    values = (
        order_id,
        customer_id,
        amount_minor,
        currency,
        status
    )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)

def get_order(order_id):
    query = """
        SELECT
            order_id,
            customer_id,
            amount_minor,
            currency,
            status,
            created_at
        FROM orders
        WHERE order_id = %s;
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (order_id,))
            return cursor.fetchone()

def get_prior_orders_for_customer(
    customer_id,
    before_time,
    exclude_order_id,
):
    query = """
        SELECT
            order_id,
            customer_id,
            amount_minor,
            currency,
            status,
            created_at
        FROM orders
        WHERE customer_id = %s
          AND created_at < %s
          AND order_id <> %s
        ORDER BY created_at;
    """

    values = (
        customer_id,
        before_time,
        exclude_order_id,
    )

    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            cursor.execute(
                query,
                values
            )

            return cursor.fetchall()

def create_payment(
    payment_id,
    order_id,
    method,
    status="CREATED",
    failure_reason=None
):
    query = """
        INSERT INTO payments (
            payment_id,
            order_id,
            method,
            status,
            failure_reason
        )
        VALUES (%s, %s, %s, %s, %s);
    """

    values = (
        payment_id,
        order_id,
        method,
        status,
        failure_reason
    )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)

def get_payments_for_order(order_id):
    query = """
        SELECT
            payment_id,
            order_id,
            method,
            status,
            failure_reason,
            created_at,
            updated_at
        FROM payments
        WHERE order_id = %s
        ORDER BY created_at;
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (order_id,))
            return cursor.fetchall()

def get_payments_for_order_before_time(
    order_id,
    before_time,
):
    query = """
        SELECT
            payment_id,
            order_id,
            method,
            failure_reason,
            created_at
        FROM payments
        WHERE order_id = %s
          AND created_at < %s
        ORDER BY created_at;
    """

    values = (
        order_id,
        before_time,
    )

    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            cursor.execute(
                query,
                values
            )

            return cursor.fetchall()

def record_payment_event(
    payment_id,
    provider_event_id,
    event_type,
    event_time,
    raw_payload=None
):
    query = """
        INSERT INTO payment_events (
            payment_id,
            provider_event_id,
            event_type,
            event_time,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, %s);
    """

    values = (
        payment_id,
        provider_event_id,
        event_type,
        event_time,
        raw_payload
    )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)

def get_payment_events_for_order_before_time(
    order_id,
    before_time,
):
    query = """
        SELECT
            p.payment_id,
            p.method,
            p.created_at AS payment_created_at,

            pe.provider_event_id,
            pe.event_type,
            pe.event_time,
            pe.received_at

        FROM payments p

        JOIN payment_events pe
          ON pe.payment_id = p.payment_id

        WHERE p.order_id = %s
          AND pe.event_time < %s
          AND pe.received_at < %s

        ORDER BY
            pe.event_time,
            pe.received_at,
            pe.event_id;
    """

    values = (
        order_id,
        before_time,
        before_time,
    )

    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            cursor.execute(
                query,
                values
            )

            return cursor.fetchall()
