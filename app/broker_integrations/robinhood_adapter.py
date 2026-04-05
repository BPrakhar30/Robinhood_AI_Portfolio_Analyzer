"""
Robinhood broker adapter via ``robin_stocks`` (synchronous library).

All blocking calls run in ``run_in_executor`` with a timeout so the async stack stays responsive.
Crypto holdings are fetched in a separate path; failures are logged and swallowed so equity data
still returns. ``store_session=False`` keeps tokens out of robin_stocks' on-disk session files.

Added: 2026-04-03
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

import robin_stocks.robinhood as rh

from app.broker_integrations.base import (
    BrokerInterface,
    PositionData,
    TransactionData,
    AccountSummary,
)
from app.utils.logging import get_logger
from app.utils.exceptions import (
    BrokerAuthenticationError,
    BrokerConnectionError,
    BrokerTimeoutError,
)

logger = get_logger("broker_integrations.robinhood")

# robin_stocks is synchronous; we run its calls in a thread pool
TIMEOUT_SECONDS = 30


def _run_sync(func, *args, **kwargs):
    """Wraps a synchronous robin_stocks call for use in async context."""
    return func(*args, **kwargs)


class RobinhoodAdapter(BrokerInterface):
    """
    Broker adapter for Robinhood using robin_stocks library.
    Supports OAuth login, position retrieval, transaction history, and cash balance.

    Authentication flow:
        1. User provides username/password + optional MFA
        2. robin_stocks handles OAuth token exchange
        3. Tokens are returned for encrypted storage (never stored in plaintext)
    """

    def __init__(self):
        self._connected = False
        self._username: Optional[str] = None

    async def authenticate(self, credentials: dict) -> dict:
        """
        Authenticate with Robinhood via robin_stocks OAuth.

        Parameters:
            credentials: {
                "username": str,
                "password": str,
                "mfa_code": str (optional),
                "device_token": str (optional)
            }

        Returns:
            {"status": "connected", "broker": "robinhood", "access_token": str, "refresh_token": str}

        Raises:
            BrokerAuthenticationError: If login fails
        """
        username = credentials.get("username")
        password = credentials.get("password")
        mfa_code = credentials.get("mfa_code")
        device_token = credentials.get("device_token")

        if not username or not password:
            raise BrokerAuthenticationError(
                "Username and password are required",
                details={"broker": "robinhood"},
            )

        logger.info("Robinhood authentication started", extra={"event": "auth_start", "broker": "robinhood"})

        try:
            login_kwargs = {
                "username": username,
                "password": password,
                "expiresIn": 86400,
                "store_session": False,  # do not persist tokens to local robin_stocks files
            }
            if mfa_code:
                login_kwargs["mfa_code"] = mfa_code
            if device_token:
                login_kwargs["device_token"] = device_token

            login_result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: _run_sync(rh.login, **login_kwargs)
                ),
                timeout=TIMEOUT_SECONDS,
            )

            if not login_result or "access_token" not in login_result:
                raise BrokerAuthenticationError(
                    "Robinhood login failed — invalid credentials or MFA required.",
                    details={"broker": "robinhood"},
                )

            self._connected = True
            self._username = username

            logger.info(
                "Robinhood authentication successful",
                extra={"event": "auth_success", "broker": "robinhood"},
            )

            return {
                "status": "connected",
                "broker": "robinhood",
                "access_token": login_result.get("access_token", ""),
                "refresh_token": login_result.get("refresh_token", ""),
                "expires_in": login_result.get("expires_in", 86400),
            }

        except asyncio.TimeoutError:
            logger.error("Robinhood authentication timed out", extra={"event": "auth_timeout", "broker": "robinhood"})
            raise BrokerTimeoutError(
                "Robinhood authentication timed out",
                details={"broker": "robinhood", "timeout_seconds": TIMEOUT_SECONDS},
            )
        except BrokerAuthenticationError:
            raise
        except Exception as e:
            logger.error(
                f"Robinhood authentication error: {e}",
                extra={"event": "auth_error", "broker": "robinhood", "error": str(e)},
            )
            raise BrokerAuthenticationError(
                f"Robinhood authentication failed: {e}",
                details={"broker": "robinhood"},
            )

    async def get_positions(self) -> list[PositionData]:
        """
        Retrieve all current holdings from Robinhood.
        Combines stock positions and crypto positions into a unified list.

        Returns:
            List of PositionData with holdings, cost basis, and current prices

        Raises:
            BrokerConnectionError: If API call fails
        """
        self._ensure_connected()
        positions: list[PositionData] = []

        try:
            stock_positions = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: rh.account.build_holdings()
                ),
                timeout=TIMEOUT_SECONDS,
            )

            if stock_positions:
                for symbol, data in stock_positions.items():
                    try:
                        quantity = float(data.get("quantity", 0))
                        if quantity <= 0:
                            continue

                        avg_cost = float(data.get("average_buy_price", 0))
                        current_price = float(data.get("price", 0))
                        equity = float(data.get("equity", 0))
                        percent_change = float(data.get("percent_change", 0))

                        unrealized = equity - (avg_cost * quantity)

                        positions.append(PositionData(
                            symbol=symbol,
                            name=data.get("name", symbol),
                            quantity=quantity,
                            average_cost=avg_cost,
                            current_price=current_price,
                            unrealized_gains=unrealized,
                            asset_type=data.get("type", "stock"),
                            sector=data.get("sector"),
                        ))
                    except (ValueError, KeyError) as e:
                        logger.warning(
                            f"Skipping malformed position for {symbol}: {e}",
                            extra={"event": "position_parse_error", "symbol": symbol},
                        )
                        continue

            logger.info(
                f"Retrieved {len(positions)} positions from Robinhood",
                extra={"event": "positions_fetched", "broker": "robinhood", "count": len(positions)},
            )

        except asyncio.TimeoutError:
            logger.error("Robinhood positions fetch timed out", extra={"event": "positions_timeout"})
            raise BrokerTimeoutError("Timed out fetching positions from Robinhood")
        except (BrokerTimeoutError, BrokerConnectionError):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}", extra={"event": "positions_error", "error": str(e)})
            raise BrokerConnectionError(f"Failed to fetch Robinhood positions: {e}")

        # Supplemental path: crypto failures are non-fatal for the overall positions response
        try:
            crypto_positions = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: rh.crypto.get_crypto_positions()
                ),
                timeout=TIMEOUT_SECONDS,
            )

            if crypto_positions:
                for crypto in crypto_positions:
                    try:
                        quantity = float(crypto.get("quantity", 0))
                        if quantity <= 0:
                            continue

                        cost_bases = crypto.get("cost_bases", [{}])
                        avg_cost = float(cost_bases[0].get("direct_cost_basis", 0)) / quantity if quantity else 0

                        symbol = crypto.get("currency", {}).get("code", "UNKNOWN")
                        positions.append(PositionData(
                            symbol=symbol,
                            name=crypto.get("currency", {}).get("name", symbol),
                            quantity=quantity,
                            average_cost=avg_cost,
                            current_price=0.0,
                            asset_type="crypto",
                        ))
                    except (ValueError, KeyError, ZeroDivisionError) as e:
                        logger.warning(f"Skipping malformed crypto position: {e}")
                        continue

        except Exception as e:
            logger.warning(
                f"Crypto positions fetch failed (non-critical): {e}",
                extra={"event": "crypto_positions_warning", "error": str(e)},
            )

        return positions

    async def get_transactions(self, limit: int = 100) -> list[TransactionData]:
        """
        Retrieve recent stock order history from Robinhood.

        Parameters:
            limit: Maximum number of transactions to return

        Returns:
            List of TransactionData
        """
        self._ensure_connected()
        transactions: list[TransactionData] = []

        try:
            orders = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: rh.orders.get_all_stock_orders()
                ),
                timeout=TIMEOUT_SECONDS,
            )

            if not orders:
                return transactions

            for order in orders[:limit]:
                try:
                    if order.get("state") != "filled":
                        continue

                    symbol = order.get("symbol", "")
                    if not symbol:
                        instrument_url = order.get("instrument", "")
                        instrument_data = await asyncio.get_event_loop().run_in_executor(
                            None, lambda url=instrument_url: rh.stocks.get_instrument_by_url(url)
                        )
                        symbol = instrument_data.get("symbol", "UNKNOWN") if instrument_data else "UNKNOWN"

                    side = order.get("side", "buy")
                    quantity = float(order.get("quantity", 0))
                    avg_price = float(order.get("average_price", 0) or 0)
                    total = quantity * avg_price
                    fees = float(order.get("fees", 0) or 0)

                    executed_at_str = order.get("last_transaction_at") or order.get("updated_at", "")
                    try:
                        executed_at = datetime.fromisoformat(executed_at_str.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        executed_at = datetime.now(timezone.utc)

                    transactions.append(TransactionData(
                        symbol=symbol,
                        transaction_type=side,
                        quantity=quantity,
                        price=avg_price,
                        total_amount=total,
                        fees=fees,
                        executed_at=executed_at,
                    ))
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping malformed order: {e}")
                    continue

            logger.info(
                f"Retrieved {len(transactions)} transactions from Robinhood",
                extra={"event": "transactions_fetched", "broker": "robinhood", "count": len(transactions)},
            )

        except asyncio.TimeoutError:
            raise BrokerTimeoutError("Timed out fetching transactions from Robinhood")
        except (BrokerTimeoutError, BrokerConnectionError):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch transactions: {e}", extra={"event": "transactions_error"})
            raise BrokerConnectionError(f"Failed to fetch Robinhood transactions: {e}")

        return transactions

    async def get_cash_balance(self) -> float:
        """
        Retrieve the current cash balance (buying power) from Robinhood.

        Returns:
            Cash balance as float
        """
        self._ensure_connected()

        try:
            profile = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: rh.profiles.load_account_profile()
                ),
                timeout=TIMEOUT_SECONDS,
            )

            if not profile:
                raise BrokerConnectionError("Empty account profile returned")

            cash = float(profile.get("cash", 0) or 0)
            logger.info(f"Retrieved cash balance from Robinhood", extra={"event": "cash_fetched", "broker": "robinhood"})
            return cash

        except asyncio.TimeoutError:
            raise BrokerTimeoutError("Timed out fetching cash balance")
        except (BrokerTimeoutError, BrokerConnectionError):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch cash balance: {e}")
            raise BrokerConnectionError(f"Failed to fetch Robinhood cash balance: {e}")

    async def get_account_summary(self) -> AccountSummary:
        """
        Build a full account summary combining positions, cash, and gains.

        Returns:
            AccountSummary with total_value, cash, position count, and gain totals
        """
        self._ensure_connected()

        try:
            positions = await self.get_positions()
            cash = await self.get_cash_balance()

            total_equity = sum(p.quantity * p.current_price for p in positions)
            total_value = total_equity + cash
            total_unrealized = sum(p.unrealized_gains for p in positions)
            total_realized = sum(p.realized_gains for p in positions)

            profile = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: rh.profiles.load_account_profile()
                ),
                timeout=TIMEOUT_SECONDS,
            )
            buying_power = float(profile.get("buying_power", 0) or 0) if profile else cash

            return AccountSummary(
                total_value=total_value,
                cash_balance=cash,
                positions_count=len(positions),
                buying_power=buying_power,
                total_realized_gains=total_realized,
                total_unrealized_gains=total_unrealized,
            )

        except (BrokerTimeoutError, BrokerConnectionError):
            raise
        except Exception as e:
            logger.error(f"Failed to build account summary: {e}")
            raise BrokerConnectionError(f"Failed to build Robinhood account summary: {e}")

    async def disconnect(self) -> bool:
        """Logout from Robinhood and clear session."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: rh.logout()
            )
            self._connected = False
            self._username = None
            logger.info("Disconnected from Robinhood", extra={"event": "disconnected", "broker": "robinhood"})
            return True
        except Exception as e:
            logger.error(f"Error during Robinhood disconnect: {e}")
            self._connected = False
            return False

    def is_connected(self) -> bool:
        return self._connected

    def _ensure_connected(self):
        if not self._connected:
            raise BrokerAuthenticationError(
                "Not authenticated with Robinhood. Call authenticate() first.",
                details={"broker": "robinhood"},
            )
