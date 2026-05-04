# Product Requirements Document - Robinhood AI Portfolio Copilot

## Product Vision

An AI Portfolio Copilot for retail investors that securely connects brokerage accounts, deeply understands portfolio structure, answers natural-language questions with direct opinions backed by data, detects risk automatically, tracks macro-economic conditions, and provides actionable insights to improve decision-making.

Example interactions:
- "Am I too concentrated in semiconductors?"
- "Which stock is hurting my returns most?"
- "Tell me the 10 best stocks for long-term growth."
- "Compare AAPL vs MSFT vs GOOGL"
- "How does the macro environment affect my portfolio?"

---

## Status Legend

- **SHIPPED** - Fully implemented and live
- **PARTIAL** - Backend or core logic done, frontend/polish pending
- **PLANNED** - Designed but not yet built

---

## CATEGORY 1 - Core / MVP (Shipped)

### 1. Account Connection Layer [SHIPPED]

Supported connection methods:
- Robinhood Direct Connection (two-step MFA: SMS, email, TOTP, push notification)
- CSV Import (standard positions CSV + Robinhood transaction export auto-detection)
- Plaid Integration [PARTIAL - backend adapter and endpoints complete, frontend Plaid Link widget pending]

Data ingested: holdings, quantity, average cost, purchase date, realized/unrealized gains, cash balance, transaction history (buy/sell/dividend/split).

### 2. Portfolio Data Model [SHIPPED]

System tracks and computes:
- Positions with sector, asset type (stock/ETF/crypto/option/mutual fund/bond), and currency
- Market value, unrealized/realized gains per position
- Portfolio snapshots with total value and cash balance over time
- Allocation breakdown by sector (computed against S&P 500 benchmarks)
- Symbol metadata cache (sector, industry, country, market cap category) via Finnhub

### 3. AI Portfolio Chat Assistant [SHIPPED]

Full conversational interface where users can ask:
- "Which stock is hurting my returns most?"
- "Show diversification issues"
- "Compare my portfolio vs S&P 500"
- "Tell me the best 10 stocks for the next 5 years"
- "Find undervalued dividend stocks in healthcare"

Capabilities:
- Multi-turn context (40-message window per session)
- Cross-session persistent memory (up to 25 facts per user)
- Streamed SSE responses with progress stages
- MCQ-based clarification when questions are too broad
- Research sub-agent for stock screening, comparison, and sector analysis
- Direct opinions and stock recommendations backed by data
- AI disclaimer appended to directional calls
- Session management (rename, star, archive, delete)
- Floating chat widget accessible from any page with page-aware suggested prompts

### 4. Portfolio Health Score [SHIPPED]

Composite 0-100 score from five sub-scores:
- Diversification (HHI-based)
- Single-stock concentration risk
- ETF overlap detection
- Volatility exposure (weighted beta)
- Expense efficiency

Each sub-score includes an explanation and improvement suggestion.

### 5. Allocation Risk Detection Engine [SHIPPED]

Automatically detects:
- Overweight sectors vs S&P 500 sector weights
- Single-stock concentration (>10% warning, >20% critical)
- ETF underlying-holding overlap

Surfaced on dedicated Alerts page and as a dashboard widget.

---

## CATEGORY 2 - Important Features (v1 Product)

### 6. Scenario Simulator [PARTIAL]

Backend module (`app/scenario_simulator/`) exists. Core simulation logic planned.

Status: Backend scaffolding present, full implementation pending.

### 7. AI Research & Analysis Engine [SHIPPED]

Replaces the original "Buy/Sell Insight Engine" concept with a more powerful approach:
- S&P 500 stock screener (filter by sector, market cap, P/E, dividend yield, momentum)
- Multi-stock fundamentals comparison (up to 5 side-by-side)
- GICS sector performance ranking (11 sectors via ETF proxies)
- Web search for qualitative context (analyst consensus, catalysts, competitive dynamics)
- Direct stock recommendations with bull/bear cases and risk disclaimers

### 8. Stock Deep Dive Mode [SHIPPED]

User clicks a stock and sees:
- Company profile (sector, industry, HQ, CEO, employees, description)
- Live quote (price, day change, volume)
- Interactive price chart (1D/1W/1M/3M/YTD/1Y/5Y/MAX with hover tooltips)
- Key stats (market cap, P/E, forward P/E, EPS, beta, 52-week range, dividend yield)
- Earnings history (last 4 quarters with EPS beat/miss/inline + next event)
- Company news with AI summaries
- AI analysis (chart interpretation, news impact, holdings effect for owned stocks)

### 9. Portfolio Strategy Detection [SHIPPED via AI Memory]

The AI assistant learns user behavior through cross-session persistent memory:
- Extracts investment preferences, risk tolerance, frequently discussed tickers
- Adapts recommendations based on accumulated user knowledge
- MCQ clarification questions to understand goals when context is missing

### 10. ETF Overlap Intelligence [SHIPPED]

Part of the Portfolio Health Score engine. Detects overlap between ETF holdings and individual positions. Overlap percentage surfaced in the health score and alerts.

---

## CATEGORY 3 - Differentiators

### 11. Macro Pulse Dashboard [SHIPPED]

Nine live macro indicators with portfolio-level impact analysis:
- VIX (volatility), 10Y Treasury Yield, CPI (inflation), S&P 500, Dollar Index (DXY)
- PMI (manufacturing), High-Yield Spreads, Oil (WTI), Baltic Dry Index

Each indicator shows: current value, health zone (green/yellow/red), plain-language definition with ranges, and what it means for the user's holdings.

Portfolio Macro Exposure: six categories (Growth, Cyclical, Defensive, Rate-Sensitive, Commodity-Linked, International) with holding-level attribution and percentage bars.

AI Macro Summary: three-section analysis (Market Environment, Portfolio Impact, Key Takeaways) connecting macro conditions to the user's specific holdings.

Dashboard macro alert widget for at-a-glance risk awareness.

### 12. Benchmark Comparison [SHIPPED via AI Assistant]

Users can ask the AI to compare portfolio performance against S&P 500, Nasdaq, or any benchmark via `get_performance_summary` and web search tools.

### 13. News-Aware Portfolio Monitoring [SHIPPED]

Portfolio News: per-holding company news aggregated from Finnhub, de-duplicated, with AI-generated 3-bullet summaries and sentiment tags (risk/positive/neutral).

Market News: broad market summary headlines and recent developments from 11+ RSS feeds, each with AI summaries.

Dashboard integration: risk/positive/neutral news counts with drill-through to full Markets page.

### 14. Smart Alerts Engine [SHIPPED]

Automatic alerts for:
- Stock exceeds allocation threshold
- Sector exposure becomes risky vs S&P 500
- Single-stock concentration warning/critical
- ETF overlap detected
- Macro indicator threshold crossings

---

## CATEGORY 4 - Advanced / Future Roadmap

### 15. Smart Rebalancing Suggestions [PLANNED]

Suggest position changes to reach target diversification. One-click rebalance plan export.

### 16. Tax Optimization Assistant [PLANNED]

Detect tax-loss harvesting opportunities, suggest replacement positions.

### 17. Portfolio Forecast Engine [PLANNED]

5-year projection with expected CAGR, worst/best case based on historical volatility and factor exposure.

### 18. Trade Impact Simulator [PLANNED]

"What happens if I add $2000 NVDA?" - show effect on allocation, volatility, diversification score.

### 19. Strategy Builder Mode [PLANNED]

User sets return target, system builds allocation, risk profile, ETF suggestions, rebalance plan.

### 20. Multi-Broker Support [PLANNED]

Future integrations: Fidelity, Schwab, Vanguard, Coinbase.

---

## Technical Architecture Summary

| Component | Technology |
|---|---|
| Backend API | FastAPI, Python, SQLAlchemy (async), Pydantic |
| AI Agent | PydanticAI, Google Gemini 2.5 Flash, FastMCP |
| Research Agent | PydanticAI sub-agent with stock screener, comparisons, sector tools |
| Database | PostgreSQL 16 (UUID PKs, JSONB, indexed FKs) |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, shadcn/ui |
| State Management | Zustand (client), TanStack Query (server) |
| Authentication | JWT + bcrypt + Fernet encryption |
| Market Data | Finnhub API, yfinance, 11 RSS feeds |
| Observability | Pydantic Logfire (OpenTelemetry) |
| Infrastructure | Docker, Docker Compose, non-root containers |
| Security | Rate limiting, CSP headers, CORS, input validation, PII redaction |
