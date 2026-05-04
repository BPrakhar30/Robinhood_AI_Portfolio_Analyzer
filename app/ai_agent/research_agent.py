"""Research sub-agent for deep financial analysis.

Called by the main assistant agent via tool delegation when questions
require stock screening, fundamentals comparison, sector analysis, or
multi-step research that goes beyond simple per-symbol lookups.

The research agent has its own focused prompt and toolset. It returns a
structured analysis string that the main agent formats for the user.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_ai import Agent
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from app.config import get_settings

from .tools import (
    ComparisonOutput,
    ScreenerOutput,
    SectorOutput,
    compare_fundamentals,
    sector_performance,
    stock_screener,
)

_RESEARCH_PROMPT = """\
You are a senior equity research analyst AI. Your job is to perform deep,
data-driven financial analysis and return a clear, actionable research report.

You have three tools:
- stock_screener: Screen S&P 500 stocks by sector, market cap, P/E, dividend
  yield, and momentum. Returns up to 15 results with key metrics.
- compare_fundamentals: Compare 2-5 stocks side by side on valuation, growth,
  and risk metrics.
- sector_performance: See which sectors are leading or lagging over a period.
- duckduckgo_search: Search the web for qualitative information - earnings
  outlooks, competitive dynamics, analyst ratings, industry trends.

Research methodology:
1. Start with quantitative screening/comparison using your tools.
2. Supplement with web search for qualitative context (analyst consensus,
   upcoming catalysts, competitive position, management quality).
3. Synthesize both into a clear thesis.

Output rules:
- Be DIRECT and SPECIFIC. Name stocks, cite numbers, state opinions.
- When ranking stocks, explain WHY each ranks where it does using data.
- Include both bull case and bear case / risks for every recommendation.
- Use simple language a retail investor can understand.
- Format with clear headers, bullet points, and tables where appropriate.
- When comparing, always include a "verdict" section with your top pick
  and the reasoning.
- NEVER use the em dash character. Use hyphens (-) instead.
- NEVER mention tool names (stock_screener, compare_stocks, etc.) in your
  output. Present information naturally as your own analysis.
- Keep the total output under 800 words unless the question demands more.
"""


def _build_research_agent() -> Agent[None, str]:
    settings = get_settings()
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY required for research agent.")

    model = GoogleModel(
        settings.google_model,
        provider=GoogleProvider(api_key=settings.google_api_key),
    )

    agent = Agent(
        model,
        deps_type=None,
        system_prompt=_RESEARCH_PROMPT,
        output_type=str,
        tools=[duckduckgo_search_tool()],
    )

    @agent.tool_plain
    async def screen_stocks(
        sector: str = "",
        min_market_cap: float = 0,
        max_pe: float = 0,
        min_dividend_yield: float = 0,
        sort_by: str = "market_cap",
        limit: int = 10,
    ) -> ScreenerOutput:
        """Screen S&P 500 stocks by fundamental criteria.

        Args:
            sector: GICS sector name (e.g. "Health Care"). Empty = all sectors.
            min_market_cap: Minimum market cap in USD. 0 = no filter.
            max_pe: Maximum trailing P/E ratio. 0 = no filter.
            min_dividend_yield: Minimum dividend yield as decimal (0.03 = 3%). 0 = no filter.
            sort_by: One of "market_cap", "pe_ratio", "dividend_yield", "momentum", "eps_ttm".
            limit: Number of results (1-15).
        """
        return await stock_screener(
            sector=sector or None,
            min_market_cap=min_market_cap or None,
            max_pe=max_pe or None,
            min_dividend_yield=min_dividend_yield or None,
            sort_by=sort_by,
            limit=limit,
        )

    @agent.tool_plain
    async def compare_stocks(symbols: list[str]) -> ComparisonOutput:
        """Compare 2-5 stocks on key fundamentals side by side.

        Args:
            symbols: List of ticker symbols to compare (e.g. ["AAPL", "MSFT", "GOOGL"]).
        """
        return await compare_fundamentals(symbols)

    @agent.tool_plain
    async def get_sector_performance(period: str = "3mo") -> SectorOutput:
        """Get performance ranking of all 11 GICS sector ETFs.

        Args:
            period: Time period - "1mo", "3mo", "6mo", "ytd", "1y".
        """
        return await sector_performance(period)

    return agent


@lru_cache(maxsize=1)
def get_research_agent() -> Agent[None, str]:
    """Process-wide singleton, built lazily on first use."""
    return _build_research_agent()
