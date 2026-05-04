"""Market data service: aggregates broad market news from free RSS feeds + Finnhub.

News sources (all free, no API key required for RSS):
  Finnhub /news (requires finnhub_api_key), CNBC, Reuters, Investing.com,
  Yahoo Finance, Forbes, FXStreet, FRED Blog, Google News Business.

Uses httpx for async HTTP, xml.etree for RSS parsing, and in-memory caching
with TTLs to avoid hammering upstream sources.

Per-symbol market data (quotes, candles, profiles, earnings, company news)
lives in ``app/stocks/`` — this module is intentionally scoped to broad
cross-market headlines only.
"""

from __future__ import annotations

import asyncio
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import httpx

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger("markets.service")

FINNHUB_BASE = "https://finnhub.io/api/v1"

# How many headlines / developments to surface to the UI.
HEADLINES_COUNT = 10
DEVELOPMENTS_COUNT = 15
# Diversity ceiling: no single outlet may contribute more than this many items
# to the Market Summary slice. Prevents a single fast-updating feed (e.g. CNBC)
# from dominating the top 10.
MAX_PER_SOURCE = 2

from app.utils.cache import BoundedTTLCache

_cache = BoundedTTLCache(maxsize=256, default_ttl=600)
NEWS_TTL = 300  # 5 min
RSS_TTL = 600  # 10 min

RSS_FEEDS: list[dict[str, str]] = [
    {
        "name": "CNBC",
        "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        "site_url": "https://www.cnbc.com/markets",
    },
    {
        "name": "CNBC Economy",
        "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "site_url": "https://www.cnbc.com/economy",
    },
    {
        "name": "CNBC Earnings",
        "url": "https://www.cnbc.com/id/15839135/device/rss/rss.html",
        "site_url": "https://www.cnbc.com/earnings",
    },
    {
        "name": "Reuters",
        "url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
        "site_url": "https://www.reuters.com/markets",
    },
    {
        "name": "Investing.com",
        "url": "https://www.investing.com/rss/news.rss",
        "site_url": "https://www.investing.com/news",
    },
    {
        "name": "Yahoo Finance",
        "url": "https://finance.yahoo.com/news/rssindex",
        "site_url": "https://finance.yahoo.com",
    },
    {
        "name": "Forbes",
        "url": "https://www.forbes.com/money/feed/",
        "site_url": "https://www.forbes.com/money",
    },
    {
        "name": "FXStreet",
        "url": "https://www.fxstreet.com/rss/news",
        "site_url": "https://www.fxstreet.com/news",
    },
    {
        "name": "FRED Blog",
        "url": "https://fredblog.stlouisfed.org/feed/",
        "site_url": "https://fredblog.stlouisfed.org",
    },
    {
        "name": "Google News Business",
        "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
        "site_url": "https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB",
    },
    {
        "name": "Trading Economics",
        "url": "https://tradingeconomics.com/rss/news.aspx",
        "site_url": "https://tradingeconomics.com/news",
    },
]

# Well-known publisher URLs for sources that arrive via Finnhub (where the
# ``source`` field is the publisher name rather than one of our RSS feeds).
# Anything not in this map falls back to the article URL's hostname, so every
# source rendered on the UI always resolves to a real link.
PUBLISHER_URLS: dict[str, str] = {
    "Bloomberg": "https://www.bloomberg.com/markets",
    "MarketWatch": "https://www.marketwatch.com",
    "Yahoo": "https://finance.yahoo.com",
    "CNBC": "https://www.cnbc.com/markets",
    "Reuters": "https://www.reuters.com/markets",
    "Finnhub": "https://finnhub.io",
    "SeekingAlpha": "https://seekingalpha.com/market-news",
    "PR Newswire": "https://www.prnewswire.com/news-releases/financial-services-latest-news/",
    "Business Insider": "https://markets.businessinsider.com",
    "The Wall Street Journal": "https://www.wsj.com/news/markets",
    "WSJ": "https://www.wsj.com/news/markets",
    "Financial Times": "https://www.ft.com/markets",
    "FT": "https://www.ft.com/markets",
    "Barron's": "https://www.barrons.com",
    "The Economist": "https://www.economist.com/finance-and-economics",
    "Fortune": "https://fortune.com/section/finance",
}


def _derive_site_url(article_url: str) -> str | None:
    """Fallback: derive a homepage URL from an article URL's hostname."""
    if not article_url:
        return None
    try:
        parsed = urlparse(article_url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return None
    return None

# ── Helpers ──────────────────────────────────────────────────────────


def _cache_get(key: str, ttl: int = 0):
    return _cache.get(key)


def _cache_set(key: str, value: object, ttl: int | None = None):
    _cache.set(key, value, ttl=ttl)


def _time_ago(dt_str: str) -> str:
    try:
        ts = (
            int(dt_str)
            if dt_str.isdigit()
            else int(datetime.fromisoformat(dt_str).timestamp())
        )
    except (ValueError, TypeError):
        return "recently"
    diff = int(time.time()) - ts
    if diff < 60:
        return "just now"
    if diff < 3600:
        m = diff // 60
        return f"{m} minute{'s' if m != 1 else ''} ago"
    if diff < 86400:
        h = diff // 3600
        return f"{h} hour{'s' if h != 1 else ''} ago"
    d = diff // 86400
    return f"{d} day{'s' if d != 1 else ''} ago"


def _parse_rfc2822(date_str: str) -> float:
    """Parse RFC-2822 date (common in RSS) to a Unix timestamp."""
    try:
        return parsedate_to_datetime(date_str).timestamp()
    except Exception:
        pass
    try:
        return datetime.fromisoformat(date_str).timestamp()
    except Exception:
        return time.time()


# ── RSS fetching ─────────────────────────────────────────────────────


async def _fetch_single_rss(
    client: httpx.AsyncClient, feed: dict[str, str]
) -> list[dict]:
    """Fetch and parse one RSS feed, returning normalised article dicts."""
    try:
        resp = await client.get(
            feed["url"],
            headers={
                "User-Agent": "RobinhoodAICopilot/1.0 (news aggregator)",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            },
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.text)
    except Exception as exc:
        logger.debug(f"RSS fetch/parse failed for {feed['name']}: {exc}")
        return []

    items: list[dict] = []
    for item in root.iter("item"):
        title_el = item.find("title")
        desc_el = item.find("description")
        link_el = item.find("link")
        pub_el = item.find("pubDate")

        title = (title_el.text or "").strip() if title_el is not None else ""
        desc = (desc_el.text or "").strip() if desc_el is not None else ""
        link = (link_el.text or "").strip() if link_el is not None else ""
        pub = (pub_el.text or "").strip() if pub_el is not None else ""

        if not title:
            continue

        # Strip HTML tags from description
        clean_desc = desc
        if "<" in clean_desc:
            import re

            clean_desc = re.sub(r"<[^>]+>", "", clean_desc).strip()

        ts = _parse_rfc2822(pub) if pub else time.time()

        items.append(
            {
                "title": title,
                "summary": clean_desc[:500] if clean_desc else "",
                "source": feed["name"],
                "source_url": feed.get("site_url", ""),
                "url": link,
                "timestamp": ts,
            }
        )

    return items


async def _fetch_all_rss() -> list[dict]:
    """Fetch all RSS feeds concurrently and merge results."""
    cached = _cache_get("rss_all", RSS_TTL)
    if cached:
        return cached

    async with httpx.AsyncClient(timeout=12) as client:
        tasks = [_fetch_single_rss(client, feed) for feed in RSS_FEEDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    merged: list[dict] = []
    for r in results:
        if isinstance(r, list):
            merged.extend(r)

    merged.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    _cache_set("rss_all", merged, ttl=RSS_TTL)
    return merged


# ── Public API ───────────────────────────────────────────────────────


def _diversify_by_source(items: list[dict], limit: int, max_per_source: int) -> list[dict]:
    """Pick up to ``limit`` items with at most ``max_per_source`` per source.

    Items are assumed to be pre-sorted by recency (newest first). We first
    walk the list respecting the per-source cap. If we fall short of
    ``limit`` (rare — happens when the union has < ``limit`` sources * cap),
    we relax the cap and fill from the remainder to preserve recency.
    """
    chosen: list[dict] = []
    counts: dict[str, int] = {}

    for item in items:
        if len(chosen) >= limit:
            break
        src = item.get("source", "") or ""
        if counts.get(src, 0) >= max_per_source:
            continue
        counts[src] = counts.get(src, 0) + 1
        chosen.append(item)

    if len(chosen) < limit:
        chosen_urls = {c.get("url") for c in chosen}
        for item in items:
            if len(chosen) >= limit:
                break
            if item.get("url") in chosen_urls:
                continue
            chosen.append(item)

    return chosen


def _resolve_source_url(item: dict) -> str:
    """Best-effort mapping of an article's source name to a homepage URL."""
    if item.get("source_url"):
        return item["source_url"]
    source_name = item.get("source", "")
    if source_name in PUBLISHER_URLS:
        return PUBLISHER_URLS[source_name]
    derived = _derive_site_url(item.get("url", ""))
    return derived or ""


async def fetch_market_news() -> dict:
    """Aggregate news from Finnhub + RSS feeds. Returns headlines + articles."""
    cached = _cache_get("market_news", NEWS_TTL)
    if cached:
        return cached

    finnhub_task = _fetch_finnhub_news()
    rss_task = _fetch_all_rss()
    finnhub_items, rss_items = await asyncio.gather(
        finnhub_task, rss_task, return_exceptions=True
    )

    if isinstance(finnhub_items, BaseException):
        finnhub_items = []
    if isinstance(rss_items, BaseException):
        rss_items = []

    # Merge and deduplicate by title similarity
    all_items: list[dict] = []
    seen_titles: set[str] = set()

    for item in finnhub_items:
        key = item.get("title", "").lower()[:60]
        if key and key not in seen_titles:
            seen_titles.add(key)
            all_items.append(item)

    for item in rss_items:
        key = item.get("title", "").lower()[:60]
        if key and key not in seen_titles:
            seen_titles.add(key)
            all_items.append(item)

    all_items.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

    # Diversified slices: each section enforces the per-source cap
    # independently so the top-10 Market Summary and top-15 Developments both
    # represent multiple outlets even when one feed is firing hot.
    headline_items = _diversify_by_source(
        all_items, limit=HEADLINES_COUNT, max_per_source=MAX_PER_SOURCE
    )
    development_items = _diversify_by_source(
        all_items, limit=DEVELOPMENTS_COUNT, max_per_source=MAX_PER_SOURCE + 1
    )

    headlines = [
        {
            "title": item["title"],
            "summary": item.get("summary", ""),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
        }
        for item in headline_items
    ]

    articles = []
    for item in development_items:
        excerpt = item.get("summary", "") or ""
        if len(excerpt) > 280:
            excerpt = excerpt[:280] + "..."
        articles.append(
            {
                "source": item.get("source", ""),
                "time_ago": _time_ago(str(int(item.get("timestamp", time.time())))),
                "title": item["title"],
                "excerpt": excerpt,
                "url": item.get("url", ""),
            }
        )

    # Sources list is strictly the union of outlets that actually contributed
    # headlines or developments — never a hardcoded allow-list.
    used_items = headline_items + development_items
    sources: list[dict] = []
    seen_src: set[str] = set()
    for item in used_items:
        name = item.get("source", "") or ""
        if not name or name in seen_src:
            continue
        seen_src.add(name)
        sources.append({"name": name, "url": _resolve_source_url(item)})

    result = {
        "headlines": headlines,
        "articles": articles,
        "sources": sources,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _cache_set("market_news", result, ttl=NEWS_TTL)
    return result


async def _fetch_finnhub_news() -> list[dict]:
    """Fetch general market news from Finnhub (requires API key)."""
    settings = get_settings()
    api_key = settings.finnhub_api_key.strip()
    if not api_key:
        return []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{FINNHUB_BASE}/news",
                params={"category": "general", "token": api_key},
            )
            resp.raise_for_status()
            raw = resp.json()
    except Exception as exc:
        logger.error(f"Finnhub market news fetch failed: {exc}")
        return []

    items = []
    for article in raw[:15]:
        article_url = article.get("url", "")
        source_name = article.get("source", "Finnhub")
        items.append(
            {
                "title": article.get("headline", ""),
                "summary": article.get("summary", ""),
                "source": source_name,
                "source_url": PUBLISHER_URLS.get(source_name)
                or _derive_site_url(article_url)
                or "",
                "url": article_url,
                "timestamp": article.get("datetime", time.time()),
            }
        )
    return items


# NOTE: Earnings endpoints (weekly calendar, per-date detail, AI highlights)
# have moved to ``app/stocks/`` where they belong alongside the rest of the
# per-symbol market data surface.
