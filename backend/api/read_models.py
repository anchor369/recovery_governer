import csv
from pathlib import Path

from backend.data_access.recovery_views import (
    get_order_recovery_records,
    get_recovery_metric_records,
    list_recovery_case_records,
)
from backend.services.payment_truth import evaluate_order_truth


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def build_order_recovery_view(order_id):
    records = get_order_recovery_records(order_id)
    if records is None:
        return None
    return {
        "order_id": order_id,
        "financial_truth": evaluate_order_truth(order_id),
        "recovery_case": records["case"],
        "decision": records["decision"],
        "candidate_action_scores": records["candidate_scores"],
        "action": records["action"],
        "outcome": records["outcome"],
    }


def build_order_timeline(order_id):
    records = get_order_recovery_records(order_id)
    if records is None:
        return None

    items = []
    for event in records["payment_events"]:
        items.append({
            "timestamp": event["event_time"],
            "type": "PAYMENT_EVENT",
            "title": event["event_type"],
            "details": {
                "payment_id": event["payment_id"],
                "provider_event_id": event["provider_event_id"],
                "method": event["method"],
                "failure_reason": event["failure_reason"],
                "amount_minor": event["amount_minor"],
                "currency": event["currency"],
            },
        })

    case = records["case"]
    if case is not None:
        items.append({
            "timestamp": case["opened_at"],
            "type": "RECOVERY_CASE_OPENED",
            "title": "Recovery case opened",
            "details": {"recovery_case_id": case["recovery_case_id"]},
        })

    decision = records["decision"]
    if decision is not None:
        items.append({
            "timestamp": decision["prediction_time"],
            "type": "RECOVERY_DECISION",
            "title": decision["proposed_action"],
            "details": {
                "decision_id": decision["decision_id"],
                "model_version": decision["model_version"],
            },
        })

    action = records["action"]
    if action is not None:
        items.append({
            "timestamp": action["executed_at"] or action["created_at"],
            "type": "RECOVERY_ACTION",
            "title": action["action_type"],
            "details": {
                "action_id": action["action_id"],
                "execution_status": action["execution_status"],
                "blocked_reason": action["blocked_reason"],
            },
        })

    outcome = records["outcome"]
    if outcome is not None:
        items.append({
            "timestamp": outcome["outcome_time"],
            "type": "RECOVERY_OUTCOME",
            "title": outcome["outcome_type"],
            "details": {
                "outcome_id": outcome["outcome_id"],
                "payment_id": outcome["payment_id"],
                "recovered_amount_minor": outcome["recovered_amount_minor"],
            },
        })

    if case is not None and case["closed_at"] is not None:
        items.append({
            "timestamp": case["closed_at"],
            "type": "RECOVERY_CASE_CLOSED",
            "title": case["closure_reason"] or "Closed",
            "details": {"recovery_case_id": case["recovery_case_id"]},
        })

    return sorted(items, key=lambda item: (item["timestamp"], item["type"]))


def list_recovery_cases(limit):
    return list_recovery_case_records(limit)


def _read_csv(name):
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def build_metrics_view():
    return {
        **get_recovery_metric_records(),
        "canonical_benchmarks": _read_csv("economic_benchmark_summary.csv"),
        "canonical_thresholds": _read_csv("governor_threshold_summary.csv"),
    }
