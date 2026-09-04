from backend.services.recovery_audit import (
    build_feature_snapshot,
)

from tests.test_recovery_decision_service import (
    build_test_state,
)


def test_feature_snapshot_is_json_safe():
    state = build_test_state()

    snapshot = build_feature_snapshot(
        state
    )

    assert (
        snapshot["current_method"]
        == "UPI"
    )

    assert (
        snapshot["failure_category"]
        == "TECHNICAL_FAILURE"
    )

    assert (
        snapshot["attempt_count"]
        == 2
    )