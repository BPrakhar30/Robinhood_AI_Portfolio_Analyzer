"""
Plaid broker adapter—primary fallback when direct Robinhood OAuth is not used.

``PLAID_ENV_MAP`` maps app config ``development`` to Plaid Sandbox because this SDK revision
does not expose a separate Development host constant. ``set_access_token`` rehydrates tokens
decrypted from the database for sync/reconnect flows without repeating Link.

Added: 2026-04-03
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

import plaid
from plaid.api import plaid_api
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.investments_transactions_get_request import (
    InvestmentsTransactionsGetRequest,
)
from plaid.model.accounts_get_request import AccountsGetRequest

from app.broker_integrations.base import (
    BrokerInterface,
    PositionData,
    TransactionData,
    AccountSummary,
)
from app.config import get_settings
from app.utils.logging import get_logger
from app.utils.exceptions import (
    BrokerAuthenticationError,
    BrokerConnectionError,
)

logger = get_logger("broker_integrations.plaid")

# "development" -> Sandbox: no distinct Development enum in this plaid-python version
PLAID_ENV_MAP = {
    "sandbox": plaid.Environment.Sandbox,
    "development": plaid.Environment.Sandbox,
    "production": plaid.Environment.Production,
}


class PlaidAdapter(BrokerInterface):
    """
    Broker adapter using Plaid for investment account access.
    Acts as the primary fallback when Robinhood direct OAuth is unavailable.

    Flow:
        1. Create a Plaid Link token (frontend initiates Link UI)
        2. Exchange public_token for access_token
        3. Use access_token for holdings/transactions/balance queries
    """

    def __init__(self):
        self._access_token: Optional[str] = None
        self._connected = False
        self._client: Optional[plaid_api.PlaidApi] = None
        self._securities_map: dict = {}
        self._init_client()

    def _init_client(self):
        settings = get_settings()
        if not settings.plaid_client_id or not settings.plaid_secret:
            logger.warning(
                "Plaid credentials not configured — adapter will not work until configured"
            )
            return

        env = PLAID_ENV_MAP.get(settings.plaid_env, plaid.Environment.Sandbox)
        configuration = plaid.Configuration(
            host=env,
            api_key={
                "clientId": settings.plaid_client_id,
                "secret": settings.plaid_secret,
            },
        )
        api_client = plaid.ApiClient(configuration)
        self._client = plaid_api.PlaidApi(api_client)

    async def create_link_token(self, user_id: str) -> str:
        """
        Create a Plaid Link token for the frontend to initiate the Link flow.

        Parameters:
            user_id: Unique identifier for the user

        Returns:
            Link token string for Plaid Link initialization

        Raises:
            BrokerConnectionError: If Link token creation fails
        """
        if not self._client:
            raise BrokerConnectionError(
                "Plaid client not initialized — check credentials"
            )

        try:
            request = LinkTokenCreateRequest(
                products=[Products("investments")],
                client_name="RobinhoodAICopilot",
                country_codes=[CountryCode("US")],
                language="en",
                user=LinkTokenCreateRequestUser(client_user_id=str(user_id)),
            )
            response = self._client.link_token_create(request)
            logger.info(
                "Plaid Link token created",
                extra={"event": "link_token_created", "broker": "plaid"},
            )
            return response.link_token
        except Exception as e:
            logger.error(
                f"Failed to create Plaid Link token: {e}",
                extra={"event": "link_token_error"},
            )
            raise BrokerConnectionError(f"Failed to create Plaid Link token: {e}")

    async def authenticate(self, credentials: dict) -> dict:
        """
        Exchange a Plaid public_token (from Link) for a persistent access_token.

        Parameters:
            credentials: {"public_token": str} from Plaid Link callback

        Returns:
            {"status": "connected", "broker": "plaid", "access_token": str, "item_id": str}

        Raises:
            BrokerAuthenticationError: If token exchange fails
        """
        if not self._client:
            raise BrokerConnectionError(
                "Plaid client not initialized — check credentials"
            )

        public_token = credentials.get("public_token")
        if not public_token:
            raise BrokerAuthenticationError(
                "public_token is required for Plaid authentication",
                details={"broker": "plaid"},
            )

        try:
            exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self._client.item_public_token_exchange(exchange_request)

            self._access_token = response.access_token
            self._connected = True

            logger.info(
                "Plaid authentication successful",
                extra={"event": "auth_success", "broker": "plaid"},
            )

            return {
                "status": "connected",
                "broker": "plaid",
                "access_token": response.access_token,
                "item_id": response.item_id,
            }

        except plaid.ApiException as e:
            logger.error(
                f"Plaid authentication error: {e}",
                extra={"event": "auth_error", "broker": "plaid"},
            )
            raise BrokerAuthenticationError(
                f"Plaid token exchange failed: {e.body}",
                details={"broker": "plaid"},
            )
        except Exception as e:
            logger.error(f"Unexpected Plaid auth error: {e}")
            raise BrokerAuthenticationError(f"Plaid authentication failed: {e}")

    def set_access_token(self, access_token: str):
        """Restore a previously stored access token (from encrypted DB storage)."""
        self._access_token = access_token
        self._connected = True

    async def get_positions(self) -> list[PositionData]:
        """
        Retrieve investment holdings via Plaid Investments API.

        Returns:
            List of PositionData with holdings and current market values
        """
        self._ensure_connected()
        positions: list[PositionData] = []

        try:
            request = InvestmentsHoldingsGetRequest(access_token=self._access_token)
            response = self._client.investments_holdings_get(request)

            securities = {s.security_id: s for s in response.securities}
            self._securities_map = securities

            for holding in response.holdings:
                try:
                    security = securities.get(holding.security_id)
                    if not security:
                        continue

                    symbol = security.ticker_symbol or "UNKNOWN"
                    quantity = float(holding.quantity or 0)
                    if quantity <= 0:
                        continue

                    cost_basis = float(holding.cost_basis or 0)
                    avg_cost = cost_basis / quantity if quantity else 0
                    current_price = float(security.close_price or 0)
                    unrealized = (current_price * quantity) - cost_basis

                    asset_type = "stock"
                    sec_type = getattr(security, "type", "")
                    if sec_type == "etf":
                        asset_type = "etf"
                    elif sec_type == "cryptocurrency":
                        asset_type = "crypto"
                    elif sec_type == "mutual fund":
                        asset_type = "mutual_fund"

                    positions.append(
                        PositionData(
                            symbol=symbol,
                            name=security.name or symbol,
                            quantity=quantity,
                            average_cost=avg_cost,
                            current_price=current_price,
                            unrealized_gains=unrealized,
                            asset_type=asset_type,
                            sector=getattr(security, "sector", None),
                        )
                    )
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Skipping malformed Plaid holding: {e}")
                    continue

            logger.info(
                f"Retrieved {len(positions)} positions from Plaid",
                extra={
                    "event": "positions_fetched",
                    "broker": "plaid",
                    "count": len(positions),
                },
            )

        except plaid.ApiException as e:
            logger.error(f"Plaid holdings API error: {e}")
            raise BrokerConnectionError(f"Plaid holdings fetch failed: {e.body}")
        except (BrokerConnectionError,):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch Plaid holdings: {e}")
            raise BrokerConnectionError(f"Failed to fetch Plaid holdings: {e}")

        return positions

    async def get_transactions(self, limit: int = 100) -> list[TransactionData]:
        """
        Retrieve investment transactions from the last 90 days via Plaid.

        Parameters:
            limit: Maximum number of transactions to return

        Returns:
            List of TransactionData
        """
        self._ensure_connected()
        transactions: list[TransactionData] = []

        try:
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=90)

            request = InvestmentsTransactionsGetRequest(
                access_token=self._access_token,
                start_date=start_date,
                end_date=end_date,
            )
            response = self._client.investments_transactions_get(request)

            securities = {s.security_id: s for s in response.securities}

            for txn in response.investment_transactions[:limit]:
                try:
                    security = securities.get(txn.security_id)
                    symbol = security.ticker_symbol if security else "UNKNOWN"

                    txn_type = str(txn.type or "buy").lower()
                    if "sell" in txn_type:
                        txn_type = "sell"
                    elif "dividend" in txn_type:
                        txn_type = "dividend"
                    else:
                        txn_type = "buy"

                    quantity = abs(float(txn.quantity or 0))
                    price = float(txn.price or 0)
                    total = abs(float(txn.amount or 0))

                    transactions.append(
                        TransactionData(
                            symbol=symbol,
                            transaction_type=txn_type,
                            quantity=quantity,
                            price=price,
                            total_amount=total,
                            fees=float(txn.fees or 0),
                            executed_at=datetime.combine(
                                txn.date, datetime.min.time()
                            ).replace(tzinfo=timezone.utc),
                        )
                    )
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Skipping malformed Plaid transaction: {e}")
                    continue

            logger.info(
                f"Retrieved {len(transactions)} transactions from Plaid",
                extra={
                    "event": "transactions_fetched",
                    "broker": "plaid",
                    "count": len(transactions),
                },
            )

        except plaid.ApiException as e:
            logger.error(f"Plaid transactions API error: {e}")
            raise BrokerConnectionError(f"Plaid transactions fetch failed: {e.body}")
        except (BrokerConnectionError,):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch Plaid transactions: {e}")
            raise BrokerConnectionError(f"Failed to fetch Plaid transactions: {e}")

        return transactions

    async def get_cash_balance(self) -> float:
        """
        Retrieve cash balance from Plaid-connected investment accounts.

        Returns:
            Total cash balance across all investment accounts
        """
        self._ensure_connected()

        try:
            request = AccountsGetRequest(access_token=self._access_token)
            response = self._client.accounts_get(request)

            cash_total = 0.0
            for account in response.accounts:
                if account.type in ("investment", "brokerage"):
                    balances = account.balances
                    cash_total += float(balances.available or balances.current or 0)

            logger.info(
                "Retrieved cash balance from Plaid",
                extra={"event": "cash_fetched", "broker": "plaid"},
            )
            return cash_total

        except plaid.ApiException as e:
            logger.error(f"Plaid accounts API error: {e}")
            raise BrokerConnectionError(f"Plaid cash balance fetch failed: {e.body}")
        except (BrokerConnectionError,):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch Plaid cash balance: {e}")
            raise BrokerConnectionError(f"Failed to fetch Plaid cash balance: {e}")

    async def get_account_summary(self) -> AccountSummary:
        """Build account summary from Plaid holdings and accounts data."""
        self._ensure_connected()

        try:
            positions = await self.get_positions()
            cash = await self.get_cash_balance()

            total_equity = sum(p.quantity * p.current_price for p in positions)
            total_value = total_equity + cash
            total_unrealized = sum(p.unrealized_gains for p in positions)

            return AccountSummary(
                total_value=total_value,
                cash_balance=cash,
                positions_count=len(positions),
                buying_power=cash,
                total_unrealized_gains=total_unrealized,
            )

        except (BrokerConnectionError,):
            raise
        except Exception as e:
            logger.error(f"Failed to build Plaid account summary: {e}")
            raise BrokerConnectionError(f"Failed to build Plaid account summary: {e}")

    async def disconnect(self) -> bool:
        """Clear the Plaid access token (item removal would require separate API call)."""
        self._access_token = None
        self._connected = False
        logger.info(
            "Disconnected from Plaid",
            extra={"event": "disconnected", "broker": "plaid"},
        )
        return True

    def is_connected(self) -> bool:
        return self._connected

    def _ensure_connected(self):
        if not self._connected or not self._access_token:
            raise BrokerAuthenticationError(
                "Not authenticated with Plaid. Call authenticate() first.",
                details={"broker": "plaid"},
            )
