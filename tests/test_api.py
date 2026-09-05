"""Boundary tests for the FastAPI control plane."""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.data_access.payments import create_customer, create_order, create_payment


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
    response = client.post("/api/demo/scenarios", json={"preset": preset})
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
