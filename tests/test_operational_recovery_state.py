import uuid
from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from backend.data_access.payments import (
    create_customer,
    create_order,
    create_payment,
    record_payment_event,
)


from backend.services.recovery_state import (
    RuntimeRecoverySignals,
    build_current_payment_features,
    build_customer_order_features,
    build_payment_method_summary,
    build_prior_order_summary,
    build_recovery_decision_state,
    normalize_failure_category,
)

from simulator.models import (
    FailureCategory,
    PaymentMethod,
)

def test_prior_order_summary_respects_payment_truth():
    suffix = uuid.uuid4().hex[:8]

    customer_id = f"C_STATE_{suffix}"

    paid_order_id = f"O_PAID_{suffix}"
    failed_order_id = f"O_FAILED_{suffix}"
    uncertain_order_id = (
        f"O_UNCERTAIN_{suffix}"
    )

    current_order_id = (
        f"O_CURRENT_{suffix}"
    )

    create_customer(
        customer_id=customer_id,
    )

    create_order(
        order_id=paid_order_id,
        customer_id=customer_id,
        amount_minor=80_000,
    )

    create_order(
        order_id=failed_order_id,
        customer_id=customer_id,
        amount_minor=90_000,
    )

    create_order(
        order_id=uncertain_order_id,
        customer_id=customer_id,
        amount_minor=100_000,
    )

    create_order(
        order_id=current_order_id,
        customer_id=customer_id,
        amount_minor=120_000,
    )

    paid_payment_id = (
        f"P_PAID_{suffix}"
    )

    failed_payment_id = (
        f"P_FAILED_{suffix}"
    )

    uncertain_payment_id = (
        f"P_UNCERTAIN_{suffix}"
    )

    create_payment(
        payment_id=paid_payment_id,
        order_id=paid_order_id,
        method="UPI",
        status="CAPTURED",
    )

    create_payment(
        payment_id=failed_payment_id,
        order_id=failed_order_id,
        method="UPI",
        status="FAILED",
        failure_reason="TECHNICAL_FAILURE",
    )

    create_payment(
        payment_id=uncertain_payment_id,
        order_id=uncertain_order_id,
        method="UPI",
        status="CREATED",
    )

    now = datetime.now(
        timezone.utc
    )

    record_payment_event(
        payment_id=paid_payment_id,
        provider_event_id=(
            f"EV_PAID_{suffix}"
        ),
        event_type="CAPTURED",
        event_time=(
            now
            - timedelta(minutes=20)
        ),
    )

    record_payment_event(
        payment_id=failed_payment_id,
        provider_event_id=(
            f"EV_FAILED_{suffix}"
        ),
        event_type="FAILED",
        event_time=(
            now
            - timedelta(minutes=15)
        ),
    )

    record_payment_event(
        payment_id=uncertain_payment_id,
        provider_event_id=(
            f"EV_UNCERTAIN_{suffix}"
        ),
        event_type="CREATED",
        event_time=(
            now
            - timedelta(minutes=10)
        ),
    )

    decision_time = (
        now
        + timedelta(seconds=5)
    )

    summary = build_prior_order_summary(
        customer_id=customer_id,
        current_order_id=current_order_id,
        decision_time=decision_time,
    )

    assert (
        summary["prior_checkout_count"]
        == 3
    )

    assert (
        summary["prior_success_count"]
        == 1
    )

    assert (
        summary["prior_failure_count"]
        == 1
    )

    assert (
        summary["prior_success_rate"]
        == pytest.approx(1 / 3)
    )

def test_customer_order_features_use_observable_order_history():
    suffix = uuid.uuid4().hex[:8]

    customer_id = (
        f"C_AMOUNT_STATE_{suffix}"
    )

    prior_order_1 = (
        f"O_AMOUNT_1_{suffix}"
    )

    prior_order_2 = (
        f"O_AMOUNT_2_{suffix}"
    )

    prior_order_3 = (
        f"O_AMOUNT_3_{suffix}"
    )

    current_order_id = (
        f"O_AMOUNT_CURRENT_{suffix}"
    )

    create_customer(
        customer_id=customer_id,
        contact_consent=False,
    )

    create_order(
        order_id=prior_order_1,
        customer_id=customer_id,
        amount_minor=80_000,
    )

    create_order(
        order_id=prior_order_2,
        customer_id=customer_id,
        amount_minor=100_000,
    )

    create_order(
        order_id=prior_order_3,
        customer_id=customer_id,
        amount_minor=120_000,
    )

    create_order(
        order_id=current_order_id,
        customer_id=customer_id,
        amount_minor=150_000,
    )

    decision_time = (
        datetime.now(timezone.utc)
        + timedelta(seconds=5)
    )

    features = (
        build_customer_order_features(
            customer_id=customer_id,
            current_order_id=current_order_id,
            decision_time=decision_time,
        )
    )

    assert (
        features["current_amount_minor"]
        == 150_000
    )

    assert (
        features["amount_ratio"]
        == pytest.approx(1.5)
    )

    assert (
        features["contact_consent"]
        is False
    )

    assert (
        features["customer_tenure_days"]
        >= 0
    )

def test_amount_ratio_is_neutral_without_prior_orders():
    suffix = uuid.uuid4().hex[:8]

    customer_id = (
        f"C_NEW_STATE_{suffix}"
    )

    current_order_id = (
        f"O_NEW_STATE_{suffix}"
    )

    create_customer(
        customer_id=customer_id,
    )

    create_order(
        order_id=current_order_id,
        customer_id=customer_id,
        amount_minor=200_000,
    )

    decision_time = (
        datetime.now(timezone.utc)
        + timedelta(seconds=5)
    )

    features = (
        build_customer_order_features(
            customer_id=customer_id,
            current_order_id=current_order_id,
            decision_time=decision_time,
        )
    )

    assert (
        features["amount_ratio"]
        == 1.0
    )

def test_payment_method_summary_separates_first_method_and_attempt_history():
    suffix = uuid.uuid4().hex[:8]

    customer_id = (
        f"C_METHOD_STATE_{suffix}"
    )

    prior_order_1 = (
        f"O_METHOD_1_{suffix}"
    )

    prior_order_2 = (
        f"O_METHOD_2_{suffix}"
    )

    current_order_id = (
        f"O_METHOD_CURRENT_{suffix}"
    )

    create_customer(
        customer_id=customer_id,
    )

    create_order(
        order_id=prior_order_1,
        customer_id=customer_id,
        amount_minor=100_000,
    )

    create_order(
        order_id=prior_order_2,
        customer_id=customer_id,
        amount_minor=110_000,
    )

    create_order(
        order_id=current_order_id,
        customer_id=customer_id,
        amount_minor=120_000,
    )

    upi_failed = (
        f"P_UPI_FAILED_{suffix}"
    )

    netbanking_success = (
        f"P_NB_SUCCESS_{suffix}"
    )

    upi_uncertain = (
        f"P_UPI_UNCERTAIN_{suffix}"
    )

    create_payment(
        payment_id=upi_failed,
        order_id=prior_order_1,
        method="UPI",
        status="FAILED",
        failure_reason="TECHNICAL_FAILURE",
    )

    create_payment(
        payment_id=netbanking_success,
        order_id=prior_order_1,
        method="NETBANKING",
        status="CAPTURED",
    )

    create_payment(
        payment_id=upi_uncertain,
        order_id=prior_order_2,
        method="UPI",
        status="CREATED",
    )

    now = datetime.now(
        timezone.utc
    )

    record_payment_event(
        payment_id=upi_failed,
        provider_event_id=(
            f"EV_UPI_FAIL_{suffix}"
        ),
        event_type="FAILED",
        event_time=(
            now
            - timedelta(minutes=30)
        ),
    )

    record_payment_event(
        payment_id=netbanking_success,
        provider_event_id=(
            f"EV_NB_CAPTURE_{suffix}"
        ),
        event_type="CAPTURED",
        event_time=(
            now
            - timedelta(minutes=20)
        ),
    )

    record_payment_event(
        payment_id=upi_uncertain,
        provider_event_id=(
            f"EV_UPI_CREATED_{suffix}"
        ),
        event_type="CREATED",
        event_time=(
            now
            - timedelta(minutes=10)
        ),
    )

    decision_time = (
        now
        + timedelta(seconds=5)
    )

    summary = (
        build_payment_method_summary(
            customer_id=customer_id,
            current_order_id=current_order_id,
            decision_time=decision_time,
        )
    )

    assert (
        summary["prior_upi_count"]
        == 2
    )

    assert (
        summary["prior_netbanking_count"]
        == 0
    )

    assert (
        summary["prior_upi_attempt_count"]
        == 2
    )

    assert (
        summary["prior_upi_success_count"]
        == 0
    )

    assert (
        summary["prior_upi_success_rate"]
        == 0.0
    )

    assert (
        summary[
            "prior_netbanking_attempt_count"
        ]
        == 1
    )

    assert (
        summary[
            "prior_netbanking_success_count"
        ]
        == 1
    )

    assert (
        summary[
            "prior_netbanking_success_rate"
        ]
        == 1.0
    )

def test_current_payment_features_use_latest_known_attempt():
    suffix = uuid.uuid4().hex[:8]

    customer_id = (
        f"C_CURRENT_PAY_{suffix}"
    )

    order_id = (
        f"O_CURRENT_PAY_{suffix}"
    )

    payment_1 = (
        f"P_CURRENT_1_{suffix}"
    )

    payment_2 = (
        f"P_CURRENT_2_{suffix}"
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
        payment_id=payment_1,
        order_id=order_id,
        method="UPI",
        status="FAILED",
        failure_reason=(
            "AUTHENTICATION_FAILURE"
        ),
    )

    create_payment(
        payment_id=payment_2,
        order_id=order_id,
        method="NETBANKING",
        status="FAILED",
        failure_reason=(
            "TECHNICAL_FAILURE"
        ),
    )

    decision_time = (
        datetime.now(timezone.utc)
        + timedelta(seconds=5)
    )

    features = (
        build_current_payment_features(
            current_order_id=order_id,
            decision_time=decision_time,
        )
    )

    assert (
        features["attempt_count"]
        == 2
    )

    assert (
        features["current_method"]
        == "NETBANKING"
    )

    assert (
        features["failure_category"]
        == "TECHNICAL_FAILURE"
    )

def test_unknown_failure_reason_uses_other_bucket():
    assert (
        normalize_failure_category(
            "SOME_NEW_PROVIDER_ERROR"
        )
        == "OTHER_CONFIRMED_FAILURE"
    )

def test_build_recovery_decision_state_from_operational_data():
    suffix = uuid.uuid4().hex[:8]

    customer_id = (
        f"C_FULL_STATE_{suffix}"
    )

    prior_order_id = (
        f"O_FULL_PRIOR_{suffix}"
    )

    current_order_id = (
        f"O_FULL_CURRENT_{suffix}"
    )

    prior_payment_id = (
        f"P_FULL_PRIOR_{suffix}"
    )

    current_payment_id = (
        f"P_FULL_CURRENT_{suffix}"
    )

    create_customer(
        customer_id=customer_id,
        contact_consent=True,
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

    create_payment(
        payment_id=prior_payment_id,
        order_id=prior_order_id,
        method="UPI",
        status="CAPTURED",
    )

    create_payment(
        payment_id=current_payment_id,
        order_id=current_order_id,
        method="NETBANKING",
        status="FAILED",
        failure_reason="TECHNICAL_FAILURE",
    )

    now = datetime.now(
        timezone.utc
    )

    record_payment_event(
        payment_id=prior_payment_id,
        provider_event_id=(
            f"EV_FULL_PRIOR_{suffix}"
        ),
        event_type="CAPTURED",
        event_time=(
            now
            - timedelta(minutes=20)
        ),
    )

    record_payment_event(
        payment_id=current_payment_id,
        provider_event_id=(
            f"EV_FULL_CURRENT_{suffix}"
        ),
        event_type="FAILED",
        event_time=(
            now
            - timedelta(minutes=5)
        ),
    )

    signals = RuntimeRecoverySignals(
        available_upi=True,
        available_credit_card=True,
        available_debit_card=False,
        available_netbanking=True,
        observed_rail_health=0.8,
        customer_active=False,
    )

    state = build_recovery_decision_state(
        current_order_id=current_order_id,
        decision_time=(
            now
            + timedelta(seconds=5)
        ),
        runtime_signals=signals,
    )

    assert (
        state.current_amount_minor
        == 150_000
    )

    assert (
        state.amount_ratio
        == pytest.approx(1.5)
    )

    assert (
        state.prior_checkout_count
        == 1
    )

    assert (
        state.prior_success_count
        == 1
    )

    assert (
        state.current_method
        == PaymentMethod.NETBANKING
    )

    assert (
        state.failure_category
        == FailureCategory.TECHNICAL_FAILURE
    )

    assert state.attempt_count == 1

    assert state.available_upi is True
    assert state.available_debit_card is False

    assert (
        state.observed_rail_health
        == pytest.approx(0.8)
    )

    assert state.contact_consent is True
    assert state.customer_active is False
