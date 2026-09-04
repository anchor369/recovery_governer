from functools import lru_cache
from pathlib import Path

import joblib

from backend.services.recovery_decision import (
    RecoveryDecisionService,
)

from policy.economics import (
    MerchantEconomics,
)


DEFAULT_MODEL_PATH = Path(
    "models/s_learner.joblib"
)


@lru_cache(maxsize=4)
def load_recovery_learner(
    model_path: str,
):
    path = Path(
        model_path
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Recovery model not found: {path}"
        )

    return joblib.load(
        path
    )


def create_recovery_decision_service(
    model_path=DEFAULT_MODEL_PATH,
    economics=None,
    max_payment_attempts=6,
    minimum_incremental_utility_minor=0.0,
):
    if economics is None:
        economics = MerchantEconomics()

    learner = load_recovery_learner(
        str(model_path)
    )

    return RecoveryDecisionService(
        learner=learner,
        economics=economics,
        max_payment_attempts=(
            max_payment_attempts
        ),
        minimum_incremental_utility_minor=(
            minimum_incremental_utility_minor
        ),
    )