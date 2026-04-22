"""PydanticAI agent wired to Google Gemini + our MCP portfolio-tools server.

Security: the LLM never sees or submits ``user_id``. ``process_tool_call``
stamps it as MCP metadata on every call. The agent holds no DB creds or
session — tool execution happens in the ``mcp-server`` container.

Construction is lazy so a missing ``GOOGLE_API_KEY`` doesn't break
non-AI endpoints at import time.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import UUID

from pydantic_ai import Agent, RunContext
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
from pydantic_ai.mcp import CallToolFunc, MCPServerStreamableHTTP, ToolResult
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from app.config import get_settings

from .prompts import SYSTEM_PROMPT


@dataclass
class AssistantDeps:
    """Per-request deps. Only the authenticated user's UUID."""

    user_id: UUID


async def _inject_user_id(
    ctx: RunContext[AssistantDeps],
    call_tool: CallToolFunc,
    name: str,
    tool_args: dict[str, Any],
) -> ToolResult:
    """Stamp server-controlled ``user_id`` onto every MCP tool call.

    The metadata dict is ours alone; the LLM can't see or override it.
    """
    return await call_tool(name, tool_args, {"user_id": str(ctx.deps.user_id)})


def _build_agent() -> Agent[AssistantDeps, str]:
    settings = get_settings()

    if not settings.google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not configured. Set it in .env to enable the assistant. "
            "Get a free key at https://aistudio.google.com/apikey"
        )

    model = GoogleModel(
        settings.google_model,
        provider=GoogleProvider(api_key=settings.google_api_key),
    )

    mcp_server = MCPServerStreamableHTTP(
        settings.mcp_server_url,
        process_tool_call=_inject_user_id,
    )

    # DuckDuckGo is a regular agent tool (no API key, works with any model).
    # The prompt keeps account-specific queries on MCP.
    agent = Agent(
        model,
        deps_type=AssistantDeps,
        system_prompt=SYSTEM_PROMPT,
        output_type=str,
        toolsets=[mcp_server],
        tools=[duckduckgo_search_tool()],
    )
    return agent


@lru_cache(maxsize=1)
def get_agent() -> Agent[AssistantDeps, str]:
    """Process-wide singleton, built lazily on first use."""
    return _build_agent()
