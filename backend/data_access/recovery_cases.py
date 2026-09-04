from backend.db import (
    get_connection,
)

from psycopg.rows import (
    dict_row,
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
