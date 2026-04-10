"""Symbol metadata enrichment via Finnhub ``/stock/profile2``.

Fetches sector, country, and market-cap data for equity symbols and caches
results in the ``symbol_metadata`` DB table so Finnhub is only called once
per symbol until the row goes stale (7 days).  Crypto and unknown ETFs get
hardcoded defaults without an API call.

Added: 2026-04-08
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger("utils.symbol_enrichment")

FINNHUB_PROFILE_URL = "https://finnhub.io/api/v1/stock/profile2"
STALE_DAYS = 7
_MEM_CACHE: dict[str, tuple[float, "SymbolProfile"]] = {}
_MEM_TTL = 86_400  # 24 h in-memory


@dataclass(frozen=True)
class SymbolProfile:
    sector: str
    industry: str
    country: str
    market_cap: float
    market_cap_category: str


GROWTH_SECTORS = frozenset({
    "Technology", "Crypto", "Cryptocurrency",
    "Communication Services", "Consumer Discretionary",
})
VALUE_SECTORS = frozenset({
    "Utilities", "Consumer Staples", "Financials",
    "Real Estate", "Energy",
})

# Well-known ETFs whose Finnhub profile is empty or misleading.
_ETF_OVERRIDES: dict[str, SymbolProfile] = {}

def _build_etf_overrides() -> dict[str, SymbolProfile]:
    """Lazy-build static ETF metadata for common funds."""
    if _ETF_OVERRIDES:
        return _ETF_OVERRIDES

    _tech = SymbolProfile("Technology", "Technology ETF", "US", 0, "N/A")
    _sp500 = SymbolProfile("Diversified", "S&P 500 ETF", "US", 0, "N/A")
    _total = SymbolProfile("Diversified", "Total Market ETF", "US", 0, "N/A")
    _intl = SymbolProfile("Diversified", "International ETF", "International", 0, "N/A")
    _em = SymbolProfile("Diversified", "Emerging Markets ETF", "Emerging Markets", 0, "N/A")
    _bond = SymbolProfile("Fixed Income", "Bond ETF", "US", 0, "N/A")
    _re = SymbolProfile("Real Estate", "Real Estate ETF", "US", 0, "N/A")
    _gold = SymbolProfile("Commodities", "Precious Metals ETF", "Global", 0, "N/A")
    _energy = SymbolProfile("Energy", "Energy ETF", "US", 0, "N/A")
    _health = SymbolProfile("Healthcare", "Healthcare ETF", "US", 0, "N/A")
    _fin = SymbolProfile("Financials", "Financials ETF", "US", 0, "N/A")
    _semi = SymbolProfile("Technology", "Semiconductor ETF", "US", 0, "N/A")
    _btc_etf = SymbolProfile("Crypto", "Bitcoin ETF", "US", 0, "N/A")
    _div = SymbolProfile("Diversified", "Dividend ETF", "US", 0, "N/A")

    mapping: dict[str, SymbolProfile] = {}
    for s in ("SPY", "IVV", "VOO", "SPLG", "RSP", "SSO", "UPRO", "SPXL", "SH", "SDS", "SPXU", "SPXS"):
        mapping[s] = _sp500
    for s in ("VTI", "ITOT", "SCHB", "SPTM", "IWV"):
        mapping[s] = _total
    for s in ("QQQ", "QQQM", "TQQQ", "SQQQ", "QLD", "PSQ", "QQQE"):
        mapping[s] = _tech
    for s in ("XLK", "VGT", "FTEC", "IGV", "TECL", "TECS"):
        mapping[s] = _tech
    for s in ("SOXX", "SMH", "SOXL", "SOXS", "XSD"):
        mapping[s] = _semi
    for s in ("VXUS", "IXUS", "IDEV", "VEA", "VEU", "SPDW", "SCHF", "EFA", "IEFA", "ACWX"):
        mapping[s] = _intl
    for s in ("VWO", "EEM", "IEMG", "SCHE", "SPEM", "EEMV"):
        mapping[s] = _em
    for s in ("BND", "AGG", "SCHZ", "BNDX", "TLT", "SHY", "IEF", "GOVT", "VGSH", "VGIT", "VGLT",
              "LQD", "HYG", "JNK", "MUB", "SUB", "VCIT", "VCSH", "VCLT", "SPAB", "SPTL",
              "TIP", "VTIP", "STIP", "EMB", "EMLC", "SHYG", "SJNK", "FLOT", "FLRN",
              "SHV", "BIL", "SGOV", "USFR", "TFLO", "TBT", "EDV", "ZROZ"):
        mapping[s] = _bond
    for s in ("VNQ", "SCHH", "XLRE", "IYR", "RWR", "REZ"):
        mapping[s] = _re
    for s in ("GLD", "IAU", "GLDM", "SLV", "SIVR", "PPLT", "PALL", "GDX", "GDXJ",
              "SIL", "SILJ", "SGOL", "GLTR", "OUNZ"):
        mapping[s] = _gold
    for s in ("XLE", "VDE", "OIH", "USO", "UNG", "XOP"):
        mapping[s] = _energy
    for s in ("XLV", "VHT", "IBB", "XBI", "IHI"):
        mapping[s] = _health
    for s in ("XLF", "VFH", "KRE", "KBE"):
        mapping[s] = _fin
    for s in ("IBIT", "FBTC", "BITB", "ARKB", "GBTC", "BITO"):
        mapping[s] = _btc_etf
    for s in ("SCHD", "VYM", "HDV", "DVY", "SDY", "DGRO", "NOBL", "VIG", "SPYD", "JEPI", "JEPQ"):
        mapping[s] = _div

    _ETF_OVERRIDES.update(mapping)
    return _ETF_OVERRIDES


def _classify_market_cap(cap_millions: float) -> str:
    if cap_millions <= 0:
        return "N/A"
    if cap_millions >= 200_000:
        return "Mega Cap"
    if cap_millions >= 10_000:
        return "Large Cap"
    if cap_millions >= 2_000:
        return "Mid Cap"
    if cap_millions >= 300:
        return "Small Cap"
    return "Micro Cap"


def classify_risk_bucket(sector: str) -> str:
    if sector in GROWTH_SECTORS:
        return "Growth"
    if sector in VALUE_SECTORS:
        return "Value"
    return "Balanced"


def _fetch_finnhub_profile_sync(symbol: str, api_key: str) -> Optional[dict]:
    if not api_key:
        return None
    try:
        resp = requests.get(
            FINNHUB_PROFILE_URL,
            params={"symbol": symbol, "token": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data and data.get("ticker"):
            return data
    except Exception as exc:
        logger.warning(f"Finnhub profile fetch failed for {symbol}: {exc}")
    return None


async def _fetch_finnhub_profile(symbol: str, api_key: str) -> Optional[dict]:
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_finnhub_profile_sync, symbol, api_key)


async def _load_from_db(symbol: str, session) -> Optional[SymbolProfile]:
    """Try to load a non-stale row from ``symbol_metadata`` table."""
    from app.database.models import SymbolMetadata
    from sqlalchemy import select

    stmt = select(SymbolMetadata).where(SymbolMetadata.symbol == symbol)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    if row.updated_at:
        age = datetime.now(timezone.utc) - row.updated_at.replace(tzinfo=timezone.utc)
        if age > timedelta(days=STALE_DAYS):
            return None
    return SymbolProfile(
        sector=row.sector or "Other",
        industry=row.industry or "Other",
        country=row.country or "US",
        market_cap=row.market_cap or 0,
        market_cap_category=row.market_cap_category or "N/A",
    )


async def _persist_to_db(symbol: str, profile: SymbolProfile, session) -> None:
    """Upsert a row into ``symbol_metadata``."""
    from app.database.models import SymbolMetadata
    from sqlalchemy import select

    stmt = select(SymbolMetadata).where(SymbolMetadata.symbol == symbol)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row:
        row.sector = profile.sector
        row.industry = profile.industry
        row.country = profile.country
        row.market_cap = profile.market_cap
        row.market_cap_category = profile.market_cap_category
        row.updated_at = datetime.now(timezone.utc)
    else:
        session.add(SymbolMetadata(
            symbol=symbol,
            sector=profile.sector,
            industry=profile.industry,
            country=profile.country,
            market_cap=profile.market_cap,
            market_cap_category=profile.market_cap_category,
        ))


async def get_symbol_profile(
    symbol: str,
    asset_type: str = "stock",
    session=None,
    api_key: str | None = None,
) -> SymbolProfile:
    """Return enriched metadata for *symbol*, using caches and API as needed.

    Cache hierarchy: in-memory dict -> ``symbol_metadata`` DB table -> Finnhub API.
    """
    symbol = symbol.upper().strip()

    now = time.time()
    cached = _MEM_CACHE.get(symbol)
    if cached and (now - cached[0]) < _MEM_TTL:
        return cached[1]

    if asset_type == "crypto":
        profile = SymbolProfile("Cryptocurrency", "Digital Asset", "Global", 0, "N/A")
        _MEM_CACHE[symbol] = (now, profile)
        return profile

    overrides = _build_etf_overrides()
    if symbol in overrides:
        profile = overrides[symbol]
        _MEM_CACHE[symbol] = (now, profile)
        return profile

    if session is not None:
        db_profile = await _load_from_db(symbol, session)
        if db_profile is not None:
            _MEM_CACHE[symbol] = (now, db_profile)
            return db_profile

    key = api_key or get_settings().finnhub_api_key.strip()
    data = await _fetch_finnhub_profile(symbol, key)
    if data:
        cap_m = data.get("marketCapitalization", 0) or 0
        profile = SymbolProfile(
            sector=data.get("finnhubIndustry", "Other") or "Other",
            industry=data.get("finnhubIndustry", "Other") or "Other",
            country=data.get("country", "US") or "US",
            market_cap=cap_m,
            market_cap_category=_classify_market_cap(cap_m),
        )
    elif asset_type == "etf":
        profile = SymbolProfile("Diversified", "ETF", "US", 0, "N/A")
    else:
        profile = SymbolProfile("Other", "Unknown", "US", 0, "N/A")

    _MEM_CACHE[symbol] = (now, profile)

    if session is not None:
        try:
            await _persist_to_db(symbol, profile, session)
        except Exception as exc:
            logger.warning(f"Failed to persist metadata for {symbol}: {exc}")

    return profile
