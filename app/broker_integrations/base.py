from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class PositionData:
    """Standardized position data returned by all broker adapters."""
    symbol: str
    name: str
    quantity: float
    average_cost: float
    current_price: float
    purchase_date: Optional[datetime] = None
    realized_gains: float = 0.0
    unrealized_gains: float = 0.0
    asset_type: str = "stock"
    sector: Optional[str] = None
    currency: str = "USD"


@dataclass
class TransactionData:
    """Standardized transaction data returned by all broker adapters."""
    symbol: str
    transaction_type: str
    quantity: float
    price: float
    total_amount: float
    fees: float = 0.0
    executed_at: datetime = field(default_factory=datetime.now)


@dataclass
class AccountSummary:
    """Standardized account summary across all broker types."""
    total_value: float
    cash_balance: float
    positions_count: int
    buying_power: float = 0.0
    total_realized_gains: float = 0.0
    total_unrealized_gains: float = 0.0


class BrokerInterface(ABC):
    """
    Abstract base class for all broker integrations.
    Implements the Interface-Based Broker Integration pattern from the developer guidelines.

    Every broker adapter (Robinhood, Plaid, CSV) must implement this interface,
    ensuring consistent data access regardless of the underlying broker.

    Subclasses must implement:
        - authenticate(): Establish connection to the broker
        - get_positions(): Retrieve current holdings
        - get_transactions(): Retrieve trade history
        - get_cash_balance(): Retrieve available cash
        - get_account_summary(): Retrieve account overview
        - disconnect(): Cleanly close the connection
    """

    @abstractmethod
    async def authenticate(self, credentials: dict) -> dict:
        """
        Authenticate with the broker and return connection metadata.

        Parameters:
            credentials: Broker-specific credentials (OAuth tokens, API keys, etc.)

        Returns:
            dict with at minimum: {"status": "connected", "broker": "<type>"}

        Raises:
            BrokerAuthenticationError: If authentication fails
        """
        ...

    @abstractmethod
    async def get_positions(self) -> list[PositionData]:
        """
        Retrieve all current positions/holdings.

        Returns:
            List of PositionData with symbol, quantity, cost basis, current price, gains

        Raises:
            BrokerConnectionError: If the API call fails
            BrokerTimeoutError: If the request times out
        """
        ...

    @abstractmethod
    async def get_transactions(self, limit: int = 100) -> list[TransactionData]:
        """
        Retrieve recent transactions/trade history.

        Parameters:
            limit: Maximum number of transactions to return

        Returns:
            List of TransactionData

        Raises:
            BrokerConnectionError: If the API call fails
        """
        ...

    @abstractmethod
    async def get_cash_balance(self) -> float:
        """
        Retrieve the current cash balance.

        Returns:
            Cash balance as a float

        Raises:
            BrokerConnectionError: If the API call fails
        """
        ...

    @abstractmethod
    async def get_account_summary(self) -> AccountSummary:
        """
        Retrieve a summary of the account including total value, cash, and gains.

        Returns:
            AccountSummary dataclass

        Raises:
            BrokerConnectionError: If the API call fails
        """
        ...

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from the broker, invalidating any tokens/sessions.

        Returns:
            True if disconnection was successful
        """
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the adapter currently has an active connection."""
        ...
