"""Boundary tests for the FastAPI control plane."""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.data_access.payments import (
    create_customer,
    create_order,
    create_payment,
    get_payment_events_for_order_before_time,
)


client = TestClient(app)


def create_payment_record():
    suffix = uuid.uuid4().hex[:10]
    customer_id = f"C_API_{suffix}"
    order_id = f"O_API_{suffix}"
    payment_id = f"P_API_{suffix}"
    create_customer(customer_id)
    create_order(order_id, customer_id, amount_minor=100_000)
    create_payment(payment_id, order_id, method="UPI", status="CREATED")
    return payment_id, f"EV_API_{suffix}"


def create_demo(preset):
    response = client.post(
        "/api/demo/scenarios",
        json={"preset": preset, "customer_profile": "new_customer"},
    )
    assert response.status_code == 200
    return response.json()


def run_recovery(scenario):
    signals = scenario["metadata"]["runtime_signals"]
    return client.post(
        f"/api/orders/{scenario['order_id']}/recovery",
        json=signals,
    )


def test_health_checks_database_and_model():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "connected",
        "model": "loaded",
    }


def test_payment_event_first_delivery():
    payment_id, event_id = create_payment_record()
    response = client.post(
        "/api/payment-events",
        json={
            "payment_id": payment_id,
            "provider_event_id": event_id,
            "event_type": "FAILED",
            "event_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 200
    assert response.json()["created"] is True
    assert response.json()["payment_status"] == "FAILED"


def test_payment_event_exact_duplicate():
    payment_id, event_id = create_payment_record()
    payload = {
        "payment_id": payment_id,
        "provider_event_id": event_id,
        "event_type": "AUTHORIZED",
        "event_time": datetime.now(timezone.utc).isoformat(),
        "raw_payload": {"attempt": 1},
    }
    first = client.post("/api/payment-events", json=payload)
    duplicate = client.post("/api/payment-events", json=payload)
    assert first.status_code == 200
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["event"]["event_id"] == first.json()["event"]["event_id"]


def test_payment_event_conflict_maps_to_409():
    payment_id, event_id = create_payment_record()
    event_time = datetime.now(timezone.utc).isoformat()
    base = {
        "payment_id": payment_id,
        "provider_event_id": event_id,
        "event_type": "FAILED",
        "event_time": event_time,
    }
    assert client.post("/api/payment-events", json=base).status_code == 200
    response = client.post(
        "/api/payment-events",
        json={**base, "raw_payload": {"different": True}},
    )
    assert response.status_code == 409
    assert "different payment evidence" in response.json()["detail"]


def test_payment_event_invalid_request_maps_to_422():
    response = client.post(
        "/api/payment-events",
        json={
            "payment_id": "P_MISSING",
            "provider_event_id": " ",
            "event_type": "FAILED",
            "event_time": "2026-09-05T12:00:00",
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("preset", "expected_payments"),
    [("two_failures", 2), ("payment_uncertain", 1), ("already_paid", 1)],
)
def test_demo_scenario_presets(preset, expected_payments):
    scenario = create_demo(preset)
    assert scenario["preset"] == preset
    assert len(scenario["payment_ids"]) == expected_payments
    assert scenario["customer_id"]
    assert scenario["order_id"]
    assert scenario["journey"]["current_payment_attempts"]


def test_two_failures_showcase_is_eligible_and_not_an_active_retry():
    scenario = create_demo("two_failures")

    assert scenario["metadata"]["contact_consent"] is True
    assert scenario["metadata"]["runtime_signals"]["customer_active"] is False
    assert scenario["journey"]["order"]["financial_truth"] == "UNPAID"
    assert scenario["journey"]["recovery_gate"]["confirmed_failure_count"] == 2
    assert scenario["journey"]["recovery_gate"]["eligible"] is True

    workflow = run_recovery(scenario)
    assert workflow.status_code == 200
    result = workflow.json()
    assert result["workflow_state"] == "DECIDED"
    assert result["chosen_action"] == result["decision"]["proposed_action"]
    assert result["chosen_action"] in {
        score["action_type"] for score in result["candidate_action_scores"]
    }


def test_active_customer_remains_an_explicit_safety_scenario():
    scenario = create_demo("active_customer")
    assert scenario["metadata"]["contact_consent"] is True
    assert scenario["metadata"]["runtime_signals"]["customer_active"] is True


@pytest.mark.parametrize(
    ("profile", "orders", "successes", "failures", "median_amount", "amount_ratio"),
    [
        ("new_customer", 0, 0, 0, None, 1.0),
        ("loyal_returning", 4, 4, 0, 150_000, 1.0),
        ("mixed_history", 4, 2, 2, 165_000, 150_000 / 165_000),
    ],
)
def test_demo_customer_profiles_create_real_time_safe_history(
    profile, orders, successes, failures, median_amount, amount_ratio
):
    response = client.post(
        "/api/demo/scenarios",
        json={"preset": "two_failures", "customer_profile": profile},
    )
    assert response.status_code == 200
    scenario = response.json()
    history = scenario["journey"]["history"]
    current_created_at = datetime.fromisoformat(
        scenario["journey"]["order"]["created_at"]
    )

    assert scenario["customer_profile"] == profile
    assert history["prior_checkout_count"] == orders
    assert history["prior_success_count"] == successes
    assert history["prior_failure_count"] == failures
    assert history["prior_uncertain_count"] == 0
    assert history["median_prior_amount_minor"] == median_amount
    assert history["amount_ratio"] == pytest.approx(amount_ratio)
    assert all(
        datetime.fromisoformat(order["created_at"]) < current_created_at
        for order in history["orders"]
    )


def test_demo_history_is_derived_into_persisted_decision_snapshot():
    scenario_response = client.post(
        "/api/demo/scenarios",
        json={"preset": "two_failures", "customer_profile": "loyal_returning"},
    )
    scenario = scenario_response.json()
    workflow = run_recovery(scenario)
    assert workflow.status_code == 200
    snapshot = workflow.json()["decision"]["feature_snapshot"]

    assert snapshot["prior_checkout_count"] == 4
    assert snapshot["prior_success_count"] == 4
    assert snapshot["prior_failure_count"] == 0
    assert snapshot["amount_ratio"] == pytest.approx(1.0)
    assert snapshot["prior_upi_attempt_count"] == 2
    assert snapshot["prior_upi_success_count"] == 2


def test_demo_history_payment_and_event_times_precede_decision_time():
    response = client.post(
        "/api/demo/scenarios",
        json={"preset": "two_failures", "customer_profile": "mixed_history"},
    )
    scenario = response.json()
    decision_time = datetime.now(timezone.utc)

    for order in scenario["journey"]["history"]["orders"]:
        events = get_payment_events_for_order_before_time(
            order_id=order["order_id"],
            before_time=decision_time,
        )
        assert events
        assert all(event["payment_created_at"] < decision_time for event in events)
        assert all(event["event_time"] < decision_time for event in events)
        assert all(event["received_at"] < decision_time for event in events)


@pytest.mark.parametrize(
    ("preset", "expected_state"),
    [
        ("two_failures", "DECIDED"),
        ("already_paid", "STOP"),
        ("payment_uncertain", "WAIT_FOR_TRUTH"),
        ("natural_retry", "ALLOW_NATURAL_RETRY"),
    ],
)
def test_recovery_preserves_domain_workflow_states(preset, expected_state):
    scenario = create_demo(preset)
    response = run_recovery(scenario)
    assert response.status_code == 200
    assert response.json()["workflow_state"] == expected_state


def test_recovery_get_is_read_only():
    scenario = create_demo("two_failures")
    run_response = run_recovery(scenario)
    assert run_response.status_code == 200

    first = client.get(f"/api/orders/{scenario['order_id']}/recovery")
    second = client.get(f"/api/orders/{scenario['order_id']}/recovery")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["decision"]["decision_id"] == second.json()["decision"]["decision_id"]
    assert first.json()["recovery_case"]["recovery_case_id"] == second.json()["recovery_case"]["recovery_case_id"]


def test_recovered_timeline_contains_full_lifecycle():
    scenario = create_demo("two_failures")
    workflow = run_recovery(scenario)
    assert workflow.status_code == 200
    workflow_data = workflow.json()
    payment_id = scenario["payment_ids"][-1]

    capture = client.post(
        "/api/payment-events",
        json={
            "payment_id": payment_id,
            "provider_event_id": f"EV_API_CAPTURE_{uuid.uuid4().hex[:10]}",
            "event_type": "CAPTURED",
            "event_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert capture.status_code == 200
    outcome = client.post(
        f"/api/recovery-cases/{workflow_data['case']['recovery_case_id']}/outcome",
        json={
            "action_id": workflow_data["execution_action"]["action_id"],
            "payment_id": payment_id,
        },
    )
    assert outcome.status_code == 200
    assert outcome.json()["outcome_type"] == "RECOVERED"
    assert outcome.json()["recovered_payment_id"] == payment_id
    assert outcome.json()["case_status"] == "CLOSED"
    assert outcome.json()["closure_reason"] == "RECOVERED"

    recovery = client.get(f"/api/orders/{scenario['order_id']}/recovery")
    assert recovery.status_code == 200
    assert recovery.json()["financial_truth"] == "PAID"
    assert recovery.json()["recovery_case"]["status"] == "CLOSED"
    assert recovery.json()["outcome"]["outcome_type"] == "RECOVERED"

    response = client.get(f"/api/orders/{scenario['order_id']}/timeline")
    assert response.status_code == 200
    timeline = response.json()
    assert [item["timestamp"] for item in timeline] == sorted(
        item["timestamp"] for item in timeline
    )
    types = {item["type"] for item in timeline}
    assert {
        "PAYMENT_EVENT",
        "RECOVERY_DECISION",
        "RECOVERY_ACTION",
        "RECOVERY_OUTCOME",
        "RECOVERY_CASE_CLOSED",
    } <= types
    failed_event = next(
        item for item in timeline
        if item["type"] == "PAYMENT_EVENT" and item["title"] == "FAILED"
    )
    assert failed_event["details"]["failure_reason"] == "TECHNICAL_FAILURE"
    assert failed_event["details"]["amount_minor"] == 150_000
    assert failed_event["details"]["currency"] == "INR"


def test_recovery_case_list_and_metrics_schemas():
    cases = client.get("/api/recovery-cases", params={"limit": 5})
    metrics = client.get("/api/metrics")
    assert cases.status_code == 200
    assert len(cases.json()) <= 5
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["total_recovery_cases"] >= body["open_cases"]
    assert body["canonical_benchmarks"]
    assert body["canonical_thresholds"]


def test_recovery_case_list_exposes_read_only_operations_fields():
    scenario = create_demo("two_failures")
    workflow = run_recovery(scenario)
    assert workflow.status_code == 200
    before = client.get("/api/metrics").json()["total_recovery_cases"]

    response = client.get("/api/recovery-cases", params={"limit": 500})
    assert response.status_code == 200
    case = next(
        row for row in response.json() if row["order_id"] == scenario["order_id"]
    )
    assert case["amount_minor"] == 150_000
    assert case["currency"] == "INR"
    assert case["financial_truth"] == "UNPAID"
    assert "recovered_amount_minor" in case
    assert client.get("/api/metrics").json()["total_recovery_cases"] == before


@pytest.mark.parametrize(
    ("domain_message", "expected_status"),
    [
        ("Payment is not confirmed CAPTURED.", 409),
        ("Payment belongs to a different order.", 409),
        ("Recovery action was not executed.", 409),
        ("Recovery case is already closed.", 409),
        ("Recovery case, action, or payment relationship could not be resolved.", 404),
    ],
)
def test_recovery_outcome_domain_errors_map_to_http(
    monkeypatch, domain_message, expected_status
):
    def reject_outcome(**_kwargs):
        raise ValueError(domain_message)

    monkeypatch.setattr(
        "backend.api.application.record_recovered_payment",
        reject_outcome,
    )
    response = client.post(
        "/api/recovery-cases/RC_API_BOUNDARY/outcome",
        json={"action_id": "ACT_API_BOUNDARY", "payment_id": "P_API_BOUNDARY"},
    )
    assert response.status_code == expected_status
    assert domain_message not in response.json()["detail"]
