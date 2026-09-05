from backend.db import get_connection
from psycopg.rows import dict_row


def get_order_recovery_records(order_id):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM orders WHERE order_id = %s;", (order_id,))
            order = cursor.fetchone()
            if order is None:
                return None

            cursor.execute(
                "SELECT * FROM recovery_cases WHERE order_id = %s "
                "ORDER BY opened_at DESC LIMIT 1;",
                (order_id,),
            )
            case = cursor.fetchone()
            decision = action = outcome = None
            scores = []

            if case is not None:
                cursor.execute(
                    "SELECT * FROM recovery_decisions WHERE recovery_case_id = %s "
                    "ORDER BY prediction_time DESC LIMIT 1;",
                    (case["recovery_case_id"],),
                )
                decision = cursor.fetchone()

            if decision is not None:
                cursor.execute(
                    "SELECT * FROM decision_action_scores WHERE decision_id = %s "
                    "ORDER BY action_type;",
                    (decision["decision_id"],),
                )
                scores = cursor.fetchall()
                cursor.execute(
                    "SELECT * FROM recovery_actions WHERE decision_id = %s "
                    "ORDER BY created_at DESC LIMIT 1;",
                    (decision["decision_id"],),
                )
                action = cursor.fetchone()

            if case is not None:
                cursor.execute(
                    "SELECT * FROM recovery_outcomes WHERE recovery_case_id = %s "
                    "ORDER BY outcome_time DESC LIMIT 1;",
                    (case["recovery_case_id"],),
                )
                outcome = cursor.fetchone()

            cursor.execute(
                """
                SELECT
                    pe.*,
                    p.method,
                    p.failure_reason,
                    o.amount_minor,
                    o.currency
                FROM payment_events pe
                JOIN payments p ON p.payment_id = pe.payment_id
                JOIN orders o ON o.order_id = p.order_id
                WHERE p.order_id = %s
                ORDER BY pe.event_time, pe.received_at, pe.event_id;
                """,
                (order_id,),
            )
            payment_events = cursor.fetchall()

    return {
        "order": order,
        "case": case,
        "decision": decision,
        "candidate_scores": scores,
        "action": action,
        "outcome": outcome,
        "payment_events": payment_events,
    }


def list_recovery_case_records(limit):
    query = """
        SELECT
            rc.order_id, rc.recovery_case_id, rc.status,
            rc.closure_reason, rc.opened_at, rc.closed_at,
            rd.proposed_action AS chosen_action,
            ra.execution_status, ro.outcome_type
        FROM recovery_cases rc
        LEFT JOIN LATERAL (
            SELECT * FROM recovery_decisions
            WHERE recovery_case_id = rc.recovery_case_id
            ORDER BY prediction_time DESC LIMIT 1
        ) rd ON TRUE
        LEFT JOIN LATERAL (
            SELECT * FROM recovery_actions
            WHERE decision_id = rd.decision_id
            ORDER BY created_at DESC LIMIT 1
        ) ra ON TRUE
        LEFT JOIN LATERAL (
            SELECT * FROM recovery_outcomes
            WHERE recovery_case_id = rc.recovery_case_id
            ORDER BY outcome_time DESC LIMIT 1
        ) ro ON TRUE
        ORDER BY rc.opened_at DESC
        LIMIT %s;
    """
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (limit,))
            return cursor.fetchall()


def get_recovery_metric_records():
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    count(*) AS total_recovery_cases,
                    count(*) FILTER (WHERE closed_at IS NULL) AS open_cases,
                    count(*) FILTER (WHERE closed_at IS NOT NULL) AS closed_cases,
                    count(*) FILTER (WHERE closure_reason = 'RECOVERED') AS recovered_cases
                FROM recovery_cases;
                """
            )
            totals = cursor.fetchone()
            cursor.execute(
                "SELECT COALESCE(sum(recovered_amount_minor), 0) "
                "AS recovered_order_value_minor FROM recovery_outcomes "
                "WHERE outcome_type = 'RECOVERED';"
            )
            totals.update(cursor.fetchone())
            cursor.execute(
                "SELECT action_type, count(*) AS count FROM recovery_actions "
                "GROUP BY action_type ORDER BY action_type;"
            )
            action_counts = {
                row["action_type"]: row["count"]
                for row in cursor.fetchall()
            }
    return {**totals, "action_counts": action_counts}
