import io
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from app.broker_integrations.base import (
    BrokerInterface,
    PositionData,
    TransactionData,
    AccountSummary,
)
from app.utils.logging import get_logger
from app.utils.exceptions import CSVParseError, BrokerAuthenticationError

logger = get_logger("broker_integrations.csv")

REQUIRED_POSITION_COLUMNS = {"symbol", "quantity", "average_cost"}

OPTIONAL_POSITION_COLUMNS = {
    "name", "current_price", "purchase_date",
    "realized_gains", "unrealized_gains", "asset_type", "sector",
}

REQUIRED_TRANSACTION_COLUMNS = {"symbol", "transaction_type", "quantity", "price"}

OPTIONAL_TRANSACTION_COLUMNS = {"total_amount", "fees", "executed_at"}

SAMPLE_CSV_TEMPLATE = """symbol,name,quantity,average_cost,current_price,purchase_date,realized_gains,unrealized_gains,asset_type,sector
AAPL,Apple Inc,10,150.00,175.50,2024-01-15,0,255.00,stock,Technology
NVDA,NVIDIA Corp,5,450.00,890.00,2024-03-01,0,2200.00,stock,Technology
VTI,Vanguard Total Stock Market ETF,20,220.00,235.00,2023-06-15,0,300.00,etf,
QQQ,Invesco QQQ Trust,8,380.00,445.00,2024-02-01,0,520.00,etf,
BTC,Bitcoin,0.5,42000.00,68000.00,2024-01-01,0,13000.00,crypto,
"""


class CSVImportAdapter(BrokerInterface):
    """
    Fallback adapter that imports portfolio data from a CSV file.
    This is the last-resort option when neither Robinhood OAuth
    nor Plaid integration is available.

    Accepts CSV with columns matching REQUIRED_POSITION_COLUMNS.
    Optional columns are filled with defaults if missing.
    """

    def __init__(self):
        self._positions: list[PositionData] = []
        self._transactions: list[TransactionData] = []
        self._cash_balance: float = 0.0
        self._connected = False
        self._filename: Optional[str] = None

    async def authenticate(self, credentials: dict) -> dict:
        """
        'Authentication' for CSV means validating and parsing the uploaded file.

        Parameters:
            credentials: {
                "csv_content": str (raw CSV text),
                "cash_balance": float (optional, manual entry),
                "filename": str (optional, for logging),
                "csv_type": str ("positions" or "transactions", default "positions")
            }

        Returns:
            {"status": "connected", "broker": "csv", "positions_count": int}
        """
        csv_content = credentials.get("csv_content")
        if not csv_content:
            raise CSVParseError("No CSV content provided")

        self._cash_balance = float(credentials.get("cash_balance", 0))
        self._filename = credentials.get("filename", "upload.csv")
        csv_type = credentials.get("csv_type", "positions")

        logger.info(
            f"CSV import started: {self._filename}",
            extra={"event": "csv_import_start", "file": self._filename, "type": csv_type},
        )

        try:
            df = pd.read_csv(io.StringIO(csv_content))
            df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        except Exception as e:
            raise CSVParseError(f"Failed to parse CSV file: {e}", details={"filename": self._filename})

        if df.empty:
            raise CSVParseError("CSV file is empty", details={"filename": self._filename})

        if csv_type == "transactions":
            self._transactions = self._parse_transactions(df)
        else:
            self._positions = self._parse_positions(df)

        self._connected = True

        logger.info(
            f"CSV import complete: {len(self._positions)} positions, {len(self._transactions)} transactions",
            extra={
                "event": "csv_import_complete",
                "positions_count": len(self._positions),
                "transactions_count": len(self._transactions),
            },
        )

        return {
            "status": "connected",
            "broker": "csv",
            "positions_count": len(self._positions),
            "transactions_count": len(self._transactions),
            "filename": self._filename,
        }

    def _parse_positions(self, df: pd.DataFrame) -> list[PositionData]:
        """
        Parse a DataFrame into a list of PositionData.

        Parameters:
            df: DataFrame with at least REQUIRED_POSITION_COLUMNS

        Returns:
            List of validated PositionData

        Raises:
            CSVParseError: If required columns are missing or data is invalid
        """
        missing = REQUIRED_POSITION_COLUMNS - set(df.columns)
        if missing:
            raise CSVParseError(
                f"CSV missing required columns: {missing}",
                details={"missing_columns": list(missing), "found_columns": list(df.columns)},
            )

        positions = []
        errors = []

        for idx, row in df.iterrows():
            try:
                symbol = str(row["symbol"]).strip().upper()
                quantity = float(row["quantity"])
                avg_cost = float(row["average_cost"])

                if quantity <= 0:
                    errors.append(f"Row {idx + 1}: quantity must be positive for {symbol}")
                    continue
                if avg_cost < 0:
                    errors.append(f"Row {idx + 1}: average_cost cannot be negative for {symbol}")
                    continue

                name = str(row.get("name", symbol)).strip() if pd.notna(row.get("name")) else symbol
                current_price = float(row.get("current_price", 0)) if pd.notna(row.get("current_price")) else 0.0
                realized = float(row.get("realized_gains", 0)) if pd.notna(row.get("realized_gains")) else 0.0
                unrealized = float(row.get("unrealized_gains", 0)) if pd.notna(row.get("unrealized_gains")) else 0.0
                asset_type = str(row.get("asset_type", "stock")).strip().lower() if pd.notna(row.get("asset_type")) else "stock"
                sector = str(row.get("sector", "")).strip() if pd.notna(row.get("sector")) else None

                purchase_date = None
                if pd.notna(row.get("purchase_date")):
                    try:
                        purchase_date = pd.to_datetime(row["purchase_date"]).to_pydatetime()
                        if purchase_date.tzinfo is None:
                            purchase_date = purchase_date.replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        pass

                if unrealized == 0 and current_price > 0:
                    unrealized = (current_price - avg_cost) * quantity

                positions.append(PositionData(
                    symbol=symbol,
                    name=name,
                    quantity=quantity,
                    average_cost=avg_cost,
                    current_price=current_price,
                    purchase_date=purchase_date,
                    realized_gains=realized,
                    unrealized_gains=unrealized,
                    asset_type=asset_type,
                    sector=sector if sector else None,
                ))

            except (ValueError, TypeError) as e:
                errors.append(f"Row {idx + 1}: {e}")
                continue

        if errors:
            logger.warning(
                f"CSV parsing had {len(errors)} warnings",
                extra={"event": "csv_parse_warnings", "warnings": errors[:10]},
            )

        if not positions:
            raise CSVParseError("No valid positions found in CSV", details={"errors": errors[:10]})

        return positions

    def _parse_transactions(self, df: pd.DataFrame) -> list[TransactionData]:
        """
        Parse a DataFrame into a list of TransactionData.

        Parameters:
            df: DataFrame with at least REQUIRED_TRANSACTION_COLUMNS

        Returns:
            List of validated TransactionData
        """
        missing = REQUIRED_TRANSACTION_COLUMNS - set(df.columns)
        if missing:
            raise CSVParseError(
                f"CSV missing required columns: {missing}",
                details={"missing_columns": list(missing)},
            )

        transactions = []

        for idx, row in df.iterrows():
            try:
                symbol = str(row["symbol"]).strip().upper()
                txn_type = str(row["transaction_type"]).strip().lower()
                quantity = abs(float(row["quantity"]))
                price = float(row["price"])
                total = float(row.get("total_amount", quantity * price)) if pd.notna(row.get("total_amount")) else quantity * price
                fees = float(row.get("fees", 0)) if pd.notna(row.get("fees")) else 0.0

                executed_at = datetime.now(timezone.utc)
                if pd.notna(row.get("executed_at")):
                    try:
                        executed_at = pd.to_datetime(row["executed_at"]).to_pydatetime()
                        if executed_at.tzinfo is None:
                            executed_at = executed_at.replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        pass

                transactions.append(TransactionData(
                    symbol=symbol,
                    transaction_type=txn_type,
                    quantity=quantity,
                    price=price,
                    total_amount=total,
                    fees=fees,
                    executed_at=executed_at,
                ))
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed CSV transaction row {idx + 1}: {e}")
                continue

        return transactions

    async def get_positions(self) -> list[PositionData]:
        """Return positions parsed from the uploaded CSV."""
        self._ensure_connected()
        return self._positions

    async def get_transactions(self, limit: int = 100) -> list[TransactionData]:
        """Return transactions parsed from the uploaded CSV."""
        self._ensure_connected()
        return self._transactions[:limit]

    async def get_cash_balance(self) -> float:
        """Return the manually provided cash balance."""
        self._ensure_connected()
        return self._cash_balance

    async def get_account_summary(self) -> AccountSummary:
        """Build account summary from CSV data."""
        self._ensure_connected()
        total_equity = sum(p.quantity * p.current_price for p in self._positions)
        total_value = total_equity + self._cash_balance

        return AccountSummary(
            total_value=total_value,
            cash_balance=self._cash_balance,
            positions_count=len(self._positions),
            buying_power=self._cash_balance,
            total_realized_gains=sum(p.realized_gains for p in self._positions),
            total_unrealized_gains=sum(p.unrealized_gains for p in self._positions),
        )

    async def disconnect(self) -> bool:
        """Clear imported data."""
        self._positions = []
        self._transactions = []
        self._cash_balance = 0.0
        self._connected = False
        self._filename = None
        logger.info("CSV import data cleared", extra={"event": "disconnected", "broker": "csv"})
        return True

    def is_connected(self) -> bool:
        return self._connected

    def _ensure_connected(self):
        if not self._connected:
            raise BrokerAuthenticationError(
                "No CSV data loaded. Call authenticate() with csv_content first.",
                details={"broker": "csv"},
            )

    @staticmethod
    def get_sample_template() -> str:
        """Return a sample CSV template that users can download and fill in."""
        return SAMPLE_CSV_TEMPLATE.strip()
