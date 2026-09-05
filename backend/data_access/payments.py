import logging
from datetime import datetime

from backend.db import get_connection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


logger = logging.getLogger(__name__)


PAYMENT_EVENT_TYPES = {
    "CREATED",
    "AUTHORIZED",
    "FAILED",
    "CAPTURED",
}


class ConflictingPaymentEventError(ValueError):
    """Raised when an idempotency key is reused for different evidence."""


def create_customer(customer_id, contact_consent=True, created_at=None):
    if created_at is None:
        query = """
            INSERT INTO customers (customer_id, contact_consent)
            VALUES (%s, %s);
        """
        values = (customer_id, contact_consent)
    else:
        query = """
            INSERT INTO customers (customer_id, contact_consent, created_at)
            VALUES (%s, %s, %s);
        """
        values = (customer_id, contact_consent, created_at)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                values
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
        currency="INR",
        created_at=None,
    ):
    columns = "order_id, customer_id, amount_minor, currency, status"
    values = (
        order_id,
        customer_id,
        amount_minor,
        currency,
        status
    )
    placeholders = "%s, %s, %s, %s, %s"
    if created_at is not None:
        columns += ", created_at"
        values += (created_at,)
        placeholders += ", %s"
    query = f"INSERT INTO orders ({columns}) VALUES ({placeholders});"

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
    failure_reason=None,
    created_at=None,
):
    columns = "payment_id, order_id, method, status, failure_reason"
    values = (
        payment_id,
        order_id,
        method,
        status,
        failure_reason
    )
    placeholders = "%s, %s, %s, %s, %s"
    if created_at is not None:
        columns += ", created_at"
        values += (created_at,)
        placeholders += ", %s"
    query = f"INSERT INTO payments ({columns}) VALUES ({placeholders});"

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
    """
    Persist provider evidence and synchronize payment truth atomically.

    The provider event identifier is the idempotency key. An exact
    re-delivery is a successful no-op; reuse for different evidence is
    rejected explicitly.
    """

    normalized_event_type = _validate_payment_event(
        payment_id=payment_id,
        provider_event_id=provider_event_id,
        event_type=event_type,
        event_time=event_time,
    )

    insert_query = """
        INSERT INTO payment_events (
            payment_id,
            provider_event_id,
            event_type,
            event_time,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (provider_event_id) DO NOTHING
        RETURNING
            event_id,
            payment_id,
            provider_event_id,
            event_type,
            event_time,
            received_at,
            raw_payload;
    """

    values = (
        payment_id,
        provider_event_id,
        normalized_event_type,
        event_time,
        (
            Jsonb(raw_payload)
            if raw_payload is not None
            else None
        ),
    )

    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            payment = _lock_payment(
                cursor=cursor,
                payment_id=payment_id,
            )

            cursor.execute(
                insert_query,
                values,
            )
            event = cursor.fetchone()

            if event is None:
                existing_event = _get_event_by_provider_id(
                    cursor=cursor,
                    provider_event_id=provider_event_id,
                )

                if not _events_match(
                    existing_event=existing_event,
                    payment_id=payment_id,
                    event_type=normalized_event_type,
                    event_time=event_time,
                    raw_payload=raw_payload,
                ):
                    logger.warning(
                        "Payment event idempotency conflict: provider_event_id=%s payment_id=%s",
                        provider_event_id,
                        payment_id,
                    )
                    raise ConflictingPaymentEventError(
                        "provider_event_id is already bound to "
                        "different payment evidence."
                    )

                logger.debug(
                    "Duplicate payment event recognized: provider_event_id=%s payment_id=%s",
                    provider_event_id,
                    payment_id,
                )
                return {
                    "created": False,
                    "duplicate": True,
                    "event": existing_event,
                    "payment_status": payment["status"],
                }

            payment_status = _synchronize_payment_status(
                cursor=cursor,
                payment_id=payment_id,
                current_status=payment["status"],
            )

            logger.info(
                "Payment event persisted: provider_event_id=%s payment_id=%s status=%s",
                provider_event_id,
                payment_id,
                payment_status,
            )

            return {
                "created": True,
                "duplicate": False,
                "event": event,
                "payment_status": payment_status,
            }


def _validate_payment_event(
    payment_id,
    provider_event_id,
    event_type,
    event_time,
):
    if not isinstance(payment_id, str) or not payment_id.strip():
        raise ValueError("payment_id is required.")

    if (
        not isinstance(provider_event_id, str)
        or not provider_event_id.strip()
    ):
        raise ValueError("provider_event_id is required.")

    if not isinstance(event_type, str):
        raise ValueError("event_type must be a string.")

    normalized_event_type = event_type.upper()

    if normalized_event_type not in PAYMENT_EVENT_TYPES:
        raise ValueError(
            f"Unsupported payment event type: {event_type}"
        )

    if (
        not isinstance(event_time, datetime)
        or event_time.tzinfo is None
        or event_time.utcoffset() is None
    ):
        raise ValueError(
            "event_time must be a timezone-aware datetime."
        )

    return normalized_event_type


def _lock_payment(cursor, payment_id):
    cursor.execute(
        """
        SELECT payment_id, status
        FROM payments
        WHERE payment_id = %s
        FOR UPDATE;
        """,
        (payment_id,),
    )
    payment = cursor.fetchone()

    if payment is None:
        raise ValueError(
            f"Payment does not exist: {payment_id}"
        )

    return payment


def _get_event_by_provider_id(
    cursor,
    provider_event_id,
):
    cursor.execute(
        """
        SELECT
            event_id,
            payment_id,
            provider_event_id,
            event_type,
            event_time,
            received_at,
            raw_payload
        FROM payment_events
        WHERE provider_event_id = %s;
        """,
        (provider_event_id,),
    )
    return cursor.fetchone()


def _events_match(
    existing_event,
    payment_id,
    event_type,
    event_time,
    raw_payload,
):
    return (
        existing_event is not None
        and existing_event["payment_id"] == payment_id
        and existing_event["event_type"] == event_type
        and existing_event["event_time"] == event_time
        and existing_event["raw_payload"] == raw_payload
    )


def _synchronize_payment_status(
    cursor,
    payment_id,
    current_status,
):
    # CAPTURED is terminal even when older provider messages arrive late.
    if current_status == "CAPTURED":
        return current_status

    cursor.execute(
        """
        SELECT event_type
        FROM payment_events
        WHERE payment_id = %s
        ORDER BY
            CASE WHEN event_type = 'CAPTURED' THEN 1 ELSE 0 END DESC,
            event_time DESC,
            received_at DESC,
            event_id DESC
        LIMIT 1;
        """,
        (payment_id,),
    )
    authoritative_event = cursor.fetchone()
    authoritative_status = authoritative_event["event_type"]

    cursor.execute(
        """
        UPDATE payments
        SET
            status = %s,
            updated_at = now()
        WHERE payment_id = %s
          AND status IS DISTINCT FROM %s
        RETURNING status;
        """,
        (
            authoritative_status,
            payment_id,
            authoritative_status,
        ),
    )
    updated_payment = cursor.fetchone()

    if updated_payment is None:
        return current_status

    return updated_payment["status"]

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
