"""Regression tests for the payment-event financial-truth boundary."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.data_access import payments as payment_data_access
from backend.data_access.payments import (
    ConflictingPaymentEventError,
    create_customer,
    create_order,
    create_payment,
    record_payment_event,
)
from backend.db import get_connection
from backend.services.payment_truth import (
    evaluate_order_truth_at_time,
)


@pytest.fixture
def payment_record():
    suffix = uuid.uuid4().hex[:10]
    record = {
        "customer_id": f"C_INGEST_{suffix}",
        "order_id": f"O_INGEST_{suffix}",
        "payment_id": f"P_INGEST_{suffix}",
        "event_prefix": f"EV_INGEST_{suffix}",
    }

    create_customer(record["customer_id"])
    create_order(
        order_id=record["order_id"],
        customer_id=record["customer_id"],
        amount_minor=100_000,
    )
    create_payment(
        payment_id=record["payment_id"],
        order_id=record["order_id"],
        method="UPI",
        status="CREATED",
    )

    yield record

    # Financial evidence is deleted before its parent rows solely to keep
    # repeated test runs isolated; production events remain immutable.
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM payment_events WHERE payment_id = %s;",
                (record["payment_id"],),
            )
            cursor.execute(
                "DELETE FROM payments WHERE payment_id = %s;",
                (record["payment_id"],),
            )
            cursor.execute(
                "DELETE FROM orders WHERE order_id = %s;",
                (record["order_id"],),
            )
            cursor.execute(
                "DELETE FROM customers WHERE customer_id = %s;",
                (record["customer_id"],),
            )


def _payment_status(payment_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT status FROM payments WHERE payment_id = %s;",
                (payment_id,),
            )
            return cursor.fetchone()[0]


def _event_count(provider_event_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT count(*)
                FROM payment_events
                WHERE provider_event_id = %s;
                """,
                (provider_event_id,),
            )
            return cursor.fetchone()[0]


def test_first_delivery_persists_event_and_updates_payment(payment_record):
    event_id = f"{payment_record['event_prefix']}_FAILED"
    result = record_payment_event(
        payment_id=payment_record["payment_id"],
        provider_event_id=event_id,
        event_type="FAILED",
        event_time=datetime.now(timezone.utc),
        raw_payload={"reason": "issuer_declined"},
    )

    assert result["created"] is True
    assert result["duplicate"] is False
    assert result["payment_status"] == "FAILED"
    assert _event_count(event_id) == 1
    assert _payment_status(payment_record["payment_id"]) == "FAILED"


def test_exact_duplicate_is_a_successful_no_op(payment_record):
    event_id = f"{payment_record['event_prefix']}_DUPLICATE"
    event_time = datetime.now(timezone.utc)
    payload = {"provider": "test", "attempt": 1}

    first = record_payment_event(
        payment_id=payment_record["payment_id"],
        provider_event_id=event_id,
        event_type="AUTHORIZED",
        event_time=event_time,
        raw_payload=payload,
    )
    duplicate = record_payment_event(
        payment_id=payment_record["payment_id"],
        provider_event_id=event_id,
        event_type="AUTHORIZED",
        event_time=event_time,
        raw_payload=payload,
    )

    assert first["created"] is True
    assert duplicate["created"] is False
    assert duplicate["duplicate"] is True
    assert duplicate["event"]["event_id"] == first["event"]["event_id"]
    assert duplicate["payment_status"] == "AUTHORIZED"
    assert _event_count(event_id) == 1


def test_conflicting_duplicate_is_rejected_explicitly(payment_record):
    event_id = f"{payment_record['event_prefix']}_CONFLICT"
    event_time = datetime.now(timezone.utc)

    record_payment_event(
        payment_id=payment_record["payment_id"],
        provider_event_id=event_id,
        event_type="AUTHORIZED",
        event_time=event_time,
        raw_payload={"amount": 100_000},
    )

    with pytest.raises(
        ConflictingPaymentEventError,
        match="different payment evidence",
    ):
        record_payment_event(
            payment_id=payment_record["payment_id"],
            provider_event_id=event_id,
            event_type="AUTHORIZED",
            event_time=event_time,
            raw_payload={"amount": 99_999},
        )

    assert _event_count(event_id) == 1
    assert _payment_status(payment_record["payment_id"]) == "AUTHORIZED"


def test_status_failure_rolls_back_event_insert(payment_record, monkeypatch):
    event_id = f"{payment_record['event_prefix']}_ROLLBACK"

    def fail_synchronization(**kwargs):
        raise RuntimeError("forced synchronization failure")

    monkeypatch.setattr(
        payment_data_access,
        "_synchronize_payment_status",
        fail_synchronization,
    )

    with pytest.raises(
        RuntimeError,
        match="forced synchronization failure",
    ):
        record_payment_event(
            payment_id=payment_record["payment_id"],
            provider_event_id=event_id,
            event_type="FAILED",
            event_time=datetime.now(timezone.utc),
        )

    # The connection context rolls back both sides of the attempted change.
    assert _event_count(event_id) == 0
    assert _payment_status(payment_record["payment_id"]) == "CREATED"


def test_captured_is_terminal_for_delayed_events(payment_record):
    now = datetime.now(timezone.utc)

    record_payment_event(
        payment_id=payment_record["payment_id"],
        provider_event_id=f"{payment_record['event_prefix']}_CAPTURED",
        event_type="CAPTURED",
        event_time=now,
    )
    record_payment_event(
        payment_id=payment_record["payment_id"],
        provider_event_id=f"{payment_record['event_prefix']}_AUTHORIZED",
        event_type="AUTHORIZED",
        event_time=now - timedelta(minutes=2),
    )
    record_payment_event(
        payment_id=payment_record["payment_id"],
        provider_event_id=f"{payment_record['event_prefix']}_FAILED_LATE",
        event_type="FAILED",
        event_time=now - timedelta(minutes=1),
    )

    assert _payment_status(payment_record["payment_id"]) == "CAPTURED"


def test_chronological_and_out_of_order_progression(payment_record):
    now = datetime.now(timezone.utc)

    for suffix, status, event_time in (
        ("CREATED", "CREATED", now - timedelta(minutes=3)),
        ("AUTHORIZED", "AUTHORIZED", now - timedelta(minutes=2)),
        ("FAILED", "FAILED", now - timedelta(minutes=1)),
    ):
        result = record_payment_event(
            payment_id=payment_record["payment_id"],
            provider_event_id=f"{payment_record['event_prefix']}_{suffix}",
            event_type=status,
            event_time=event_time,
        )
        assert result["payment_status"] == status

    # Older non-terminal evidence is retained but cannot regress the latest
    # materialized state selected by event_time/received_at/event_id.
    delayed = record_payment_event(
        payment_id=payment_record["payment_id"],
        provider_event_id=f"{payment_record['event_prefix']}_DELAYED",
        event_type="AUTHORIZED",
        event_time=now - timedelta(minutes=10),
    )

    assert delayed["payment_status"] == "FAILED"
    assert _payment_status(payment_record["payment_id"]) == "FAILED"


def test_historical_truth_still_uses_both_strict_cutoffs(payment_record):
    now = datetime.now(timezone.utc)
    record_payment_event(
        payment_id=payment_record["payment_id"],
        provider_event_id=f"{payment_record['event_prefix']}_HISTORICAL",
        event_type="FAILED",
        event_time=now - timedelta(minutes=1),
    )

    assert evaluate_order_truth_at_time(
        order_id=payment_record["order_id"],
        before_time=now - timedelta(minutes=2),
    ) == "UNCERTAIN"
    assert evaluate_order_truth_at_time(
        order_id=payment_record["order_id"],
        before_time=datetime.now(timezone.utc) + timedelta(seconds=1),
    ) == "UNPAID"


@pytest.mark.parametrize(
    ("provider_event_id", "event_type", "event_time"),
    [
        (None, "FAILED", datetime.now(timezone.utc)),
        ("EVENT", "UNKNOWN", datetime.now(timezone.utc)),
        ("EVENT", "FAILED", datetime.now()),
    ],
)
def test_invalid_financial_evidence_is_rejected_before_write(
    payment_record,
    provider_event_id,
    event_type,
    event_time,
):
    with pytest.raises(ValueError):
        record_payment_event(
            payment_id=payment_record["payment_id"],
            provider_event_id=provider_event_id,
            event_type=event_type,
            event_time=event_time,
        )
