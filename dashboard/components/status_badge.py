from html import escape


def status_badge(value, tone="neutral"):
    label = escape(str(value).replace("_", " "))
    return f'<span class="status-badge tone-{tone}">{label}</span>'


def tone_for_status(value):
    normalized = str(value or "").upper()
    if normalized in {"PAID", "RECOVERED", "CLOSED", "EXECUTED", "DECIDED"}:
        return "success"
    if normalized in {"UNCERTAIN", "WAIT_FOR_TRUTH", "ALLOW_NATURAL_RETRY"}:
        return "warning"
    if normalized in {"FAILED", "BLOCKED", "STOP"}:
        return "danger"
    if normalized in {"OPEN", "PENDING"}:
        return "info"
    return "neutral"
