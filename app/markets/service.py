"""Market data service: aggregates news from multiple free RSS feeds + Finnhub,
and earnings data from Finnhub.

News sources (all free, no API key required for RSS):
  Finnhub /news (requires finnhub_api_key), CNBC, Reuters, Investing.com,
  Yahoo Finance, Forbes, FXStreet, FRED Blog, Google News Business.

Uses httpx for async HTTP, xml.etree for RSS parsing, and in-memory caching
with TTLs to avoid hammering upstream sources.
"""
from __future__ import annotations

import asyncio
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger("markets.service")

FINNHUB_BASE = "https://finnhub.io/api/v1"

_cache: dict[str, tuple[float, object]] = {}
NEWS_TTL = 300        # 5 min
EARNINGS_TTL = 900    # 15 min
RSS_TTL = 600         # 10 min

RSS_FEEDS: list[dict[str, str]] = [
    {
        "name": "CNBC",
        "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    },
    {
        "name": "CNBC Economy",
        "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    },
    {
        "name": "CNBC Earnings",
        "url": "https://www.cnbc.com/id/15839135/device/rss/rss.html",
    },
    {
        "name": "Reuters",
        "url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
    },
    {
        "name": "Investing.com",
        "url": "https://www.investing.com/rss/news.rss",
    },
    {
        "name": "Yahoo Finance",
        "url": "https://finance.yahoo.com/news/rssindex",
    },
    {
        "name": "Forbes",
        "url": "https://www.forbes.com/money/feed/",
    },
    {
        "name": "FXStreet",
        "url": "https://www.fxstreet.com/rss/news",
    },
    {
        "name": "FRED Blog",
        "url": "https://fredblog.stlouisfed.org/feed/",
    },
    {
        "name": "Google News Business",
        "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
    },
    {
        "name": "Trading Economics",
        "url": "https://tradingeconomics.com/rss/news.aspx",
    },
]

# ── Helpers ──────────────────────────────────────────────────────────


def _cache_get(key: str, ttl: int):
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < ttl:
        return entry[1]
    return None


def _cache_set(key: str, value: object):
    _cache[key] = (time.time(), value)


def _time_ago(dt_str: str) -> str:
    try:
        ts = int(dt_str) if dt_str.isdigit() else int(
            datetime.fromisoformat(dt_str).timestamp()
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

        items.append({
            "title": title,
            "summary": clean_desc[:500] if clean_desc else "",
            "source": feed["name"],
            "url": link,
            "timestamp": ts,
        })

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
    _cache_set("rss_all", merged)
    return merged


# ── Public API ───────────────────────────────────────────────────────


async def fetch_market_news() -> dict:
    """Aggregate news from Finnhub + RSS feeds. Returns headlines + articles."""
    cached = _cache_get("market_news", NEWS_TTL)
    if cached:
        return cached

    # Fire Finnhub and RSS in parallel
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

    headlines = []
    for item in all_items[:10]:
        headlines.append({
            "title": item["title"],
            "summary": item.get("summary", ""),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
        })

    articles = []
    for item in all_items[:15]:
        excerpt = item.get("summary", "") or ""
        if len(excerpt) > 280:
            excerpt = excerpt[:280] + "..."
        articles.append({
            "source": item.get("source", ""),
            "time_ago": _time_ago(str(int(item.get("timestamp", time.time())))),
            "title": item["title"],
            "excerpt": excerpt,
            "url": item.get("url", ""),
        })

    # Collect unique source names
    source_names = []
    seen_src: set[str] = set()
    for item in all_items:
        s = item.get("source", "")
        if s and s not in seen_src:
            seen_src.add(s)
            source_names.append(s)

    result = {
        "headlines": headlines,
        "articles": articles,
        "sources": source_names,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _cache_set("market_news", result)
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
        items.append({
            "title": article.get("headline", ""),
            "summary": article.get("summary", ""),
            "source": article.get("source", "Finnhub"),
            "url": article.get("url", ""),
            "timestamp": article.get("datetime", time.time()),
        })
    return items


# ── Earnings (unchanged — Finnhub only) ─────────────────────────────


async def fetch_earnings_calendar(target_date: str | None = None) -> dict:
    """Fetch earnings calendar for the week containing *target_date*."""
    today = datetime.now(timezone.utc).date()
    if target_date:
        try:
            center = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            center = today
    else:
        center = today

    weekday = center.isoweekday() % 7
    week_start = center - timedelta(days=weekday)
    week_end = week_start + timedelta(days=6)

    cache_key = f"earnings_{week_start.isoformat()}"
    cached = _cache_get(cache_key, EARNINGS_TTL)
    if cached:
        return cached

    settings = get_settings()
    api_key = settings.finnhub_api_key.strip()
    if not api_key:
        logger.warning("Finnhub API key not set; returning empty earnings")
        return _empty_earnings_week(week_start, today)

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{FINNHUB_BASE}/calendar/earnings",
                params={
                    "from": week_start.isoformat(),
                    "to": week_end.isoformat(),
                    "token": api_key,
                },
            )
            resp.raise_for_status()
            raw = resp.json()
    except Exception as exc:
        logger.error(f"Finnhub earnings fetch failed: {exc}")
        return _empty_earnings_week(week_start, today)

    earnings_list = raw.get("earningsCalendar", [])

    by_date: dict[str, list[dict]] = {}
    for e in earnings_list:
        d = e.get("date", "")
        by_date.setdefault(d, []).append(e)

    day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    week = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_str = day.isoformat()
        entries = by_date.get(day_str, [])
        week.append({
            "date": day_str,
            "day_label": day_labels[i],
            "earnings_count": len(entries),
            "symbols": [e.get("symbol", "") for e in entries[:5]],
        })

    result = {
        "week": week,
        "selected_date": center.isoformat(),
    }
    _cache_set(cache_key, result)
    return result


async def fetch_earnings_for_date(date: str) -> dict:
    """Return detailed earnings entries for a specific date."""
    cache_key = f"earnings_detail_{date}"
    cached = _cache_get(cache_key, EARNINGS_TTL)
    if cached:
        return cached

    settings = get_settings()
    api_key = settings.finnhub_api_key.strip()
    if not api_key:
        return {"entries": [], "date": date}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{FINNHUB_BASE}/calendar/earnings",
                params={"from": date, "to": date, "token": api_key},
            )
            resp.raise_for_status()
            raw = resp.json()
    except Exception as exc:
        logger.error(f"Finnhub earnings detail fetch failed: {exc}")
        return {"entries": [], "date": date}

    entries = []
    for e in raw.get("earningsCalendar", []):
        hour_raw = e.get("hour", "")
        if hour_raw == "bmo":
            hour_display = "Before Open"
        elif hour_raw == "amc":
            hour_display = "After Close"
        else:
            hour_display = hour_raw or "TBD"

        entries.append({
            "symbol": e.get("symbol", ""),
            "company": e.get("symbol", ""),
            "date": e.get("date", date),
            "hour": hour_display,
            "quarter": e.get("quarter", 0),
            "year": e.get("year", 0),
            "eps_estimate": e.get("epsEstimate"),
            "eps_actual": e.get("epsActual"),
            "revenue_estimate": e.get("revenueEstimate"),
            "revenue_actual": e.get("revenueActual"),
        })

    symbols_to_resolve = [e["symbol"] for e in entries if e["symbol"]]
    if symbols_to_resolve and api_key:
        try:
            profiles = await _batch_profiles(symbols_to_resolve[:20], api_key)
            for e in entries:
                if e["symbol"] in profiles:
                    e["company"] = profiles[e["symbol"]]
        except Exception:
            pass

    result = {"entries": entries, "date": date}
    _cache_set(cache_key, result)
    return result


async def _batch_profiles(symbols: list[str], api_key: str) -> dict[str, str]:
    """Fetch company names for a batch of symbols. Cached per-symbol."""
    _profile_cache_key = "company_profiles"
    profiles = _cache_get(_profile_cache_key, 86400) or {}
    missing = [s for s in symbols if s not in profiles]

    if missing:
        async with httpx.AsyncClient(timeout=10) as client:
            for sym in missing[:20]:
                try:
                    resp = await client.get(
                        f"{FINNHUB_BASE}/stock/profile2",
                        params={"symbol": sym, "token": api_key},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        name = data.get("name", sym)
                        profiles[sym] = name if name else sym
                except Exception:
                    profiles[sym] = sym
        _cache_set(_profile_cache_key, profiles)

    return profiles


def _empty_earnings_week(week_start, today) -> dict:
    day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    week = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        week.append({
            "date": day.isoformat(),
            "day_label": day_labels[i],
            "earnings_count": 0,
            "symbols": [],
        })
    return {"week": week, "selected_date": today.isoformat()}
