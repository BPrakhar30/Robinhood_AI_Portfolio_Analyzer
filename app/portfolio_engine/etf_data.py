"""
Static reference data for ETF overlap, expense ratios, beta defaults,
and S&P 500 sector benchmark weights.

Coverage: top ~150 ETFs by AUM (captures >95% of retail ETF holdings),
top ~35 ETFs for overlap detection, comprehensive sector/industry betas,
and individual ETF beta overrides for the most common funds.

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
# Top ~150 ETFs by AUM. For unknown ETFs the health score defaults to
# 0.20% which is the asset-weighted average across all US ETFs.
ETF_EXPENSE_RATIOS: dict[str, float] = {
    # ── Broad US equity ─────────────────────────────────
    "VOO": 0.03, "VTI": 0.03, "IVV": 0.03, "SPY": 0.09,
    "SPLG": 0.02, "SPTM": 0.03, "ITOT": 0.03, "SCHB": 0.03,
    "SCHX": 0.03, "SCHK": 0.05, "VV": 0.04, "MGC": 0.07,
    "VONE": 0.08, "IWB": 0.15, "SPHQ": 0.15, "RSP": 0.20,
    "SPGP": 0.34, "QUAL": 0.15, "MTUM": 0.15, "VLUE": 0.15,
    "USMV": 0.15, "DGRO": 0.08, "NOBL": 0.35, "SDY": 0.35,
    "DVY": 0.38, "VIG": 0.06, "VYMI": 0.22,
    # ── Growth & value ──────────────────────────────────
    "QQQ": 0.20, "QQQM": 0.15, "VUG": 0.04, "VTV": 0.04,
    "IWF": 0.19, "IWD": 0.19, "VOOG": 0.10, "VOOV": 0.10,
    "IVW": 0.18, "IVE": 0.18, "SPYG": 0.04, "SPYV": 0.04,
    "SCHG": 0.04, "SCHV": 0.04, "RPG": 0.35, "RPV": 0.35,
    "MGK": 0.07, "MGV": 0.07, "IUSG": 0.04, "IUSV": 0.04,
    # ── Small & mid cap ─────────────────────────────────
    "IWM": 0.19, "IJR": 0.06, "IJH": 0.05, "SCHA": 0.04,
    "VB": 0.05, "VXF": 0.06, "VO": 0.04, "IVOO": 0.10,
    "SLYG": 0.15, "SLYV": 0.15, "IWO": 0.24, "IWN": 0.24,
    "VBK": 0.07, "VBR": 0.07, "VIOO": 0.10, "VIOV": 0.15,
    "VTWO": 0.10, "MDY": 0.23, "MDYG": 0.15, "MDYV": 0.15,
    "CALF": 0.59, "AVUV": 0.25, "AVLV": 0.15,
    # ── Dividends & income ──────────────────────────────
    "SCHD": 0.06, "VYM": 0.06, "HDV": 0.08, "SPYD": 0.07,
    "DIVO": 0.55, "JEPI": 0.35, "JEPQ": 0.35, "XYLD": 0.60,
    "QYLD": 0.60, "NUSI": 0.68, "PFF": 0.46, "PGX": 0.50,
    # ── Sector ETFs ─────────────────────────────────────
    "XLK": 0.09, "XLF": 0.09, "XLV": 0.09, "XLE": 0.09,
    "XLI": 0.09, "XLY": 0.09, "XLP": 0.09, "XLU": 0.09,
    "XLB": 0.09, "XLRE": 0.09, "XLC": 0.09,
    "VGT": 0.10, "VHT": 0.10, "VFH": 0.10, "VDE": 0.10,
    "VIS": 0.10, "VCR": 0.10, "VDC": 0.10, "VOX": 0.10,
    "VAW": 0.10, "VPU": 0.10, "VNQ": 0.12,
    "IYW": 0.39, "IYH": 0.39, "IYF": 0.39, "IYE": 0.39,
    "FHLC": 0.08, "FTEC": 0.08, "FNCL": 0.08, "FENY": 0.08,
    # ── Thematic & sector specialty ─────────────────────
    "ARKK": 0.75, "ARKW": 0.75, "ARKG": 0.75, "ARKF": 0.75,
    "ARKQ": 0.75, "SOXX": 0.35, "SMH": 0.35, "XSD": 0.35,
    "PSI": 0.56, "HACK": 0.60, "BUG": 0.50, "WCLD": 0.45,
    "SKYY": 0.60, "CLOU": 0.55, "BOTZ": 0.68, "ROBO": 0.95,
    "TAN": 0.67, "ICLN": 0.40, "QCLN": 0.58, "PBW": 0.65,
    "FAN": 0.61, "LIT": 0.75, "REMX": 0.56, "URA": 0.69,
    "XBI": 0.35, "IBB": 0.44, "GNOM": 0.50,
    "XHB": 0.35, "ITB": 0.39, "XRT": 0.35, "CIBR": 0.60,
    "KWEB": 0.70, "MCHI": 0.59, "FXI": 0.74,
    "KRE": 0.35, "KBE": 0.35, "XOP": 0.35, "OIH": 0.35,
    "GDX": 0.51, "GDXJ": 0.52, "SIL": 0.65,
    "DIA": 0.16, "IHI": 0.39, "XME": 0.35,
    # ── International equity ────────────────────────────
    "VXUS": 0.07, "VEA": 0.05, "VWO": 0.08, "IXUS": 0.07,
    "IEFA": 0.07, "EFA": 0.32, "EEM": 0.68, "IEMG": 0.09,
    "VGK": 0.08, "VPL": 0.08, "SPDW": 0.04, "SPEM": 0.07,
    "SCZ": 0.39, "VSS": 0.07, "FNDF": 0.25, "FNDE": 0.39,
    "AVDV": 0.36, "AVES": 0.36, "DLS": 0.58,
    "EWJ": 0.50, "EWG": 0.50, "EWU": 0.50, "INDA": 0.64,
    "EWZ": 0.57, "EWT": 0.57, "EWY": 0.57, "EWA": 0.50,
    "EWC": 0.50, "EWH": 0.50, "EWS": 0.50,
    # ── Fixed income ────────────────────────────────────
    "BND": 0.03, "AGG": 0.03, "BNDX": 0.07, "IAGG": 0.07,
    "BSV": 0.04, "BIV": 0.04, "BLV": 0.04,
    "VCSH": 0.04, "VCIT": 0.04, "VCLT": 0.04,
    "TLT": 0.15, "IEF": 0.15, "SHY": 0.15, "SHV": 0.15,
    "GOVT": 0.05, "VTIP": 0.04, "TIP": 0.19, "STIP": 0.03,
    "LQD": 0.14, "IGSB": 0.06, "IGIB": 0.06,
    "HYG": 0.49, "JNK": 0.40, "USHY": 0.15, "SHYG": 0.30,
    "EMB": 0.39, "VWOB": 0.20, "PCY": 0.50,
    "MUB": 0.07, "VTEB": 0.05, "SUB": 0.07,
    "MBB": 0.04, "VMBS": 0.04, "SPMB": 0.04,
    "JPST": 0.18, "MINT": 0.35, "NEAR": 0.25,
    "FLOT": 0.15, "FLRN": 0.15, "USFR": 0.15,
    "SGOV": 0.05, "BIL": 0.14, "GBIL": 0.12,
    # ── Commodities & alternatives ──────────────────────
    "GLD": 0.40, "IAU": 0.25, "GLDM": 0.10, "SGOL": 0.17,
    "SLV": 0.50, "SIVR": 0.30, "PPLT": 0.60,
    "USO": 0.81, "BNO": 0.84, "DBC": 0.85, "DBA": 0.89,
    "PDBC": 0.59, "GSG": 0.75, "COMT": 0.48,
    "ABRN": 0.50, "REET": 0.14, "RWR": 0.25,
    "VNQI": 0.12, "REM": 0.48, "MORT": 0.41,
    # ── Multi-asset & target date ───────────────────────
    "AOR": 0.15, "AOA": 0.15, "AOM": 0.15, "AOK": 0.15,
    "VBIAX": 0.07, "GAL": 0.35, "RPAR": 0.50,
    # ── Leveraged & inverse (high expense, important to flag) ──
    "TQQQ": 0.86, "SQQQ": 0.95, "UPRO": 0.91, "SPXU": 0.90,
    "QLD": 0.95, "SSO": 0.89, "SDS": 0.89, "SH": 0.89,
    "SOXL": 0.96, "SOXS": 0.96, "LABU": 1.01, "LABD": 1.01,
    "TNA": 0.95, "TZA": 1.02, "UVXY": 0.95, "SVXY": 0.95,
    "FAS": 0.93, "FAZ": 0.99, "NUGT": 1.35, "DUST": 1.23,
    "TECL": 1.01, "TECS": 1.06, "TMF": 1.09, "TMV": 1.00,
    "FNGU": 0.95, "FNGD": 0.95, "BULZ": 0.95,
}

# ── Approximate beta values by sector / asset type ──────────────────
# Covers all GICS sectors plus common sub-industries and special cases.
SECTOR_BETA: dict[str, float] = {
    # GICS sectors
    "Technology": 1.25,
    "Information Technology": 1.25,
    "Healthcare": 0.85,
    "Health Care": 0.85,
    "Financials": 1.10,
    "Financial Services": 1.10,
    "Consumer Discretionary": 1.15,
    "Consumer Cyclical": 1.15,
    "Communication Services": 1.10,
    "Industrials": 1.05,
    "Consumer Staples": 0.65,
    "Consumer Defensive": 0.65,
    "Energy": 1.30,
    "Utilities": 0.55,
    "Real Estate": 0.80,
    "Materials": 1.10,
    "Basic Materials": 1.10,
    # Sub-industries
    "Semiconductors": 1.45,
    "Software": 1.20,
    "Software - Infrastructure": 1.20,
    "Software - Application": 1.25,
    "Internet Content & Information": 1.30,
    "Internet Retail": 1.35,
    "Pharmaceuticals": 0.80,
    "Biotechnology": 1.40,
    "Medical Devices": 0.90,
    "Banks": 1.05,
    "Insurance": 0.90,
    "Capital Markets": 1.30,
    "Aerospace & Defense": 0.95,
    "Airlines": 1.50,
    "Automobiles": 1.35,
    "Auto Manufacturers": 1.35,
    "Homebuilders": 1.25,
    "Restaurants": 0.95,
    "Retail": 1.05,
    "Specialty Retail": 1.10,
    "Mining": 1.35,
    "Oil & Gas": 1.30,
    "Renewable Energy": 1.50,
    "REITs": 0.80,
    "Telecom": 0.75,
    "Media": 1.00,
    "Transportation": 1.00,
    "Packaging": 0.85,
    "Chemicals": 1.05,
    "Construction": 1.10,
    "Food & Beverage": 0.60,
    "Tobacco": 0.55,
    "Gaming": 1.40,
    # Asset-type overrides
    "Diversified": 1.00,
    "Unknown": 1.00,
    "Crypto": 2.50,
    "Bond": 0.30,
    "Fixed Income": 0.30,
    "Cash": 0.00,
    "Commodity": 0.50,
    "Gold": 0.15,
    "Precious Metals": 0.30,
}

# ── Per-ETF beta overrides ──────────────────────────────────────────
# More accurate than sector-inferred beta for commonly held ETFs.
ETF_BETA: dict[str, float] = {
    # Broad market
    "VOO": 1.00, "VTI": 1.00, "SPY": 1.00, "IVV": 1.00,
    "SPLG": 1.00, "ITOT": 1.00, "SCHB": 1.00, "SCHX": 1.00,
    "RSP": 1.05, "DIA": 0.95,
    # Growth
    "QQQ": 1.15, "QQQM": 1.15, "VUG": 1.15, "IWF": 1.15,
    "SCHG": 1.15, "SPYG": 1.10, "MGK": 1.15,
    # Value
    "VTV": 0.90, "IWD": 0.90, "SCHV": 0.85, "SPYV": 0.85,
    "MGV": 0.85, "VOOV": 0.90,
    # Small / mid
    "IWM": 1.20, "IJR": 1.20, "VB": 1.20, "SCHA": 1.20,
    "IJH": 1.10, "VO": 1.05, "MDY": 1.10, "VXF": 1.15,
    # Dividends
    "SCHD": 0.85, "VYM": 0.80, "HDV": 0.75, "SPYD": 0.85,
    "VIG": 0.85, "DGRO": 0.90, "NOBL": 0.80, "SDY": 0.80,
    "JEPI": 0.65, "JEPQ": 0.75,
    # Sector
    "XLK": 1.20, "VGT": 1.20, "FTEC": 1.20,
    "XLF": 1.10, "VFH": 1.10,
    "XLV": 0.80, "VHT": 0.80, "FHLC": 0.80,
    "XLE": 1.25, "VDE": 1.25, "FENY": 1.25,
    "XLI": 1.00, "VIS": 1.00,
    "XLY": 1.10, "VCR": 1.10,
    "XLP": 0.60, "VDC": 0.60,
    "XLU": 0.50, "VPU": 0.50,
    "XLB": 1.05, "VAW": 1.05,
    "XLRE": 0.75, "VNQ": 0.80,
    "XLC": 1.05, "VOX": 1.05,
    # Thematic
    "SOXX": 1.40, "SMH": 1.40, "SOXL": 4.20,
    "ARKK": 1.80, "ARKW": 1.70, "ARKG": 1.60,
    "TAN": 1.60, "ICLN": 1.30, "XBI": 1.35, "IBB": 0.95,
    "KWEB": 1.50, "MCHI": 1.10, "FXI": 1.00,
    "GDX": 0.40, "GDXJ": 0.55,
    # International
    "VXUS": 0.85, "VEA": 0.80, "VWO": 0.90,
    "IEFA": 0.80, "EFA": 0.80, "EEM": 0.95, "IEMG": 0.90,
    "VGK": 0.85, "VPL": 0.80, "SPDW": 0.80, "SPEM": 0.90,
    # Fixed income
    "BND": 0.05, "AGG": 0.05, "BNDX": 0.05,
    "TLT": 0.20, "IEF": 0.10, "SHY": 0.02,
    "LQD": 0.15, "HYG": 0.40, "JNK": 0.45,
    "GOVT": 0.05, "VTIP": 0.05, "TIP": 0.10,
    "EMB": 0.35, "MUB": 0.05,
    "BIL": 0.00, "SHV": 0.00, "SGOV": 0.00,
    # Commodities
    "GLD": 0.15, "IAU": 0.15, "GLDM": 0.15,
    "SLV": 0.30, "USO": 0.80, "DBC": 0.60,
    # Leveraged (effective beta)
    "TQQQ": 3.45, "SQQQ": -3.45, "UPRO": 3.00, "SPXU": -3.00,
    "QLD": 2.30, "SSO": 2.00, "SDS": -2.00, "SH": -1.00,
    "SOXS": -4.20, "TNA": 3.60, "TZA": -3.60,
    "FAS": 3.30, "FAZ": -3.30,
    "TMF": 0.60, "TMV": -0.60,
    "FNGU": 3.00, "FNGD": -3.00,
}


# ── Top holdings for major ETFs (symbol → weight %) ─────────────────
# Used for ETF overlap detection. Top ~15 holdings per ETF.
# Covers the ~35 most widely held ETFs in retail portfolios.
ETF_TOP_HOLDINGS: dict[str, dict[str, float]] = {
    # ── S&P 500 trackers ────────────────────────────────
    "VOO": {
        "AAPL": 7.1, "MSFT": 6.5, "NVDA": 6.0, "AMZN": 3.8,
        "META": 2.5, "GOOGL": 2.1, "GOOG": 1.8, "BRK.B": 1.7,
        "LLY": 1.4, "JPM": 1.3, "AVGO": 1.3, "UNH": 1.2,
        "V": 1.1, "XOM": 1.1, "TSLA": 1.0,
    },
    "SPY": {
        "AAPL": 7.1, "MSFT": 6.5, "NVDA": 6.0, "AMZN": 3.8,
        "META": 2.5, "GOOGL": 2.1, "GOOG": 1.8, "BRK.B": 1.7,
        "LLY": 1.4, "JPM": 1.3, "AVGO": 1.3, "UNH": 1.2,
        "V": 1.1, "XOM": 1.1, "TSLA": 1.0,
    },
    "IVV": {
        "AAPL": 7.1, "MSFT": 6.5, "NVDA": 6.0, "AMZN": 3.8,
        "META": 2.5, "GOOGL": 2.1, "GOOG": 1.8, "BRK.B": 1.7,
        "LLY": 1.4, "JPM": 1.3, "AVGO": 1.3, "UNH": 1.2,
        "V": 1.1, "XOM": 1.1, "TSLA": 1.0,
    },
    "SPLG": {
        "AAPL": 7.1, "MSFT": 6.5, "NVDA": 6.0, "AMZN": 3.8,
        "META": 2.5, "GOOGL": 2.1, "GOOG": 1.8, "BRK.B": 1.7,
        "LLY": 1.4, "JPM": 1.3, "AVGO": 1.3, "UNH": 1.2,
        "V": 1.1, "XOM": 1.1, "TSLA": 1.0,
    },
    # ── Total market ────────────────────────────────────
    "VTI": {
        "AAPL": 6.5, "MSFT": 5.9, "NVDA": 5.4, "AMZN": 3.5,
        "META": 2.3, "GOOGL": 1.9, "GOOG": 1.6, "BRK.B": 1.5,
        "LLY": 1.3, "JPM": 1.2, "AVGO": 1.2, "UNH": 1.1,
        "V": 1.0, "XOM": 1.0, "TSLA": 0.9,
    },
    "ITOT": {
        "AAPL": 6.5, "MSFT": 5.9, "NVDA": 5.4, "AMZN": 3.5,
        "META": 2.3, "GOOGL": 1.9, "GOOG": 1.6, "BRK.B": 1.5,
        "LLY": 1.3, "JPM": 1.2, "AVGO": 1.2, "UNH": 1.1,
        "V": 1.0, "XOM": 1.0, "TSLA": 0.9,
    },
    "SCHB": {
        "AAPL": 6.4, "MSFT": 5.8, "NVDA": 5.3, "AMZN": 3.4,
        "META": 2.2, "GOOGL": 1.9, "GOOG": 1.6, "BRK.B": 1.5,
        "LLY": 1.3, "JPM": 1.2, "AVGO": 1.1, "UNH": 1.1,
        "V": 1.0, "XOM": 0.9, "TSLA": 0.9,
    },
    # ── Nasdaq 100 ──────────────────────────────────────
    "QQQ": {
        "AAPL": 9.2, "MSFT": 8.3, "NVDA": 7.8, "AMZN": 5.3,
        "META": 4.8, "AVGO": 4.2, "GOOGL": 3.1, "GOOG": 2.7,
        "COST": 2.5, "TSLA": 2.4, "NFLX": 2.0, "AMD": 1.8,
        "LIN": 1.5, "ADBE": 1.4, "QCOM": 1.3,
    },
    "QQQM": {
        "AAPL": 9.2, "MSFT": 8.3, "NVDA": 7.8, "AMZN": 5.3,
        "META": 4.8, "AVGO": 4.2, "GOOGL": 3.1, "GOOG": 2.7,
        "COST": 2.5, "TSLA": 2.4, "NFLX": 2.0, "AMD": 1.8,
        "LIN": 1.5, "ADBE": 1.4, "QCOM": 1.3,
    },
    # ── Growth ──────────────────────────────────────────
    "VUG": {
        "AAPL": 12.5, "MSFT": 11.8, "NVDA": 10.2, "AMZN": 6.5,
        "META": 4.3, "GOOGL": 3.0, "GOOG": 2.6, "AVGO": 2.3,
        "TSLA": 2.1, "LLY": 1.8, "COST": 1.5, "NFLX": 1.3,
    },
    "IWF": {
        "AAPL": 11.8, "MSFT": 11.0, "NVDA": 9.8, "AMZN": 6.2,
        "META": 4.1, "GOOGL": 2.8, "GOOG": 2.4, "AVGO": 2.2,
        "TSLA": 2.0, "LLY": 1.7, "CRM": 1.2, "NFLX": 1.2,
    },
    "SCHG": {
        "AAPL": 12.0, "MSFT": 11.2, "NVDA": 10.0, "AMZN": 6.3,
        "META": 4.2, "GOOGL": 2.9, "GOOG": 2.5, "AVGO": 2.2,
        "TSLA": 2.0, "LLY": 1.7, "COST": 1.4, "NFLX": 1.2,
    },
    "SPYG": {
        "AAPL": 12.8, "MSFT": 11.5, "NVDA": 10.5, "AMZN": 6.4,
        "META": 4.4, "GOOGL": 3.0, "GOOG": 2.6, "AVGO": 2.3,
        "TSLA": 2.2, "LLY": 1.8, "COST": 1.5, "NFLX": 1.3,
    },
    # ── Value ───────────────────────────────────────────
    "VTV": {
        "BRK.B": 3.5, "JPM": 2.8, "UNH": 2.5, "XOM": 2.3,
        "JNJ": 2.1, "PG": 2.0, "HD": 1.8, "CVX": 1.7,
        "MRK": 1.6, "ABBV": 1.5, "BAC": 1.4, "PFE": 1.2,
    },
    "IWD": {
        "BRK.B": 3.3, "JPM": 2.7, "UNH": 2.4, "XOM": 2.2,
        "JNJ": 2.0, "PG": 1.9, "HD": 1.7, "CVX": 1.6,
        "MRK": 1.5, "ABBV": 1.4, "BAC": 1.3, "WFC": 1.1,
    },
    "SCHV": {
        "BRK.B": 3.6, "JPM": 2.9, "UNH": 2.6, "XOM": 2.4,
        "JNJ": 2.2, "PG": 2.1, "HD": 1.9, "CVX": 1.8,
        "MRK": 1.7, "ABBV": 1.6, "BAC": 1.4, "PFE": 1.2,
    },
    # ── Dividend ────────────────────────────────────────
    "SCHD": {
        "ABBV": 4.5, "MRK": 4.3, "HD": 4.1, "CSCO": 4.0,
        "AMGN": 3.8, "PEP": 3.7, "KO": 3.5, "CVX": 3.3,
        "TXN": 3.2, "PFE": 3.0, "VZ": 2.8, "BMY": 2.7,
    },
    "VYM": {
        "BRK.B": 3.4, "JPM": 2.8, "XOM": 2.5, "JNJ": 2.2,
        "PG": 2.0, "HD": 1.9, "ABBV": 1.7, "CVX": 1.6,
        "MRK": 1.5, "KO": 1.4, "PEP": 1.3, "CSCO": 1.2,
    },
    "VIG": {
        "AAPL": 4.8, "MSFT": 4.5, "JPM": 2.8, "UNH": 2.5,
        "V": 2.2, "MA": 2.0, "HD": 1.9, "PG": 1.8,
        "AVGO": 1.6, "COST": 1.4, "JNJ": 1.3, "ABT": 1.2,
    },
    # ── Small cap ───────────────────────────────────────
    "IWM": {
        "SMCI": 0.7, "INSM": 0.4, "FTAI": 0.4, "SPR": 0.3,
        "FN": 0.3, "CORT": 0.3, "ANF": 0.3, "ONTO": 0.3,
        "CRS": 0.3, "LUMN": 0.3, "ALKS": 0.2, "IOVA": 0.2,
    },
    "IJR": {
        "SMCI": 0.9, "INSM": 0.5, "FN": 0.4, "ANF": 0.4,
        "CRS": 0.4, "ONTO": 0.4, "CORT": 0.3, "SPR": 0.3,
        "LUMN": 0.3, "ALKS": 0.3, "IOVA": 0.3, "EXLS": 0.3,
    },
    # ── Sector: Technology ──────────────────────────────
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
    "FTEC": {
        "AAPL": 16.2, "MSFT": 14.6, "NVDA": 11.8, "AVGO": 4.4,
        "CRM": 2.1, "AMD": 2.0, "ADBE": 1.8, "ACN": 1.6,
        "ORCL": 1.4, "CSCO": 1.3, "INTU": 1.3, "IBM": 1.0,
    },
    # ── Semiconductors ──────────────────────────────────
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
    # ── Healthcare ──────────────────────────────────────
    "XLV": {
        "LLY": 11.0, "UNH": 9.5, "JNJ": 6.5, "MRK": 5.8,
        "ABBV": 5.5, "ABT": 4.2, "TMO": 3.8, "PFE": 3.2,
        "AMGN": 3.0, "DHR": 2.8, "BMY": 2.5, "ISRG": 2.2,
    },
    "VHT": {
        "LLY": 10.5, "UNH": 9.0, "JNJ": 6.2, "MRK": 5.5,
        "ABBV": 5.2, "ABT": 4.0, "TMO": 3.6, "PFE": 3.0,
        "AMGN": 2.8, "DHR": 2.6, "BMY": 2.3, "ISRG": 2.0,
    },
    # ── Financials ──────────────────────────────────────
    "XLF": {
        "BRK.B": 13.5, "JPM": 10.0, "V": 7.5, "MA": 6.5,
        "BAC": 4.5, "WFC": 3.5, "GS": 3.0, "SPGI": 2.8,
        "MS": 2.5, "AXP": 2.3, "BLK": 2.0, "C": 1.8,
    },
    # ── Thematic / innovation ───────────────────────────
    "ARKK": {
        "TSLA": 10.5, "ROKU": 7.5, "COIN": 7.2, "SQ": 6.8,
        "PATH": 5.5, "RBLX": 5.0, "SHOP": 4.8, "DKNG": 4.2,
        "HOOD": 3.8, "U": 3.5, "TWLO": 3.2, "ZM": 3.0,
    },
    # ── International ───────────────────────────────────
    "VXUS": {
        "TSM": 2.0, "NOVO-B": 1.5, "ASML": 1.3, "SAP": 1.0,
        "SHEL": 0.9, "NVS": 0.8, "TM": 0.8, "AZN": 0.7,
        "NESN": 0.7, "ROG": 0.6, "MC": 0.6, "SONY": 0.5,
    },
    "VEA": {
        "TSM": 2.2, "NOVO-B": 1.7, "ASML": 1.5, "SAP": 1.2,
        "SHEL": 1.0, "NVS": 0.9, "TM": 0.9, "AZN": 0.8,
        "NESN": 0.8, "ROG": 0.7, "MC": 0.7, "SONY": 0.6,
    },
    # ── Fixed income (minimal overlap with equity) ─────
    "BND": {
        "US-TREASURY": 42.0, "US-AGENCY": 20.0, "US-CORP-IG": 25.0,
        "US-MBS": 13.0,
    },
    "AGG": {
        "US-TREASURY": 41.0, "US-AGENCY": 19.0, "US-CORP-IG": 26.0,
        "US-MBS": 14.0,
    },
}

# ── Default expense ratio for unknown ETFs ──────────────────────────
DEFAULT_EXPENSE_RATIO = 0.20


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


def get_beta(sector: str, asset_type: str = "stock", symbol: str = "") -> float:
    """Return beta for a holding.

    Priority: per-ETF override → sector lookup → default 1.0
    """
    if asset_type.lower() in ("crypto", "cryptocurrency"):
        return SECTOR_BETA["Crypto"]
    if symbol:
        etf_b = ETF_BETA.get(symbol.upper())
        if etf_b is not None:
            return etf_b
    return SECTOR_BETA.get(sector, SECTOR_BETA["Unknown"])
