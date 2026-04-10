"""
Portfolio Health Score calculator.

Computes a composite 0-100 score from five sub-scores:
  Diversification (30%) · Concentration (25%) · ETF Overlap (20%)
  Volatility (15%) · Expense Efficiency (10%)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from itertools import combinations

from .etf_data import (
    compute_etf_overlap,
    get_beta,
    get_expense_ratio,
)

logger = logging.getLogger(__name__)

# ── Weight coefficients ─────────────────────────────────────────────
WEIGHTS = {
    "diversification": 0.30,
    "concentration": 0.25,
    "overlap": 0.20,
    "volatility": 0.15,
    "expenses": 0.10,
}


def _grade(score: float) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "Fair"
    return "Poor"


# ── Sub-score A: Diversification (HHI) ─────────────────────────────

def _diversification_score(
    sector_weights: dict[str, float],
) -> tuple[float, dict]:
    """HHI-based diversification score.

    HHI = sum(w_i^2) where w_i is the fraction in [0,1].
    HHI ranges from 1/N (perfectly spread) to 1.0 (single sector).
    Mapped to 0-100 where lower HHI = higher score.
    """
    if not sector_weights:
        return 0.0, {"hhi": 1.0, "sector_count": 0}

    total = sum(sector_weights.values())
    if total <= 0:
        return 0.0, {"hhi": 1.0, "sector_count": 0}

    fractions = [v / total for v in sector_weights.values()]
    hhi = sum(f * f for f in fractions)
    n = len(fractions)

    # Map HHI to score: HHI=1→0, HHI=1/n→100
    min_hhi = 1.0 / n if n > 0 else 1.0
    if hhi <= min_hhi:
        score = 100.0
    elif hhi >= 1.0:
        score = 0.0
    else:
        score = max(0.0, min(100.0, (1.0 - hhi) / (1.0 - min_hhi) * 100.0))

    return round(score, 1), {"hhi": round(hhi, 4), "sector_count": n}


# ── Sub-score B: Risk Concentration ─────────────────────────────────

def _concentration_score(
    holdings: list[tuple[str, float]],
    total_value: float,
) -> tuple[float, dict]:
    """Score based on top-holding weights. Lower concentration = higher score."""
    if not holdings or total_value <= 0:
        return 100.0, {"top_holding_pct": 0, "top3_pct": 0}

    sorted_h = sorted(holdings, key=lambda x: x[1], reverse=True)
    top1_pct = (sorted_h[0][1] / total_value) * 100
    top3_pct = sum(h[1] for h in sorted_h[:3]) / total_value * 100

    # Score: top1 > 30% → 0-20, 20-30% → 20-50, 10-20% → 50-75, <10% → 75-100
    if top1_pct >= 30:
        score = max(0, 20 - (top1_pct - 30))
    elif top1_pct >= 20:
        score = 20 + (30 - top1_pct)
    elif top1_pct >= 10:
        score = 50 + (20 - top1_pct) * 2.5
    else:
        score = 75 + min(25, (10 - top1_pct) * 2.5)

    return round(min(100, max(0, score)), 1), {
        "top_holding": sorted_h[0][0],
        "top_holding_pct": round(top1_pct, 1),
        "top3_pct": round(top3_pct, 1),
    }


# ── Sub-score C: ETF Overlap ───────────────────────────────────────

def _overlap_score(etf_symbols: list[str]) -> tuple[float, dict]:
    """Score based on pairwise ETF overlap. Less overlap = higher score."""
    if len(etf_symbols) < 2:
        return 100.0, {"worst_pair": None, "max_overlap": 0}

    worst_overlap = 0.0
    worst_pair = None
    total_overlap = 0.0
    pair_count = 0

    for a, b in combinations(set(etf_symbols), 2):
        ov = compute_etf_overlap(a, b)
        if ov > 0:
            total_overlap += ov
            pair_count += 1
            if ov > worst_overlap:
                worst_overlap = ov
                worst_pair = f"{a}/{b}"

    avg_overlap = total_overlap / pair_count if pair_count > 0 else 0

    # Score: avg_overlap > 50% → 0-30, 25-50% → 30-60, 10-25% → 60-85, <10% → 85-100
    if avg_overlap >= 50:
        score = max(0, 30 - (avg_overlap - 50) * 0.6)
    elif avg_overlap >= 25:
        score = 30 + (50 - avg_overlap) * 1.2
    elif avg_overlap >= 10:
        score = 60 + (25 - avg_overlap) * 1.67
    else:
        score = 85 + min(15, (10 - avg_overlap) * 1.5)

    return round(min(100, max(0, score)), 1), {
        "worst_pair": worst_pair,
        "max_overlap_pct": round(worst_overlap, 1),
        "avg_overlap_pct": round(avg_overlap, 1),
        "etf_count": len(set(etf_symbols)),
    }


# ── Sub-score D: Volatility Exposure ───────────────────────────────

def _volatility_score(
    holdings: list[tuple[str, float, str, str]],
    total_value: float,
) -> tuple[float, dict]:
    """Weighted-average beta score. holdings = [(symbol, mv, sector, asset_type)]"""
    if not holdings or total_value <= 0:
        return 50.0, {"weighted_beta": 1.0}

    weighted_beta = sum(
        (mv / total_value) * get_beta(sector, asset_type)
        for _, mv, sector, asset_type in holdings
    )

    # Score: beta > 2.0 → 0-20, 1.5-2.0 → 20-50, 1.0-1.5 → 50-80, <1.0 → 80-100
    if weighted_beta >= 2.0:
        score = max(0, 20 - (weighted_beta - 2.0) * 20)
    elif weighted_beta >= 1.5:
        score = 20 + (2.0 - weighted_beta) * 60
    elif weighted_beta >= 1.0:
        score = 50 + (1.5 - weighted_beta) * 60
    else:
        score = 80 + min(20, (1.0 - weighted_beta) * 40)

    return round(min(100, max(0, score)), 1), {
        "weighted_beta": round(weighted_beta, 2),
    }


# ── Sub-score E: Expense Efficiency ────────────────────────────────

def _expense_score(
    etf_holdings: list[tuple[str, float]],
    total_value: float,
) -> tuple[float, dict]:
    """Weighted-average expense ratio score. etf_holdings = [(symbol, mv)]"""
    if not etf_holdings or total_value <= 0:
        return 100.0, {"weighted_expense_ratio": 0}

    etf_total = sum(mv for _, mv in etf_holdings)
    if etf_total <= 0:
        return 100.0, {"weighted_expense_ratio": 0}

    weighted_er = sum(
        (mv / etf_total) * (get_expense_ratio(sym) or 0.20)
        for sym, mv in etf_holdings
    )

    # Score: ER > 0.75% → 0-20, 0.5-0.75% → 20-50, 0.1-0.5% → 50-85, <0.1% → 85-100
    if weighted_er >= 0.75:
        score = max(0, 20 - (weighted_er - 0.75) * 40)
    elif weighted_er >= 0.50:
        score = 20 + (0.75 - weighted_er) * 120
    elif weighted_er >= 0.10:
        score = 50 + (0.50 - weighted_er) * 87.5
    else:
        score = 85 + min(15, (0.10 - weighted_er) * 150)

    return round(min(100, max(0, score)), 1), {
        "weighted_expense_ratio_pct": round(weighted_er, 3),
        "etf_count": len(etf_holdings),
    }


# ── Composite ──────────────────────────────────────────────────────

def compute_health_score(
    positions: list[dict],
    sector_profiles: dict[str, str],
) -> dict:
    """Compute the full health score.

    positions: list of dicts with keys:
        symbol, name, quantity, current_price, asset_type, sector
    sector_profiles: symbol → sector mapping (from enrichment)

    Returns dict matching HealthScoreResponse shape.
    """
    if not positions:
        empty_sub = {
            "score": 0, "label": "No data", "description": "Connect a broker to see your score.", "details": {}
        }
        return {
            "overall_score": 0,
            "grade": "N/A",
            "sub_scores": {k: empty_sub for k in WEIGHTS},
            "top_issues": ["No positions found. Connect a broker or import a CSV to get started."],
            "suggestions": [],
        }

    # Prepare data
    total_value = 0.0
    sector_values: dict[str, float] = defaultdict(float)
    holdings_mv: list[tuple[str, float]] = []
    vol_holdings: list[tuple[str, float, str, str]] = []
    etf_symbols: list[str] = []
    etf_holdings_mv: list[tuple[str, float]] = []

    for p in positions:
        mv = p["quantity"] * (p["current_price"] or 0)
        if mv <= 0:
            continue
        total_value += mv
        sym = p["symbol"]
        sector = p.get("sector") or sector_profiles.get(sym, "Unknown")
        asset_type = p.get("asset_type", "stock")

        holdings_mv.append((sym, mv))
        sector_values[sector] += mv
        vol_holdings.append((sym, mv, sector, asset_type))

        if asset_type.lower() == "etf":
            etf_symbols.append(sym)
            etf_holdings_mv.append((sym, mv))

    if total_value <= 0:
        empty_sub = {
            "score": 0, "label": "No data", "description": "All positions have zero market value.", "details": {}
        }
        return {
            "overall_score": 0,
            "grade": "N/A",
            "sub_scores": {k: empty_sub for k in WEIGHTS},
            "top_issues": ["All positions have zero market value. Sync your broker to update prices."],
            "suggestions": ["Sync your broker connection to fetch current market prices."],
        }

    # Compute sub-scores
    div_score, div_detail = _diversification_score(sector_values)
    conc_score, conc_detail = _concentration_score(holdings_mv, total_value)
    ovl_score, ovl_detail = _overlap_score(etf_symbols)
    vol_score, vol_detail = _volatility_score(vol_holdings, total_value)
    exp_score, exp_detail = _expense_score(etf_holdings_mv, total_value)

    sub_scores = {
        "diversification": {
            "score": div_score,
            "label": "Diversification",
            "description": _div_description(div_score, div_detail),
            "details": div_detail,
        },
        "concentration": {
            "score": conc_score,
            "label": "Concentration",
            "description": _conc_description(conc_score, conc_detail),
            "details": conc_detail,
        },
        "overlap": {
            "score": ovl_score,
            "label": "ETF Overlap",
            "description": _ovl_description(ovl_score, ovl_detail),
            "details": ovl_detail,
        },
        "volatility": {
            "score": vol_score,
            "label": "Volatility",
            "description": _vol_description(vol_score, vol_detail),
            "details": vol_detail,
        },
        "expenses": {
            "score": exp_score,
            "label": "Expenses",
            "description": _exp_description(exp_score, exp_detail),
            "details": exp_detail,
        },
    }

    overall = sum(sub_scores[k]["score"] * WEIGHTS[k] for k in WEIGHTS)
    overall = round(overall, 1)

    top_issues = _build_issues(sub_scores)
    suggestions = _build_suggestions(sub_scores)

    return {
        "overall_score": overall,
        "grade": _grade(overall),
        "sub_scores": sub_scores,
        "top_issues": top_issues[:3],
        "suggestions": suggestions[:3],
    }


# ── Description generators (plain-English, no LLM) ────────────────

def _div_description(score: float, d: dict) -> str:
    n = d.get("sector_count", 0)
    hhi = d.get("hhi", 1)
    if score >= 80:
        return f"Well diversified across {n} sectors."
    if score >= 50:
        return f"Moderately diversified across {n} sectors. Some concentration detected."
    return f"Concentrated in only {n} sector{'s' if n != 1 else ''}. Consider broadening exposure."


def _conc_description(score: float, d: dict) -> str:
    top = d.get("top_holding", "?")
    pct = d.get("top_holding_pct", 0)
    if score >= 75:
        return f"No single holding dominates. Top position ({top}) is {pct:.0f}%."
    if score >= 50:
        return f"{top} is {pct:.0f}% of your portfolio — moderate concentration."
    return f"{top} is {pct:.0f}% of your portfolio — high single-stock risk."


def _ovl_description(score: float, d: dict) -> str:
    pair = d.get("worst_pair")
    if not pair:
        return "No significant ETF overlap detected."
    ov = d.get("max_overlap_pct", 0)
    if score >= 80:
        return f"Minimal ETF overlap. Largest overlap is {pair} at {ov:.0f}%."
    if score >= 50:
        return f"Moderate ETF overlap — {pair} share {ov:.0f}% of holdings."
    return f"High ETF redundancy — {pair} overlap by {ov:.0f}%. Consider consolidating."


def _vol_description(score: float, d: dict) -> str:
    beta = d.get("weighted_beta", 1.0)
    if score >= 80:
        return f"Low volatility exposure (beta {beta:.2f})."
    if score >= 50:
        return f"Moderate volatility (beta {beta:.2f}). Close to market average."
    return f"High volatility exposure (beta {beta:.2f}). Portfolio swings amplified."


def _exp_description(score: float, d: dict) -> str:
    er = d.get("weighted_expense_ratio_pct", 0)
    if score >= 85:
        return f"Excellent cost efficiency — weighted ER is {er:.2f}%."
    if score >= 50:
        return f"Reasonable expenses — weighted ER is {er:.2f}%."
    return f"High expense drag — weighted ER is {er:.2f}%. Look for lower-cost alternatives."


def _build_issues(sub_scores: dict) -> list[str]:
    issues = []
    for key in sorted(sub_scores, key=lambda k: sub_scores[k]["score"]):
        s = sub_scores[key]
        if s["score"] < 60:
            issues.append(f"{s['label']}: {s['description']}")
    return issues


def _build_suggestions(sub_scores: dict) -> list[str]:
    suggestions = []
    d = sub_scores["diversification"]
    if d["score"] < 60:
        suggestions.append("Add positions in under-represented sectors like Healthcare, Consumer Staples, or Utilities.")
    c = sub_scores["concentration"]
    if c["score"] < 60:
        top = c["details"].get("top_holding", "your top holding")
        suggestions.append(f"Consider trimming {top} and spreading into broader index ETFs.")
    o = sub_scores["overlap"]
    if o["score"] < 60 and o["details"].get("worst_pair"):
        pair = o["details"]["worst_pair"]
        suggestions.append(f"Consolidate overlapping ETFs ({pair}) into a single broad-market fund.")
    v = sub_scores["volatility"]
    if v["score"] < 50:
        suggestions.append("Add low-beta holdings like bonds (BND) or defensive sectors to reduce volatility.")
    e = sub_scores["expenses"]
    if e["score"] < 50:
        suggestions.append("Switch high-expense ETFs to lower-cost index alternatives (e.g., VOO, VTI).")
    if not suggestions:
        suggestions.append("Your portfolio looks healthy. Keep monitoring allocation as positions change.")
    return suggestions
