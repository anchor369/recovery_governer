import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.application import (
    OrderNotFoundError,
    RecoveryOutcomeConflictError,
    RecoveryOutcomeLinkNotFoundError,
    attribute_recovery_outcome,
    run_order_recovery,
)
from backend.api.dependencies import get_decision_service
from backend.api.read_models import (
    build_order_recovery_view,
    build_order_timeline,
    list_recovery_cases,
)
from backend.api.schemas.recovery import (
    RecoveryCaseSummary,
    RecoveryOutcomeRequest,
    RecoveryOutcomeResponse,
    RecoveryRunResponse,
    RecoveryViewResponse,
    RuntimeSignalsRequest,
    TimelineItem,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["recovery"])


@router.post(
    "/recovery-cases/{case_id}/outcome",
    response_model=RecoveryOutcomeResponse,
)
def create_recovery_outcome(case_id: str, request: RecoveryOutcomeRequest):
    try:
        return attribute_recovery_outcome(case_id, request)
    except RecoveryOutcomeLinkNotFoundError as error:
        raise HTTPException(status_code=404, detail="Outcome linkage not found") from error
    except RecoveryOutcomeConflictError as error:
        raise HTTPException(status_code=409, detail="Outcome conflicts with current state") from error


@router.post("/orders/{order_id}/recovery", response_model=RecoveryRunResponse)
def recover_order(
    order_id: str,
    request: RuntimeSignalsRequest,
    decision_service=Depends(get_decision_service),
):
    try:
        return run_order_recovery(order_id, request, decision_service)
    except OrderNotFoundError as error:
        raise HTTPException(status_code=404, detail="Order not found") from error
    except Exception as error:
        logger.exception("Recovery API workflow failed: order_id=%s", order_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recovery workflow failed",
        ) from error


@router.get("/orders/{order_id}/recovery", response_model=RecoveryViewResponse)
def get_recovery(order_id: str):
    view = build_order_recovery_view(order_id)
    if view is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return view


@router.get("/orders/{order_id}/timeline", response_model=list[TimelineItem])
def get_timeline(order_id: str):
    timeline = build_order_timeline(order_id)
    if timeline is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return timeline


@router.get("/recovery-cases", response_model=list[RecoveryCaseSummary])
def get_recovery_cases(limit: int = Query(default=100, ge=1, le=500)):
    return list_recovery_cases(limit)
