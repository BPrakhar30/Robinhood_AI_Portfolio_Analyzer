# Robinhood AI Portfolio Analyzer

An AI-powered portfolio analysis application that connects to your Robinhood brokerage account, imports your holdings and transaction history, and provides intelligent insights into your investments.

## What Has Been Built

- **User Authentication** — Registration, login, email verification (6-digit OTP), password reset via emailed token, and JWT-based sessions. Passwords hashed with bcrypt.
- **Account Deletion** — Users can permanently delete their account and all associated data from Settings or the topbar menu, with confirmation dialog.
- **Robinhood Direct Connection** — Two-step MFA flow (SMS, email, TOTP, and push notification) using `robin_stocks` internals. Includes 30-second countdown for push approval, auto-trigger, and inline status feedback.
- **CSV Import** — Upload a standard positions CSV or a Robinhood transaction export. Robinhood exports are auto-detected and run through an aggregation engine that computes positions from buy/sell/split/dividend transactions, with live prices from Finnhub.
- **Plaid Integration (backend only)** — Backend adapter, endpoints, and service layer are complete. Frontend wiring (Plaid Link widget) is planned for a future release.
- **Dashboard** — Portfolio overview, connected brokers, positions, unrealized gains, cash balance, plus Health Score and Risk Alert summary widgets.
- **Broker Management** — Connect, sync, disconnect, or delete broker accounts and data. Encrypted token storage with Fernet.
- **Portfolio Health Score** — Composite 0–100 score built from five sub-scores (diversification via HHI, single-stock concentration, ETF overlap, volatility exposure via weighted beta, expense efficiency) with per-factor explanations and improvement suggestions.
- **Allocation Risk Detection** — Sector-overweight detection vs S&P 500, single-stock concentration thresholds (>10% yellow, >20% red), and ETF underlying-holding overlap detection, surfaced on a dedicated Alerts page and as a dashboard widget.
- **Markets Page** — News tab with collapsible market-summary headlines and a recent-developments carousel, aggregated from Finnhub plus eleven free RSS feeds (CNBC, Reuters, Investing.com, Yahoo Finance, Forbes, FXStreet, FRED Blog, Google News Business, Trading Economics, etc.). Earnings tab with a weekly calendar strip and per-stock detail view.
- **AI Portfolio Assistant** — Full chat interface with resizable history sidebar, session rename/star/archive, persistent multi-turn context, and streamed responses. Powered by **PydanticAI** on **Google Gemini 2.5 Flash** (free tier), with portfolio data access delegated to a separate **FastMCP** tool server for security isolation.
- **Observability** — Full-stack tracing via **Pydantic Logfire**: every LLM call (prompt, tokens, cost, latency), every MCP tool call (name, args, result, duration), every SQL query, and every inbound/outbound HTTP request is captured as structured spans. Free tier ships 10M spans/month; leave the token empty to run purely locally.
- **Settings** — Profile info, system diagnostics, logout, and account deletion (danger zone).
- **Dockerized Dev Environment** — `docker compose up --build` runs everything with bind mounts for live reloading.
- **Responsive UI** — Next.js 16, Tailwind CSS, shadcn/ui, dark/light mode, protected routes, sidebar + topbar layout.

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy (async), Pydantic, JWT, bcrypt, Fernet encryption, Finnhub API, async RSS aggregation
- **AI / Agent**: PydanticAI, Google Gemini 2.5 Flash (via Google AI Studio free tier, swappable), FastMCP (Streamable-HTTP transport), DuckDuckGo web-search tool
- **Observability**: Pydantic Logfire (OpenTelemetry-compatible) with auto-instrumentation for PydanticAI, FastAPI, SQLAlchemy, and HTTPX
- **Frontend**: Next.js 16, React, TypeScript, Tailwind CSS, shadcn/ui, Zustand, TanStack Query, Server-Sent Events for streaming
- **Database**: PostgreSQL 16 (required — `User.id` and related tables use UUID primary keys)
- **DevOps**: Docker, Docker Compose, concurrently (for multi-process dev)

## AI Backend Architecture

- **LLM Provider** — Google Gemini via Google AI Studio's direct free tier (10 RPM / 250K TPM / 250 RPD on `gemini-2.5-flash`, no billing required). Set `GOOGLE_API_KEY` (free at https://aistudio.google.com/apikey) and optionally `GOOGLE_MODEL`. The agent is provider-agnostic through PydanticAI — swapping to Anthropic/OpenAI/OpenRouter is a ~5-line change.
- **Agent Framework** — PydanticAI. Typed, schema-first agents with built-in tool calling, streaming, and message-history replay for multi-turn chat.
- **Tool Protocol** — MCP (Model Context Protocol). Portfolio tools live in a separate FastMCP process (`app/mcp_server`) and are consumed by the agent over Streamable HTTP. Clean process-level isolation between LLM orchestration and data access.
- **Available Tools (5)** — The LLM sees only this fixed toolset; it cannot write SQL or reach the DB directly.
  - `get_holdings(limit)` — current positions ordered by market value.
  - `get_recent_transactions(limit)` — latest trades, dividends, fees.
  - `get_cash_position()` — latest cash balance from the newest snapshot.
  - `get_performance_summary(period)` — portfolio value change over 1W / 1M / 3M / 6M / 1Y / ALL.
  - `duckduckgo_search(query)` — general web search for news, macro data, and concepts (not account data).
- **Tool Routing** — Handled by the LLM itself via OpenAI-style function calling on the tool schemas PydanticAI emits. No custom router, no text-to-SQL. The system prompt forbids using web search for account data.
- **User-Scoping** — `user_id` is injected server-side as MCP request metadata via a `process_tool_call` hook. The LLM never sees, argues for, or can forge it.
- **Read-Only by Design** — No write tools exposed: the agent cannot place trades, move money, or mutate account state. Queries are hand-written SQLAlchemy scoped by `user_id`.
- **Chat Persistence** — `ChatSession.agent_history` stores the serialized PydanticAI `ModelMessage` list per session. On each turn, the last 40 messages are replayed via `run_stream(message_history=…)` so context, tool results, and prior reasoning carry forward.
- **Streaming** — Backend streams tokens to the frontend as Server-Sent Events (`delta` / `done` / `error`). The user's message is persisted before the stream opens so aborted streams still show the question.
- **Lazy Construction** — The agent is built at first use and memoized. A missing `GOOGLE_API_KEY` does not crash non-AI endpoints; it only 503s the assistant routes.
- **Transport Security** — FastMCP runs with DNS-rebinding protection and a host allow-list. No ports are exposed publicly from the `mcp-server` container in Docker.

## Observability (Pydantic Logfire)

Every request, LLM call, tool invocation, and SQL query is automatically traced end-to-end.

- **What's captured** — PydanticAI agent runs (model, tokens, cost, duration), MCP tool calls (name, arguments, result, latency), FastAPI requests, outbound HTTPX calls (market data, RSS, broker APIs), SQLAlchemy queries, and system metrics. Backend and MCP server appear as two distinct services in the UI, linked by OTel trace IDs.
- **Privacy controls** — Default scrubber redacts common PII patterns (card numbers, emails, tokens). Set `LOGFIRE_SCRUB_PROMPTS=true` in `.env` to additionally redact user questions and LLM prompts — useful before sharing traces.
- **Console fallback** — With `LOGFIRE_CONSOLE=true` (default), spans also print to stdout in dev, so you can debug without leaving your terminal.
- **Zero-config mode** — If `LOGFIRE_TOKEN` is empty, Logfire runs as a local no-op: no spans are shipped, no account is required, the app works unchanged.
- **Enabling cloud traces** — Create a free project at https://logfire.pydantic.dev, run `logfire auth` followed by `logfire projects use <name>`, or paste the write token into `LOGFIRE_TOKEN` in `.env`. Restart `npm run dev` to pick it up.
- **Not locked in** — Logfire is built on OpenTelemetry. If you switch to Honeycomb/Datadog/Grafana Tempo later, the instrumentation keeps working via standard OTLP exporters.

## Running the App

### Option 1: Docker (Recommended)

1. Install and start [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. Copy `.env.example` to `.env` and configure. At minimum set `GOOGLE_API_KEY` (free key at https://aistudio.google.com/apikey) to enable the AI Assistant. Optionally set `LOGFIRE_TOKEN` for cloud observability.
3. Build and start:
   ```
   docker compose up --build
   ```
4. Open:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Swagger Docs: http://localhost:8000/docs
5. Source code is bind-mounted — edit files and changes reflect automatically.
6. Stop: `docker compose down`
7. Rebuild after dependency changes: `docker compose up --build`

### Option 2: Local Development

1. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Install frontend dependencies:
   ```
   cd frontend && npm install
   ```
3. Copy `.env.example` to `.env` and configure. Ensure `DATABASE_URL` points to `postgresql+asyncpg://postgres:postgres@localhost:5432/robinhood_ai`, `MCP_SERVER_URL=http://localhost:8765/mcp`, and `GOOGLE_API_KEY` is set. Optional: set `LOGFIRE_TOKEN` to ship traces to the Logfire UI.
4. Start PostgreSQL (one-time per session) using the project's Docker compose service:
   ```
   docker compose up -d postgres
   ```
5. Start all three services (backend on 8000, MCP tool server on 8765, frontend on 3000):
   ```
   cd frontend && npm run dev
   ```
   Runs FastAPI, the FastMCP portfolio-tools server, and Next.js concurrently with colored, labeled logs. `Ctrl+C` shuts down all three.
