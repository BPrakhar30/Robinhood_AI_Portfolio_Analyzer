"""
Robinhood broker adapter — two-step MFA flow + data fetching via ``robin_stocks``.

The login flow uses ``robin_stocks``' internal HTTP helpers (which carry the correct
API-version header, User-Agent, TLS session, and cookies) but controls the
verification-workflow lifecycle manually so we never hit the blocking ``input()``
call inside ``rh.login()``.

Robinhood's current auth sequence:

  1. POST ``/oauth2/token/`` with credentials
     → ``access_token`` (no MFA) **or** ``verification_workflow``
  2. POST ``/pathfinder/user_machine/`` with workflow_id → ``machine_id``
  3. GET  ``/pathfinder/inquiries/{machine_id}/user_view/`` → ``sheriff_challenge``
     (type = "sms" | "email" | "prompt")
  4. For sms/email: POST ``/challenge/{id}/respond/`` with user code
     For prompt: poll ``/push/{id}/get_prompts_status/`` until validated
  5. POST ``/pathfinder/inquiries/{machine_id}/user_view/`` with continue → approved
  6. Retry ``/oauth2/token/`` → ``access_token``

``initiate_login`` covers steps 1-3 and stores state.
``complete_mfa``   covers steps 4-6 and returns the tokens.

Added: 2026-04-03
Updated: 2026-04-06 — two-step MFA using robin_stocks internals
"""
import asyncio
import time as _time
from datetime import datetime, timezone, timedelta
from typing import Optional

import robin_stocks.robinhood as rh
from robin_stocks.robinhood.helper import (
    request_post as _rh_post,
    request_get as _rh_get,
    update_session as _rh_update_session,
    set_login_state as _rh_set_login_state,
)
from robin_stocks.robinhood.authentication import (
    generate_device_token as _rh_device_token,
)
from robin_stocks.robinhood.urls import login_url as _rh_login_url

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

TIMEOUT_SECONDS = 30
_RH_CLIENT_ID = "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS"

_PATHFINDER_URL = "https://api.robinhood.com/pathfinder/user_machine/"
_INQUIRIES_URL = "https://api.robinhood.com/pathfinder/inquiries/{mid}/user_view/"
_CHALLENGE_URL = "https://api.robinhood.com/challenge/{cid}/respond/"
_PUSH_URL = "https://api.robinhood.com/push/{cid}/get_prompts_status/"

# Pending MFA states keyed by user_id
_pending_challenges: dict[int, dict] = {}
_CHALLENGE_TTL = timedelta(minutes=5)


def _cleanup_expired():
    now = datetime.now(timezone.utc)
    expired = [uid for uid, s in _pending_challenges.items()
               if now - s["created_at"] > _CHALLENGE_TTL]
    for uid in expired:
        _pending_challenges.pop(uid, None)


class RobinhoodAdapter(BrokerInterface):
    """
    Broker adapter for Robinhood.

    Two-step MFA flow (static methods — no instance needed):
        ``initiate_login``  → sends credentials, returns challenge info
        ``complete_mfa``    → sends MFA code, completes the stored challenge

    Data fetching (instance methods — call after ``set_access_token``):
        ``get_positions``, ``get_transactions``, ``get_cash_balance``, etc.
    """

    def __init__(self):
        self._connected = False
        self._username: Optional[str] = None

    # ────────────── Two-step MFA flow ──────────────

    @staticmethod
    async def initiate_login(user_id: int, username: str, password: str) -> dict:
        """
        Step 1: Send credentials → if MFA needed, walk through the pathfinder
        flow until we know the challenge type, then return to the caller.
        """
        _cleanup_expired()

        def _step1():
            device_token = _rh_device_token()
            url = _rh_login_url()

            payload = {
                "client_id": _RH_CLIENT_ID,
                "expires_in": 86400,
                "grant_type": "password",
                "password": password,
                "scope": "internal",
                "username": username,
                "device_token": device_token,
                "try_passkeys": False,
                "token_request_path": "/login",
                "create_read_only_secondary_token": True,
            }

            data = _rh_post(url, payload)

            if not data:
                return {"_error": "No response from Robinhood. Please try again."}

            # ── Immediate success (no MFA) ──
            if "access_token" in data:
                token = f"{data.get('token_type', 'Bearer')} {data['access_token']}"
                _rh_update_session("Authorization", token)
                _rh_set_login_state(True)
                return {"status": "authenticated", **data}

            # ── New verification-workflow flow ──
            if "verification_workflow" in data:
                workflow_id = data["verification_workflow"]["id"]

                machine_data = _rh_post(
                    url=_PATHFINDER_URL,
                    payload={
                        "device_id": device_token,
                        "flow": "suv",
                        "input": {"workflow_id": workflow_id},
                    },
                    json=True,
                )

                if not machine_data or "id" not in machine_data:
                    return {"_error": "Failed to initialize verification. Please try again."}

                machine_id = machine_data["id"]
                inq_url = _INQUIRIES_URL.format(mid=machine_id)

                challenge_info = None
                t0 = _time.time()
                while _time.time() - t0 < 30:
                    _time.sleep(3)
                    resp = _rh_get(inq_url)
                    if (resp
                            and "context" in resp
                            and "sheriff_challenge" in resp["context"]):
                        c = resp["context"]["sheriff_challenge"]
                        challenge_info = {
                            "type": c["type"],
                            "status": c["status"],
                            "id": c["id"],
                        }
                        break

                if not challenge_info:
                    return {"_error": "Timed out waiting for verification challenge."}

                return {
                    "status": "mfa_required",
                    "challenge": challenge_info,
                    "device_token": device_token,
                    "payload": payload,
                    "machine_id": machine_id,
                    "workflow_id": workflow_id,
                }

            # ── Legacy TOTP (mfa_required) ──
            if "mfa_required" in data:
                return {
                    "status": "mfa_required_totp",
                    "device_token": device_token,
                    "payload": payload,
                }

            detail = data.get("detail", "Login failed — check your credentials.")
            return {"_error": str(detail)}

        logger.info("Robinhood login initiated",
                     extra={"event": "rh_initiate", "user_id": user_id})

        result = await asyncio.get_event_loop().run_in_executor(None, _step1)

        if "_error" in result:
            raise BrokerAuthenticationError(
                result["_error"], details={"broker": "robinhood"})

        if result["status"] == "authenticated":
            logger.info("Robinhood login OK (no MFA)",
                         extra={"event": "rh_auth_ok"})
            return {
                "status": "authenticated",
                "access_token": result["access_token"],
                "refresh_token": result.get("refresh_token", ""),
            }

        if result["status"] == "mfa_required":
            ch = result["challenge"]
            _pending_challenges[user_id] = {
                "flow": "verification_workflow",
                "device_token": result["device_token"],
                "payload": result["payload"],
                "machine_id": result["machine_id"],
                "workflow_id": result["workflow_id"],
                "challenge_type": ch["type"],
                "challenge_id": ch["id"],
                "created_at": datetime.now(timezone.utc),
            }
            logger.info("Robinhood MFA required",
                         extra={"event": "rh_mfa", "type": ch["type"]})
            return {"status": "mfa_required", "mfa_type": ch["type"]}

        if result["status"] == "mfa_required_totp":
            _pending_challenges[user_id] = {
                "flow": "totp",
                "device_token": result["device_token"],
                "payload": result["payload"],
                "created_at": datetime.now(timezone.utc),
            }
            logger.info("Robinhood TOTP MFA required",
                         extra={"event": "rh_mfa_totp"})
            return {"status": "mfa_required", "mfa_type": "app"}

        raise BrokerAuthenticationError(
            "Unexpected login response.", details={"broker": "robinhood"})

    @staticmethod
    async def complete_mfa(user_id: int, mfa_code: str) -> dict:
        """
        Step 2: Complete the pending challenge, finalize the workflow,
        and retry the login to obtain an access token.
        """
        state = _pending_challenges.pop(user_id, None)
        if not state:
            raise BrokerAuthenticationError(
                "No pending MFA challenge. Please start the login process again.",
                details={"broker": "robinhood"})

        if datetime.now(timezone.utc) - state["created_at"] > _CHALLENGE_TTL:
            raise BrokerAuthenticationError(
                "MFA challenge expired. Please start the login process again.",
                details={"broker": "robinhood"})

        def _step2():
            flow = state.get("flow", "verification_workflow")

            # ── Legacy TOTP path ──
            if flow == "totp":
                payload = {**state["payload"], "mfa_code": mfa_code}
                data = _rh_post(_rh_login_url(), payload)
                if data and "access_token" in data:
                    token = f"{data.get('token_type', 'Bearer')} {data['access_token']}"
                    _rh_update_session("Authorization", token)
                    _rh_set_login_state(True)
                    return data
                return {"_error": "Invalid authenticator code. Please try again."}

            # ── New verification-workflow path ──
            challenge_type = state["challenge_type"]
            challenge_id = state["challenge_id"]
            machine_id = state["machine_id"]

            # 4a. SMS / email → submit the code
            if challenge_type in ("sms", "email"):
                resp = _rh_post(
                    url=_CHALLENGE_URL.format(cid=challenge_id),
                    payload={"response": mfa_code},
                )
                if not resp or resp.get("status") != "validated":
                    return {"_retry": True,
                            "_error": "Invalid verification code. Please try again."}

            # 4b. Push notification → poll until approved (30s window)
            elif challenge_type == "prompt":
                push_url = _PUSH_URL.format(cid=challenge_id)
                validated = False
                t0 = _time.time()
                while _time.time() - t0 < 30:
                    r = _rh_get(url=push_url)
                    if r and r.get("challenge_status") == "validated":
                        validated = True
                        break
                    _time.sleep(2)
                if not validated:
                    return {"_retry": True,
                            "_error": "Push notification was not approved in time. Please try again."}

            # 5. Finalize the workflow
            inq_url = _INQUIRIES_URL.format(mid=machine_id)
            approved = False
            t0 = _time.time()
            while _time.time() - t0 < 30:
                r = _rh_post(
                    url=inq_url,
                    payload={"sequence": 0, "user_input": {"status": "continue"}},
                    json=True,
                )
                if r:
                    tc = r.get("type_context", {})
                    if tc.get("result") == "workflow_status_approved":
                        approved = True
                        break
                    ws = r.get("verification_workflow", {}).get("workflow_status")
                    if ws == "workflow_status_approved":
                        approved = True
                        break
                _time.sleep(3)

            if not approved:
                return {"_error": "Workflow approval timed out. Please try again."}

            # 6. Retry login → should now return access_token
            data = _rh_post(_rh_login_url(), state["payload"])

            if data and "access_token" in data:
                token = f"{data.get('token_type', 'Bearer')} {data['access_token']}"
                _rh_update_session("Authorization", token)
                _rh_set_login_state(True)
                return data

            return {"_error": "Login failed after verification. Please start over."}

        logger.info("Robinhood MFA completion started",
                     extra={"event": "rh_mfa_complete", "user_id": user_id})

        result = await asyncio.get_event_loop().run_in_executor(None, _step2)

        if result.get("_retry"):
            state["created_at"] = datetime.now(timezone.utc)
            _pending_challenges[user_id] = state
            raise BrokerAuthenticationError(
                result["_error"], details={"broker": "robinhood"})

        if "_error" in result:
            raise BrokerAuthenticationError(
                result["_error"], details={"broker": "robinhood"})

        logger.info("Robinhood MFA completed",
                     extra={"event": "rh_mfa_ok", "user_id": user_id})
        return {
            "status": "connected",
            "access_token": result["access_token"],
            "refresh_token": result.get("refresh_token", ""),
        }

    # ────────────── Legacy single-step authenticate ──────────────

    async def authenticate(self, credentials: dict) -> dict:
        username = credentials.get("username")
        password = credentials.get("password")
        mfa_code = credentials.get("mfa_code")
        device_token = credentials.get("device_token")

        if not username or not password:
            raise BrokerAuthenticationError(
                "Username and password are required",
                details={"broker": "robinhood"})

        logger.info("Robinhood authentication started",
                     extra={"event": "auth_start", "broker": "robinhood"})

        try:
            login_kwargs = {
                "username": username,
                "password": password,
                "expiresIn": 86400,
                "store_session": False,
            }
            if mfa_code:
                login_kwargs["mfa_code"] = mfa_code
            if device_token:
                login_kwargs["device_token"] = device_token

            login_result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: rh.login(**login_kwargs)),
                timeout=TIMEOUT_SECONDS,
            )

            if not login_result or "access_token" not in login_result:
                raise BrokerAuthenticationError(
                    "Robinhood login failed — invalid credentials or MFA required.",
                    details={"broker": "robinhood"})

            self._connected = True
            self._username = username

            return {
                "status": "connected",
                "broker": "robinhood",
                "access_token": login_result.get("access_token", ""),
                "refresh_token": login_result.get("refresh_token", ""),
                "expires_in": login_result.get("expires_in", 86400),
            }

        except asyncio.TimeoutError:
            raise BrokerTimeoutError(
                "Robinhood authentication timed out",
                details={"broker": "robinhood", "timeout_seconds": TIMEOUT_SECONDS})
        except BrokerAuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Robinhood authentication error: {e}",
                         extra={"event": "auth_error", "broker": "robinhood"})
            raise BrokerAuthenticationError(
                f"Robinhood authentication failed: {e}",
                details={"broker": "robinhood"})

    def set_access_token(self, access_token: str):
        """Bootstrap robin_stocks session with an existing token for data fetching."""
        rh.authentication.SESSION.headers["Authorization"] = f"Bearer {access_token}"
        self._connected = True

    # ────────────── Data fetching ──────────────

    async def get_positions(self) -> list[PositionData]:
        self._ensure_connected()
        positions: list[PositionData] = []

        try:
            stock_positions = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: rh.account.build_holdings()),
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
                        logger.warning(f"Skipping malformed position for {symbol}: {e}")
                        continue

            logger.info(f"Retrieved {len(positions)} positions from Robinhood",
                        extra={"event": "positions_fetched", "broker": "robinhood",
                               "count": len(positions)})

        except asyncio.TimeoutError:
            raise BrokerTimeoutError("Timed out fetching positions from Robinhood")
        except (BrokerTimeoutError, BrokerConnectionError):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            raise BrokerConnectionError(f"Failed to fetch Robinhood positions: {e}")

        try:
            crypto_positions = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: rh.crypto.get_crypto_positions()),
                timeout=TIMEOUT_SECONDS,
            )
            if crypto_positions:
                for crypto in crypto_positions:
                    try:
                        quantity = float(crypto.get("quantity", 0))
                        if quantity <= 0:
                            continue
                        cost_bases = crypto.get("cost_bases", [{}])
                        avg_cost = (float(cost_bases[0].get("direct_cost_basis", 0))
                                    / quantity if quantity else 0)
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
            logger.warning(f"Crypto positions fetch failed (non-critical): {e}")

        return positions

    async def get_transactions(self, limit: int = 100) -> list[TransactionData]:
        self._ensure_connected()
        transactions: list[TransactionData] = []

        try:
            orders = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: rh.orders.get_all_stock_orders()),
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
                            None,
                            lambda url=instrument_url: rh.stocks.get_instrument_by_url(url),
                        )
                        symbol = (instrument_data.get("symbol", "UNKNOWN")
                                  if instrument_data else "UNKNOWN")
                    side = order.get("side", "buy")
                    quantity = float(order.get("quantity", 0))
                    avg_price = float(order.get("average_price", 0) or 0)
                    total = quantity * avg_price
                    fees = float(order.get("fees", 0) or 0)
                    executed_at_str = (order.get("last_transaction_at")
                                       or order.get("updated_at", ""))
                    try:
                        executed_at = datetime.fromisoformat(
                            executed_at_str.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        executed_at = datetime.now(timezone.utc)
                    transactions.append(TransactionData(
                        symbol=symbol, transaction_type=side, quantity=quantity,
                        price=avg_price, total_amount=total, fees=fees,
                        executed_at=executed_at,
                    ))
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping malformed order: {e}")
                    continue

            logger.info(
                f"Retrieved {len(transactions)} transactions from Robinhood",
                extra={"event": "transactions_fetched", "broker": "robinhood",
                       "count": len(transactions)})

        except asyncio.TimeoutError:
            raise BrokerTimeoutError(
                "Timed out fetching transactions from Robinhood")
        except (BrokerTimeoutError, BrokerConnectionError):
            raise
        except Exception as e:
            raise BrokerConnectionError(
                f"Failed to fetch Robinhood transactions: {e}")

        return transactions

    async def get_cash_balance(self) -> float:
        self._ensure_connected()
        try:
            profile = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: rh.profiles.load_account_profile()),
                timeout=TIMEOUT_SECONDS,
            )
            if not profile:
                raise BrokerConnectionError("Empty account profile returned")
            return float(profile.get("cash", 0) or 0)
        except asyncio.TimeoutError:
            raise BrokerTimeoutError("Timed out fetching cash balance")
        except (BrokerTimeoutError, BrokerConnectionError):
            raise
        except Exception as e:
            raise BrokerConnectionError(
                f"Failed to fetch Robinhood cash balance: {e}")

    async def get_account_summary(self) -> AccountSummary:
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
                    None, lambda: rh.profiles.load_account_profile()),
                timeout=TIMEOUT_SECONDS,
            )
            buying_power = (float(profile.get("buying_power", 0) or 0)
                            if profile else cash)
            return AccountSummary(
                total_value=total_value, cash_balance=cash,
                positions_count=len(positions), buying_power=buying_power,
                total_realized_gains=total_realized,
                total_unrealized_gains=total_unrealized,
            )
        except (BrokerTimeoutError, BrokerConnectionError):
            raise
        except Exception as e:
            raise BrokerConnectionError(
                f"Failed to build Robinhood account summary: {e}")

    async def disconnect(self) -> bool:
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: rh.logout())
            self._connected = False
            self._username = None
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
                details={"broker": "robinhood"})
