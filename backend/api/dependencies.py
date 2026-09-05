from functools import lru_cache

from backend.data_access.health import database_is_connected
from backend.services.recovery_factory import (
    DEFAULT_MODEL_PATH,
    create_recovery_decision_service,
    load_recovery_learner,
)


@lru_cache(maxsize=1)
def get_decision_service():
    return create_recovery_decision_service()


def get_health_status():
    database = "connected" if database_is_connected() else "unavailable"
    load_recovery_learner(str(DEFAULT_MODEL_PATH))
    return {
        "status": "ok",
        "database": database,
        "model": "loaded",
    }
