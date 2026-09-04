from backend.db import (
    get_connection,
)

from psycopg.rows import (
    dict_row,
)


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
