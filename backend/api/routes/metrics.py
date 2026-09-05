from fastapi import APIRouter

from backend.api.read_models import build_metrics_view
from backend.api.schemas.metrics import MetricsResponse


router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/metrics", response_model=MetricsResponse)
def metrics():
    return build_metrics_view()
