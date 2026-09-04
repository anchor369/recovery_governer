from backend.db import (
    get_connection,
)

from psycopg.rows import (
    dict_row,
)

from psycopg.types.json import (
    Jsonb,
)


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
