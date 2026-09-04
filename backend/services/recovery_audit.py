import uuid
from dataclasses import asdict

from backend.data_access.recovery import (
    create_recovery_decision_audit_bundle,
)

from simulator.models import (
    ActionType,
)


DEFAULT_MODEL_VERSION = (
    "s_learner_corrected_v1"
)


def action_label(action):
    """
    Convert a RecoveryAction into the canonical label
    stored in the database.
    """

    if (
        action.action_type
        == ActionType.SWITCH_METHOD
    ):
        return (
            "SWITCH_"
            + action.target_method.value
        )

    if (
        action.action_type
        == ActionType.APPROVED_OFFER
    ):
        return (
            "OFFER_"
            + str(
                int(
                    action.discount_percent
                )
            )
        )

    return action.action_type.value


def build_feature_snapshot(state):
    """
    Convert RecoveryDecisionState into a JSON-safe
    snapshot for audit storage.
    """

    snapshot = asdict(
        state
    )

    snapshot["current_method"] = (
        state.current_method.value
    )

    snapshot["failure_category"] = (
        state.failure_category.value
    )

    return snapshot


def persist_operational_decision(
    recovery_case_id,
    prediction_time,
    operational_decision,
    governor,
    model_version=DEFAULT_MODEL_VERSION,
):
    """
    Persist one Governor decision and all candidate
    action scores in one atomic database transaction.
    """

    decision_id = (
        "D_"
        + uuid.uuid4().hex[:12]
    )

    state = (
        operational_decision.state
    )

    governor_decision = (
        operational_decision
        .governor_decision
    )

    chosen_label = action_label(
        governor_decision.chosen_action
    )

    feature_snapshot = (
        build_feature_snapshot(
            state
        )
    )

    explanation = (
        f"Governor selected {chosen_label} "
        "based on deterministic policy "
        "and maximum positive incremental "
        "merchant utility."
    )

    decision_data = {
        "decision_id":
            decision_id,

        "recovery_case_id":
            recovery_case_id,

        "prediction_time":
            prediction_time,

        "model_version":
            model_version,

        "proposed_action":
            chosen_label,

        "feature_snapshot":
            feature_snapshot,

        "explanation":
            explanation,
    }

    score_by_label = {
        action_label(
            score.action
        ): score

        for score
        in governor_decision.scores
    }

    no_action_score = (
        score_by_label[
            "NO_ACTION"
        ]
    )

    baseline_probability = (
        no_action_score
        .predicted_recovery_probability
    )

    score_rows = []

    for action in (
        operational_decision.candidates
    ):
        label = action_label(
            action
        )

        policy_check = (
            governor.check_action_policy(
                state=state,
                action=action,
            )
        )

        score = (
            score_by_label.get(
                label
            )
        )

        # Action was structurally generated,
        # but deterministic policy blocked it.
        if (
            not policy_check.allowed
            or score is None
        ):
            score_rows.append(
                {
                    "decision_id":
                        decision_id,

                    "action_type":
                        label,

                    "is_eligible":
                        False,

                    "ineligible_reason":
                        policy_check.reason,

                    "predicted_success_probability":
                        None,

                    "uplift":
                        None,

                    "expected_incremental_utility_minor":
                        None,

                    "payment_processing_cost_minor":
                        None,

                    "action_cost_minor":
                        None,

                    "discount_cost_minor":
                        None,

                    "expected_merchant_value_minor":
                        None,
                }
            )

            continue

        probability = (
            score
            .predicted_recovery_probability
        )

        uplift = (
            probability
            - baseline_probability
        )

        action_cost_minor = 0.0
        discount_cost_minor = 0.0

        if (
            action.action_type
            == ActionType.NUDGE
        ):
            action_cost_minor = (
                governor.economics
                .nudge_cost_minor
            )

        elif (
            action.action_type
            == ActionType.SWITCH_METHOD
        ):
            action_cost_minor = (
                governor.economics
                .switch_cost_minor
            )

        elif (
            action.action_type
            == ActionType.APPROVED_OFFER
        ):
            action_cost_minor = (
                governor.economics
                .offer_execution_cost_minor
            )

            discount_percent = (
                action.discount_percent
                or 0.0
            )

            discount_if_recovered = (
                state.current_amount_minor
                * discount_percent
                / 100.0
            )

            discount_cost_minor = (
                probability
                * discount_if_recovered
            )

        score_rows.append(
            {
                "decision_id":
                    decision_id,

                "action_type":
                    label,

                "is_eligible":
                    True,

                "ineligible_reason":
                    None,

                "predicted_success_probability":
                    probability,

                "uplift":
                    uplift,

                "expected_incremental_utility_minor":
                    round(
                        score.incremental_utility_minor
                    ),

                # We currently do not model
                # processor fees separately.
                "payment_processing_cost_minor":
                    0,

                "action_cost_minor":
                    round(
                        action_cost_minor
                    ),

                "discount_cost_minor":
                    round(
                        discount_cost_minor
                    ),

                "expected_merchant_value_minor":
                    round(
                        score.expected_value_minor
                    ),
            }
        )

    return (
        create_recovery_decision_audit_bundle(
            decision_data=decision_data,
            score_rows=score_rows,
        )
    )