from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from backend.services import (
    recovery_outcome,
)


def build_context(
    **overrides,
):
    now = datetime.now(
        timezone.utc
    )

    context = {
        "recovery_case_id":
            "RC_TEST",

        "recovery_order_id":
            "O_TEST",

        "recovery_case_status":
            "OPEN",

        "opened_at":
            now - timedelta(
                minutes=5
            ),

        "closed_at":
            None,

        "order_amount_minor":
            150_000,

        "action_id":
            "A_TEST",

        "action_type":
            "NUDGE",

        "execution_status":
            "EXECUTED",

        "payment_id":
            "P_TEST",

        "payment_order_id":
            "O_TEST",

        "materialized_payment_status":
            "CAPTURED",

        "latest_payment_event_type":
            "CAPTURED",
    }

    context.update(
        overrides
    )

    return context


def test_captured_payment_records_recovery(
    monkeypatch,
):
    context = build_context()

    monkeypatch.setattr(
        recovery_outcome,
        "get_recovery_outcome_context",
        lambda **kwargs: context,
    )

    def fake_write(**kwargs):
        return {
            "outcome": kwargs,
            "case": {
                "status": "CLOSED",
                "closure_reason":
                    "RECOVERED",
            },
        }

    monkeypatch.setattr(
        recovery_outcome,
        "create_recovered_outcome_and_close_case",
        fake_write,
    )

    result = (
        recovery_outcome
        .record_recovered_payment(
            recovery_case_id=(
                "RC_TEST"
            ),
            action_id="A_TEST",
            payment_id="P_TEST",
        )
    )

    assert (
        result["outcome"][
            "payment_id"
        ]
        == "P_TEST"
    )

    assert (
        result["outcome"][
            "recovered_amount_minor"
        ]
        == 150_000
    )

    assert (
        result["case"]["status"]
        == "CLOSED"
    )

    assert (
        result["case"][
            "closure_reason"
        ]
        == "RECOVERED"
    )


def test_payment_from_different_order_is_rejected(
    monkeypatch,
):
    context = build_context(
        payment_order_id=(
            "O_SOMEONE_ELSE"
        )
    )

    monkeypatch.setattr(
        recovery_outcome,
        "get_recovery_outcome_context",
        lambda **kwargs: context,
    )

    with pytest.raises(
        ValueError,
        match=(
            "different order"
        ),
    ):
        recovery_outcome.record_recovered_payment(
            recovery_case_id="RC_TEST",
            action_id="A_TEST",
            payment_id="P_TEST",
        )


def test_uncaptured_payment_is_rejected(
    monkeypatch,
):
    context = build_context(
        latest_payment_event_type=(
            "AUTHORIZED"
        )
    )

    monkeypatch.setattr(
        recovery_outcome,
        "get_recovery_outcome_context",
        lambda **kwargs: context,
    )

    with pytest.raises(
        ValueError,
        match="not confirmed CAPTURED",
    ):
        recovery_outcome.record_recovered_payment(
            recovery_case_id="RC_TEST",
            action_id="A_TEST",
            payment_id="P_TEST",
        )


def test_blocked_action_cannot_claim_recovery(
    monkeypatch,
):
    context = build_context(
        execution_status="BLOCKED"
    )

    monkeypatch.setattr(
        recovery_outcome,
        "get_recovery_outcome_context",
        lambda **kwargs: context,
    )

    with pytest.raises(
        ValueError,
        match="was not executed",
    ):
        recovery_outcome.record_recovered_payment(
            recovery_case_id="RC_TEST",
            action_id="A_TEST",
            payment_id="P_TEST",
        )


def test_already_closed_case_is_rejected(monkeypatch):
    context = build_context(
        recovery_case_status="CLOSED",
        closed_at=datetime.now(timezone.utc),
    )
    monkeypatch.setattr(
        recovery_outcome,
        "get_recovery_outcome_context",
        lambda **kwargs: context,
    )

    with pytest.raises(ValueError, match="already closed"):
        recovery_outcome.record_recovered_payment(
            recovery_case_id="RC_TEST",
            action_id="A_TEST",
            payment_id="P_TEST",
        )
