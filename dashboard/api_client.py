import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dashboard.config import load_config, normalize_base_url


class RecoveryAPIError(RuntimeError):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class RecoveryAPIUnavailable(RecoveryAPIError):
    pass


class RecoveryAPIClient:
    def __init__(self, base_url=None, timeout=None):
        config = load_config()
        self.base_url = normalize_base_url(base_url or config.api_base_url)
        self.timeout = config.api_timeout if timeout is None else float(timeout)

    def build_url(self, path):
        return f"{self.base_url}/{path.lstrip('/')}"

    def _request(self, method, path, payload=None):
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(
            self.build_url(path),
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            try:
                detail = json.loads(error.read().decode("utf-8")).get("detail")
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                detail = None
            raise RecoveryAPIError(
                detail or f"API request failed with status {error.code}",
                status_code=error.code,
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            raise RecoveryAPIUnavailable(
                f"FastAPI is unavailable at {self.base_url}"
            ) from error

    def health_check(self):
        return self._request("GET", "/health")

    def create_demo_scenario(self, preset):
        return self._request("POST", "/api/demo/scenarios", {"preset": preset})

    def run_recovery(self, order_id, runtime_signals):
        return self._request(
            "POST", f"/api/orders/{order_id}/recovery", runtime_signals
        )

    def get_recovery(self, order_id):
        return self._request("GET", f"/api/orders/{order_id}/recovery")

    def get_timeline(self, order_id):
        return self._request("GET", f"/api/orders/{order_id}/timeline")

    def list_recovery_cases(self, limit=100):
        return self._request("GET", f"/api/recovery-cases?limit={int(limit)}")

    def get_metrics(self):
        return self._request("GET", "/api/metrics")

    def record_payment_event(
        self, payment_id, provider_event_id, event_type, event_time=None
    ):
        if event_time is None:
            event_time = datetime.now(timezone.utc).isoformat()
        return self._request(
            "POST",
            "/api/payment-events",
            {
                "payment_id": payment_id,
                "provider_event_id": provider_event_id,
                "event_type": event_type,
                "event_time": event_time,
                "raw_payload": {"source": "streamlit_recovery_lab"},
            },
        )

    def record_recovery_outcome(self, case_id, action_id, payment_id):
        return self._request(
            "POST",
            f"/api/recovery-cases/{case_id}/outcome",
            {"action_id": action_id, "payment_id": payment_id},
        )
