"""Per-symbol market data  -  quotes, candles, profiles, earnings, news.

This module is intentionally decoupled from ``app/markets/`` (which is
broad market headlines + earnings calendar). It owns every endpoint used
by the Stock Detail page and the new per-symbol MCP tools so the
assistant can reason about individual holdings.
"""
