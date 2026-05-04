# Architecture Reference Guide

A comprehensive reference for developers working on the Robinhood AI Portfolio Copilot. Covers every component, data flow, and design decision in the codebase.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Project Structure](#2-project-structure)
3. [Backend Architecture](#3-backend-architecture)
4. [Frontend Architecture](#4-frontend-architecture)
5. [Database Layer](#5-database-layer)
6. [Authentication Flow](#6-authentication-flow)
7. [Broker Integration Flow](#7-broker-integration-flow)
8. [Market Data Pipeline](#8-market-data-pipeline)
9. [AI / ML Architecture](#9-ai--ml-architecture)
10. [Real-Time Streaming](#10-real-time-streaming)
11. [Security Architecture](#11-security-architecture)
12. [Observability](#12-observability)
13. [Infrastructure & DevOps](#13-infrastructure--devops)
14. [Configuration Management](#14-configuration-management)
15. [Error Handling Patterns](#15-error-handling-patterns)
16. [Caching Strategy](#16-caching-strategy)
17. [API Reference](#17-api-reference)
18. [Common Patterns](#18-common-patterns)

---

## 1. System Overview

The platform consists of three runtime processes:

```
User Browser (Next.js)
    |
    v
FastAPI Backend (port 8000)  --->  FastMCP Tool Server (port 8765)
    |                                       |
    v                                       v
PostgreSQL 16                        PostgreSQL 16 (same DB)
```

- **Frontend** (Next.js 16): Renders UI, manages client state, calls backend REST APIs.
- **Backend** (FastAPI): Handles auth, business logic, market data fetching, AI orchestration.
- **MCP Server** (FastMCP): Serves read-only portfolio tools to the AI agent over Streamable HTTP. Separate process for security isolation - the LLM orchestration layer never has direct DB credentials for write operations.

All three share the same PostgreSQL database but through different connection patterns.

---

## 2. Project Structure

```
Robinhood_ai_app/
  app/                          # Backend (Python/FastAPI)
    main.py                     # App entry: middleware, routers, exception handlers
    config.py                   # Settings from .env via pydantic-settings
    auth/                       # User authentication module
      router.py                 # HTTP endpoints (register, login, verify, reset)
      service.py                # Business logic (hashing, JWT, lockout, verification)
      schemas.py                # Pydantic request/response models
    broker_integrations/        # Brokerage connection module
      router.py                 # HTTP endpoints (connect, sync, disconnect, CSV import)
      service.py                # Core broker logic (positions, transactions, snapshots)
      robinhood_adapter.py      # robin_stocks MFA flow
      plaid_adapter.py          # Plaid API adapter
      csv_adapter.py            # CSV parsing and position aggregation
      export_aggregator.py      # Transaction-to-position aggregation engine
      schemas.py                # Request/response models
    portfolio_engine/           # Portfolio analytics module
      router.py                 # GET /portfolio/health-score, GET /portfolio/alerts
      health_score.py           # Composite score computation (HHI, beta, overlap)
      risk_detection.py         # Sector, concentration, overlap alert detection
      schemas.py                # Response models
    stocks/                     # Stock data module
      router.py                 # GET /stocks, GET /stocks/{symbol}, candles, analysis
      service.py                # Finnhub + yfinance fetchers, universe builder
      ai_analysis.py            # AI-generated stock analysis (chart + news + holdings)
      schemas.py                # Data models (profile, quote, candles, earnings, etc.)
      data/sp500.json           # Static S&P 500 universe seed
    markets/                    # Market news module
      router.py                 # GET /markets/news, GET /markets/portfolio-news
      service.py                # RSS + Finnhub news aggregation
      ai_service.py             # AI summary enrichment for news articles
      schemas.py                # News response models
    macro/                      # Macro Pulse module
      router.py                 # GET /macro/pulse, GET /macro/alerts
      service.py                # yfinance-based indicator fetching, exposure scoring
      ai_service.py             # AI macro summary generation
      prompts.py                # LLM prompts for macro analysis
      schemas.py                # Indicator, exposure, alert models
    ai_agent/                   # AI assistant module
      agent.py                  # PydanticAI agent construction (lazy singleton)
      research_agent.py         # Research sub-agent (screener, comparison, sectors)
      tools.py                  # Research tool implementations (yfinance-based)
      service.py                # AssistantService (ask, stream, session management)
      memory.py                 # Cross-session persistent user memory
      prompts.py                # System prompt for the assistant
      models.py                 # Pydantic models for tool outputs
      title.py                  # Auto-title generation for chat sessions
      router.py                 # POST /assistant/ask, POST /assistant/stream
    mcp_server/                 # FastMCP portfolio tool server
      server.py                 # 10 read-only tools (holdings, transactions, quotes, etc.)
      __main__.py               # Entry point for `python -m app.mcp_server`
    chat/                       # Chat session management
      router.py                 # CRUD for sessions, message truncation
      service.py                # DB operations for sessions and messages
      schemas.py                # Session and message models
    database/                   # Database layer
      engine.py                 # SQLAlchemy async engine, session factory
      models.py                 # ORM models (User, Position, Transaction, etc.)
    utils/                      # Shared utilities
      security.py               # Rate limiter, security headers middleware
      encryption.py             # Fernet encrypt/decrypt for broker tokens
      cache.py                  # BoundedTTLCache (thread-safe, LRU eviction)
      logging.py                # Structured JSON logging setup
      observability.py          # Logfire/OpenTelemetry initialization
      exceptions.py             # Custom exception classes
      email.py                  # SMTP email sending (verification, reset)
      symbol_enrichment.py      # Finnhub symbol metadata enrichment

  frontend/                     # Frontend (Next.js/React)
    src/
      app/                      # Next.js App Router pages
        page.tsx                # Root redirect (to /login or /dashboard)
        login/page.tsx          # Login page
        register/page.tsx       # Registration page
        verify-email/page.tsx   # Email verification page
        forgot-password/        # Forgot password page
        reset-password/         # Password reset page
        not-found.tsx           # Custom 404 page
        error.tsx               # Custom 500 error boundary
        global-error.tsx        # Root layout error boundary
        (protected)/            # Auth-guarded route group
          dashboard/page.tsx    # Portfolio overview dashboard
          markets/page.tsx      # Market news + portfolio news
          markets/[symbol]/     # Individual stock detail page
          positions/page.tsx    # All positions list
          transactions/page.tsx # Transaction history
          health/page.tsx       # Portfolio health score
          alerts/page.tsx       # Risk alerts
          allocation/page.tsx   # Allocation breakdown
          assistant/page.tsx    # AI chat assistant (full page)
          macro-pulse/page.tsx  # Macro indicators dashboard
          brokers/page.tsx      # Broker connections management
          settings/page.tsx     # User settings
          summary/page.tsx      # Portfolio summary
      features/                 # Feature-based module structure
        auth/                   # Auth API calls, hooks, store
        ai/                     # AI chat API, hooks, floating widget
        stocks/                 # Stock API calls, hooks
        markets/                # Market news API, hooks
        brokers/                # Broker connection API, hooks
        alerts/                 # Alerts API, hooks
        analytics/              # Analytics/allocation API
        portfolio-health/       # Health score API, hooks
        macro/                  # Macro pulse API, hooks
        chat/                   # Chat sessions API, hooks
        system/                 # System diagnostics
      components/               # Shared React components
        layout/                 # Sidebar, Topbar, ProtectedRoute
        portfolio/              # Portfolio-specific widgets
        visuals/                # Charts, animations, loaders
        feedback/               # Toast notifications, error displays
        ui/                     # shadcn/ui primitives (Button, Card, Input, etc.)

  docker-compose.yml            # Multi-container orchestration
  Dockerfile                    # Backend Docker image
  frontend/Dockerfile           # Frontend Docker image
  requirements.txt              # Python dependencies
  .env.example                  # Environment variable template
  scripts/                      # Utility scripts (migrations, etc.)
```

---

## 3. Backend Architecture

### Framework: FastAPI

Entry point: `app/main.py`. Registers middleware and routers in this order:

1. **SecurityHeadersMiddleware** - CSP, HSTS, X-Frame-Options, etc.
2. **HTTPSRedirectMiddleware** - Only in non-debug mode
3. **CORSMiddleware** - Dev origins in debug, single `FRONTEND_URL` in prod
4. **Rate Limiter** - slowapi attached to `app.state`

### Router Registration

All routers are prefixed with `/api/v1`:

| Router | Prefix | Purpose |
|---|---|---|
| auth_router | `/api/v1/auth` | Registration, login, JWT, password reset |
| broker_router | `/api/v1/broker` | Broker connections, sync, positions, transactions |
| portfolio_router | `/api/v1/portfolio` | Health score, risk alerts |
| markets_router | `/api/v1/markets` | Market news, portfolio news |
| stocks_router | `/api/v1/stocks` | Stock universe, detail, candles, AI analysis |
| macro_router | `/api/v1/macro` | Macro pulse indicators, alerts |
| assistant_router | `/api/v1/assistant` | AI chat (ask + stream) |
| chat_router | `/api/v1/chat` | Chat session CRUD |

### Module Pattern

Each backend module follows a consistent pattern:

```
module/
  __init__.py
  router.py       # HTTP endpoint definitions (thin - delegates to service)
  service.py      # Business logic (DB queries, computations, external API calls)
  schemas.py      # Pydantic models for request validation and response serialization
  ai_service.py   # (optional) LLM-powered enrichment for this module
  prompts.py      # (optional) System prompts for AI features
```

**Rule**: Routers never contain business logic. They validate input, call the service, and return the response.

### Dependency Injection

FastAPI's `Depends()` is used throughout:

```python
@router.get("/endpoint")
async def handler(
    current_user: User = Depends(get_current_user),   # JWT -> User object
    db: AsyncSession = Depends(get_async_session),     # DB session per request
):
```

- `get_current_user` extracts and validates the JWT from the `Authorization` header, queries the user, checks `is_active` and `token_version`.
- `get_async_session` yields a fresh `AsyncSession` per request, commits on success, rolls back on error.

---

## 4. Frontend Architecture

### Framework: Next.js 16 with App Router

- **Routing**: File-system based. `(protected)` route group wraps all auth-required pages.
- **Auth Guard**: `ProtectedRoute` component checks for JWT in `sessionStorage` and redirects to `/login` if missing.
- **Layout**: Sidebar (navigation) + Topbar (user menu, notifications) wrapping all protected pages.

### State Management

Two complementary patterns:

1. **Zustand** (client state): Auth tokens, UI state (sidebar collapse, theme). Stores in `features/*/store.ts`.
2. **TanStack Query** (server state): All API data. Auto-caching, refetch-on-focus, stale-while-revalidate. Hooks in `features/*/hooks.ts`.

### Feature Module Pattern

```
features/module-name/
  api.ts            # Axios calls to backend endpoints
  hooks.ts          # TanStack Query hooks (useQuery, useMutation)
  types.ts          # TypeScript interfaces
  store.ts          # (optional) Zustand store for client-only state
  components/       # (optional) Feature-specific React components
```

### API Client

A centralized Axios instance (`features/*/api.ts`) with:
- Base URL from `NEXT_PUBLIC_API_URL` env var
- JWT token injected via request interceptor from `sessionStorage`
- 401 responses trigger automatic redirect to `/login`

### Component Library

Based on shadcn/ui (Radix primitives + Tailwind CSS). Components live in `components/ui/`. Customized via `class-variance-authority` for variant props.

### Charting

Recharts for all data visualizations (stock price charts, allocation pie charts, health score gauges). Interactive features: hover tooltips with price/time display, range selectors.

---

## 5. Database Layer

### Engine Setup (`app/database/engine.py`)

- **Async engine**: `create_async_engine` with `asyncpg` driver, `pool_recycle=300` to prevent stale connections.
- **Session factory**: `async_sessionmaker` producing `AsyncSession` instances.
- **Base**: Declarative base for ORM models.

### ORM Models (`app/database/models.py`)

| Table | Primary Key | Purpose |
|---|---|---|
| `users` | UUID (v4) | User accounts with auth fields |
| `broker_connections` | Integer (auto) | Per-user broker links (Robinhood, Plaid, CSV) |
| `positions` | Integer (auto) | Current stock/ETF holdings |
| `transactions` | Integer (auto) | Trade history (buy, sell, dividend, etc.) |
| `portfolio_snapshots` | Integer (auto) | Point-in-time portfolio value + cash |
| `chat_sessions` | UUID (v4) | AI chat threads with agent_history JSON |
| `chat_messages` | Integer (auto) | Individual messages (user/assistant) |
| `user_memory` | UUID (FK to users) | Cross-session AI memory (JSON array of facts) |
| `symbol_metadata` | String (symbol) | Cached Finnhub symbol profiles |

### Key Design Decisions

- **UUID primary keys on users and chat sessions** - Safe to expose in tokens and URLs, non-sequential.
- **Integer PKs elsewhere** - Efficient for high-volume tables (positions, transactions).
- **Cascade deletes** - `ondelete="CASCADE"` on all FKs + SQLAlchemy `cascade="all, delete-orphan"`. Deleting a user removes all their data.
- **Indexed columns** - All foreign keys, `symbol`, `executed_at`, `updated_at` are indexed for query performance.
- **JSONB for agent_history** - Stores the full PydanticAI message list per chat session. Avoids a separate table for tool call/result pairs.
- **Timezone-aware datetimes** - All `DateTime(timezone=True)` columns use UTC.

### Relationships

```
User
  |-- BrokerConnection (1:N, cascade delete)
  |     |-- Position (1:N, cascade delete)
  |     |-- Transaction (1:N, cascade delete)
  |     |-- PortfolioSnapshot (1:N, cascade delete)
  |-- ChatSession (1:N, cascade delete)
  |     |-- ChatMessage (1:N, cascade delete)
  |-- UserMemory (1:1, cascade delete)
```

---

## 6. Authentication Flow

### Registration

```
Browser                   Backend                        Database
  |                         |                               |
  |  POST /auth/register    |                               |
  |  {email, password, name}|                               |
  |------------------------>|                               |
  |                         |  bcrypt.hash(password)        |
  |                         |  generate 6-digit OTP         |
  |                         |  hmac.digest(OTP)             |
  |                         |  INSERT user (unverified)---->|
  |                         |  send OTP email               |
  |  {message, user_id}     |                               |
  |<------------------------|                               |
```

### Email Verification

```
Browser                   Backend                        Database
  |                         |                               |
  |  POST /auth/verify-email|                               |
  |  {email, code}          |                               |
  |------------------------>|                               |
  |                         |  hmac.digest(code)            |
  |                         |  timing-safe compare -------->|
  |                         |  SET is_email_verified=true -->|
  |  {success}              |                               |
  |<------------------------|                               |
```

### Login

```
Browser                   Backend                        Database
  |                         |                               |
  |  POST /auth/login       |                               |
  |  {email, password}      |                               |
  |------------------------>|                               |
  |                         |  check lockout (BoundedTTLCache)
  |                         |  SELECT user by email ------->|
  |                         |  bcrypt.verify(password)      |
  |                         |  check is_active, is_verified |
  |                         |  create JWT (sub=user_id,     |
  |                         |    token_version=N)           |
  |  {access_token}         |  clear login tracker          |
  |<------------------------|                               |
```

### JWT Structure

```json
{
  "sub": "user-uuid",
  "token_version": 0,
  "exp": 1234567890
}
```

- **Stateless revocation**: Incrementing `token_version` in the DB invalidates all prior tokens without a blocklist.
- **Verification**: Every protected endpoint calls `get_current_user` which decodes the JWT, queries the user, and compares `token_version`.

### Account Lockout

After 5 failed login attempts, the account is locked for 5 minutes. Tracked in a `BoundedTTLCache` (max 10,000 entries, auto-eviction by LRU + TTL) to prevent memory exhaustion from distributed attacks.

---

## 7. Broker Integration Flow

### Robinhood Connection (MFA)

```
Browser                   Backend                    Robinhood API
  |                         |                            |
  |  POST /broker/          |                            |
  |   robinhood/initiate    |                            |
  |  {username, password}   |                            |
  |------------------------>|  robin_stocks.login ------>|
  |                         |<-- MFA challenge ----------|
  |  {challenge_type,       |                            |
  |   device_token}         |                            |
  |<------------------------|                            |
  |                         |                            |
  |  POST /broker/          |                            |
  |   robinhood/mfa         |                            |
  |  {mfa_code}             |                            |
  |------------------------>|  submit MFA code --------->|
  |                         |<-- access_token -----------|
  |                         |  Fernet.encrypt(token)     |
  |                         |  INSERT broker_connection  |
  |                         |  fetch & store positions   |
  |                         |  fetch & store transactions|
  |                         |  create portfolio snapshot |
  |  {connection_id}        |                            |
  |<------------------------|                            |
```

### CSV Import

```
Browser                   Backend
  |                         |
  |  POST /broker/csv/upload|
  |  {csv_content, filename}|
  |------------------------>|
  |                         |  detect format (standard vs Robinhood)
  |                         |  if Robinhood: run aggregation engine
  |                         |    (compute positions from transactions)
  |                         |  enrich with live prices (Finnhub)
  |                         |  INSERT positions, transactions
  |                         |  create portfolio snapshot
  |  {connection_id}        |
  |<------------------------|
```

### Sync Flow

`POST /broker/{id}/sync` re-fetches positions and transactions from the connected broker, updates prices, and creates a new portfolio snapshot.

---

## 8. Market Data Pipeline

### Data Sources

| Source | Data Type | Usage |
|---|---|---|
| Finnhub API | Quotes, company profiles, company news, symbol search | Primary for real-time quotes and news |
| yfinance | Historical candles, key stats, earnings, fundamentals | Primary for charts and detailed stats |
| RSS Feeds (11) | Market news headlines | CNBC, Reuters, Yahoo Finance, Forbes, Investing.com, FXStreet, FRED Blog, Google News Business, Trading Economics, etc. |

### Stock Detail Flow

```
Browser                   Backend                    External APIs
  |                         |                            |
  |  GET /stocks/AAPL       |                            |
  |------------------------>|                            |
  |                         |  asyncio.gather(           |
  |                         |    fetch_profile(AAPL),    |  --> Finnhub /stock/profile2
  |                         |    fetch_quote(AAPL),      |  --> Finnhub /quote
  |                         |    fetch_candles(AAPL,1M), |  --> yfinance download
  |                         |    fetch_key_stats(AAPL),  |  --> yfinance .info
  |                         |    fetch_earnings(AAPL),   |  --> Finnhub /calendar/earnings
  |                         |    fetch_news(AAPL),       |  --> Finnhub /company-news
  |                         |    build_position(AAPL),   |  --> DB query
  |                         |  )                         |
  |  {profile, quote,       |                            |
  |   candles, stats,       |                            |
  |   earnings, news,       |                            |
  |   position, analysis}   |                            |
  |<------------------------|                            |
```

All external API calls are cached with `BoundedTTLCache` (60s for quotes, 5min for profiles, 30min for news).

### Market News Flow

```
Backend                           External
  |                                  |
  |  fetch_market_news()             |
  |  asyncio.gather(                 |
  |    fetch_finnhub_news(),    ---->| Finnhub /news
  |    fetch_rss_feeds(),       ---->| 11 RSS endpoints
  |  )                               |
  |  deduplicate by URL              |
  |  sort by timestamp               |
  |  split into headlines + articles |
  |                                  |
  |  enrich_news_payload()           |
  |  batch Gemini calls (2 max)      |
  |  attach ai_summary per article   |
```

### Macro Data Flow

```
Backend                         yfinance
  |                                |
  |  build_macro_pulse()           |
  |  yf.download(                  |
  |    "^VIX ^TNX ^GSPC DX-Y.NYB  |
  |     CL=F", period="5d"   ---->|
  |  )                             |
  |  compute health zones          |
  |  score portfolio exposure      |
  |  generate alerts               |
  |  generate AI summary (Gemini)  |
```

---

## 9. AI / ML Architecture

This is the most complex subsystem. Three layers:

### Layer 1: Main Assistant Agent

**File**: `app/ai_agent/agent.py`

```
User Question
    |
    v
AssistantService.stream()          # app/ai_agent/service.py
    |
    |-- Load chat history (last 40 messages from DB)
    |-- Load user memory (up to 25 facts from DB)
    |-- Build AssistantDeps(user_id, user_memory)
    |
    v
PydanticAI Agent.run_stream()      # app/ai_agent/agent.py
    |
    |-- System Prompt (app/ai_agent/prompts.py)
    |   + Injected user memory facts
    |
    |-- Available Tools:
    |   [MCP Portfolio Tools] <-- via FastMCP Streamable HTTP
    |   [DuckDuckGo Search]   <-- direct tool
    |   [research_and_analyze] <-- delegates to Layer 2
    |
    v
SSE Stream (delta/done/error)      # app/ai_agent/router.py
    |
    v
Browser (renders incrementally)
```

### Layer 2: Research Sub-Agent

**File**: `app/ai_agent/research_agent.py`

Invoked by the main agent when questions require broad market analysis:

```
Main Agent calls research_and_analyze(question)
    |
    v
Research Agent (separate PydanticAI Agent)
    |
    |-- Tools:
    |   screen_stocks()          # S&P 500 screener (sector, P/E, market cap, etc.)
    |   compare_stocks()         # Side-by-side fundamentals for 2-5 tickers
    |   get_sector_performance() # 11 GICS sector ETF performance
    |   duckduckgo_search()      # Qualitative web search
    |
    |-- Data Source: yfinance (asyncio.to_thread for sync calls)
    |
    v
Structured analysis string returned to main agent
```

### Layer 3: MCP Tool Server

**File**: `app/mcp_server/server.py`

Runs as a separate process. Exposes 10 read-only tools over Streamable HTTP:

| Tool | Purpose | Data Source |
|---|---|---|
| `get_holdings` | User's positions by market value | DB: positions table |
| `get_recent_transactions` | Latest trades/dividends | DB: transactions table |
| `get_cash_position` | Cash balance from latest snapshot | DB: portfolio_snapshots |
| `get_performance_summary` | Portfolio value change over period | DB: portfolio_snapshots |
| `get_position_for_symbol` | User's position in one ticker | DB + Finnhub quote |
| `get_symbol_profile` | Company profile | Finnhub API |
| `get_symbol_quote` | Live price/change | Finnhub API |
| `get_symbol_key_stats` | Fundamentals (P/E, EPS, etc.) | Finnhub API |
| `get_symbol_earnings` | Earnings calendar + history | Finnhub API |
| `get_symbol_candles_summary` | OHLC summary for a period | yfinance |

**Security**: `user_id` is injected server-side via `process_tool_call` hook. The LLM never sees, submits, or can forge it. Tool calls include server-side caps (50 holdings max, 100 transactions max).

### User Memory System

**File**: `app/ai_agent/memory.py`

Three memory tiers:

1. **In-Session Buffer** (already in PydanticAI): Last 40 messages replayed via `message_history=` parameter. Stored in `ChatSession.agent_history` (JSONB).

2. **Cross-Session Memory** (this module): After each completed turn, a background task extracts memorable facts (investment goals, risk tolerance, favorite tickers) via an LLM call. Facts stored as a JSON array of up to 25 short strings in `UserMemory` table. Injected into system prompt of every future session.

3. **Summary Memory** (planned): When history exceeds the window, summarize earliest turns to preserve context while reducing tokens.

### MCQ Clarification Flow

When the AI determines a question is too broad:

```
AI Response contains:
---mcq---
**What is your investment time horizon?**
- Option A: Short-term (1-2 years)
- Option B: Medium-term (3-5 years)
- Option C: Long-term (5+ years)
---end-mcq---

Frontend parses the MCQ block and renders interactive buttons.
User clicks an option.
The selected option text is sent as the next user message.
AI uses the selection to provide a targeted response.
```

### AI Analysis for Stocks

**File**: `app/stocks/ai_analysis.py`

When a user opens a stock detail page, a separate AI analysis is generated:

```
GET /stocks/AAPL/analysis
    |
    v
Gather: candles (3M), quote, key_stats, news, user_position
    |
    v
generate_stock_analysis()
    |-- Section 1: Chart Interpretation (trend, support/resistance, momentum)
    |-- Section 2: News Impact (recent headlines, sentiment, catalysts)
    |-- Section 3: Holdings Effect (only if user owns the stock)
    |       How chart trends and news affect the user's specific position
    v
StockAnalysisResponse (3 sections, each with title + content)
```

### AI for Market/Macro Summaries

- **Market News**: `app/markets/ai_service.py` - Batched Gemini calls to generate 50-80 word summaries for each headline/article. Cached 30min per URL.
- **Portfolio News**: Same module enriches per-holding news with 3-bullet summaries and sentiment tags.
- **Macro Summary**: `app/macro/ai_service.py` - Generates a three-section summary (Market Environment, Portfolio Impact, Key Takeaways) connecting indicator values to the user's specific holdings.

### Key AI Design Decisions

- **Provider-agnostic**: PydanticAI abstracts the LLM. Swapping Gemini for Anthropic/OpenAI is a config change.
- **Lazy construction**: `@lru_cache(maxsize=1)` on `get_agent()`. Missing API key doesn't crash non-AI endpoints.
- **No text-to-SQL**: The LLM cannot write SQL. All DB access is through predefined, parameterized tool functions.
- **Read-only**: No write tools exposed. The agent cannot place trades or modify data.
- **Structured outputs**: All tool return types are Pydantic models, giving the LLM typed schemas.
- **Token management**: MCP tool results use summary models (not raw data) to stay within context limits. Example: `CandleSummary` returns start/end/change instead of thousands of OHLC bars.

---

## 10. Real-Time Streaming

### SSE (Server-Sent Events) for AI Chat

```
POST /assistant/stream
  |
  v
AssistantService.stream()
  |-- Persist user message to DB (before streaming starts)
  |-- Agent.run_stream(question, message_history=...)
  |
  |-- Yield SSE events:
  |     event: stage    data: {"type":"stage","stage":"Analyzing your portfolio..."}
  |     event: delta    data: {"type":"delta","content":"Based on..."}
  |     event: delta    data: {"type":"delta","content":" your holdings..."}
  |     event: done     data: {"type":"done","content":"full response","tools_used":[...]}
  |
  |-- On error:
  |     event: error    data: {"type":"error","message":"..."}
  |
  |-- After stream:
  |     Persist assistant message to DB
  |     Fire-and-forget: extract memory facts
  |     Fire-and-forget: auto-generate session title
```

**Frontend consumption**: The browser reads the SSE stream via `fetch()` (not `EventSource`, because POST with auth headers is needed). Tokens are appended incrementally to the UI.

---

## 11. Security Architecture

### Defense in Depth

| Layer | Mechanism |
|---|---|
| Transport | HTTPS redirect in production, HSTS header |
| Authentication | JWT with bcrypt, stateless revocation, account lockout |
| Authorization | `user_id` from JWT on every request, never from request body |
| Rate Limiting | slowapi per-endpoint (5/min register, 10/min login, 20/min AI) |
| Input Validation | Pydantic `max_length`, `Query` bounds, bounded pagination |
| CORS | Explicit origins, methods, headers. No wildcards in production |
| Headers | CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy |
| Error Handling | Generic messages to clients, detailed logging server-side |
| Secrets | Fernet for broker tokens, production startup guard for insecure defaults |
| Logging | PII redaction (hashed emails), no API keys in logs |
| Caching | BoundedTTLCache with maxsize + TTL to prevent memory exhaustion |
| Docker | Non-root `appuser`, `.dockerignore` excludes `.env` |
| AI Safety | `user_id` injected server-side, read-only tools, no text-to-SQL |

### Production Startup Guard

`app/config.py` refuses to start outside `development` if:
- `SECRET_KEY` or `JWT_SECRET_KEY` are insecure defaults
- `ENCRYPTION_KEY` is empty
- `DEBUG=true`
- `FRONTEND_URL` uses wildcards or non-HTTPS

---

## 12. Observability

### Pydantic Logfire Integration

**File**: `app/utils/observability.py`

Auto-instruments:
- FastAPI (every HTTP request as a span)
- SQLAlchemy (every query)
- HTTPX (outbound HTTP calls)
- PydanticAI (agent runs with token count, cost, duration)
- MCP tool calls (name, args, result, latency)

### Configuration

| Env Var | Purpose |
|---|---|
| `LOGFIRE_TOKEN` | Cloud shipping token (empty = local-only no-op) |
| `LOGFIRE_CONSOLE` | Print spans to stdout (default: true) |
| `LOGFIRE_SCRUB_PROMPTS` | Redact user questions from traces |

Backend and MCP server appear as two distinct services in the Logfire UI, linked by OpenTelemetry trace IDs.

---

## 13. Infrastructure & DevOps

### Docker Compose Services

| Service | Image | Port | Purpose |
|---|---|---|---|
| `postgres` | postgres:16-alpine | 5432 | Database |
| `backend` | Custom (Dockerfile) | 8000 | FastAPI app |
| `mcp-server` | Custom (same Dockerfile) | internal only | FastMCP tool server |
| `frontend` | Custom (frontend/Dockerfile) | 3000 | Next.js app |

### Key Docker Design Decisions

- **MCP server has no exposed ports** - Only reachable within the Docker network. The backend connects to it over the internal `mcp-server:8765` hostname.
- **Bind mounts for development** - Source code is mounted into containers so edits reflect without rebuilds.
- **Named volumes for node_modules/.next** - Prevents platform mismatch issues (Windows host vs Linux container).
- **watchfiles for MCP hot-reload** - Since FastMCP isn't a web framework, `watchfiles` watches `.py` files and restarts the process.
- **Non-root users** - Both Dockerfiles create an `appuser` with no elevated privileges.
- **Health checks** - Postgres has a `pg_isready` health check. Backend depends on it with `condition: service_healthy`.

### Local Development

`npm run dev` (from `frontend/`) uses `concurrently` to start all three processes:

```
concurrently -n backend,mcp,frontend -c blue,magenta,green
  "cd .. && python -m uvicorn app.main:app --reload --port 8000"
  "cd .. && python -m app.mcp_server"
  "next dev --port 3000"
```

---

## 14. Configuration Management

### Settings (`app/config.py`)

Uses `pydantic-settings` to load from `.env` file and environment variables. Single `Settings` class with all config grouped by domain:

| Category | Key Settings |
|---|---|
| App | `APP_ENV`, `DEBUG`, `SECRET_KEY` |
| Database | `DATABASE_URL`, `DATABASE_URL_SYNC` |
| Auth | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` |
| Encryption | `ENCRYPTION_KEY` (Fernet) |
| Broker | `ROBINHOOD_CLIENT_ID`, `PLAID_CLIENT_ID`, `PLAID_SECRET` |
| Market Data | `FINNHUB_API_KEY`, `POLYGON_API_KEY` |
| AI | `GOOGLE_API_KEY`, `GOOGLE_MODEL`, `MCP_SERVER_URL` |
| Email | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` |
| Observability | `LOGFIRE_TOKEN`, `LOGFIRE_CONSOLE`, `LOGFIRE_SCRUB_PROMPTS` |
| Frontend | `FRONTEND_URL` |

**Memoized**: `@lru_cache()` on `get_settings()` ensures a single instance process-wide.

---

## 15. Error Handling Patterns

### Backend

Two global exception handlers in `app/main.py`:

1. **AppException handler** - Catches custom exceptions and returns structured JSON with status code and message.
2. **Generic handler** - Catches all unhandled exceptions, logs the full error, returns a generic "internal error" message (no stack traces).

### Frontend

Three Next.js error boundaries:

1. `not-found.tsx` - Custom 404 page with link to dashboard.
2. `error.tsx` - Per-page error boundary with retry button. Logs to console, never shows raw errors.
3. `global-error.tsx` - Root layout crash handler.

### Pattern

```python
# Router (thin)
try:
    return await service.do_thing()
except ServiceSpecificError:
    raise HTTPException(status_code=4xx, detail="User-friendly message")
except Exception:
    logger.error("...", extra={...})
    raise HTTPException(status_code=502, detail="Generic safe message")
```

---

## 16. Caching Strategy

### BoundedTTLCache (`app/utils/cache.py`)

Thread-safe, in-memory cache with:
- **Max size** (LRU eviction when full)
- **TTL per entry** (auto-expiry)
- **delete()** method for explicit invalidation

Used throughout the backend:

| Cache | maxsize | TTL | Purpose |
|---|---|---|---|
| Stock quotes | 256 | 60s | Avoid hammering Finnhub for the same ticker |
| Stock profiles | 512 | 5min | Company info changes rarely |
| News articles | 128 | 30min | News summaries cached per URL |
| Macro indicators | 128 | 5min | VIX, yields, etc. same for all users |
| Macro exposure | 256 | 15min | Per-user portfolio exposure scores |
| Login tracker | 10,000 | 5min | Account lockout tracking |
| Symbol metadata | 512 | 30min | Finnhub symbol enrichment |

### Why Not Redis?

Redis is optional (used by slowapi when configured). The app runs fine without it using in-memory caches. This keeps the deployment simple for single-instance setups. For horizontal scaling, swap `BoundedTTLCache` instances for Redis-backed equivalents.

---

## 17. API Reference

### Auth Endpoints

| Method | Path | Rate Limit | Purpose |
|---|---|---|---|
| POST | `/api/v1/auth/register` | 5/min | Create account |
| POST | `/api/v1/auth/verify-email` | 10/min | Verify with OTP |
| POST | `/api/v1/auth/resend-verification` | 3/min | Resend OTP |
| POST | `/api/v1/auth/login` | 10/min | Get JWT |
| POST | `/api/v1/auth/forgot-password` | 3/min | Request reset email |
| POST | `/api/v1/auth/reset-password` | 5/min | Set new password |
| POST | `/api/v1/auth/logout` | 20/min | Revoke tokens |
| GET | `/api/v1/auth/me` | - | Current user profile |
| DELETE | `/api/v1/auth/account` | - | Delete account + all data |

### Broker Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/broker/robinhood/initiate` | Start MFA flow |
| POST | `/api/v1/broker/robinhood/mfa` | Submit MFA code |
| POST | `/api/v1/broker/csv/upload` | Import CSV |
| GET | `/api/v1/broker/connections` | List connections |
| POST | `/api/v1/broker/{id}/sync` | Re-sync data |
| POST | `/api/v1/broker/{id}/disconnect` | Disconnect broker |
| DELETE | `/api/v1/broker/{id}` | Delete connection + data |
| GET | `/api/v1/broker/positions` | All positions |
| GET | `/api/v1/broker/transactions` | Transaction history |
| GET | `/api/v1/broker/summary` | Account summary |
| GET | `/api/v1/broker/allocation` | Allocation breakdown |

### Stock Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/stocks` | Browsable stock grid |
| GET | `/api/v1/stocks/{symbol}` | Full detail (profile, quote, candles, earnings, news, position) |
| GET | `/api/v1/stocks/{symbol}/candles` | Price history for a range |
| GET | `/api/v1/stocks/{symbol}/analysis` | AI-generated analysis |

### Markets Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/markets/news` | Market summary + recent developments |
| GET | `/api/v1/markets/portfolio-news` | Per-holding news with AI summaries |

### Macro Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/macro/pulse` | Full macro dashboard (indicators + exposure + AI summary) |
| GET | `/api/v1/macro/alerts` | Active macro alerts only |

### AI Assistant Endpoints

| Method | Path | Rate Limit | Purpose |
|---|---|---|---|
| POST | `/api/v1/assistant/ask` | 20/min | One-shot Q&A |
| POST | `/api/v1/assistant/stream` | 20/min | Streaming SSE response |

### Chat Session Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/chat/sessions` | List sessions (paginated) |
| POST | `/api/v1/chat/sessions` | Create session |
| GET | `/api/v1/chat/sessions/{id}` | Session detail + messages |
| PATCH | `/api/v1/chat/sessions/{id}` | Update title/starred/archived |
| DELETE | `/api/v1/chat/sessions/{id}` | Delete session |
| POST | `/api/v1/chat/sessions/{id}/messages/truncate` | Truncate messages (for edit/regenerate) |

### Portfolio Engine Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/portfolio/health-score` | Composite 0-100 score |
| GET | `/api/v1/portfolio/alerts` | Risk alerts |

### Health Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Basic health check |
| GET | `/status` | Component-level health (API + DB) |

---

## 18. Common Patterns

### Adding a New Backend Module

1. Create `app/new_module/` with `__init__.py`, `router.py`, `service.py`, `schemas.py`.
2. Define Pydantic schemas for request/response models.
3. Implement business logic in `service.py`.
4. Create thin router endpoints that delegate to service functions.
5. Register the router in `app/main.py`: `app.include_router(new_router, prefix="/api/v1")`.
6. Add any new DB models to `app/database/models.py` with appropriate indexes and cascade relationships.

### Adding a New AI Tool (MCP)

1. Define a Pydantic return model.
2. Add a `@mcp.tool()` function in `app/mcp_server/server.py`.
3. Extract `user_id` via `_extract_user_id(ctx)`.
4. Use `_DbSession()` context manager for DB access.
5. Log the tool call via `_log_tool_call()`.
6. Cap result sizes server-side.

### Adding a New Frontend Page

1. Create `frontend/src/app/(protected)/page-name/page.tsx`.
2. Add API functions in `frontend/src/features/module/api.ts`.
3. Create TanStack Query hooks in `frontend/src/features/module/hooks.ts`.
4. Add navigation link to the Sidebar component.
5. Use shadcn/ui components for consistent styling.

### Adding a New Research Tool

1. Implement the tool function in `app/ai_agent/tools.py` (return a Pydantic model).
2. Register it as `@agent.tool_plain` in `app/ai_agent/research_agent.py`.
3. Update the research agent prompt with usage guidance.
4. The main agent's `research_and_analyze` tool will automatically have access.

---

*This document should be the first thing a new developer reads when onboarding to the project.*
