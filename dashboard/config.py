import os
from dataclasses import dataclass


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_API_TIMEOUT = 30.0


def normalize_base_url(value):
    normalized = (value or DEFAULT_API_BASE_URL).strip().rstrip("/")
    if not normalized.startswith(("http://", "https://")):
        raise ValueError("RECOVERY_API_BASE_URL must use http:// or https://")
    return normalized


@dataclass(frozen=True)
class DashboardConfig:
    api_base_url: str
    api_timeout: float


def load_config():
    timeout = float(os.getenv("RECOVERY_API_TIMEOUT", str(DEFAULT_API_TIMEOUT)))
    if timeout <= 0:
        raise ValueError("RECOVERY_API_TIMEOUT must be greater than zero")
    return DashboardConfig(
        api_base_url=normalize_base_url(os.getenv("RECOVERY_API_BASE_URL")),
        api_timeout=timeout,
    )
