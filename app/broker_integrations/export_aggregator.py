"""
Aggregation engine for Robinhood-style brokerage transaction exports.

Converts a raw CSV transaction ledger (Activity Date, Process Date, Settle Date,
Instrument, Description, Trans Code, Quantity, Price, Amount) into aggregated
position and transaction records compatible with the broker adapter interface.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict, List, Optional, Set, Tuple

import requests

from app.broker_integrations.base import PositionData, TransactionData
from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger("broker_integrations.export_aggregator")

FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"
DATE_FMT = "%m/%d/%Y"
D0 = Decimal("0")
D2 = Decimal("0.01")
D6 = Decimal("0.000001")

ROBINHOOD_EXPORT_COLUMNS = {
    "activity_date",
    "process_date",
    "settle_date",
    "instrument",
    "description",
    "trans_code",
    "quantity",
    "price",
    "amount",
}

IGNORED_CODES = {"NRAT", "DTAX", "ACH", "RTP", "INT"}
SPLIT_CODES = {"SPL"}
UNSUPPORTED_CODES = {"SPR", "REC"}
TXN_CODE_MAP = {"BUY": "buy", "SELL": "sell"}


def is_robinhood_export(columns: set[str]) -> bool:
    return ROBINHOOD_EXPORT_COLUMNS.issubset(columns)


def _parse_date(raw: str) -> datetime:
    dt = datetime.strptime(raw.strip(), DATE_FMT)
    return dt.replace(tzinfo=timezone.utc)


def _parse_money(raw: str) -> Decimal:
    text = (raw or "").strip()
    if not text:
        return D0
    text = text.replace("$", "").replace(",", "")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    return Decimal(text)


def _parse_quantity(raw: str) -> Decimal:
    text = (raw or "").strip().upper()
    if not text:
        return D0
    sign = -1 if text.endswith("S") else 1
    text = text.rstrip("S")
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text:
        return D0
    return Decimal(text) * sign


def _extract_name(description: str) -> str:
    if not description:
        return ""
    first_line = description.splitlines()[0].strip()
    if (
        first_line.startswith("Cash Div:")
        or first_line.startswith("Instant bank")
        or first_line
        in {
            "ACH Deposit",
            "Interest Payment",
        }
    ):
        return ""
    return first_line


def _quantize(value: Decimal, places: Decimal) -> float:
    return float(value.quantize(places, rounding=ROUND_HALF_UP))


def _fetch_price(symbol: str, api_key: str) -> Optional[float]:
    if not api_key:
        return None
    try:
        resp = requests.get(
            FINNHUB_QUOTE_URL,
            params={"symbol": symbol, "token": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        c = resp.json().get("c")
        if c is not None and float(c) > 0:
            return round(float(c), 2)
    except Exception:
        pass
    return None


# US-listed ETF tickers for ``asset_type`` classification in CSV export aggregation.
# Curated (~614): major issuers, sectors, bonds, international, thematic, leveraged.
# Exhaustive coverage would require 3000+ US-listed ETFs or a security-master API;
# symbols not in this set are labeled ``stock`` until you extend the list.
_ETF_SYMBOLS: frozenset[str] = frozenset({
    "AAA", "AADR", "AAXJ", "ACES", "ACIM", "ACIO", "ACWI", "ACWV", "ACWX", "AIA",
    "AIQ", "AIRR", "AIVI", "AIVL", "ALTL", "AMJ", "AMLP", "AMOM", "AMZA", "ANGL",
    "AOA", "AOK", "AOM", "AOR", "ARGT", "ARKB", "ARKG", "ARKK", "ARKQ", "ARKW",
    "ARKX", "ASHR", "ASHS", "ATMP", "AUGM", "AVDE", "AVEM", "AVIG", "AVLV", "AVSC",
    "AVUS", "AVUV", "AWAY", "BAB", "BAL", "BATT", "BBAX", "BBCA", "BBJP", "BBUS",
    "BCD", "BCI", "BDRY", "BETZ", "BFIT", "BIB", "BIL", "BINC", "BITB", "BITI",
    "BITO", "BIV", "BIZD", "BJK", "BKLN", "BLOK", "BLV", "BND", "BNDW", "BNDX",
    "BOIL", "BOTZ", "BRZU", "BTEC", "BUG", "CANE", "CARZ", "CCOR", "CDC", "CDL",
    "CEFS", "CFA", "CIBR", "CLOU", "CNXT", "COM", "COMT", "COPX", "CORN", "CPER",
    "CRAK", "CRBN", "CURE", "CVY", "CWB", "CWBC", "CWI", "DBA", "DBC", "DBEF",
    "DBJP", "DBO", "DEFA", "DEM", "DES", "DEUS", "DEW", "DFAC", "DFAE", "DFAI",
    "DFAR", "DFAS", "DFAT", "DFAU", "DFAX", "DFEA", "DFEM", "DFEV", "DFUS", "DFUV",
    "DGRO", "DGS", "DIA", "DIHP", "DIM", "DIVO", "DLS", "DNL", "DRIP", "DRIV",
    "DSI", "DTD", "DTH", "DVY", "DWAS", "DWX", "DXJ", "EBND", "ECH", "EDEN",
    "EDIV", "EDV", "EEM", "EEMS", "EEMV", "EES", "EEV", "EFA", "EFAD", "EFAV",
    "EFG", "EFIV", "EIDO", "EINC", "EIRL", "EIS", "EMB", "EMLC", "EMMF", "EMQQ",
    "ENOR", "ENZL", "EPHE", "EPI", "EPOL", "EPS", "EQAL", "ESGD", "ESGE", "ESGU",
    "ESGV", "ESML", "ESPO", "ETHA", "ETHE", "EUFN", "EUFX", "EWA", "EWC", "EWD",
    "EWG", "EWH", "EWI", "EWJ", "EWK", "EWL", "EWM", "EWN", "EWP", "EWQ",
    "EWS", "EWT", "EWUS", "EWW", "EWY", "EWZ", "EWZS", "EXI", "EZA", "EZBC",
    "EZU", "FAD", "FAS", "FAZ", "FBCG", "FBND", "FBTC", "FCVT", "FDN", "FDNI",
    "FEM", "FENY", "FEX", "FEZ", "FFEB", "FGD", "FGM", "FHA", "FIW", "FLAX",
    "FLEX", "FLOT", "FLRN", "FM", "FMQQ", "FMX", "FNDA", "FNDC", "FNDE", "FNGD",
    "FNGU", "FNRG", "FPE", "FPX", "FRDM", "FREL", "FRN", "FSTA", "FTCS", "FTEC",
    "FTGC", "FTLS", "FV", "FVAL", "FXD", "FXI", "FXL", "FXY", "GAMR", "GBIL",
    "GBTC", "GDE", "GDX", "GDXJ", "GEM", "GHYB", "GLD", "GLDM", "GLIN", "GLL",
    "GLTR", "GMET", "GMOM", "GOAU", "GOEX", "GOVT", "GREK", "GSG", "GUNR", "GUSH",
    "GVI", "GVIP", "GWX", "HACK", "HAIL", "HAP", "HAUZ", "HAWX", "HDV", "HEFA",
    "HEWJ", "HEZU", "HIBL", "HIBS", "HYDW", "HYEM", "HYG", "HYLB", "HYLS", "HYMB",
    "HYS", "IAGG", "IAI", "IAK", "IAT", "IAUM", "IBB", "IBIT", "IBND", "IBO",
    "IBUY", "ICLN", "IDEV", "IDX", "IEF", "IEFA", "IEI", "IEMG", "IEUR", "IEV",
    "IGF", "IGIB", "IGM", "IGOV", "IGSB", "IGV", "IHE", "IHF", "IHI", "IJH",
    "IJK", "IJR", "INCO", "INDA", "INDL", "INDY", "IQLT", "ITB", "ITM", "ITOT",
    "IUSB", "IVOG", "IVOL", "IVOO", "IVV", "IVW", "IWB", "IWC", "IWD", "IWF",
    "IWM", "IWN", "IWO", "IWP", "IWR", "IWS", "IWV", "IWX", "IWY", "IXUS",
    "IYT", "IYY", "IYZ", "JEPI", "JEPQ", "JPME", "JPST", "KBA", "KBE", "KBWY",
    "KOLD", "KRE", "KSA", "KWEB", "LABD", "LABU", "LIT", "LQD", "MBB", "MCHI",
    "MDY", "MJ", "MORT", "MSOS", "MTUM", "MUB", "NAIL", "NEAR", "NOBL", "NORW",
    "NUSI", "OEF", "OIH", "OUNZ", "PALL", "PAVE", "PBW", "PCEF", "PCY", "PDBC",
    "PFF", "PFFD", "PFFR", "PFXF", "PGJ", "PHB", "PICK", "PILL", "PIN", "PLTM",
    "PPLT", "PSIL", "PSQ", "PST", "PZA", "QAI", "QCLN", "QID", "QLD", "QQEW",
    "QQQ", "QQQE", "QQQM", "QTEC", "QUAL", "QYLD", "REMX", "RING", "RSP", "RSPA",
    "RSPM", "RWL", "RWR", "RYLD", "SATO", "SCHB", "SCHC", "SCHD", "SCHE", "SCHF",
    "SCHG", "SCHH", "SCHJ", "SCHM", "SCHP", "SCHQ", "SCHV", "SCHX", "SCHY", "SCHZ",
    "SDOW", "SDY", "SFY", "SGOL", "SH", "SHY", "SHYG", "SIL", "SILJ", "SJNK",
    "SKF", "SLV", "SMBS", "SMH", "SMIN", "SNSR", "SOXL", "SOXS", "SOXX", "SPAB",
    "SPDW", "SPEM", "SPEU", "SPGP", "SPHY", "SPLB", "SPLG", "SPLV", "SPMO", "SPSB",
    "SPSM", "SPTI", "SPTL", "SPTM", "SPUS", "SPXL", "SPXS", "SPXU", "SPY", "SPYD",
    "SPYG", "SPYV", "SQQQ", "SRLN", "SRVR", "SSO", "STIP", "SUB", "TAN", "TBT",
    "TECL", "TECS", "TFI", "TFLO", "THD", "THNQ", "TIP", "TLH", "TLT", "TMF",
    "TMV", "TNA", "TQQQ", "TTT", "TUR", "TWM", "TZA", "UBT", "UCO", "UDOW",
    "UGA", "UGL", "UNG", "UPRO", "UPW", "URA", "URNM", "USCI", "USFR", "USMV",
    "USO", "UUP", "UWM", "UYG", "VCIT", "VCLT", "VCR", "VCSH", "VDC", "VDE",
    "VEA", "VEU", "VFH", "VFMO", "VGIT", "VGK", "VGLT", "VGSH", "VGT", "VHT",
    "VIG", "VIS", "VLU", "VMBS", "VNQ", "VNQI", "VO", "VOE", "VONG", "VONV",
    "VOO", "VOOG", "VOOV", "VOT", "VOX", "VPL", "VPU", "VRP", "VSGX", "VT",
    "VTEB", "VTI", "VTIP", "VTV", "VTWG", "VTWO", "VTWV", "VUG", "VUSB", "VWO",
    "VWOB", "VXF", "VXUS", "VYM", "VYMI", "WCLD", "WEAT", "WEBL", "WEBS", "XAR",
    "XBI", "XES", "XHB", "XHE", "XHS", "XLB", "XLC", "XLE", "XLF", "XLI",
    "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY", "XME", "XMLV", "XOP", "XPH",
    "XRT", "XSD", "XSLV", "XSMO", "XSVM", "XSW", "XTN", "XWEB", "XYLD", "YANG",
    "YINN", "YOLO", "ZROZ", "ZSL",
})


def classify_symbol_asset_type(symbol: str, default: str = "stock") -> str:
    normalized = (symbol or "").strip().upper()
    if normalized in _ETF_SYMBOLS:
        return "etf"
    return default


def aggregate_export(
    csv_content: str,
) -> Tuple[List[PositionData], List[TransactionData]]:
    """
    Parse a Robinhood transaction export CSV and return aggregated positions
    and individual transaction records.
    """
    api_key = get_settings().finnhub_api_key.strip()
    if api_key:
        logger.info(f"Finnhub API key loaded ({api_key[:4]}...{api_key[-4:]})")
    else:
        logger.warning("FINNHUB_API_KEY is empty — current prices will be zero")

    reader = csv.DictReader(io.StringIO(csv_content))
    raw_rows: List[dict] = []
    parse_errors: List[str] = []
    sort_entries: List[Tuple[datetime, datetime, int, dict]] = []

    for i, row in enumerate(reader):
        if not row.get("Activity Date"):
            continue
        try:
            activity_date = _parse_date(row["Activity Date"])
            pd_raw = (row.get("Process Date") or "").strip()
            process_date = _parse_date(pd_raw) if pd_raw else activity_date
        except (InvalidOperation, ValueError) as exc:
            parse_errors.append(f"row {i + 2}: date parse: {exc}")
            continue
        row["_idx"] = i
        raw_rows.append(row)
        sort_entries.append((process_date, activity_date, i, row))

    sort_entries.sort(key=lambda x: (x[0], x[1], x[2]))
    ordered_rows = [e[3] for e in sort_entries]

    # ── Aggregate positions ──

    class _Pos:
        __slots__ = ("symbol", "name", "qty", "cost", "invested", "last_purchased")

        def __init__(self, symbol: str):
            self.symbol = symbol
            self.name = ""
            self.qty = D0
            self.cost = D0
            self.invested = D0
            self.last_purchased: Optional[datetime] = None

    positions: Dict[str, _Pos] = {}
    transactions: List[TransactionData] = []
    unknown_codes: Set[str] = set()

    for row in ordered_rows:
        code = (row.get("Trans Code") or "").strip().upper()
        symbol = (row.get("Instrument") or "").strip().upper()

        if not symbol:
            continue

        if symbol not in positions:
            positions[symbol] = _Pos(symbol)
        pos = positions[symbol]

        if not pos.name:
            n = _extract_name(row.get("Description", ""))
            if n:
                pos.name = n

        try:
            qty = _parse_quantity(row.get("Quantity", ""))
            amount = _parse_money(row.get("Amount", ""))
            price = _parse_money(row.get("Price", ""))
            process_date_raw = (row.get("Process Date") or "").strip()
            process_date = (
                _parse_date(process_date_raw)
                if process_date_raw
                else _parse_date(row["Activity Date"])
            )
        except (InvalidOperation, ValueError) as exc:
            parse_errors.append(f"row {row['_idx'] + 2}: {symbol} {code}: {exc}")
            continue

        if code == "BUY":
            if qty <= D0:
                continue
            cost = abs(amount) if amount != D0 else qty * price
            pos.qty += qty
            pos.cost += cost
            pos.invested += cost
            if pos.last_purchased is None or process_date > pos.last_purchased:
                pos.last_purchased = process_date

            transactions.append(
                TransactionData(
                    symbol=symbol,
                    transaction_type="buy",
                    quantity=_quantize(qty, D6),
                    price=(
                        _quantize(price, D2)
                        if price != D0
                        else _quantize(cost / qty, D2)
                    ),
                    total_amount=_quantize(cost, D2),
                    fees=0.0,
                    executed_at=process_date,
                )
            )
            continue

        if code == "SELL":
            if qty <= D0 or pos.qty <= D0:
                continue
            sell_qty = min(qty, pos.qty)
            cost_removed = (pos.cost / pos.qty) * sell_qty if pos.qty > D0 else D0
            pos.qty -= sell_qty
            pos.cost -= cost_removed

            transactions.append(
                TransactionData(
                    symbol=symbol,
                    transaction_type="sell",
                    quantity=_quantize(sell_qty, D6),
                    price=_quantize(price, D2) if price != D0 else 0.0,
                    total_amount=_quantize(abs(amount), D2) if amount != D0 else 0.0,
                    fees=0.0,
                    executed_at=process_date,
                )
            )
            continue

        if code in SPLIT_CODES:
            if qty == D0:
                continue
            pos.qty += qty
            if pos.qty < D0:
                parse_errors.append(f"SPL produced negative qty for {symbol}")
                pos.qty = D0
                pos.cost = D0
            continue

        if code == "CDIV":
            if amount > D0:
                transactions.append(
                    TransactionData(
                        symbol=symbol,
                        transaction_type="dividend",
                        quantity=0.0,
                        price=0.0,
                        total_amount=_quantize(amount, D2),
                        fees=0.0,
                        executed_at=process_date,
                    )
                )
            continue

        if code in IGNORED_CODES or code in UNSUPPORTED_CODES:
            continue

        if code:
            unknown_codes.add(code)

    if parse_errors:
        logger.warning(
            f"Export aggregation had {len(parse_errors)} parse issues",
            extra={
                "event": "export_aggregation_warnings",
                "warnings": parse_errors[:20],
            },
        )
    if unknown_codes:
        logger.warning(f"Unknown Trans Code(s): {', '.join(sorted(unknown_codes))}")

    # ── Enrich with current prices and build PositionData ──

    result_positions: List[PositionData] = []
    for pos in sorted(positions.values(), key=lambda p: p.symbol):
        if pos.qty <= D0:
            continue

        avg_cost = _quantize(pos.cost / pos.qty, D2)
        quantity = _quantize(pos.qty, D6)
        invested = _quantize(pos.invested, D2)

        current_price = _fetch_price(pos.symbol, api_key) or 0.0
        unrealized = (
            round((current_price - avg_cost) * quantity, 2)
            if current_price > 0
            else 0.0
        )
        asset_type = classify_symbol_asset_type(pos.symbol)

        result_positions.append(
            PositionData(
                symbol=pos.symbol,
                name=pos.name or pos.symbol,
                quantity=quantity,
                average_cost=avg_cost,
                current_price=current_price,
                purchase_date=pos.last_purchased,
                realized_gains=0.0,
                unrealized_gains=unrealized,
                asset_type=asset_type,
                total_amount_invested=invested,
            )
        )

    return result_positions, transactions
