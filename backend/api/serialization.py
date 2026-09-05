from backend.services.recovery_state import RuntimeRecoverySignals


def runtime_signals_from_request(request):
    return RuntimeRecoverySignals(**request.model_dump())


def serialize_workflow_result(result):
    audit = result.audit or {}
    decision = audit.get("decision")
    return {
        "workflow_state": result.workflow_state,
        "reason": result.reason,
        "case": result.case,
        "decision": decision,
        "chosen_action": (
            decision.get("proposed_action")
            if decision is not None
            else None
        ),
        "execution_action": result.action,
        "candidate_action_scores": audit.get("scores", []),
    }
