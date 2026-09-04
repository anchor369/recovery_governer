from backend.services import (
    payment_truth,
)


def test_missing_order_returns_order_not_found(
    monkeypatch,
):
    monkeypatch.setattr(
        payment_truth,
        "get_order",
        lambda order_id: None,
    )

    result = (
        payment_truth.evaluate_order_truth(
            "O_MISSING"
        )
    )

    assert result == "ORDER_NOT_FOUND"


def test_captured_payment_means_paid(
    monkeypatch,
):
    monkeypatch.setattr(
        payment_truth,
        "get_order",
        lambda order_id: {
            "order_id": order_id,
        },
    )

    monkeypatch.setattr(
        payment_truth,
        "get_payments_for_order",
        lambda order_id: [
            {
                "status": "FAILED",
            },
            {
                "status": "CAPTURED",
            },
        ],
    )

    result = (
        payment_truth.evaluate_order_truth(
            "O_TEST"
        )
    )

    assert result == "PAID"


def test_unresolved_payment_means_uncertain(
    monkeypatch,
):
    monkeypatch.setattr(
        payment_truth,
        "get_order",
        lambda order_id: {
            "order_id": order_id,
        },
    )

    monkeypatch.setattr(
        payment_truth,
        "get_payments_for_order",
        lambda order_id: [
            {
                "status": "FAILED",
            },
            {
                "status": "AUTHORIZED",
            },
        ],
    )

    result = (
        payment_truth.evaluate_order_truth(
            "O_TEST"
        )
    )

    assert result == "UNCERTAIN"


def test_all_failed_payments_mean_unpaid(
    monkeypatch,
):
    monkeypatch.setattr(
        payment_truth,
        "get_order",
        lambda order_id: {
            "order_id": order_id,
        },
    )

    monkeypatch.setattr(
        payment_truth,
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
        payment_truth.evaluate_order_truth(
            "O_TEST"
        )
    )

    assert result == "UNPAID"