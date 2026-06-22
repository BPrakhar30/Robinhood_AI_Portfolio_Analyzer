"""Pydantic Logfire observability setup.

Tracing strategy
----------------
- **LLM + tools**: ``logfire.instrument_pydantic_ai()`` auto-captures every
  agent run, each LLM call (model, tokens, cost, errors), and every tool call
  (name, arguments, result, duration). Works transparently with MCP because
  MCP calls are just Python function invocations inside the agent run.
- **HTTP inbound**: ``logfire.instrument_fastapi(app)`` wraps each request
  with a span including route, status, and duration.
- **HTTP outbound**: ``logfire.instrument_httpx()`` captures every request
  from ``httpx.AsyncClient`` (market data, broker APIs, MCP transport).
- **Database**: ``logfire.instrument_sqlalchemy(engine)`` emits a span per
  query, so slow portfolio aggregations are easy to spot.
- **Metrics**: ``logfire.instrument_system_metrics()`` adds CPU, memory, GC
  stats as time-series metrics.

Token behavior
--------------
- If ``LOGFIRE_TOKEN`` is empty, ``send_to_logfire='if-token-present'`` makes
  the whole stack a no-op  -  so local dev without a Logfire account still
  works. When a token is set, spans ship to the Logfire UI.
- ``console`` output is enabled in development so you can see spans in the
  terminal without leaving your editor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import logfire

from app.config import get_settings

if TYPE_CHECKING:
    from fastapi import FastAPI


_configured = False


def _scrubbing_callback(match: logfire.ScrubMatch) -> Any:
    """Keep OpenTelemetry's own span names alongside pydantic-ai prompt content.

    Logfire's default scrubber redacts obvious PII patterns. We augment it by
    optionally dropping full prompt/response payloads when ``logfire_scrub_prompts``
    is true (opt-in stricter mode for finance use-cases).
    """
    settings = get_settings()
    if not settings.logfire_scrub_prompts:
        # Let Logfire's default scrubber handle cards/emails/etc; keep prompts.
        return match.value

    # When strict mode is on, aggressively redact message contents that may
    # include portfolio figures or user questions.
    sensitive_paths = {"messages", "content", "input", "prompt", "answer", "output"}
    if any(segment in sensitive_paths for segment in match.path if isinstance(segment, str)):
        return "[scrubbed-prompt]"
    return match.value


def setup_logfire(service_name: str, app: "FastAPI | None" = None) -> None:
    """Configure Logfire exactly once per process and wire instrumentations.

    Safe to call from the FastAPI lifespan and from the MCP server's
    ``__main__``; subsequent calls are no-ops.
    """
    global _configured
    if _configured:
        return

    settings = get_settings()

    logfire.configure(
        service_name=service_name,
        service_version="0.1.0",
        environment=settings.app_env.value,
        token=settings.logfire_token or None,
        send_to_logfire="if-token-present",
        console=logfire.ConsoleOptions(min_log_level="info")
        if settings.logfire_console
        else False,
        scrubbing=logfire.ScrubbingOptions(callback=_scrubbing_callback),
    )

    # PydanticAI: captures agent runs, LLM calls, tool calls (v2 schema: the
    # UI renders chat transcripts, MCP tool args/results, and token usage).
    logfire.instrument_pydantic_ai()

    # Outbound HTTP  -  market data, RSS, MCP, broker APIs.
    logfire.instrument_httpx(capture_headers=False)

    # Inbound HTTP (FastAPI only, not the MCP server's internal transport).
    if app is not None:
        logfire.instrument_fastapi(app, capture_headers=False)

    # SQLAlchemy  -  wrap the app's async engine if it exists.
    try:
        from app.database.engine import async_engine  # noqa: WPS433

        logfire.instrument_sqlalchemy(engine=async_engine.sync_engine)
    except Exception:  # noqa: BLE001
        # MCP server process doesn't touch the DB; safe to skip.
        pass

    # Process metrics (CPU, memory)  -  only meaningful in long-running servers.
    try:
        logfire.instrument_system_metrics()
    except Exception:  # noqa: BLE001
        pass

    _configured = True
