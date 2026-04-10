"""
Allocation Risk Detection Engine.

Three detection systems:
  A) Sector overweight detection (vs S&P 500 benchmarks)
  B) Single-stock concentration risk (> 10% yellow, > 20% red)
  C) ETF overlap detection (pairwise holdings intersection)
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from itertools import combinations

from .etf_data import SP500_SECTOR_WEIGHTS, compute_etf_overlap


def _alert_id(*parts: str) -> str:
    return hashlib.md5(":".join(parts).encode()).hexdigest()[:12]


def detect_sector_overweight(
    sector_weights_pct: dict[str, float],
) -> list[dict]:
    """Compare user sector weights against S&P 500 benchmarks."""
    alerts: list[dict] = []

    for sector, user_pct in sector_weights_pct.items():
        bench_pct = SP500_SECTOR_WEIGHTS.get(sector)
        if bench_pct is None:
            continue
        diff = user_pct - bench_pct
        if diff <= 5:
            continue

        if diff >= 15:
            severity = "high"
        elif diff >= 10:
            severity = "medium"
        else:
            severity = "low"

        alerts.append({
            "id": _alert_id("sector", sector),
            "severity": severity,
            "category": "sector_overweight",
            "title": f"{sector} overweight",
            "description": (
                f"Your {sector} allocation is {user_pct:.1f}%, "
                f"which is {diff:.1f}pp above the S&P 500 benchmark ({bench_pct:.1f}%). "
                f"This concentrates your risk around {sector.lower()} sector volatility."
            ),
            "metric": f"{user_pct:.1f}%",
            "threshold": f"Benchmark: {bench_pct:.1f}%",
        })

    return alerts


def detect_single_stock_concentration(
    holdings: list[tuple[str, str, float]],
    total_value: float,
    yellow_threshold: float = 10.0,
    red_threshold: float = 20.0,
) -> list[dict]:
    """Flag stocks above concentration thresholds.

    holdings: [(symbol, name, market_value)]
    """
    alerts: list[dict] = []
    if total_value <= 0:
        return alerts

    for symbol, name, mv in holdings:
        pct = (mv / total_value) * 100
        if pct < yellow_threshold:
            continue

        severity = "high" if pct >= red_threshold else "medium"
        display = name if name and name != symbol else symbol

        alerts.append({
            "id": _alert_id("conc", symbol),
            "severity": severity,
            "category": "concentration",
            "title": f"{display} concentration",
            "description": (
                f"{display} ({symbol}) represents {pct:.1f}% of your portfolio. "
                f"{'This is a significant single-stock risk.' if severity == 'high' else 'Consider whether this level of exposure is intentional.'}"
            ),
            "metric": f"{pct:.1f}%",
            "threshold": f"{'> ' + str(int(red_threshold)) + '% (high)' if severity == 'high' else '> ' + str(int(yellow_threshold)) + '% (moderate)'}",
        })

    return alerts


def detect_etf_overlap(
    etf_symbols: list[str],
    etf_values: dict[str, float],
    total_value: float,
) -> list[dict]:
    """Flag significant pairwise ETF overlap."""
    alerts: list[dict] = []
    unique = list(set(etf_symbols))
    if len(unique) < 2:
        return alerts

    for a, b in combinations(unique, 2):
        ov = compute_etf_overlap(a, b)
        if ov < 15:
            continue

        if ov >= 40:
            severity = "high"
        elif ov >= 25:
            severity = "medium"
        else:
            severity = "low"

        combined_pct = 0
        if total_value > 0:
            combined_pct = (etf_values.get(a, 0) + etf_values.get(b, 0)) / total_value * 100

        alerts.append({
            "id": _alert_id("overlap", a, b),
            "severity": severity,
            "category": "etf_overlap",
            "title": f"{a}/{b} overlap",
            "description": (
                f"{a} and {b} share ~{ov:.0f}% of their top holdings. "
                f"Together they make up {combined_pct:.1f}% of your portfolio. "
                f"{'Consider consolidating into a single fund.' if severity == 'high' else 'Monitor this redundancy.'}"
            ),
            "metric": f"{ov:.0f}% overlap",
            "threshold": "Combined holdings overlap",
        })

    return alerts


def detect_all_risks(
    positions: list[dict],
    sector_profiles: dict[str, str],
) -> dict:
    """Run all three detection systems and return unified alert list.

    positions: list of dicts with symbol, name, quantity, current_price, asset_type, sector
    sector_profiles: symbol → sector mapping from enrichment
    """
    total_value = 0.0
    sector_values: dict[str, float] = defaultdict(float)
    holdings: list[tuple[str, str, float]] = []
    etf_symbols: list[str] = []
    etf_values: dict[str, float] = defaultdict(float)

    for p in positions:
        mv = p["quantity"] * (p["current_price"] or 0)
        if mv <= 0:
            continue
        total_value += mv
        sym = p["symbol"]
        name = p.get("name") or sym
        sector = p.get("sector") or sector_profiles.get(sym, "Unknown")
        asset_type = p.get("asset_type", "stock")

        holdings.append((sym, name, mv))
        sector_values[sector] += mv

        if asset_type.lower() == "etf":
            etf_symbols.append(sym)
            etf_values[sym] += mv

    if total_value <= 0:
        return {
            "alerts": [],
            "summary": {"high": 0, "medium": 0, "low": 0},
        }

    sector_weights_pct = {s: (v / total_value) * 100 for s, v in sector_values.items()}

    all_alerts: list[dict] = []
    all_alerts.extend(detect_sector_overweight(sector_weights_pct))
    all_alerts.extend(detect_single_stock_concentration(holdings, total_value))
    all_alerts.extend(detect_etf_overlap(etf_symbols, dict(etf_values), total_value))

    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_alerts.sort(key=lambda a: severity_order.get(a["severity"], 3))

    summary = {
        "high": sum(1 for a in all_alerts if a["severity"] == "high"),
        "medium": sum(1 for a in all_alerts if a["severity"] == "medium"),
        "low": sum(1 for a in all_alerts if a["severity"] == "low"),
    }

    return {"alerts": all_alerts, "summary": summary}
