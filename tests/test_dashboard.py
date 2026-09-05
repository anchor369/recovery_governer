import json
import tomllib
from pathlib import Path
from urllib.error import URLError

import pytest

from dashboard.api_client import RecoveryAPIClient, RecoveryAPIUnavailable
from dashboard.components.action_matrix import (
    build_action_rows,
    humanize_action,
    humanize_method,
)
from dashboard.components.timeline import build_timeline_rows
from dashboard.config import load_config, normalize_base_url
from dashboard.pages.recovery_lab import (
    capture_decision_snapshot,
    chosen_score,
    comparison_summary,
    extract_identifiers,
    safety_message,
)


def test_dashboard_config_normalizes_api_url(monkeypatch):
    monkeypatch.setenv("RECOVERY_API_BASE_URL", "http://localhost:8123/")
    monkeypatch.setenv("RECOVERY_API_TIMEOUT", "12.5")
    config = load_config()
    assert config.api_base_url == "http://localhost:8123"
    assert config.api_timeout == 12.5
    assert normalize_base_url(None) == "http://127.0.0.1:8000"


def test_api_client_constructs_expected_http_request(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"workflow_state":"DECIDED"}'

    def fake_urlopen(request, timeout):
        captured.update(
            method=request.get_method(),
            url=request.full_url,
            payload=json.loads(request.data),
            timeout=timeout,
        )
        return Response()

    monkeypatch.setattr("dashboard.api_client.urlopen", fake_urlopen)
    client = RecoveryAPIClient("http://api.test/", timeout=9)
    result = client.run_recovery("O_123", {"customer_active": False})

    assert captured == {
        "method": "POST",
        "url": "http://api.test/api/orders/O_123/recovery",
        "payload": {"customer_active": False},
        "timeout": 9.0,
    }
    assert result["workflow_state"] == "DECIDED"

    client.create_demo_scenario("two_failures", "loyal_returning")
    assert captured["url"] == "http://api.test/api/demo/scenarios"
    assert captured["payload"] == {
        "preset": "two_failures",
        "customer_profile": "loyal_returning",
    }


def test_api_client_reports_unavailable_backend(monkeypatch):
    def unavailable_urlopen(_request, timeout):
        assert timeout == 2.0
        raise URLError("connection refused")

    monkeypatch.setattr("dashboard.api_client.urlopen", unavailable_urlopen)
    client = RecoveryAPIClient("http://api.test", timeout=2)

    with pytest.raises(
        RecoveryAPIUnavailable, match="FastAPI is unavailable at http://api.test"
    ):
        client.health_check()


def test_recovery_lab_extracts_only_api_identifiers():
    scenario = {"order_id": "O_1"}
    workflow = {
        "case": {"recovery_case_id": "RC_1"},
        "decision": {"decision_id": "D_1"},
        "execution_action": {"action_id": "A_1"},
    }
    assert extract_identifiers(scenario, workflow) == {
        "order_id": "O_1",
        "case_id": "RC_1",
        "decision_id": "D_1",
        "action_id": "A_1",
    }


def test_action_matrix_uses_persisted_score_fields():
    score = {
        "action_type": "NUDGE",
        "is_eligible": True,
        "ineligible_reason": None,
        "predicted_success_probability": 0.75,
        "uplift": 0.12,
        "expected_merchant_value_minor": 12345,
        "expected_incremental_utility_minor": 2345,
    }
    rows = build_action_rows([score], "NUDGE")
    assert rows[0]["Recovery Action"] == "Customer nudge"
    assert rows[0]["Predicted Recovery"] == "75.0%"
    assert rows[0]["Lift vs Natural"] == "+12.0 pp"
    assert rows[0]["Incremental Value"] == "INR 23.45"
    assert rows[0]["Selected"] is True
    assert chosen_score({"chosen_action": "NUDGE", "candidate_action_scores": [score]}) == score


def test_safety_states_do_not_claim_ai_decision():
    assert safety_message({"workflow_state": "STOP"})[0] == "PAID → STOP"
    assert safety_message({"workflow_state": "WAIT_FOR_TRUTH"})[0] == (
        "UNCERTAIN → WAIT FOR TRUTH"
    )
    assert safety_message({"workflow_state": "ALLOW_NATURAL_RETRY"})[0] == (
        "1 CONFIRMED FAILURE → NATURAL RETRY"
    )
    assert humanize_action("NO_ACTION") == "No action"


def test_comparison_and_decision_snapshot_keep_decision_time_evidence():
    workflow = {
        "reason": "RECOVERY_DECISION_CREATED",
        "chosen_action": "NUDGE",
        "execution_action": {"execution_status": "EXECUTED"},
        "candidate_action_scores": [
            {
                "action_type": "NO_ACTION",
                "predicted_success_probability": 0.60,
                "expected_merchant_value_minor": 30_000,
                "uplift": 0.0,
                "expected_incremental_utility_minor": 0,
            },
            {
                "action_type": "NUDGE",
                "predicted_success_probability": 0.64,
                "expected_merchant_value_minor": 31_500,
                "uplift": 0.04,
                "expected_incremental_utility_minor": 1_500,
            },
        ],
    }
    scenario = {
        "journey": {
            "customer": {"contact_consent": True},
            "order": {"financial_truth": "UNPAID"},
            "recovery_gate": {"eligible": True},
        },
        "metadata": {"runtime_signals": {"customer_active": False}},
    }
    snapshot = capture_decision_snapshot(
        scenario,
        workflow,
        {"financial_truth": "UNPAID"},
    )
    comparison = comparison_summary(workflow)

    assert snapshot["financial_truth"] == "UNPAID"
    assert snapshot["execution_status"] == "EXECUTED"
    assert comparison["baseline_probability"] == 0.60
    assert comparison["chosen_probability"] == 0.64
    assert comparison["incremental_value_minor"] == 1_500


def test_timeline_rows_prioritize_payment_story_over_ids():
    rows = build_timeline_rows([
        {
            "timestamp": "2026-09-05T14:45:30+05:30",
            "type": "PAYMENT_EVENT",
            "title": "FAILED",
            "details": {
                "payment_id": "P_INTERNAL",
                "provider_event_id": "EV_INTERNAL",
                "method": "UPI",
                "failure_reason": "AUTHENTICATION_FAILURE",
                "amount_minor": 150_000,
            },
        }
    ])

    assert rows == [{
        "time": "14:45:30",
        "title": "Payment attempt failed",
        "summary": "UPI · Authentication Failure",
        "tone": "danger",
    }]
    assert humanize_method("UPI") == "UPI"


def test_same_second_timeline_uses_merchant_lifecycle_order():
    rows = build_timeline_rows([
        {
            "timestamp": "2026-09-05T14:47:36.100000+05:30",
            "type": "RECOVERY_DECISION",
            "title": "NUDGE",
            "details": {},
        },
        {
            "timestamp": "2026-09-05T14:47:36.200000+05:30",
            "type": "RECOVERY_CASE_OPENED",
            "title": "Recovery case opened",
            "details": {},
        },
        {
            "timestamp": "2026-09-05T14:47:36.300000+05:30",
            "type": "RECOVERY_ACTION",
            "title": "NUDGE",
            "details": {"execution_status": "EXECUTED"},
        },
    ])

    assert [row["title"] for row in rows] == [
        "Recovery case opened",
        "Recovery decision",
        "Action executed",
    ]


def test_streamlit_builtin_page_navigation_is_disabled():
    config = tomllib.loads(Path(".streamlit/config.toml").read_text(encoding="utf-8"))
    assert config["client"]["showSidebarNavigation"] is False
