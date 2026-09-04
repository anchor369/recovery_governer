from backend.services import (
    recovery_eligibility,
)


def set_truth(
    monkeypatch,
    truth,
):
    monkeypatch.setattr(
        recovery_eligibility,
        "evaluate_order_truth",
        lambda order_id: truth,
    )


def test_missing_order_is_not_eligible(
    monkeypatch,
):
    set_truth(
        monkeypatch,
        "ORDER_NOT_FOUND",
    )

    result = (
        recovery_eligibility
        .evaluate_recovery_eligibility(
            "O_TEST"
        )
    )

    assert result == {
        "eligible": False,
        "reason": "ORDER_NOT_FOUND",
    }


def test_paid_order_is_not_eligible(
    monkeypatch,
):
    set_truth(
        monkeypatch,
        "PAID",
    )

    result = (
        recovery_eligibility
        .evaluate_recovery_eligibility(
            "O_TEST"
        )
    )

    assert result == {
        "eligible": False,
        "reason": "ORDER_ALREADY_PAID",
    }


def test_uncertain_payment_is_not_eligible(
    monkeypatch,
):
    set_truth(
        monkeypatch,
        "UNCERTAIN",
    )

    result = (
        recovery_eligibility
        .evaluate_recovery_eligibility(
            "O_TEST"
        )
    )

    assert result == {
        "eligible": False,
        "reason": "PAYMENT_STATE_UNCERTAIN",
    }


def test_existing_recovery_case_blocks_new_case(
    monkeypatch,
):
    set_truth(
        monkeypatch,
        "UNPAID",
    )

    monkeypatch.setattr(
        recovery_eligibility,
        "get_active_recovery_case_for_order",
        lambda order_id: {
            "recovery_case_id": "RC_EXISTING",
        },
    )

    result = (
        recovery_eligibility
        .evaluate_recovery_eligibility(
            "O_TEST"
        )
    )

    assert result == {
        "eligible": False,
        "reason": "RECOVERY_CASE_ALREADY_EXISTS",
    }


def test_zero_failures_is_not_eligible(
    monkeypatch,
):
    set_truth(
        monkeypatch,
        "UNPAID",
    )

    monkeypatch.setattr(
        recovery_eligibility,
        "get_active_recovery_case_for_order",
        lambda order_id: None,
    )

    monkeypatch.setattr(
        recovery_eligibility,
        "get_payments_for_order",
        lambda order_id: [],
    )

    result = (
        recovery_eligibility
        .evaluate_recovery_eligibility(
            "O_TEST"
        )
    )

    assert result == {
        "eligible": False,
        "reason": "NO_CONFIRMED_FAILURE",
    }


def test_first_failure_allows_natural_retry(
    monkeypatch,
):
    set_truth(
        monkeypatch,
        "UNPAID",
    )

    monkeypatch.setattr(
        recovery_eligibility,
        "get_active_recovery_case_for_order",
        lambda order_id: None,
    )

    monkeypatch.setattr(
        recovery_eligibility,
        "get_payments_for_order",
        lambda order_id: [
            {
                "status": "FAILED",
            },
        ],
    )

    result = (
        recovery_eligibility
        .evaluate_recovery_eligibility(
            "O_TEST"
        )
    )

    assert result == {
        "eligible": False,
        "reason": "ALLOW_NATURAL_RETRY",
    }


def test_multiple_failures_are_recovery_eligible(
    monkeypatch,
):
    set_truth(
        monkeypatch,
        "UNPAID",
    )

    monkeypatch.setattr(
        recovery_eligibility,
        "get_active_recovery_case_for_order",
        lambda order_id: None,
    )

    monkeypatch.setattr(
        recovery_eligibility,
        "get_payments_for_order",
        lambda order_id: [
            {
                "status": "FAILED",
            },
            {
                "status": "FAILED",
            },
        ],
    )

    result = (
        recovery_eligibility
        .evaluate_recovery_eligibility(
            "O_TEST"
        )
    )

    assert result == {
        "eligible": True,
        "reason": "MULTIPLE_CONFIRMED_FAILURES",
    }