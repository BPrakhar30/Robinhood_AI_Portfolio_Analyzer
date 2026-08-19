"""Per-user assistant metrics for the observability stack.

Uses Pydantic Logfire's OpenTelemetry-backed metrics API. Each instrument is
created lazily as a proxy and binds to the real meter after ``logfire.configure``
runs, so importing this module is side-effect free.

The ``user_id`` label answers "who is using the app, and how much" across:
requests, latency, tokens, and tool calls. Tokens are the direct proxy for
LLM cost; exact dollar cost can be derived in the dashboard from tokens.
"""

from __future__ import annotations

from uuid import UUID

import logfire

# Counters get a ``_total`` suffix when exposed to Prometheus; the histogram
# is recorded in seconds so it surfaces as ``..._duration_seconds``.
_assistant_requests = logfire.metric_counter(
    "portfolio.assistant.requests",
    unit="1",
    description="Number of assistant turns (ask + stream).",
)
_assistant_duration = logfire.metric_histogram(
    "portfolio.assistant.duration_seconds",
    unit="s",
    description="Wall-clock latency per assistant turn.",
)
_assistant_tokens = logfire.metric_counter(
    "portfolio.assistant.tokens",
    unit="1",
    description="LLM tokens consumed per turn, split by input/output.",
)
_assistant_tool_calls = logfire.metric_counter(
    "portfolio.assistant.tool_calls",
    unit="1",
    description="MCP/tool calls made per turn.",
)


def set_user_attribute(user_id: UUID) -> None:
    """Tag the current span with the authenticated user id.

    Called from the auth dependency so every child span (agent run, LLM call,
    tool call) is grouped under the request span that carries this attribute,
    letting Tempo filter traces by ``enduser.id``.
    """
    try:
        from opentelemetry import trace as otel_trace

        otel_trace.get_current_span().set_attribute("enduser.id", str(user_id))
    except Exception:  # noqa: BLE001 - observability must never break auth
        pass


def record_assistant_turn(
    user_id: UUID,
    duration_s: float,
    request_tokens: int,
    response_tokens: int,
    tool_call_count: int,
) -> None:
    """Record one completed assistant turn's usage against a user."""
    uid = str(user_id)
    try:
        _assistant_requests.add(1, attributes={"user_id": uid})
        _assistant_duration.record(duration_s, attributes={"user_id": uid})
        _assistant_tokens.add(
            request_tokens, attributes={"user_id": uid, "direction": "input"}
        )
        _assistant_tokens.add(
            response_tokens, attributes={"user_id": uid, "direction": "output"}
        )
        _assistant_tool_calls.add(tool_call_count, attributes={"user_id": uid})
    except Exception:  # noqa: BLE001 - metrics must never break the response
        pass
