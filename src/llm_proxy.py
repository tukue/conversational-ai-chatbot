"""Buffered, text-only LLM policy gateway. See docs/LLM_PROXY.md."""
import anyio
from collections import Counter
from contextlib import asynccontextmanager
import math
from dataclasses import dataclass
import hmac
import json
import os
import re
from time import monotonic
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.proxy_analytics import AnalyticsStore

from src.guardrails import (
    PII_PATTERNS, SECRET_OUTPUT_PATTERNS, PROMPT_INJECTION_PATTERNS,
    DANGEROUS_OUTPUT_PATTERNS, _normalize_unicode, _detect_encoding_attacks,
)


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=16000)


class Completion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    model: str = Field(min_length=1, max_length=128)
    messages: list[Message] = Field(min_length=1, max_length=32)
    max_tokens: int = Field(default=512, ge=1, le=4096)
    stream: Literal[False] = False


class Usage(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)


@dataclass(frozen=True)
class Settings:
    client_key: str
    admin_key: str
    upstream_key: str
    upstream_url: str
    models: tuple[str, ...]
    requests_per_minute: int = 60
    timeout_seconds: float = 30
    max_concurrent_requests: int = 16
    upload_timeout_seconds: float = 10
    analytics_db: str | None = None
    analytics_retention_days: int = 90

    def __post_init__(self):
        if not all((self.client_key, self.admin_key, self.upstream_key, self.models)):
            raise ValueError("Proxy credentials and model allowlist are required")
        if self.client_key == self.admin_key:
            raise ValueError("Use separate client and administrator keys")
        url = httpx.URL(self.upstream_url)
        if url.scheme != "https" or not url.host or url.userinfo or url.query or url.fragment:
            raise ValueError("Upstream must be a fixed HTTPS URL without credentials or query")
        if (self.analytics_retention_days < 1 or self.requests_per_minute < 1 or self.max_concurrent_requests < 1
                or not all(math.isfinite(t) and t > 0 for t in
                           (self.timeout_seconds, self.upload_timeout_seconds))):
            raise ValueError("Limits must be positive")


def violation(text: str) -> str | None:
    normalized = _normalize_unicode(text)
    for reason, patterns in (
        ("pii", PII_PATTERNS), ("secret", SECRET_OUTPUT_PATTERNS),
        ("unsafe_markup", DANGEROUS_OUTPUT_PATTERNS),
        ("injection", PROMPT_INJECTION_PATTERNS),
    ):
        if any(re.search(pattern, normalized, re.I) for pattern in patterns):
            return reason
    if _detect_encoding_attacks(normalized):
        return "injection"
    return None


def create_app(settings: Settings, transport=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        if settings.analytics_db:
            app.state.analytics_store = await anyio.to_thread.run_sync(
                AnalyticsStore, settings.analytics_db, settings.analytics_retention_days)
        async with httpx.AsyncClient(
            transport=transport, timeout=settings.timeout_seconds,
            follow_redirects=False, trust_env=False,
            limits=httpx.Limits(max_connections=settings.max_concurrent_requests,
                               max_keepalive_connections=settings.max_concurrent_requests),
        ) as client:
            app.state.upstream = client
            app.state.ready = True
            try:
                yield
            finally:
                app.state.ready = False

    app = FastAPI(title="LLM policy proxy", docs_url=None, redoc_url=None,
                  openapi_url=None, lifespan=lifespan)
    app.state.ready = False
    app.state.analytics_store = None
    active_requests = 0

    @app.get("/health/live")
    async def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    async def ready():
        return JSONResponse({"ready": app.state.ready}, status_code=200 if app.state.ready else 503)
    counters = Counter()
    window_start = monotonic()
    window_requests = 0

    def authenticate(request: Request, key: str):
        supplied = request.headers.get("authorization", "").encode()
        if not hmac.compare_digest(supplied, f"Bearer {key}".encode()):
            raise HTTPException(401, "Unauthorized")

    @app.get("/analytics")
    async def analytics(request: Request):
        authenticate(request, settings.admin_key)
        return {"scope": "process_lifetime", "policy_version": "1", **dict(counters)}

    @app.get("/analytics/history")
    async def history(request: Request, days: int = Query(default=7, ge=1)):
        authenticate(request, settings.admin_key)
        if app.state.analytics_store is None:
            raise HTTPException(503, "Persistent analytics not configured")
        if days > settings.analytics_retention_days:
            raise HTTPException(422, "Report window exceeds retention")
        try:
            return await anyio.to_thread.run_sync(app.state.analytics_store.report, days)
        except Exception:
            raise HTTPException(503, "Analytics unavailable") from None

    @app.post("/v1/chat/completions")
    async def complete(request: Request):
        nonlocal window_start, window_requests, active_requests
        started = monotonic()
        request_id = str(uuid4())
        outcome = "internal_error"
        admitted = False
        metrics = Counter(requests=1)
        try:
            authenticate(request, settings.client_key)
            if not app.state.ready:
                raise HTTPException(503, "Service not ready")
            if active_requests >= settings.max_concurrent_requests:
                raise HTTPException(503, "Service busy", headers={"Retry-After": "1"})
            active_requests += 1
            admitted = True
            if started - window_start >= 60:
                window_start, window_requests = started, 0
            if window_requests >= settings.requests_per_minute:
                raise HTTPException(429, "Rate limit exceeded",
                                    headers={"Retry-After": str(max(1, math.ceil(60 - (started - window_start))))})
            window_requests += 1
            body = bytearray()
            try:
                with anyio.fail_after(settings.upload_timeout_seconds):
                    async for chunk in request.stream():
                        if len(body) + len(chunk) > 65536:
                            raise HTTPException(413, "Request too large")
                        body.extend(chunk)
            except TimeoutError:
                raise HTTPException(408, "Request upload timeout") from None
            try:
                payload = Completion.model_validate_json(bytes(body))
            except ValidationError:
                raise HTTPException(422, "Invalid request") from None
            if payload.model not in settings.models:
                raise HTTPException(403, "Model not allowed")
            # Also inspect concatenation to catch patterns split across messages.
            texts = [m.content for m in payload.messages]
            reason = next((r for t in texts + ["\n".join(texts)] if (r := violation(t))), None)
            if reason:
                metrics[f"input_blocked_{reason}"] += 1
                raise HTTPException(403, "Input blocked by policy")
            metrics["upstream_requests"] += 1
            try:
                with anyio.fail_after(settings.timeout_seconds):
                    async with app.state.upstream.stream(
                        "POST", settings.upstream_url,
                        headers={"Authorization": f"Bearer {settings.upstream_key}"},
                        json=payload.model_dump(),
                    ) as response:
                        response.raise_for_status()
                        raw = bytearray()
                        async for chunk in response.aiter_bytes():
                            if len(raw) + len(chunk) > 262144:
                                raise ValueError("Oversized upstream response")
                            raw.extend(chunk)
                data = json.loads(raw)
                usage = Usage.model_validate(data["usage"])
                metrics["prompt_tokens"] += usage.prompt_tokens
                metrics["completion_tokens"] += usage.completion_tokens
                choices = data["choices"]
                if len(choices) != 1:
                    raise ValueError("Expected one choice")
                message = choices[0]["message"]
                content = message["content"]
                if (message.get("role") != "assistant" or not isinstance(content, str)
                        or not content.strip() or len(content) > 16000
                        or message.get("tool_calls") or message.get("function_call")):
                    raise ValueError("Unsupported upstream message")
            except (TimeoutError, httpx.TimeoutException):
                raise HTTPException(504, "Upstream timeout") from None
            except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
                raise HTTPException(502, "Invalid upstream response") from None
            reason = violation(content)
            if reason:
                metrics[f"output_blocked_{reason}"] += 1
                raise HTTPException(403, "Output blocked by policy")
            outcome = "allowed"
            # Rebuild response: never forward uninspected provider metadata.
            return JSONResponse({
                "id": request_id, "model": payload.model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": content}}],
                "usage": {**usage.model_dump(), "total_tokens": usage.prompt_tokens + usage.completion_tokens},
            }, headers={"X-Request-ID": request_id})
        except HTTPException as exc:
            outcome = f"status_{exc.status_code}"
            return JSONResponse({"error": exc.detail, "request_id": request_id},
                                status_code=exc.status_code,
                                headers={"X-Request-ID": request_id, **(exc.headers or {})})
        except anyio.get_cancelled_exc_class():
            outcome = "cancelled"
            raise
        except Exception:
            # Do not expose policy exceptions, credentials or provider content.
            return JSONResponse({"error": "Internal proxy error", "request_id": request_id},
                                status_code=500, headers={"X-Request-ID": request_id})
        finally:
            metrics[outcome] += 1
            metrics["latency_ms_total"] += round((monotonic() - started) * 1000)
            counters.update(metrics)
            try:
                if app.state.analytics_store is not None:
                    # Persist before returning; cancellation must not interrupt accounting.
                    with anyio.CancelScope(shield=True):
                        await anyio.to_thread.run_sync(app.state.analytics_store.record, dict(metrics))
            except Exception:
                # Analytics availability must not change a policy decision or trigger retries.
                counters["analytics_write_errors"] += 1
            finally:
                if admitted:
                    active_requests -= 1

    return app


def app_from_env():
    return create_app(Settings(
        client_key=os.environ["PROXY_CLIENT_KEY"],
        admin_key=os.environ["PROXY_ADMIN_KEY"],
        upstream_key=os.environ["PROXY_UPSTREAM_KEY"],
        upstream_url=os.environ["PROXY_UPSTREAM_URL"],
        analytics_db=os.getenv("PROXY_ANALYTICS_DB") or None,
        analytics_retention_days=int(os.getenv("PROXY_ANALYTICS_RETENTION_DAYS", "90")),
        requests_per_minute=int(os.getenv("PROXY_REQUESTS_PER_MINUTE", "60")),
        timeout_seconds=float(os.getenv("PROXY_TIMEOUT_SECONDS", "30")),
        max_concurrent_requests=int(os.getenv("PROXY_MAX_CONCURRENT_REQUESTS", "16")),
        upload_timeout_seconds=float(os.getenv("PROXY_UPLOAD_TIMEOUT_SECONDS", "10")),
        models=tuple(m.strip() for m in os.environ["PROXY_MODELS"].split(",") if m.strip()),
    ))
