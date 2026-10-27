"""Process-local, bounded aggregate metrics. Never retain conversation content."""
import logging
from collections import Counter
from contextvars import ContextVar
from threading import Lock

logger = logging.getLogger(__name__)
_metrics = Counter()
_lock = Lock()
request_outcome = ContextVar("chat_outcome", default="completed")


def record_event(event):
    # Callers supply fixed labels, never user text or identifiers.
    if event in {"input_blocked", "rate_limited"}:
        request_outcome.set(event)
    with _lock:
        _metrics[event] += 1


def record_request(message, response, outcome, latency_ms):
    metrics = {
        "requests": 1,
        "outcome_" + outcome: 1,
        "input_chars_total": len(message) if isinstance(message, str) else 0,
        "output_chars_total": len(response) if isinstance(response, str) else 0,
        "latency_ms_total": round(latency_ms, 3),
    }
    with _lock:
        _metrics.update(metrics)
    logger.info("chat_request outcome=%s input_chars=%d output_chars=%d latency_ms=%.3f",
                outcome, metrics["input_chars_total"], metrics["output_chars_total"], latency_ms)


def get_monitoring_metrics():
    """Return an independent snapshot for trusted operator integrations."""
    with _lock:
        result = dict(_metrics)
    count = result.get("requests", 0)
    result["latency_ms_mean"] = result.get("latency_ms_total", 0) / count if count else 0
    return result


def reset_monitoring_metrics():
    with _lock:
        _metrics.clear()
