from backend.db import get_connection
from psycopg.rows import dict_row


def get_active_recovery_case_for_order(order_id):
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
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (order_id,))
            return cursor.fetchone()
        
def create_recovery_case(
    recovery_case_id,
    order_id,
    status="OPEN"
):
    query = """
        INSERT INTO recovery_cases (
            recovery_case_id,
            order_id,
            status
        )
        VALUES (%s, %s, %s)
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
        status
    )

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, values)
            return cursor.fetchone()