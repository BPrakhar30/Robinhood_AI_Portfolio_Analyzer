"""
Static reference data for ETF overlap, expense ratios, beta defaults,
and S&P 500 sector benchmark weights.

Refreshed manually or via a scheduled job — does not need real-time data.
"""

# ── S&P 500 approximate sector weights (%) ──────────────────────────
SP500_SECTOR_WEIGHTS: dict[str, float] = {
    "Technology": 29.5,
    "Healthcare": 12.5,
    "Financials": 13.0,
    "Consumer Discretionary": 10.5,
    "Communication Services": 8.5,
    "Industrials": 8.5,
    "Consumer Staples": 6.0,
    "Energy": 4.0,
    "Utilities": 2.5,
    "Real Estate": 2.5,
    "Materials": 2.5,
}

# ── ETF expense ratios (%) ──────────────────────────────────────────
ETF_EXPENSE_RATIOS: dict[str, float] = {
    "VOO": 0.03, "VTI": 0.03, "IVV": 0.03, "SPY": 0.09,
    "QQQ": 0.20, "QQQM": 0.15, "VUG": 0.04, "VTV": 0.04,
    "VGT": 0.10, "VHT": 0.10, "VNQ": 0.12, "VWO": 0.08,
    "VXUS": 0.07, "VEA": 0.05, "BND": 0.03, "AGG": 0.03,
    "SCHD": 0.06, "SCHX": 0.03, "SCHB": 0.03, "SCHA": 0.04,
    "IWM": 0.19, "IWF": 0.19, "IWD": 0.19, "IJR": 0.06,
    "IJH": 0.05, "DIA": 0.16, "XLK": 0.09, "XLF": 0.09,
    "XLV": 0.09, "XLE": 0.09, "XLI": 0.09, "XLY": 0.09,
    "XLP": 0.09, "XLU": 0.09, "XLB": 0.09, "XLRE": 0.09,
    "XLC": 0.09, "ARKK": 0.75, "ARKW": 0.75, "ARKG": 0.75,
    "SOXX": 0.35, "SMH": 0.35, "TAN": 0.67, "ICLN": 0.40,
    "GLD": 0.40, "SLV": 0.50, "TLT": 0.15, "SHY": 0.15,
    "LQD": 0.14, "HYG": 0.49, "EMB": 0.39, "EFA": 0.32,
    "EEM": 0.68, "IEMG": 0.09, "GOVT": 0.05, "VTIP": 0.04,
}

# ── Approximate beta values by sector / asset type ──────────────────
SECTOR_BETA: dict[str, float] = {
    "Technology": 1.25,
    "Semiconductors": 1.45,
    "Software": 1.20,
    "Communication Services": 1.10,
    "Consumer Discretionary": 1.15,
    "Financials": 1.10,
    "Healthcare": 0.85,
    "Pharmaceuticals": 0.80,
    "Industrials": 1.05,
    "Energy": 1.30,
    "Materials": 1.10,
    "Consumer Staples": 0.65,
    "Utilities": 0.55,
    "Real Estate": 0.80,
    "Diversified": 1.00,
    "Unknown": 1.00,
    "Crypto": 2.50,
}

# ── Top holdings for major ETFs (symbol → weight %) ─────────────────
# Used for ETF overlap detection. Top ~15 holdings per ETF.
ETF_TOP_HOLDINGS: dict[str, dict[str, float]] = {
    "VOO": {
        "AAPL": 7.1, "MSFT": 6.5, "NVDA": 6.0, "AMZN": 3.8,
        "META": 2.5, "GOOGL": 2.1, "GOOG": 1.8, "BRK.B": 1.7,
        "LLY": 1.4, "JPM": 1.3, "AVGO": 1.3, "UNH": 1.2,
        "V": 1.1, "XOM": 1.1, "TSLA": 1.0,
    },
    "VTI": {
        "AAPL": 6.5, "MSFT": 5.9, "NVDA": 5.4, "AMZN": 3.5,
        "META": 2.3, "GOOGL": 1.9, "GOOG": 1.6, "BRK.B": 1.5,
        "LLY": 1.3, "JPM": 1.2, "AVGO": 1.2, "UNH": 1.1,
        "V": 1.0, "XOM": 1.0, "TSLA": 0.9,
    },
    "SPY": {
        "AAPL": 7.1, "MSFT": 6.5, "NVDA": 6.0, "AMZN": 3.8,
        "META": 2.5, "GOOGL": 2.1, "GOOG": 1.8, "BRK.B": 1.7,
        "LLY": 1.4, "JPM": 1.3, "AVGO": 1.3, "UNH": 1.2,
        "V": 1.1, "XOM": 1.1, "TSLA": 1.0,
    },
    "QQQ": {
        "AAPL": 9.2, "MSFT": 8.3, "NVDA": 7.8, "AMZN": 5.3,
        "META": 4.8, "AVGO": 4.2, "GOOGL": 3.1, "GOOG": 2.7,
        "COST": 2.5, "TSLA": 2.4, "NFLX": 2.0, "AMD": 1.8,
        "LIN": 1.5, "ADBE": 1.4, "QCOM": 1.3,
    },
    "IVV": {
        "AAPL": 7.1, "MSFT": 6.5, "NVDA": 6.0, "AMZN": 3.8,
        "META": 2.5, "GOOGL": 2.1, "GOOG": 1.8, "BRK.B": 1.7,
        "LLY": 1.4, "JPM": 1.3, "AVGO": 1.3, "UNH": 1.2,
        "V": 1.1, "XOM": 1.1, "TSLA": 1.0,
    },
    "SCHD": {
        "ABBV": 4.5, "MRK": 4.3, "HD": 4.1, "CSCO": 4.0,
        "AMGN": 3.8, "PEP": 3.7, "KO": 3.5, "CVX": 3.3,
        "TXN": 3.2, "PFE": 3.0, "VZ": 2.8, "BMY": 2.7,
    },
    "VUG": {
        "AAPL": 12.5, "MSFT": 11.8, "NVDA": 10.2, "AMZN": 6.5,
        "META": 4.3, "GOOGL": 3.0, "GOOG": 2.6, "AVGO": 2.3,
        "TSLA": 2.1, "LLY": 1.8, "COST": 1.5, "NFLX": 1.3,
    },
    "VTV": {
        "BRK.B": 3.5, "JPM": 2.8, "UNH": 2.5, "XOM": 2.3,
        "JNJ": 2.1, "PG": 2.0, "HD": 1.8, "CVX": 1.7,
        "MRK": 1.6, "ABBV": 1.5, "BAC": 1.4, "PFE": 1.2,
    },
    "ARKK": {
        "TSLA": 10.5, "ROKU": 7.5, "COIN": 7.2, "SQ": 6.8,
        "PATH": 5.5, "RBLX": 5.0, "SHOP": 4.8, "DKNG": 4.2,
        "HOOD": 3.8, "U": 3.5, "TWLO": 3.2, "ZM": 3.0,
    },
    "VGT": {
        "AAPL": 16.5, "MSFT": 14.8, "NVDA": 12.0, "AVGO": 4.5,
        "CRM": 2.2, "AMD": 2.0, "ADBE": 1.8, "ACN": 1.7,
        "ORCL": 1.5, "CSCO": 1.4, "INTU": 1.3, "IBM": 1.1,
    },
    "XLK": {
        "AAPL": 16.0, "MSFT": 14.5, "NVDA": 11.5, "AVGO": 4.3,
        "CRM": 2.1, "AMD": 1.9, "ADBE": 1.7, "ACN": 1.6,
        "ORCL": 1.4, "CSCO": 1.3, "INTU": 1.2, "IBM": 1.0,
    },
    "SOXX": {
        "NVDA": 10.0, "AVGO": 8.5, "AMD": 7.0, "QCOM": 5.5,
        "TXN": 5.0, "INTC": 4.5, "MU": 4.0, "LRCX": 3.8,
        "AMAT": 3.5, "KLAC": 3.2, "MRVL": 3.0, "ADI": 2.8,
    },
    "SMH": {
        "NVDA": 11.0, "TSM": 9.0, "AVGO": 7.0, "AMD": 5.5,
        "QCOM": 5.0, "TXN": 4.5, "INTC": 4.0, "MU": 3.5,
        "LRCX": 3.2, "AMAT": 3.0, "ASML": 2.8, "KLAC": 2.5,
    },
}


def compute_etf_overlap(etf_a: str, etf_b: str) -> float:
    """Return the overlap % between two ETFs (0-100).

    Overlap is defined as the sum of the minimum weight for each stock
    that appears in both ETFs' top-holdings lists.
    """
    a = ETF_TOP_HOLDINGS.get(etf_a.upper(), {})
    b = ETF_TOP_HOLDINGS.get(etf_b.upper(), {})
    if not a or not b:
        return 0.0
    common = set(a.keys()) & set(b.keys())
    return sum(min(a[s], b[s]) for s in common)


def get_expense_ratio(symbol: str) -> float | None:
    """Return expense ratio for an ETF, or None if unknown."""
    return ETF_EXPENSE_RATIOS.get(symbol.upper())


def get_beta(sector: str, asset_type: str = "stock") -> float:
    """Approximate beta based on sector/asset type."""
    if asset_type.lower() in ("crypto", "cryptocurrency"):
        return SECTOR_BETA["Crypto"]
    return SECTOR_BETA.get(sector, SECTOR_BETA["Unknown"])
