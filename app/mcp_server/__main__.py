"""Run the MCP server over Streamable HTTP. Config comes from env vars
read at import time in ``server.py``.

Usage: ``python -m app.mcp_server``
"""

from __future__ import annotations

from app.utils.logging import get_logger
from app.utils.observability import setup_logfire

from .server import mcp

logger = get_logger("mcp_server.main")


def main() -> None:
    # MCP runs as a separate process, so it needs its own Logfire setup
    # to appear as a distinct service in the observability UI.
    setup_logfire(service_name="robinhood-ai-mcp")
    logger.info(
        "MCP server starting",
        extra={
            "event": "mcp_server_start",
            "host": mcp.settings.host,
            "port": mcp.settings.port,
            "transport": "streamable-http",
        },
    )
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
