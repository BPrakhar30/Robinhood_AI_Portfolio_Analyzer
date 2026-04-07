"""
Broker orchestration: adapter selection, encrypted token persistence, and portfolio sync into ORM models.

``_get_adapter`` is the factory for broker-specific implementations. ``_upsert_connection`` merges on
(user, broker_type) to avoid duplicate rows. ``_sync_portfolio`` deletes then re-inserts positions
and transactions for the connection so stale symbols cannot linger. Tokens are sealed at rest with
the app Fernet encryptor. Robinhood re-sync is rejected intentionally—robin_stocks session tokens
expire quickly and cannot be reliably refreshed from DB alone.

Added: 2026-04-03
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.broker_integrations.base import BrokerInterface, PositionData, TransactionData
from app.broker_integrations.robinhood_adapter import RobinhoodAdapter
from app.broker_integrations.plaid_adapter import PlaidAdapter
from app.broker_integrations.csv_adapter import CSVImportAdapter
from app.database.models import (
    BrokerConnection,
    BrokerType,
    ConnectionStatus,
    Position,
    Transaction,
    PortfolioSnapshot,
    AssetType,
    TransactionType,
    User,
)
from app.utils.encryption import get_encryptor
from app.utils.logging import get_logger
from app.utils.exceptions import (
    BrokerConnectionError,
    BrokerAuthenticationError,
    PortfolioSyncError,
)

logger = get_logger("broker_integrations.service")

ASSET_TYPE_MAP = {
    "stock": AssetType.STOCK,
    "etf": AssetType.ETF,
    "crypto": AssetType.CRYPTO,
    "option": AssetType.OPTION,
    "mutual_fund": AssetType.MUTUAL_FUND,
    "bond": AssetType.BOND,
    "cash": AssetType.CASH,
}

TXN_TYPE_MAP = {
    "buy": TransactionType.BUY,
    "sell": TransactionType.SELL,
    "dividend": TransactionType.DIVIDEND,
    "transfer": TransactionType.TRANSFER,
    "interest": TransactionType.INTEREST,
    "fee": TransactionType.FEE,
}


def _get_adapter(broker_type: BrokerType) -> BrokerInterface:
    """Factory method to create the correct adapter based on broker type."""
    if broker_type == BrokerType.ROBINHOOD:
        return RobinhoodAdapter()
    elif broker_type == BrokerType.PLAID:
        return PlaidAdapter()
    elif broker_type == BrokerType.CSV:
        return CSVImportAdapter()
    else:
        raise BrokerConnectionError(f"Unsupported broker type: {broker_type}")


class BrokerService:
    """
    Orchestrates broker connections, token management, and portfolio syncing.
    Handles the business logic between API routes and broker adapters,
    including encrypted token storage and fallback data sourcing.
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._encryptor = get_encryptor()

    async def connect_robinhood(self, user: User, credentials: dict) -> BrokerConnection:
        """
        Connect a user's Robinhood account via OAuth.

        Parameters:
            user: Authenticated User model
            credentials: {"username": str, "password": str, "mfa_code": str?, "device_token": str?}

        Returns:
            BrokerConnection model with encrypted tokens stored

        Raises:
            BrokerAuthenticationError: If Robinhood login fails
        """
        adapter = RobinhoodAdapter()
        auth_result = await adapter.authenticate(credentials)

        connection = await self._upsert_connection(
            user_id=user.id,
            broker_type=BrokerType.ROBINHOOD,
            access_token=auth_result.get("access_token", ""),
            refresh_token=auth_result.get("refresh_token", ""),
        )

        try:
            await self._sync_portfolio(adapter, connection, user.id)
        except Exception as e:
            logger.warning(
                f"Initial portfolio sync failed (connection still saved): {e}",
                extra={"event": "initial_sync_warning", "broker": "robinhood"},
            )
            connection.sync_error_message = str(e)

        await adapter.disconnect()
        return connection

    async def connect_robinhood_with_tokens(
        self, user: User, access_token: str, refresh_token: str = ""
    ) -> BrokerConnection:
        """
        Create/update a Robinhood connection using pre-obtained OAuth tokens
        (from the two-step MFA flow). Bootstraps robin_stocks for portfolio sync.
        """
        adapter = RobinhoodAdapter()
        adapter.set_access_token(access_token)

        connection = await self._upsert_connection(
            user_id=user.id,
            broker_type=BrokerType.ROBINHOOD,
            access_token=access_token,
            refresh_token=refresh_token,
        )

        try:
            await self._sync_portfolio(adapter, connection, user.id)
        except Exception as e:
            logger.warning(
                f"Initial portfolio sync failed (connection still saved): {e}",
                extra={"event": "initial_sync_warning", "broker": "robinhood"},
            )
            connection.sync_error_message = str(e)

        try:
            await adapter.disconnect()
        except Exception:
            pass

        return connection

    async def connect_plaid(self, user: User, public_token: str) -> BrokerConnection:
        """
        Connect via Plaid by exchanging a public_token for an access_token.

        Parameters:
            user: Authenticated User model
            public_token: Token from Plaid Link frontend flow

        Returns:
            BrokerConnection model
        """
        adapter = PlaidAdapter()
        auth_result = await adapter.authenticate({"public_token": public_token})

        connection = await self._upsert_connection(
            user_id=user.id,
            broker_type=BrokerType.PLAID,
            access_token=auth_result.get("access_token", ""),
            metadata={"item_id": auth_result.get("item_id")},
        )

        try:
            await self._sync_portfolio(adapter, connection, user.id)
        except Exception as e:
            logger.warning(f"Initial Plaid sync failed: {e}")
            connection.sync_error_message = str(e)

        return connection

    async def connect_csv(self, user: User, csv_content: str, cash_balance: float = 0.0, filename: str = "upload.csv") -> BrokerConnection:
        """
        Import portfolio from CSV file.

        Parameters:
            user: Authenticated User model
            csv_content: Raw CSV string content
            cash_balance: Manually entered cash balance
            filename: Original filename for logging

        Returns:
            BrokerConnection model
        """
        adapter = CSVImportAdapter()
        await adapter.authenticate({
            "csv_content": csv_content,
            "cash_balance": cash_balance,
            "filename": filename,
        })

        connection = await self._upsert_connection(
            user_id=user.id,
            broker_type=BrokerType.CSV,
            metadata={"filename": filename, "cash_balance": cash_balance},
        )

        await self._sync_portfolio(adapter, connection, user.id)
        return connection

    async def disconnect_broker(self, user: User, connection_id: int) -> bool:
        """
        Disconnect a broker connection and clear its tokens.

        Parameters:
            user: Authenticated User model
            connection_id: ID of the BrokerConnection to disconnect

        Returns:
            True if disconnection was successful
        """
        result = await self._session.execute(
            select(BrokerConnection).where(
                BrokerConnection.id == connection_id,
                BrokerConnection.user_id == user.id,
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise BrokerConnectionError("Connection not found", details={"connection_id": connection_id})

        connection.status = ConnectionStatus.DISCONNECTED
        connection.access_token_encrypted = None
        connection.refresh_token_encrypted = None
        await self._session.flush()

        logger.info(
            "Broker disconnected",
            extra={"event": "broker_disconnected", "broker": connection.broker_type.value, "user_id": user.id},
        )
        return True

    async def get_connections(self, user: User) -> list[BrokerConnection]:
        """Get all broker connections for a user."""
        result = await self._session.execute(
            select(BrokerConnection).where(BrokerConnection.user_id == user.id)
        )
        return list(result.scalars().all())

    async def get_positions(self, user: User, connection_id: Optional[int] = None) -> list[Position]:
        """
        Retrieve stored positions for a user, optionally filtered by connection.

        Parameters:
            user: Authenticated User model
            connection_id: Optional filter by broker connection
        """
        query = select(Position).where(Position.user_id == user.id)
        if connection_id:
            query = query.where(Position.broker_connection_id == connection_id)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_transactions(self, user: User, connection_id: Optional[int] = None, limit: int = 100) -> list[Transaction]:
        """Retrieve stored transactions for a user."""
        query = select(Transaction).where(Transaction.user_id == user.id)
        if connection_id:
            query = query.where(Transaction.broker_connection_id == connection_id)
        query = query.order_by(Transaction.executed_at.desc()).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def sync_connection(self, user: User, connection_id: int) -> BrokerConnection:
        """
        Re-sync portfolio data from a connected broker.
        Uses stored encrypted tokens to re-authenticate.

        Parameters:
            user: Authenticated User model
            connection_id: BrokerConnection ID to sync

        Returns:
            Updated BrokerConnection with fresh sync timestamp

        Raises:
            PortfolioSyncError: If sync fails
        """
        result = await self._session.execute(
            select(BrokerConnection).where(
                BrokerConnection.id == connection_id,
                BrokerConnection.user_id == user.id,
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise BrokerConnectionError("Connection not found")

        if connection.status == ConnectionStatus.DISCONNECTED:
            raise BrokerConnectionError("Connection is disconnected — reconnect first")

        adapter = _get_adapter(connection.broker_type)

        try:
            if connection.broker_type == BrokerType.ROBINHOOD:
                if not connection.access_token_encrypted:
                    raise BrokerAuthenticationError("No stored token — reconnection required")
                token = self._encryptor.decrypt(connection.access_token_encrypted)
                # Short-lived robin_stocks tokens: force full reconnect instead of silent stale sync
                raise PortfolioSyncError(
                    "Robinhood re-sync requires re-authentication (session tokens are short-lived)",
                    details={"broker": "robinhood"},
                )

            elif connection.broker_type == BrokerType.PLAID:
                if not connection.access_token_encrypted:
                    raise BrokerAuthenticationError("No stored Plaid token")
                token = self._encryptor.decrypt(connection.access_token_encrypted)
                adapter.set_access_token(token)

            elif connection.broker_type == BrokerType.CSV:
                raise PortfolioSyncError("CSV connections cannot be re-synced — re-upload the file")

            await self._sync_portfolio(adapter, connection, user.id)
            return connection

        except (PortfolioSyncError, BrokerAuthenticationError, BrokerConnectionError):
            raise
        except Exception as e:
            logger.error(f"Sync failed: {e}", extra={"event": "sync_error", "connection_id": connection_id})
            connection.status = ConnectionStatus.ERROR
            connection.sync_error_message = str(e)
            await self._session.flush()
            raise PortfolioSyncError(f"Portfolio sync failed: {e}")

    async def _upsert_connection(
        self,
        user_id: int,
        broker_type: BrokerType,
        access_token: str = "",
        refresh_token: str = "",
        metadata: Optional[dict] = None,
    ) -> BrokerConnection:
        """Insert or refresh the user's row for this broker; Fernet-encrypt secrets before flush."""
        result = await self._session.execute(
            select(BrokerConnection).where(
                BrokerConnection.user_id == user_id,
                BrokerConnection.broker_type == broker_type,
            )
        )
        connection = result.scalar_one_or_none()

        encrypted_access = self._encryptor.encrypt(access_token) if access_token else None
        encrypted_refresh = self._encryptor.encrypt(refresh_token) if refresh_token else None

        if connection:
            connection.access_token_encrypted = encrypted_access
            connection.refresh_token_encrypted = encrypted_refresh
            connection.status = ConnectionStatus.ACTIVE
            connection.sync_error_message = None
            connection.metadata_ = metadata
        else:
            connection = BrokerConnection(
                user_id=user_id,
                broker_type=broker_type,
                status=ConnectionStatus.ACTIVE,
                access_token_encrypted=encrypted_access,
                refresh_token_encrypted=encrypted_refresh,
                metadata_=metadata,
            )
            self._session.add(connection)

        await self._session.flush()
        await self._session.refresh(connection)

        logger.info(
            "Broker connection saved",
            extra={"event": "connection_saved", "broker": broker_type.value, "user_id": user_id},
        )
        return connection

    async def _sync_portfolio(
        self,
        adapter: BrokerInterface,
        connection: BrokerConnection,
        user_id: int,
    ):
        """
        Pull adapter snapshots into SQLAlchemy. Full replace (delete then insert) per connection
        keeps the DB mirror aligned with the broker without merge logic.
        """
        logger.info(
            "Portfolio sync started",
            extra={"event": "portfolio_sync_start", "broker": connection.broker_type.value},
        )

        try:
            positions_data = await adapter.get_positions()
        except Exception as e:
            logger.error(f"Failed to fetch positions during sync: {e}")
            raise PortfolioSyncError(f"Failed to fetch positions: {e}")

        try:
            transactions_data = await adapter.get_transactions()
        except Exception as e:
            logger.warning(f"Failed to fetch transactions (non-critical): {e}")
            transactions_data = []

        try:
            cash_balance = await adapter.get_cash_balance()
        except Exception as e:
            logger.warning(f"Failed to fetch cash balance (non-critical): {e}")
            cash_balance = 0.0

        # Full replace avoids orphaned rows when the broker drops symbols
        existing_positions = await self._session.execute(
            select(Position).where(Position.broker_connection_id == connection.id)
        )
        for pos in existing_positions.scalars().all():
            await self._session.delete(pos)

        existing_txns = await self._session.execute(
            select(Transaction).where(Transaction.broker_connection_id == connection.id)
        )
        for txn in existing_txns.scalars().all():
            await self._session.delete(txn)

        # Persist new positions
        for pd_ in positions_data:
            position = Position(
                user_id=user_id,
                broker_connection_id=connection.id,
                symbol=pd_.symbol,
                name=pd_.name,
                quantity=pd_.quantity,
                average_cost=pd_.average_cost,
                current_price=pd_.current_price,
                purchase_date=pd_.purchase_date,
                realized_gains=pd_.realized_gains,
                unrealized_gains=pd_.unrealized_gains,
                asset_type=ASSET_TYPE_MAP.get(pd_.asset_type, AssetType.STOCK),
                sector=pd_.sector,
                currency=pd_.currency,
            )
            self._session.add(position)

        # Persist new transactions
        for td_ in transactions_data:
            txn = Transaction(
                user_id=user_id,
                broker_connection_id=connection.id,
                symbol=td_.symbol,
                transaction_type=TXN_TYPE_MAP.get(td_.transaction_type, TransactionType.BUY),
                quantity=td_.quantity,
                price=td_.price,
                total_amount=td_.total_amount,
                fees=td_.fees,
                executed_at=td_.executed_at,
            )
            self._session.add(txn)

        # Save portfolio snapshot
        total_value = sum(p.quantity * p.current_price for p in positions_data) + cash_balance
        snapshot = PortfolioSnapshot(
            user_id=user_id,
            broker_connection_id=connection.id,
            total_value=total_value,
            cash_balance=cash_balance,
            positions_data=[
                {
                    "symbol": p.symbol,
                    "name": p.name,
                    "quantity": p.quantity,
                    "average_cost": p.average_cost,
                    "current_price": p.current_price,
                    "unrealized_gains": p.unrealized_gains,
                    "asset_type": p.asset_type,
                }
                for p in positions_data
            ],
        )
        self._session.add(snapshot)

        connection.last_sync_at = datetime.now(timezone.utc)
        connection.status = ConnectionStatus.ACTIVE
        connection.sync_error_message = None

        await self._session.flush()

        logger.info(
            f"Portfolio sync complete: {len(positions_data)} positions, {len(transactions_data)} transactions",
            extra={
                "event": "portfolio_sync_complete",
                "broker": connection.broker_type.value,
                "positions_count": len(positions_data),
                "transactions_count": len(transactions_data),
                "total_value": total_value,
            },
        )
