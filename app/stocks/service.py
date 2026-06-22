"""Per-symbol market data service.

Uses yfinance (unofficial Yahoo wrapper) for quotes / candles / key stats
and Finnhub for company profile, news, and earnings. Every outbound call
is wrapped in a short-TTL in-memory cache to keep the Stock Detail page
feeling instant while still surviving the Finnhub free-tier rate limit.

yfinance is synchronous  -  we run every yfinance call inside
``asyncio.to_thread`` so we don't block the event loop.

All public functions return typed Pydantic models from ``schemas.py``.
Failures degrade gracefully: a Finnhub 429 never tanks the whole
endpoint, it just returns ``None`` for that field.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

try:
    import yfinance as yf  # noqa: F401  (used inside threads)

    _YF_AVAILABLE = True
except Exception:  # pragma: no cover  -  yfinance missing in some envs
    yf = None  # type: ignore[assignment]
    _YF_AVAILABLE = False

from app.config import get_settings
from app.utils.logging import get_logger

from .schemas import (
    CandlePoint,
    CandleRange,
    EarningsQuarter,
    PortfolioNewsResponse,
    StockCandles,
    StockCardOut,
    StockDetailResponse,
    StockEarnings,
    StockKeyStats,
    StockNewsItem,
    StockNewsResponse,
    StockPositionSummary,
    StockProfile,
    StockQuote,
    StockUniverseResponse,
)

logger = get_logger("stocks.service")

FINNHUB_BASE = "https://finnhub.io/api/v1"

# ── In-memory caches ──────────────────────────────────────────────────

from app.utils.cache import BoundedTTLCache

_cache = BoundedTTLCache(maxsize=4096, default_ttl=900)

QUOTE_TTL = 60           # 1 min  -  prices move
PROFILE_TTL = 24 * 3600  # 24 h  -  profiles rarely change
KEYSTATS_TTL = 15 * 60   # 15 min  -  fundamentals update slowly
EARNINGS_TTL = 60 * 60   # 1 h  -  EPS history doesn't change intra-day
NEWS_TTL = 5 * 60        # 5 min  -  news is the only fast-moving field
CANDLES_TTL_FAST = 60    # 1 min for intraday (1D / 1W)
CANDLES_TTL_SLOW = 15 * 60  # 15 min for daily+

# yfinance history parameters per range.
_RANGE_PARAMS: dict[CandleRange, tuple[str, str]] = {
    "1D":  ("1d",   "5m"),
    "1W":  ("5d",   "30m"),
    "1M":  ("1mo",  "1d"),
    "3M":  ("3mo",  "1d"),
    "YTD": ("ytd",  "1d"),
    "1Y":  ("1y",   "1d"),
    "5Y":  ("5y",   "1wk"),
    "MAX": ("max",  "1mo"),
}


def _cache_get(key: str, ttl: int = 0) -> Any | None:
    """Read from bounded cache. *ttl* param is kept for call-site compat but
    the actual TTL is enforced at write time via ``_cache_set``."""
    return _cache.get(key)


def _cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    _cache.set(key, value, ttl=ttl or 900)


# ── Universe ─────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _load_sp500_seed() -> list[dict[str, str]]:
    """Load the curated universe JSON once and cache it."""
    path = Path(__file__).parent / "data" / "sp500.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # noqa: BLE001  -  never break the endpoint
        logger.error(f"Failed to load sp500.json: {exc}")
        return []


def get_universe_seed() -> list[dict[str, str]]:
    """Public accessor used by the router to list the browsable universe."""
    return list(_load_sp500_seed())


def _time_ago(ts: datetime | float | int | None) -> str:
    """Human-friendly 'X min ago' helper. Accepts unix seconds or datetime."""
    if ts is None:
        return ""
    if isinstance(ts, (int, float)):
        seconds = int(ts)
    else:
        seconds = int(ts.timestamp())
    diff = int(time.time()) - seconds
    if diff < 60:
        return "just now"
    if diff < 3600:
        m = diff // 60
        return f"{m} min{'s' if m != 1 else ''} ago"
    if diff < 86400:
        h = diff // 3600
        return f"{h}h ago"
    return f"{diff // 86400}d ago"


# ── yfinance helpers (sync, run in thread) ───────────────────────────


_CRYPTO_YAHOO_SUFFIX = "-USD"
_CRYPTO_NAMES = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "DOGE": "Dogecoin",
    "ADA": "Cardano",
    "XRP": "XRP",
    "LTC": "Litecoin",
    "BCH": "Bitcoin Cash",
    "AVAX": "Avalanche",
    "LINK": "Chainlink",
    "DOT": "Polkadot",
    "MATIC": "Polygon",
}


def _is_crypto_symbol(symbol: str, asset_type: Optional[str] = None) -> bool:
    return (asset_type or "").lower() == "crypto" or symbol.upper() in _CRYPTO_NAMES


def _market_symbol(symbol: str, asset_type: Optional[str] = None) -> str:
    """Provider ticker symbol. Crypto needs Yahoo's pair form, e.g. BTC-USD."""
    sym = symbol.replace(".", "-").upper()
    if _is_crypto_symbol(sym, asset_type) and "-" not in sym:
        return f"{sym}{_CRYPTO_YAHOO_SUFFIX}"
    return sym


def _yf_ticker(symbol: str):
    """Construct a yfinance Ticker  -  BRK.B / RDS.B use hyphens on Yahoo."""
    if yf is None:
        raise RuntimeError("yfinance is not installed")
    return yf.Ticker(_market_symbol(symbol))


def _yf_history(symbol: str, period: str, interval: str):
    """Blocking: return a pandas DataFrame of OHLCV candles."""
    t = _yf_ticker(symbol)
    # ``auto_adjust=False`` keeps the raw Close column so we can report
    # split/dividend unadjusted prices alongside adjusted-close charts.
    return t.history(period=period, interval=interval, auto_adjust=False)


def _yf_fast_info(symbol: str) -> dict[str, Any]:
    """Blocking: lightweight quote snapshot (no API call to Yahoo's slow /info)."""
    t = _yf_ticker(symbol)
    fi = getattr(t, "fast_info", None)
    if fi is None:
        return {}
    try:
        # ``fast_info`` is a dict-like object in newer yfinance; fall back to dict().
        return {k: fi[k] for k in fi.keys()}  # type: ignore[attr-defined]
    except Exception:
        try:
            return dict(fi)  # type: ignore[call-overload]
        except Exception:
            return {}


def _yf_info(symbol: str) -> dict[str, Any]:
    """Blocking: full ``.info`` dict. Heavier than fast_info  -  use sparingly."""
    t = _yf_ticker(symbol)
    try:
        info = t.get_info()  # type: ignore[attr-defined]
    except Exception:
        info = {}
    return info or {}


# ── Quote ─────────────────────────────────────────────────────────────


async def fetch_quote(symbol: str) -> StockQuote:
    """Latest quote snapshot. Always returns a StockQuote (empty on failure)."""
    symbol = symbol.upper()
    is_crypto = _is_crypto_symbol(symbol)
    key = f"quote:{symbol}"
    cached = _cache_get(key, QUOTE_TTL)
    if cached is not None:
        return cached

    fi: dict[str, Any] = {}
    if _YF_AVAILABLE:
        try:
            fi = await asyncio.to_thread(_yf_fast_info, symbol)
        except Exception as exc:
            logger.debug(f"fast_info failed for {symbol}: {exc}")
            fi = {}

    def _f(key_: str) -> Optional[float]:
        v = fi.get(key_)
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    price = _f("last_price") or _f("lastPrice") or _f("regular_market_price")
    prev_close = (
        _f("previous_close")
        or _f("previousClose")
        or _f("regular_market_previous_close")
    )
    change = (price - prev_close) if (price is not None and prev_close) else None
    change_pct = (
        (change / prev_close * 100.0) if (change is not None and prev_close) else None
    )

    if price is None and not is_crypto:
        fin_quote = await _finnhub_get("/quote", {"symbol": symbol}) or {}

        def _q(k: str) -> Optional[float]:
            v = fin_quote.get(k)
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        price = _q("c")
        prev_close = _q("pc")
        change = _q("d")
        change_pct = _q("dp")
        quote = StockQuote(
            symbol=symbol,
            price=price,
            previous_close=prev_close,
            open=_q("o"),
            day_high=_q("h"),
            day_low=_q("l"),
            change=change,
            change_percent=change_pct,
            currency="USD",
            as_of=(
                datetime.fromtimestamp(int(fin_quote["t"]), tz=timezone.utc)
                if fin_quote.get("t")
                else datetime.now(timezone.utc)
            ),
        )
    else:
        quote = StockQuote(
            symbol=symbol,
            price=price,
            previous_close=prev_close,
            open=_f("open") or _f("regular_market_open"),
            day_high=_f("day_high") or _f("dayHigh") or _f("regular_market_day_high"),
            day_low=_f("day_low") or _f("dayLow") or _f("regular_market_day_low"),
            volume=_f("last_volume") or _f("regular_market_volume") or _f("volume"),
            change=change,
            change_percent=change_pct,
            currency=str(fi.get("currency") or "USD"),
            market_state=str(fi.get("market_state") or fi.get("marketState") or "") or None,
            as_of=datetime.now(timezone.utc),
        )
    _cache_set(key, quote, ttl=QUOTE_TTL)
    return quote


# ── Candles ──────────────────────────────────────────────────────────


async def fetch_candles(symbol: str, range_: CandleRange) -> StockCandles:
    symbol = symbol.upper()
    if range_ not in _RANGE_PARAMS:
        range_ = "1M"
    period, interval = _RANGE_PARAMS[range_]

    ttl = CANDLES_TTL_FAST if range_ in ("1D", "1W") else CANDLES_TTL_SLOW
    key = f"candles:{symbol}:{range_}"
    cached = _cache_get(key, ttl)
    if cached is not None:
        return cached

    df = None
    if _YF_AVAILABLE:
        try:
            df = await asyncio.to_thread(_yf_history, symbol, period, interval)
        except Exception as exc:
            logger.debug(f"history({symbol}, {range_}) failed: {exc}")
            df = None

    points: list[CandlePoint] = []
    if df is not None and not df.empty:
        # df is a pandas DataFrame with DatetimeIndex and columns Open/High/Low/Close/Volume.
        for idx, row in df.iterrows():
            try:
                t = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                o = float(row["Open"])
                h = float(row["High"])
                lo = float(row["Low"])
                c = float(row["Close"])
                v = float(row.get("Volume", 0) or 0)
            except Exception:
                continue
            # Skip rows where yfinance occasionally reports NaN for all fields.
            if any(x != x for x in (o, h, lo, c)):  # NaN check
                continue
            points.append(CandlePoint(t=t, o=o, h=h, l=lo, c=c, v=v))

    if not points:
        try:
            async with httpx.AsyncClient(
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"},
            ) as client:
                resp = await client.get(
                    f"https://query1.finance.yahoo.com/v8/finance/chart/{_market_symbol(symbol)}",
                    params={"range": period, "interval": interval},
                )
                resp.raise_for_status()
                result = (resp.json().get("chart", {}).get("result") or [None])[0]
        except Exception as exc:
            logger.debug(f"Yahoo chart fallback failed for {symbol}: {exc}")
            result = None

        if result:
            timestamps = result.get("timestamp") or []
            quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
            opens = quote.get("open") or []
            highs = quote.get("high") or []
            lows = quote.get("low") or []
            closes = quote.get("close") or []
            volumes = quote.get("volume") or []
            for i, ts in enumerate(timestamps):
                try:
                    o = float(opens[i])
                    h = float(highs[i])
                    lo = float(lows[i])
                    c = float(closes[i])
                    v = float(volumes[i]) if i < len(volumes) and volumes[i] is not None else None
                except (TypeError, ValueError, IndexError):
                    continue
                if any(x != x for x in (o, h, lo, c)):  # NaN check
                    continue
                points.append(
                    CandlePoint(
                        t=datetime.fromtimestamp(int(ts), tz=timezone.utc),
                        o=o,
                        h=h,
                        l=lo,
                        c=c,
                        v=v,
                    )
                )

    if not points and not _is_crypto_symbol(symbol):
        resolution = {
            "1D": "5",
            "1W": "30",
            "1M": "D",
            "3M": "D",
            "YTD": "D",
            "1Y": "D",
            "5Y": "W",
            "MAX": "M",
        }[range_]
        now = datetime.now(timezone.utc)
        start = {
            "1D": now - timedelta(days=1),
            "1W": now - timedelta(days=7),
            "1M": now - timedelta(days=31),
            "3M": now - timedelta(days=93),
            "YTD": datetime(now.year, 1, 1, tzinfo=timezone.utc),
            "1Y": now - timedelta(days=366),
            "5Y": now - timedelta(days=365 * 5 + 2),
            "MAX": now - timedelta(days=365 * 10),
        }[range_]
        raw = await _finnhub_get(
            "/stock/candle",
            {
                "symbol": symbol,
                "resolution": resolution,
                "from": int(start.timestamp()),
                "to": int(now.timestamp()),
            },
        ) or {}
        if raw.get("s") == "ok":
            rows = zip(
                raw.get("t", []),
                raw.get("o", []),
                raw.get("h", []),
                raw.get("l", []),
                raw.get("c", []),
                raw.get("v", []),
            )
            for ts, o, h, lo, c, v in rows:
                try:
                    points.append(
                        CandlePoint(
                            t=datetime.fromtimestamp(int(ts), tz=timezone.utc),
                            o=float(o),
                            h=float(h),
                            l=float(lo),
                            c=float(c),
                            v=float(v) if v is not None else None,
                        )
                    )
                except (TypeError, ValueError):
                    continue

    start_price = points[0].c if points else None
    end_price = points[-1].c if points else None
    change = (
        (end_price - start_price) if (start_price is not None and end_price is not None) else None
    )
    change_pct = (
        (change / start_price * 100.0)
        if (change is not None and start_price)
        else None
    )

    out = StockCandles(
        symbol=symbol,
        range=range_,
        interval=interval,
        points=points,
        start_price=start_price,
        end_price=end_price,
        change=change,
        change_percent=change_pct,
    )
    candle_ttl = CANDLES_TTL_FAST if range_ in ("1D", "1W") else CANDLES_TTL_SLOW
    _cache_set(key, out, ttl=candle_ttl)
    return out


# ── Key stats ────────────────────────────────────────────────────────


async def fetch_key_stats(symbol: str) -> StockKeyStats:
    symbol = symbol.upper()
    is_crypto = _is_crypto_symbol(symbol)
    key = f"keystats:{symbol}"
    cached = _cache_get(key, KEYSTATS_TTL)
    if cached is not None:
        return cached

    info: dict[str, Any] = {}
    fast_info: dict[str, Any] = {}
    if _YF_AVAILABLE:
        try:
            info = await asyncio.to_thread(_yf_info, symbol)
        except Exception as exc:
            logger.debug(f"info({symbol}) failed: {exc}")
            info = {}
        try:
            fast_info = await asyncio.to_thread(_yf_fast_info, symbol)
        except Exception as exc:
            logger.debug(f"fast_info({symbol}) failed: {exc}")
            fast_info = {}

    def _f(k: str) -> Optional[float]:
        v = info.get(k)
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    def _fi(k: str) -> Optional[float]:
        v = fast_info.get(k)
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    stats = StockKeyStats(
        symbol=symbol,
        market_cap=_f("marketCap") or _fi("marketCap"),
        pe_ratio=_f("trailingPE"),
        forward_pe=_f("forwardPE"),
        dividend_yield=_f("dividendYield"),
        eps_ttm=_f("trailingEps"),
        beta=_f("beta"),
        average_volume=_f("averageVolume") or _fi("tenDayAverageVolume") or _fi("threeMonthAverageVolume"),
        volume=_f("volume") or _f("regularMarketVolume") or _fi("lastVolume"),
        day_high=_f("dayHigh") or _f("regularMarketDayHigh") or _fi("dayHigh"),
        day_low=_f("dayLow") or _f("regularMarketDayLow") or _fi("dayLow"),
        open_price=_f("open") or _f("regularMarketOpen") or _fi("open"),
        fifty_two_week_high=_f("fiftyTwoWeekHigh") or _fi("yearHigh"),
        fifty_two_week_low=_f("fiftyTwoWeekLow") or _fi("yearLow"),
        short_ratio=_f("shortRatio"),
        shares_outstanding=_f("sharesOutstanding") or _fi("shares"),
    )
    if not is_crypto and all(
        getattr(stats, field) is None
        for field in (
            "market_cap",
            "pe_ratio",
            "forward_pe",
            "eps_ttm",
            "beta",
            "fifty_two_week_high",
            "fifty_two_week_low",
        )
    ):
        metrics_raw = await _finnhub_get(
            "/stock/metric",
            {"symbol": symbol, "metric": "all"},
        ) or {}
        metric = metrics_raw.get("metric", {}) if isinstance(metrics_raw, dict) else {}
        quote_raw = await _finnhub_get("/quote", {"symbol": symbol}) or {}

        def _m(k: str) -> Optional[float]:
            v = metric.get(k)
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        def _q(k: str) -> Optional[float]:
            v = quote_raw.get(k)
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        market_cap_m = _m("marketCapitalization")
        shares_m = _m("shareOutstanding")
        stats = StockKeyStats(
            symbol=symbol,
            market_cap=(market_cap_m * 1_000_000 if market_cap_m is not None else None),
            pe_ratio=_m("peTTM") or _m("peNormalizedAnnual"),
            forward_pe=_m("forwardPE"),
            dividend_yield=(
                _m("dividendYieldIndicatedAnnual") / 100
                if _m("dividendYieldIndicatedAnnual") is not None
                else None
            ),
            eps_ttm=_m("epsInclExtraItemsTTM"),
            beta=_m("beta"),
            average_volume=(
                _m("10DayAverageTradingVolume") * 1_000_000
                if _m("10DayAverageTradingVolume") is not None
                else None
            ),
            volume=_q("v"),
            day_high=_q("h"),
            day_low=_q("l"),
            open_price=_q("o"),
            fifty_two_week_high=_m("52WeekHigh"),
            fifty_two_week_low=_m("52WeekLow"),
            short_ratio=_m("shortInterestRatio"),
            shares_outstanding=(shares_m * 1_000_000 if shares_m is not None else None),
        )
    _cache_set(key, stats, ttl=KEYSTATS_TTL)
    return stats


# ── Finnhub helpers ──────────────────────────────────────────────────


async def _finnhub_get(
    path: str, params: dict[str, Any], *, timeout: int = 10
) -> Any | None:
    """Thin Finnhub GET with graceful failure + logging."""
    settings = get_settings()
    api_key = settings.finnhub_api_key.strip()
    if not api_key:
        return None
    query = {**params, "token": api_key}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{FINNHUB_BASE}{path}", params=query)
            if resp.status_code == 429:
                logger.warning(f"Finnhub rate limit on {path}")
                return None
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.debug(f"Finnhub {path} failed: {exc}")
        return None


# ── Profile ──────────────────────────────────────────────────────────


_ETF_HINT_SECTORS = {"ETF", "Exchange Traded Fund"}
_CARD_ASSET_TYPES = {
    "stock",
    "etf",
    "crypto",
    "option",
    "mutual_fund",
    "bond",
    "cash",
    "unknown",
}


def _normalize_card_asset_type(value: Any, *, sector: Optional[str] = None) -> str:
    """Keep portfolio asset types from breaking the Stocks tab response."""
    if value:
        asset_type = str(value).strip().lower()
        if asset_type in _CARD_ASSET_TYPES:
            return asset_type
    return "etf" if sector == "ETF" else "stock"


async def fetch_profile(symbol: str) -> StockProfile:
    """Finnhub-first profile with yfinance fallback for description/CEO/etc."""
    symbol = symbol.upper()
    key = f"profile:{symbol}"
    cached = _cache_get(key, PROFILE_TTL)
    if cached is not None:
        return cached

    if _is_crypto_symbol(symbol):
        profile = StockProfile(
            symbol=symbol,
            name=_CRYPTO_NAMES.get(symbol, symbol),
            asset_type="crypto",
            exchange="Crypto",
            currency="USD",
            sector="Cryptocurrency",
            industry="Digital Assets",
        )
        _cache_set(key, profile, ttl=PROFILE_TTL)
        return profile

    # 1) Finnhub /stock/profile2  -  canonical source for sector/industry/logo.
    fin = await _finnhub_get("/stock/profile2", {"symbol": symbol}) or {}

    # 2) yfinance .info  -  richer free-text fields (description, CEO, HQ).
    info: dict[str, Any] = {}
    if _YF_AVAILABLE:
        try:
            info = await asyncio.to_thread(_yf_info, symbol) or {}
        except Exception:
            info = {}

    name = (
        fin.get("name")
        or info.get("longName")
        or info.get("shortName")
        or symbol
    )

    sector_raw = fin.get("finnhubIndustry") or info.get("sector")
    is_etf = (
        (info.get("quoteType") or "").lower() == "etf"
        or (sector_raw or "") in _ETF_HINT_SECTORS
        or symbol.endswith("ETF")
    )
    asset_type = "etf" if is_etf else ("stock" if sector_raw else "unknown")

    # Headquarters string: "City, State" or "City, Country".
    city = info.get("city") or ""
    state = info.get("state") or ""
    country = info.get("country") or fin.get("country") or ""
    hq_parts = [p for p in (city, state, country) if p]
    headquarters = ", ".join(hq_parts) if hq_parts else None

    # ipo_date is an ISO-format string like "1980-12-12" from Finnhub.
    ipo: Optional[date] = None
    ipo_raw = fin.get("ipo")
    if ipo_raw:
        try:
            ipo = date.fromisoformat(str(ipo_raw))
        except ValueError:
            ipo = None

    # CEO pulled from the first officer marked with a CEO-ish title.
    ceo: Optional[str] = None
    officers = info.get("companyOfficers") or []
    for o in officers:
        title = (o.get("title") or "").lower()
        if "chief executive" in title or title.endswith("ceo") or "ceo" in title:
            ceo = o.get("name")
            break

    founded: Optional[int] = None
    founded_raw = info.get("founded") or info.get("foundedYear")
    try:
        if founded_raw is not None:
            founded = int(founded_raw)
    except (TypeError, ValueError):
        founded = None

    profile = StockProfile(
        symbol=symbol,
        name=name,
        asset_type=asset_type,  # type: ignore[arg-type]
        exchange=fin.get("exchange") or info.get("exchange"),
        currency=(fin.get("currency") or info.get("currency") or "USD"),
        country=country or None,
        sector=(info.get("sector") or None),
        industry=(fin.get("finnhubIndustry") or info.get("industry") or None),
        website=(fin.get("weburl") or info.get("website")),
        logo=fin.get("logo"),
        description=(info.get("longBusinessSummary") or None),
        ceo=ceo,
        employees=(int(info["fullTimeEmployees"]) if info.get("fullTimeEmployees") else None),
        headquarters=headquarters,
        founded=founded,
        ipo_date=ipo,
    )
    _cache_set(key, profile, ttl=PROFILE_TTL)
    return profile


# ── Earnings ─────────────────────────────────────────────────────────


def _surprise(est: Optional[float], actual: Optional[float]) -> tuple[
    Optional[str], Optional[float]
]:
    if est is None or actual is None or est == 0:
        return (None, None)
    pct = (actual - est) / abs(est) * 100.0
    if pct > 1:
        return ("beat", pct)
    if pct < -1:
        return ("miss", pct)
    return ("inline", pct)


async def fetch_earnings(symbol: str, *, history: int = 4) -> StockEarnings:
    """Past (default 4) + next earnings event, from Finnhub.

    Uses two Finnhub endpoints:
      - ``/stock/earnings`` for reported quarters with EPS est/actual.
      - ``/calendar/earnings`` for the next scheduled event.
    """
    symbol = symbol.upper()
    if _is_crypto_symbol(symbol):
        return StockEarnings(symbol=symbol)

    key = f"earnings:{symbol}:{history}"
    cached = _cache_get(key, EARNINGS_TTL)
    if cached is not None:
        return cached

    history_raw = await _finnhub_get("/stock/earnings", {"symbol": symbol}) or []
    past: list[EarningsQuarter] = []
    for e in history_raw[:history]:
        try:
            d = date.fromisoformat(e["period"])
        except (KeyError, ValueError):
            continue
        est = e.get("estimate")
        act = e.get("actual")
        sur_label, sur_pct = _surprise(est, act)
        past.append(
            EarningsQuarter(
                date=d,
                quarter=e.get("quarter"),
                year=e.get("year") or d.year,
                eps_estimate=est,
                eps_actual=act,
                surprise=sur_label,  # type: ignore[arg-type]
                surprise_percent=sur_pct,
                reported=act is not None,
            )
        )

    # Next event: query 90 days out.
    today = date.today()
    future_end = (today + timedelta(days=90)).isoformat()
    cal = await _finnhub_get(
        "/calendar/earnings",
        {"symbol": symbol, "from": today.isoformat(), "to": future_end},
    ) or {}
    cal_rows = cal.get("earningsCalendar", []) if isinstance(cal, dict) else []

    next_event: Optional[EarningsQuarter] = None
    for row in cal_rows:
        try:
            d = date.fromisoformat(row["date"])
        except (KeyError, ValueError):
            continue
        if d < today:
            continue
        hour_raw = (row.get("hour") or "").lower()
        hour = {"bmo": "Before Open", "amc": "After Close"}.get(hour_raw, hour_raw or None)
        est = row.get("epsEstimate")
        act = row.get("epsActual")
        next_event = EarningsQuarter(
            date=d,
            quarter=row.get("quarter"),
            year=row.get("year") or d.year,
            eps_estimate=est,
            eps_actual=act,
            revenue_estimate=row.get("revenueEstimate"),
            revenue_actual=row.get("revenueActual"),
            hour=hour,
            reported=act is not None,
        )
        break

    out = StockEarnings(symbol=symbol, next_event=next_event, history=past)
    _cache_set(key, out, ttl=EARNINGS_TTL)
    return out


# ── News (per-symbol) ────────────────────────────────────────────────


def _derive_host(url: str) -> Optional[str]:
    try:
        p = urlparse(url)
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}"
    except Exception:
        return None
    return None


# Hostname → display name. We prefer the URL hostname when it points to a
# known publisher because Finnhub's ``source`` text is occasionally wrong
# (it sometimes labels an article "Yahoo" when the URL goes to Reuters).
# For finnhub.io aggregator URLs the hostname is useless, so we fall back
# to Finnhub's ``source`` field  -  see ``_publisher_for_article``.
_PUBLISHER_BY_HOST: dict[str, str] = {
    "reuters.com": "Reuters",
    "bloomberg.com": "Bloomberg",
    "cnbc.com": "CNBC",
    "wsj.com": "Wall Street Journal",
    "nytimes.com": "New York Times",
    "ft.com": "Financial Times",
    "marketwatch.com": "MarketWatch",
    "barrons.com": "Barron's",
    "fortune.com": "Fortune",
    "forbes.com": "Forbes",
    "seekingalpha.com": "Seeking Alpha",
    "investors.com": "IBD",
    "investorplace.com": "InvestorPlace",
    "fool.com": "Motley Fool",
    "businesswire.com": "Business Wire",
    "prnewswire.com": "PR Newswire",
    "globenewswire.com": "GlobeNewswire",
    "yahoo.com": "Yahoo Finance",
    "finance.yahoo.com": "Yahoo Finance",
    "google.com": "Google News",
    "news.google.com": "Google News",
    "apnews.com": "AP News",
    "axios.com": "Axios",
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "theguardian.com": "The Guardian",
    "ft.com.uk": "Financial Times",
    "techcrunch.com": "TechCrunch",
    "theverge.com": "The Verge",
    "engadget.com": "Engadget",
    "investopedia.com": "Investopedia",
    "kiplinger.com": "Kiplinger",
    "morningstar.com": "Morningstar",
    "zacks.com": "Zacks",
    "thestreet.com": "TheStreet",
    "benzinga.com": "Benzinga",
    "coindesk.com": "CoinDesk",
    "cointelegraph.com": "Cointelegraph",
    "decrypt.co": "Decrypt",
    "theblock.co": "The Block",
}


def _humanize_host(host: str) -> str:
    """Fallback display name when a hostname isn't in ``_PUBLISHER_BY_HOST``.

    Drops common subdomains, then title-cases the second-level domain:
    ``markets.businessinsider.com`` -> ``Businessinsider``.
    """
    parts = [p for p in host.split(".") if p and p not in {"www", "m", "amp", "mobile"}]
    if not parts:
        return host
    if len(parts) == 1:
        return parts[0].capitalize()
    return parts[-2].capitalize()


# Hosts where the URL itself is just a redirector / aggregator and tells
# us nothing about the actual publisher. For these we MUST fall back to
# Finnhub's ``source`` field  -  humanizing the hostname would render
# "Finnhub" or "Google" on every card.
_AGGREGATOR_HOSTS: set[str] = {
    "finnhub.io",
    "finnhub.com",
    "news.google.com",
    "google.com",
    "msn.com",
    "flipboard.com",
    "feedproxy.google.com",
}

# Finnhub source values that are too generic to display.
_GENERIC_SOURCE_VALUES: set[str] = {
    "",
    "finnhub",
    "finnhub news",
    "news",
    "rss",
    "feed",
    "n/a",
    "unknown",
}


def _publisher_for_article(url: str, finnhub_source: Optional[str]) -> str:
    """Best-effort publisher name combining URL hostname + Finnhub's source.

    Priority:
      1. URL hostname mapped to a known publisher (most accurate).
      2. Finnhub's ``source`` text when it isn't generic.
      3. For aggregator URLs (``finnhub.io`` etc.) we MUST use Finnhub's
         text even if generic  -  humanizing the hostname would label every
         card "Finnhub", which is exactly the bug we're fixing.
      4. Humanize the hostname as a last resort.

    Always returns something non-empty.
    """
    finnhub_text = (finnhub_source or "").strip()
    finnhub_clean = finnhub_text.lower()

    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        host = ""
    short = ".".join(host.split(".")[-2:]) if host else ""

    if host in _PUBLISHER_BY_HOST:
        return _PUBLISHER_BY_HOST[host]
    if short in _PUBLISHER_BY_HOST:
        return _PUBLISHER_BY_HOST[short]

    if finnhub_text and finnhub_clean not in _GENERIC_SOURCE_VALUES:
        return finnhub_text

    if host in _AGGREGATOR_HOSTS or short in _AGGREGATOR_HOSTS:
        return finnhub_text or "News"

    if host:
        return _humanize_host(host)
    return "News"


# Match standalone uppercase tickers (1–5 chars). Used to verify whether
# the queried symbol actually appears in the article text before we tag.
_TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")


@lru_cache(maxsize=1)
def _seed_name_index() -> dict[str, list[str]]:
    """Symbol -> list of name fragments (full + first word) for substring matching.

    Built once from the SP500 seed and crypto names so we can recognize
    company mentions without a per-call database lookup. The first word
    of the full name (e.g., "Apple" from "Apple Inc.") catches the common
    case where headlines drop the corporate suffix.
    """
    idx: dict[str, list[str]] = {}
    for entry in _load_sp500_seed():
        sym = (entry.get("symbol") or "").upper()
        name = (entry.get("name") or "").strip()
        if not sym or not name:
            continue
        first = name.split()[0]
        idx[sym] = [name, first] if first.lower() != name.lower() else [name]
    for sym, name in _CRYPTO_NAMES.items():
        idx[sym] = [name]
    return idx


def _article_mentions_symbol(symbol: str, *parts: str) -> bool:
    """True if ``symbol`` (or its company name) appears in any part."""
    needle = symbol.upper()
    for part in parts:
        if not part:
            continue
        if needle in {m.group(0) for m in _TICKER_RE.finditer(part)}:
            return True
        if f"({needle})" in part or f" {needle} " in f" {part} ":
            return True

    # Company-name fallback: "Nvidia announces..." should still tag NVDA.
    names = _seed_name_index().get(needle) or []
    if names:
        haystack = " ".join(p for p in parts if p).lower()
        for name in names:
            if name and name.lower() in haystack:
                return True
    return False


async def fetch_symbol_news(symbol: str, *, limit: int = 12) -> StockNewsResponse:
    symbol = symbol.upper()
    # ``v2`` forces a refresh after the publisher-resolution rewrite so
    # cards previously cached with "Finnhub" as the source clear out.
    key = f"news:v2:{symbol}:{limit}"
    cached = _cache_get(key, NEWS_TTL)
    if cached is not None:
        return cached

    today = date.today()
    frm = (today - timedelta(days=14)).isoformat()
    raw = (
        await _finnhub_get(
            "/company-news",
            {"symbol": symbol, "from": frm, "to": today.isoformat()},
        )
        or []
    )

    items: list[StockNewsItem] = []
    for a in raw[:limit]:
        url = a.get("url") or ""
        headline = a.get("headline") or ""
        if not headline or not url:
            continue
        ts = a.get("datetime")
        try:
            published = (
                datetime.fromtimestamp(int(ts), tz=timezone.utc)
                if ts
                else datetime.now(timezone.utc)
            )
        except (TypeError, ValueError):
            published = datetime.now(timezone.utc)

        # Combine Finnhub's source field with the URL hostname for the most
        # accurate publisher label. See ``_publisher_for_article`` for rules.
        publisher = _publisher_for_article(url, a.get("source"))

        # Tag with the queried symbol only when the article actually
        # mentions it. Otherwise prefer a related ticker if Finnhub
        # provided one, else leave the tag empty so the UI doesn't lie.
        excerpt = a.get("summary") or ""
        related = (a.get("related") or "").upper()
        related_tickers = [
            t for t in re.split(r"[,\s]+", related) if t and 1 <= len(t) <= 5
        ]

        if _article_mentions_symbol(symbol, headline, excerpt):
            tag_symbol: Optional[str] = symbol
        else:
            tag_symbol = next(
                (
                    t
                    for t in related_tickers
                    if t != symbol
                    and _article_mentions_symbol(t, headline, excerpt)
                ),
                None,
            )

        items.append(
            StockNewsItem(
                id=str(a.get("id")) if a.get("id") else None,
                symbol=tag_symbol,
                headline=headline,
                summary=excerpt,
                source=publisher,
                source_url=_derive_host(url),
                url=url,
                image=a.get("image") or None,
                published_at=published,
                time_ago=_time_ago(published),
            )
        )

    out = StockNewsResponse(
        symbol=symbol,
        articles=items,
        updated_at=datetime.now(timezone.utc),
    )
    _cache_set(key, out, ttl=NEWS_TTL)
    return out


# ── Position summary (optional  -  built by the router) ────────────────


def build_position_summary(
    symbol: str,
    *,
    quantity: float = 0.0,
    average_cost: Optional[float] = None,
    current_price: Optional[float] = None,
    previous_close: Optional[float] = None,
    asset_type: Optional[str] = None,
    portfolio_total_value: Optional[float] = None,
) -> StockPositionSummary:
    """Build a StockPositionSummary from raw position fields + live prices."""
    symbol = symbol.upper()
    owned = quantity > 0
    market_value = (
        quantity * current_price
        if (current_price is not None and owned)
        else None
    )
    total_invested = (
        quantity * average_cost
        if (average_cost is not None and owned)
        else None
    )
    total_return = (
        market_value - total_invested
        if (market_value is not None and total_invested is not None)
        else None
    )
    total_return_pct = (
        (total_return / total_invested * 100.0)
        if (total_return is not None and total_invested)
        else None
    )
    todays_return = (
        (current_price - previous_close) * quantity
        if (current_price is not None and previous_close is not None and owned)
        else None
    )
    todays_return_pct = (
        ((current_price - previous_close) / previous_close * 100.0)
        if (current_price is not None and previous_close)
        else None
    )
    weight = (
        (market_value / portfolio_total_value * 100.0)
        if (market_value is not None and portfolio_total_value)
        else None
    )
    return StockPositionSummary(
        symbol=symbol,
        owned=owned,
        shares=quantity,
        average_cost=average_cost,
        market_value=market_value,
        total_invested=total_invested,
        todays_return=todays_return,
        todays_return_percent=todays_return_pct,
        total_return=total_return,
        total_return_percent=total_return_pct,
        portfolio_weight_percent=weight,
        asset_type=asset_type,
    )


# ── Composite detail ─────────────────────────────────────────────────


async def fetch_stock_detail(
    symbol: str,
    *,
    position: Optional[StockPositionSummary] = None,
    news_limit: int = 8,
) -> StockDetailResponse:
    """Fetch every per-symbol field concurrently and assemble the response."""
    symbol = symbol.upper()
    position = position or StockPositionSummary(symbol=symbol)

    profile, quote, key_stats, earnings, news = await asyncio.gather(
        fetch_profile(symbol),
        fetch_quote(symbol),
        fetch_key_stats(symbol),
        fetch_earnings(symbol),
        fetch_symbol_news(symbol, limit=news_limit),
        return_exceptions=False,
    )

    return StockDetailResponse(
        symbol=symbol,
        profile=profile,
        quote=quote,
        key_stats=key_stats,
        earnings=earnings,
        position=position,
        news=news.articles,
    )


# ── Universe listing ─────────────────────────────────────────────────

_LOGO_CDN = "https://financialmodelingprep.com/image-stock"


def _logo_url(symbol: str, asset_type: str = "stock") -> Optional[str]:
    """Free CDN logo for US equities and ETFs."""
    if asset_type == "crypto":
        return None
    return f"{_LOGO_CDN}/{symbol}.png"


def _yf_batch_download(symbols: list[str]) -> dict[str, dict]:
    """Synchronous: call ``yf.download`` for many tickers in one batch.

    Returns ``{SYMBOL: {"price": float, "prev_close": float, "change_pct": float}}``.
    """
    import pandas as pd  # local import  -  only needed here

    if not symbols:
        return {}
    try:
        df = yf.download(
            tickers=" ".join(symbols),
            period="2d",
            interval="1d",
            group_by="ticker",
            threads=True,
            progress=False,
            auto_adjust=False,
        )
    except Exception as exc:
        logger.warning(f"yf.download batch failed: {exc}")
        return {}

    if df is None or df.empty:
        return {}

    result: dict[str, dict] = {}

    # Single-ticker download doesn't group by ticker  -  columns are flat OHLCV.
    if len(symbols) == 1:
        sym = symbols[0]
        try:
            closes = df["Close"].dropna()
            if len(closes) >= 2:
                price = float(closes.iloc[-1])
                prev = float(closes.iloc[-2])
            elif len(closes) == 1:
                price = float(closes.iloc[-1])
                prev = price
            else:
                return {}
            change_pct = ((price - prev) / prev * 100.0) if prev else 0.0
            # Map back from yahoo symbol (e.g. BTC-USD) to original
            orig = next((s for s in symbols if _market_symbol(s) == sym or s == sym), sym)
            result[orig] = {"price": price, "prev_close": prev, "change_pct": change_pct}
        except Exception:
            pass
        return result

    for sym in symbols:
        try:
            if sym not in df.columns.get_level_values(0):
                continue
            ticker_df = df[sym]
            closes = ticker_df["Close"].dropna()
            if len(closes) >= 2:
                price = float(closes.iloc[-1])
                prev = float(closes.iloc[-2])
            elif len(closes) == 1:
                price = float(closes.iloc[-1])
                prev = price
            else:
                continue
            change_pct = ((price - prev) / prev * 100.0) if prev else 0.0
            result[sym] = {"price": price, "prev_close": prev, "change_pct": change_pct}
        except Exception:
            continue
    return result


async def _yf_batch_quotes(symbols: list[str]) -> dict[str, dict]:
    """Fetch quotes for many symbols in one ``yf.download`` call.

    Returns ``{ORIGINAL_SYMBOL: {"price": ..., "prev_close": ..., "change_pct": ...}}``.
    Cached under ``batch_quotes`` key with QUOTE_TTL.
    """
    cached = _cache_get("batch_quotes", QUOTE_TTL)
    if cached is not None:
        return cached

    # Build mapping: yahoo_symbol -> original_symbol
    yahoo_to_orig: dict[str, str] = {}
    yahoo_symbols: list[str] = []
    for sym in symbols:
        ysym = _market_symbol(sym)
        yahoo_to_orig[ysym] = sym
        yahoo_symbols.append(ysym)

    raw = await asyncio.to_thread(_yf_batch_download, yahoo_symbols)

    # Re-key from yahoo symbols back to original symbols
    out: dict[str, dict] = {}
    for ysym, data in raw.items():
        orig = yahoo_to_orig.get(ysym, ysym)
        out[orig] = data

    _cache_set("batch_quotes", out, ttl=QUOTE_TTL)
    return out


async def fetch_universe_cards(
    *,
    owned_symbols: set[str],
    universe: str = "all",  # "all" | "owned"
    search: Optional[str] = None,
    limit: int = 200,
    live_quotes: bool = True,
    owned_positions: Optional[dict[str, dict[str, Any]]] = None,
) -> StockUniverseResponse:
    """Build the list rendered on the Stocks tab.

    ``owned_positions`` is a dict like ``{"AAPL": {"name": ..., "sector": ...,
    "asset_type": ..., "current_price": ...}}`` so we surface holdings the user
    owns that aren't in the curated SP500 seed.
    """
    seed = _load_sp500_seed()

    merged: dict[str, dict[str, Any]] = {}
    for entry in seed:
        sym = entry["symbol"].upper()
        merged[sym] = {
            "symbol": sym,
            "name": entry.get("name", sym),
            "sector": entry.get("sector"),
        }

    # Overlay owned positions so we never hide something the user holds.
    if owned_positions:
        for sym, fields in owned_positions.items():
            sym = sym.upper()
            existing = merged.get(sym, {"symbol": sym})
            existing.setdefault("name", fields.get("name") or sym)
            if fields.get("sector"):
                existing["sector"] = fields["sector"]
            if fields.get("asset_type"):
                existing["asset_type"] = fields["asset_type"]
            if fields.get("current_price") is not None:
                existing["price"] = fields["current_price"]
            merged[sym] = existing

    # Filter by universe flag.
    if universe == "owned":
        merged = {s: v for s, v in merged.items() if s in owned_symbols}

    # Search.
    if search:
        q = search.strip().lower()
        merged = {
            s: v
            for s, v in merged.items()
            if q in s.lower() or q in (v.get("name", "") or "").lower()
        }

    # Sort: owned first, then alpha by name.
    items_sorted = sorted(
        merged.values(),
        key=lambda v: (
            0 if v["symbol"] in owned_symbols else 1,
            (v.get("name") or v["symbol"]).lower(),
        ),
    )[:limit]

    # Enrich with live quotes via a single batch download.
    cards: list[StockCardOut] = []
    if live_quotes and items_sorted and _YF_AVAILABLE:
        all_symbols = [e["symbol"] for e in items_sorted]
        batch = await _yf_batch_quotes(all_symbols)

        for entry in items_sorted:
            sym = entry["symbol"]
            asset_type = _normalize_card_asset_type(
                entry.get("asset_type"),
                sector=entry.get("sector"),
            )
            quote_data = batch.get(sym, {})
            price = quote_data.get("price") or entry.get("price")
            change_pct = quote_data.get("change_pct")
            cards.append(
                StockCardOut(
                    symbol=sym,
                    name=entry.get("name") or sym,
                    sector=entry.get("sector"),
                    asset_type=asset_type,  # type: ignore[arg-type]
                    owned=sym in owned_symbols,
                    price=price,
                    change_percent=change_pct,
                    logo=_logo_url(sym, asset_type),
                )
            )
    else:
        for entry in items_sorted:
            sym = entry["symbol"]
            asset_type = _normalize_card_asset_type(
                entry.get("asset_type"),
                sector=entry.get("sector"),
            )
            cards.append(
                StockCardOut(
                    symbol=sym,
                    name=entry.get("name") or sym,
                    sector=entry.get("sector"),
                    asset_type=asset_type,  # type: ignore[arg-type]
                    owned=sym in owned_symbols,
                    price=entry.get("price"),
                    logo=_logo_url(sym, asset_type),
                )
            )

    owned_in_response = sum(1 for c in cards if c.owned)
    return StockUniverseResponse(
        items=cards,
        total=len(cards),
        owned_count=owned_in_response,
    )


# ── Portfolio news aggregation (lives here  -  router in markets calls it) ──


# Publishers we consider reputable for portfolio-news ranking. Used as a
# tie-breaker so cards from these outlets float above PR/blog noise.
_REPUTABLE_PUBLISHERS: set[str] = {
    "Reuters", "Bloomberg", "CNBC", "Wall Street Journal", "Financial Times",
    "MarketWatch", "Barron's", "Fortune", "Forbes", "Seeking Alpha", "IBD",
    "Motley Fool", "AP News", "BBC", "Yahoo Finance", "Morningstar",
    "Investopedia", "Kiplinger", "Zacks", "TheStreet", "Benzinga",
    "Business Insider", "CoinDesk", "Cointelegraph", "Decrypt", "The Block",
    "New York Times", "The Guardian", "Axios",
}


async def aggregate_portfolio_news(
    symbols: list[str], *, per_symbol: int = 6, total_limit: int = 24
) -> PortfolioNewsResponse:
    """Aggregate the latest N news items per holding into one deduped feed.

    Only articles we can confirm are about a stock the user actually owns
    are returned. ``fetch_symbol_news`` already verifies the queried symbol
    against the headline/summary (or a related ticker), so here we simply
    drop anything that came back with no verified tag  -  those are the
    spurious "stock X is mentioned somewhere on the page" cases that gave
    us mis-tagged cards in the previous version.

    ``per_symbol`` is bumped from 3 to 6 because we now filter aggressively;
    we still want a healthy feed even when half of the per-symbol pulls
    fail verification.
    """
    symbols = [s.upper() for s in symbols if s]
    owned_set = set(symbols)
    if not symbols:
        return PortfolioNewsResponse(
            articles=[],
            symbols=[],
            updated_at=datetime.now(timezone.utc),
        )

    sem = asyncio.Semaphore(5)

    async def _fetch(sym: str) -> list[StockNewsItem]:
        async with sem:
            resp = await fetch_symbol_news(sym, limit=per_symbol)
        return resp.articles

    nested = await asyncio.gather(*[_fetch(s) for s in symbols])

    seen_urls: set[str] = set()
    merged: list[StockNewsItem] = []
    for bundle in nested:
        for item in bundle:
            if item.url in seen_urls:
                continue
            # Verification gate: the article must be about a symbol the
            # user actually holds. Untagged or off-topic articles are
            # dropped so the rail never carries unrelated news.
            if not item.symbol or item.symbol not in owned_set:
                continue
            seen_urls.add(item.url)
            merged.append(item)

    # Sort newest-first, breaking ties by publisher reputation so finance
    # outlets appear before press releases of equal recency.
    merged.sort(
        key=lambda a: (
            a.published_at,
            1 if a.source in _REPUTABLE_PUBLISHERS else 0,
        ),
        reverse=True,
    )
    merged = merged[:total_limit]

    return PortfolioNewsResponse(
        articles=merged,
        symbols=symbols,
        updated_at=datetime.now(timezone.utc),
    )
