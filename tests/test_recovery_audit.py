import uuid
from datetime import (
    datetime,
    timezone,
)
import pytest

from backend.data_access.payments import (
    create_customer,
    create_order,
)

from backend.data_access.recovery import (
    create_decision_action_score,
    create_recovery_case,
    create_recovery_decision,
    create_recovery_decision_audit_bundle,
    get_recovery_decision,
)

def test_create_recovery_decision():
    suffix = uuid.uuid4().hex[:8]

    customer_id = (
        f"C_AUDIT_{suffix}"
    )

    order_id = (
        f"O_AUDIT_{suffix}"
    )

    recovery_case_id = (
        f"RC_AUDIT_{suffix}"
    )

    decision_id = (
        f"D_AUDIT_{suffix}"
    )

    create_customer(
        customer_id=customer_id,
    )

    create_order(
        order_id=order_id,
        customer_id=customer_id,
        amount_minor=150_000,
    )

    create_recovery_case(
        recovery_case_id=(
            recovery_case_id
        ),
        order_id=order_id,
    )

    prediction_time = datetime.now(
        timezone.utc
    )

    decision = (
        create_recovery_decision(
            decision_id=decision_id,
            recovery_case_id=(
                recovery_case_id
            ),
            prediction_time=(
                prediction_time
            ),
            model_version=(
                "s_learner_corrected_v1"
            ),
            proposed_action="NUDGE",
            feature_snapshot={
                "attempt_count": 2,
                "amount_ratio": 1.5,
                "contact_consent": True,
            },
            explanation=(
                "NUDGE had the highest "
                "positive incremental "
                "merchant value."
            ),
        )
    )

    assert (
        decision["decision_id"]
        == decision_id
    )

    assert (
        decision["proposed_action"]
        == "NUDGE"
    )

    assert (
        decision["model_version"]
        == "s_learner_corrected_v1"
    )

    assert (
        decision["feature_snapshot"][
            "attempt_count"
        ]
        == 2
    )

def test_create_decision_action_score():
    suffix = uuid.uuid4().hex[:8]

    customer_id = (
        f"C_SCORE_{suffix}"
    )

    order_id = (
        f"O_SCORE_{suffix}"
    )

    recovery_case_id = (
        f"RC_SCORE_{suffix}"
    )

    decision_id = (
        f"D_SCORE_{suffix}"
    )

    create_customer(
        customer_id=customer_id,
    )

    create_order(
        order_id=order_id,
        customer_id=customer_id,
        amount_minor=150_000,
    )

    create_recovery_case(
        recovery_case_id=(
            recovery_case_id
        ),
        order_id=order_id,
    )

    create_recovery_decision(
        decision_id=decision_id,
        recovery_case_id=(
            recovery_case_id
        ),
        prediction_time=(
            datetime.now(
                timezone.utc
            )
        ),
        model_version=(
            "s_learner_corrected_v1"
        ),
        proposed_action="NUDGE",
        feature_snapshot={
            "attempt_count": 2,
        },
        explanation=(
            "Test decision."
        ),
    )

    score = (
        create_decision_action_score(
            decision_id=decision_id,

            action_type="NUDGE",

            is_eligible=True,

            ineligible_reason=None,

            predicted_success_probability=(
                0.7299
            ),

            uplift=0.0208,

            expected_incremental_utility_minor=(
                890
            ),

            payment_processing_cost_minor=0,

            action_cost_minor=200,

            discount_cost_minor=0,

            expected_merchant_value_minor=(
                38_118
            ),
        )
    )

    assert (
        score["decision_id"]
        == decision_id
    )

    assert (
        score["action_type"]
        == "NUDGE"
    )

    assert (
        score[
            "predicted_success_probability"
        ]
        == 0.7299
    )

    assert (
        score["uplift"]
        == 0.0208
    )

    assert (
        score[
            "expected_incremental_utility_minor"
        ]
        == 890
    )

    assert (
        score[
            "expected_merchant_value_minor"
        ]
        == 38_118
    )

def test_audit_bundle_rolls_back_if_one_score_fails():
    suffix = uuid.uuid4().hex[:8]

    customer_id = (
        f"C_ROLLBACK_{suffix}"
    )

    order_id = (
        f"O_ROLLBACK_{suffix}"
    )

    recovery_case_id = (
        f"RC_ROLLBACK_{suffix}"
    )

    decision_id = (
        f"D_ROLLBACK_{suffix}"
    )

    create_customer(
        customer_id=customer_id,
    )

    create_order(
        order_id=order_id,
        customer_id=customer_id,
        amount_minor=150_000,
    )

    create_recovery_case(
        recovery_case_id=recovery_case_id,
        order_id=order_id,
    )

    decision_data = {
        "decision_id":
            decision_id,

        "recovery_case_id":
            recovery_case_id,

        "prediction_time":
            datetime.now(
                timezone.utc
            ),

        "model_version":
            "s_learner_corrected_v1",

        "proposed_action":
            "NUDGE",

        "feature_snapshot":
            {
                "attempt_count": 2,
            },

        "explanation":
            "Rollback test.",
    }

    score_rows = [
        {
            "decision_id":
                decision_id,

            "action_type":
                "NO_ACTION",

            "is_eligible":
                True,

            "ineligible_reason":
                None,

            "predicted_success_probability":
                0.60,

            "uplift":
                0.0,

            "expected_incremental_utility_minor":
                0,

            "payment_processing_cost_minor":
                0,

            "action_cost_minor":
                0,

            "discount_cost_minor":
                0,

            "expected_merchant_value_minor":
                30_000,
        },

        # Deliberately same action_type again.
        # This violates the primary key:
        # (decision_id, action_type)
        {
            "decision_id":
                decision_id,

            "action_type":
                "NO_ACTION",

            "is_eligible":
                True,

            "ineligible_reason":
                None,

            "predicted_success_probability":
                0.61,

            "uplift":
                0.01,

            "expected_incremental_utility_minor":
                100,

            "payment_processing_cost_minor":
                0,

            "action_cost_minor":
                0,

            "discount_cost_minor":
                0,

            "expected_merchant_value_minor":
                30_100,
        },
    ]

    with pytest.raises(Exception):
        create_recovery_decision_audit_bundle(
            decision_data=decision_data,
            score_rows=score_rows,
        )

    persisted_decision = (
        get_recovery_decision(
            decision_id
        )
    )

    assert persisted_decision is None