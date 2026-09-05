import logging

from fastapi import APIRouter, HTTPException

from backend.api.dependencies import get_health_status


logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    try:
        return get_health_status()
    except Exception as error:
        logger.exception("Health check failed")
        raise HTTPException(status_code=503, detail="Service unavailable") from error
