from backend.services import (
    recovery_engine,
)


def test_ineligible_order_does_not_open_case(
    monkeypatch,
):
    monkeypatch.setattr(
        recovery_engine,
        "evaluate_recovery_eligibility",
        lambda order_id: {
            "eligible": False,
            "reason": "ORDER_ALREADY_PAID",
        },
    )

    create_called = False

    def fake_create_recovery_case(
        recovery_case_id,
        order_id,
    ):
        nonlocal create_called

        create_called = True

    monkeypatch.setattr(
        recovery_engine,
        "create_recovery_case",
        fake_create_recovery_case,
    )

    result = (
        recovery_engine
        .open_recovery_case_if_eligible(
            "O_TEST"
        )
    )

    assert result == {
        "opened": False,
        "reason": "ORDER_ALREADY_PAID",
        "case": None,
    }

    assert create_called is False


def test_eligible_order_opens_recovery_case(
    monkeypatch,
):
    monkeypatch.setattr(
        recovery_engine,
        "evaluate_recovery_eligibility",
        lambda order_id: {
            "eligible": True,
            "reason": "MULTIPLE_CONFIRMED_FAILURES",
        },
    )

    def fake_create_recovery_case(
        recovery_case_id,
        order_id,
    ):
        return {
            "recovery_case_id":
                recovery_case_id,

            "order_id":
                order_id,

            "status":
                "OPEN",
        }

    monkeypatch.setattr(
        recovery_engine,
        "create_recovery_case",
        fake_create_recovery_case,
    )

    result = (
        recovery_engine
        .open_recovery_case_if_eligible(
            "O_TEST"
        )
    )

    assert result["opened"] is True

    assert (
        result["reason"]
        == "RECOVERY_CASE_OPENED"
    )

    assert (
        result["case"]["order_id"]
        == "O_TEST"
    )

    assert (
        result["case"]["status"]
        == "OPEN"
    )

    assert (
        result["case"][
            "recovery_case_id"
        ].startswith(
            "RC_"
        )
    )