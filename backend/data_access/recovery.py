from backend.db import (
    get_connection,
)

from psycopg.rows import (
    dict_row,
)

from psycopg.types.json import (
    Jsonb,
)


WORKFLOW_FAILURE_REASONS = {
    "DECISION_FAILED",
    "AUDIT_FAILED",
    "ACTION_CREATION_FAILED",
}


def get_active_recovery_case_for_order(
    order_id,
):
    query = """
        SELECT
            recovery_case_id,
            order_id,
            status,
            closure_reason,
            opened_at,
            closed_at
        FROM recovery_cases
        WHERE order_id = %s
          AND closed_at IS NULL;
    """

    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            cursor.execute(
                query,
                (order_id,),
            )

            return cursor.fetchone()


def create_recovery_case(
    recovery_case_id,
    order_id,
    status="OPEN",
):
    query = """
        INSERT INTO recovery_cases (
            recovery_case_id,
            order_id,
            status
        )
        VALUES (
            %s,
            %s,
            %s
        )
        RETURNING
            recovery_case_id,
            order_id,
            status,
            closure_reason,
            opened_at,
            closed_at;
    """

    values = (
        recovery_case_id,
        order_id,
        status,
    )

    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            cursor.execute(
                query,
                values,
            )

            return cursor.fetchone()


def close_recovery_case_for_workflow_failure(
    recovery_case_id,
    closure_reason,
):
    """Durably resolve an active case after orchestration failure."""

    if closure_reason not in WORKFLOW_FAILURE_REASONS:
        raise ValueError(
            "Unsupported workflow failure reason: "
            f"{closure_reason}"
        )

    query = """
        UPDATE recovery_cases
        SET
            status = 'CLOSED',
            closure_reason = %s,
            closed_at = now()
        WHERE recovery_case_id = %s
          AND closed_at IS NULL
        RETURNING
            recovery_case_id,
            order_id,
            status,
            closure_reason,
            opened_at,
            closed_at;
    """

    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            cursor.execute(
                query,
                (
                    closure_reason,
                    recovery_case_id,
                ),
            )

            return cursor.fetchone()


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

def create_recovery_action(
    action_id,
    decision_id,
    action_type,
    execution_status,
    blocked_reason=None,
    policy_checks=None,
    executed_at=None,
):
    query = """
        INSERT INTO recovery_actions (
            action_id,
            decision_id,
            action_type,
            execution_status,
            blocked_reason,
            policy_checks,
            executed_at
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
            action_id,
            decision_id,
            action_type,
            execution_status,
            blocked_reason,
            policy_checks,
            executed_at,
            created_at;
    """

    values = (
        action_id,
        decision_id,
        action_type,
        execution_status,
        blocked_reason,

        (
            Jsonb(policy_checks)
            if policy_checks is not None
            else None
        ),

        executed_at,
    )

    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            cursor.execute(
                query,
                values,
            )

            return cursor.fetchone()

def _transition_pending_recovery_action(
    cursor,
    action_id,
    execution_status,
    blocked_reason=None,
    executed_at=None,
):
    query = """
        UPDATE recovery_actions
        SET
            execution_status = %s,
            blocked_reason = %s,
            executed_at = %s
        WHERE action_id = %s
          AND execution_status = 'PENDING'
        RETURNING
            action_id,
            decision_id,
            action_type,
            execution_status,
            blocked_reason,
            policy_checks,
            executed_at,
            created_at;
    """

    values = (
        execution_status,
        blocked_reason,
        executed_at,
        action_id,
    )

    cursor.execute(
        query,
        values,
    )

    return cursor.fetchone()


def transition_pending_recovery_action(
    action_id,
    execution_status,
    blocked_reason=None,
    executed_at=None,
):
    """Atomically move an action out of PENDING at most once."""

    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            action = _transition_pending_recovery_action(
                cursor=cursor,
                action_id=action_id,
                execution_status=execution_status,
                blocked_reason=blocked_reason,
                executed_at=executed_at,
            )

            if action is not None:
                return {
                    "transition_applied": True,
                    "action": action,
                }

            cursor.execute(
                """
                SELECT
                    action_id,
                    decision_id,
                    action_type,
                    execution_status,
                    blocked_reason,
                    policy_checks,
                    executed_at,
                    created_at
                FROM recovery_actions
                WHERE action_id = %s;
                """,
                (action_id,),
            )

            existing_action = cursor.fetchone()

            if existing_action is None:
                raise ValueError(
                    f"Recovery action does not exist: {action_id}"
                )

            return {
                "transition_applied": False,
                "action": existing_action,
            }

def get_recovery_outcome_context(
    recovery_case_id,
    action_id,
    payment_id,
):
    """
    Read everything required to verify that a
    captured payment can legitimately close a
    particular recovery case.
    """

    query = """
        SELECT
            rc.recovery_case_id,
            rc.order_id AS recovery_order_id,
            rc.status AS recovery_case_status,
            rc.opened_at,
            rc.closed_at,

            o.amount_minor AS order_amount_minor,

            ra.action_id,
            ra.action_type,
            ra.execution_status,

            p.payment_id,
            p.order_id AS payment_order_id,
            p.status AS materialized_payment_status,

            latest_event.event_type
                AS latest_payment_event_type

        FROM recovery_cases rc

        JOIN orders o
            ON o.order_id = rc.order_id

        JOIN recovery_decisions rd
            ON rd.recovery_case_id
               = rc.recovery_case_id

        JOIN recovery_actions ra
            ON ra.decision_id
               = rd.decision_id

        JOIN payments p
            ON p.payment_id = %s

        LEFT JOIN LATERAL (
            SELECT
                pe.event_type
            FROM payment_events pe
            WHERE pe.payment_id = p.payment_id
            ORDER BY
                pe.event_time DESC,
                pe.received_at DESC,
                pe.event_id DESC
            LIMIT 1
        ) latest_event
            ON TRUE

        WHERE
            rc.recovery_case_id = %s
            AND ra.action_id = %s;
    """

    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            cursor.execute(
                query,
                (
                    payment_id,
                    recovery_case_id,
                    action_id,
                ),
            )

            return cursor.fetchone()

def create_recovered_outcome_and_close_case(
    outcome_id,
    recovery_case_id,
    action_id,
    payment_id,
    recovered_amount_minor,
    outcome_time,
    time_to_recovery_seconds,
):
    """
    Store the recovered outcome and close the
    recovery case in one database transaction.
    """

    with get_connection() as connection:
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:

            outcome_query = """
                INSERT INTO recovery_outcomes (
                    outcome_id,
                    recovery_case_id,
                    action_id,
                    payment_id,
                    outcome_type,
                    recovered_amount_minor,
                    outcome_time,
                    time_to_recovery_seconds
                )
                VALUES (
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
                    outcome_id,
                    recovery_case_id,
                    action_id,
                    payment_id,
                    outcome_type,
                    recovered_amount_minor,
                    outcome_time,
                    time_to_recovery_seconds,
                    created_at;
            """

            cursor.execute(
                outcome_query,
                (
                    outcome_id,
                    recovery_case_id,
                    action_id,
                    payment_id,
                    "RECOVERED",
                    recovered_amount_minor,
                    outcome_time,
                    time_to_recovery_seconds,
                ),
            )

            outcome = cursor.fetchone()

            close_query = """
                UPDATE recovery_cases
                SET
                    status = 'CLOSED',
                    closure_reason = 'RECOVERED',
                    closed_at = %s
                WHERE
                    recovery_case_id = %s
                    AND closed_at IS NULL
                RETURNING
                    recovery_case_id,
                    order_id,
                    status,
                    closure_reason,
                    opened_at,
                    closed_at;
            """

            cursor.execute(
                close_query,
                (
                    outcome_time,
                    recovery_case_id,
                ),
            )

            recovery_case = (
                cursor.fetchone()
            )

            if recovery_case is None:
                raise ValueError(
                    "Recovery case was already closed "
                    "or does not exist."
                )

            return {
                "outcome": outcome,
                "case": recovery_case,
            }
