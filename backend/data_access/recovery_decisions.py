from backend.db import (
    get_connection,
)

from psycopg.rows import (
    dict_row,
)

from psycopg.types.json import (
    Jsonb,
)


def _insert_recovery_decision(
    cursor,
    decision_id,
    recovery_case_id,
    prediction_time,
    model_version,
    proposed_action,
    feature_snapshot,
    explanation=None,
):
    query = """
        INSERT INTO recovery_decisions (
            decision_id,
            recovery_case_id,
            prediction_time,
            model_version,
            proposed_action,
            feature_snapshot,
            explanation
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        RETURNING
            decision_id,
            recovery_case_id,
            prediction_time,
            model_version,
            proposed_action,
            feature_snapshot,
            explanation,
            created_at;
    """

    values = (
        decision_id,
        recovery_case_id,
        prediction_time,
        model_version,
        proposed_action,
        Jsonb(
            feature_snapshot
        ),
        explanation,
    )

    cursor.execute(
        query,
        values,
    )

    return cursor.fetchone()


def create_recovery_decision(
    decision_id,
    recovery_case_id,
    prediction_time,
    model_version,
    proposed_action,
    feature_snapshot,
    explanation=None,
):
    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            return _insert_recovery_decision(
                cursor=cursor,
                decision_id=decision_id,
                recovery_case_id=(
                    recovery_case_id
                ),
                prediction_time=(
                    prediction_time
                ),
                model_version=model_version,
                proposed_action=(
                    proposed_action
                ),
                feature_snapshot=(
                    feature_snapshot
                ),
                explanation=explanation,
            )


def _insert_decision_action_score(
    cursor,
    decision_id,
    action_type,
    is_eligible,
    ineligible_reason,
    predicted_success_probability,
    uplift,
    expected_incremental_utility_minor,
    payment_processing_cost_minor,
    action_cost_minor,
    discount_cost_minor,
    expected_merchant_value_minor,
):
    query = """
        INSERT INTO decision_action_scores (
            decision_id,
            action_type,
            is_eligible,
            ineligible_reason,
            predicted_success_probability,
            uplift,
            expected_incremental_utility_minor,
            payment_processing_cost_minor,
            action_cost_minor,
            discount_cost_minor,
            expected_merchant_value_minor
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        RETURNING
            decision_id,
            action_type,
            is_eligible,
            ineligible_reason,
            predicted_success_probability,
            uplift,
            expected_incremental_utility_minor,
            payment_processing_cost_minor,
            action_cost_minor,
            discount_cost_minor,
            expected_merchant_value_minor;
    """

    values = (
        decision_id,
        action_type,
        is_eligible,
        ineligible_reason,
        predicted_success_probability,
        uplift,
        expected_incremental_utility_minor,
        payment_processing_cost_minor,
        action_cost_minor,
        discount_cost_minor,
        expected_merchant_value_minor,
    )

    cursor.execute(
        query,
        values,
    )

    return cursor.fetchone()


def create_decision_action_score(
    decision_id,
    action_type,
    is_eligible,
    ineligible_reason,
    predicted_success_probability,
    uplift,
    expected_incremental_utility_minor,
    payment_processing_cost_minor,
    action_cost_minor,
    discount_cost_minor,
    expected_merchant_value_minor,
):
    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            return _insert_decision_action_score(
                cursor=cursor,
                decision_id=decision_id,
                action_type=action_type,
                is_eligible=is_eligible,
                ineligible_reason=(
                    ineligible_reason
                ),
                predicted_success_probability=(
                    predicted_success_probability
                ),
                uplift=uplift,
                expected_incremental_utility_minor=(
                    expected_incremental_utility_minor
                ),
                payment_processing_cost_minor=(
                    payment_processing_cost_minor
                ),
                action_cost_minor=(
                    action_cost_minor
                ),
                discount_cost_minor=(
                    discount_cost_minor
                ),
                expected_merchant_value_minor=(
                    expected_merchant_value_minor
                ),
            )


def create_recovery_decision_audit_bundle(
    decision_data,
    score_rows,
):
    """
    Insert the decision header and every action score
    in one database transaction.

    If any insert fails, the entire transaction rolls back.
    """

    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:

            decision = (
                _insert_recovery_decision(
                    cursor=cursor,
                    **decision_data,
                )
            )

            scores = []

            for score_data in score_rows:
                score = (
                    _insert_decision_action_score(
                        cursor=cursor,
                        **score_data,
                    )
                )

                scores.append(
                    score
                )

            return {
                "decision": decision,
                "scores": scores,
            }


def get_recovery_decision(
    decision_id,
):
    query = """
        SELECT
            decision_id,
            recovery_case_id,
            prediction_time,
            model_version,
            proposed_action,
            feature_snapshot,
            explanation,
            created_at
        FROM recovery_decisions
        WHERE decision_id = %s;
    """

    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            cursor.execute(
                query,
                (decision_id,),
            )

            return cursor.fetchone()
