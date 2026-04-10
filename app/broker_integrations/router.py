"""
HTTP API for broker connect/disconnect, Plaid link token, CSV import, and read models.

``_api_response`` is the shared envelope (status/data/error/timestamp) expected by client code.
Connect/disconnect/sync and Plaid link-token handlers catch ``AppException`` and re-raise as
``HTTPException`` so broker-layer errors surface with consistent HTTP status and ``detail``.

Added: 2026-04-03
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import get_current_user
from app.broker_integrations.schemas import (
    RobinhoodConnectRequest,
    RobinhoodInitiateRequest,
    RobinhoodMFARequest,
    RobinhoodInitiateResponse,
    PlaidPublicTokenRequest,
    CSVUploadRequest,
    BrokerConnectionResponse,
    PositionResponse,
    TransactionResponse,
    AccountSummaryResponse,
    SyncStatusResponse,
    PlaidLinkTokenResponse,
    CSVTemplateResponse,
    AllocationHolding,
    AllocationBreakdown,
    AllocationResponse,
    APIResponse,
)
from app.broker_integrations.service import BrokerService
from app.broker_integrations.plaid_adapter import PlaidAdapter
from app.broker_integrations.csv_adapter import CSVImportAdapter
from app.database.engine import get_async_session
from app.database.models import User
from app.utils.exceptions import AppException
from app.utils.logging import get_logger

logger = get_logger("broker_integrations.router")

router = APIRouter(prefix="/broker", tags=["Broker Connections"])


def _api_response(data=None, error=None, status_val="success"):
    """Uniform success payload for mutating broker routes (team API contract)."""
    return {
        "status": status_val,
        "data": data,
        "error_message": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ──────────────────────────────── Connection Endpoints ────────────────────────────────


@router.post("/connect/robinhood", response_model=APIResponse)
async def connect_robinhood(
    payload: RobinhoodConnectRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Connect a Robinhood account via OAuth (username/password + optional MFA)."""
    try:
        service = BrokerService(session)
        connection = await service.connect_robinhood(
            user=current_user,
            credentials=payload.model_dump(),
        )
        return _api_response(
            data={
                "connection_id": connection.id,
                "broker_type": connection.broker_type.value,
                "status": connection.status.value,
            }
        )
    except AppException as e:
        logger.error(f"Robinhood connect failed: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/connect/robinhood/initiate", response_model=RobinhoodInitiateResponse)
async def initiate_robinhood(
    payload: RobinhoodInitiateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Step 1: Send credentials to Robinhood. Returns MFA challenge info or immediate auth."""
    try:
        from app.broker_integrations.robinhood_adapter import RobinhoodAdapter

        result = await RobinhoodAdapter.initiate_login(
            user_id=current_user.id,
            username=payload.username,
            password=payload.password,
        )

        if result["status"] == "authenticated":
            # No MFA needed — complete the connection immediately
            service = BrokerService(session)
            connection = await service.connect_robinhood_with_tokens(
                user=current_user,
                access_token=result["access_token"],
                refresh_token=result.get("refresh_token", ""),
            )
            return RobinhoodInitiateResponse(
                status="authenticated",
                data={
                    "connection_id": connection.id,
                    "broker_type": connection.broker_type.value,
                    "connection_status": connection.status.value,
                },
            )

        return RobinhoodInitiateResponse(
            status="mfa_required",
            mfa_type=result.get("mfa_type"),
        )

    except AppException as e:
        logger.error(f"Robinhood initiate failed: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/connect/robinhood/complete-mfa", response_model=APIResponse)
async def complete_robinhood_mfa(
    payload: RobinhoodMFARequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Step 2: Complete MFA with the code the user received (SMS or authenticator app)."""
    try:
        from app.broker_integrations.robinhood_adapter import RobinhoodAdapter

        result = await RobinhoodAdapter.complete_mfa(
            user_id=current_user.id,
            mfa_code=payload.mfa_code,
        )

        service = BrokerService(session)
        connection = await service.connect_robinhood_with_tokens(
            user=current_user,
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token", ""),
        )
        return _api_response(data={
            "connection_id": connection.id,
            "broker_type": connection.broker_type.value,
            "status": connection.status.value,
        })

    except AppException as e:
        logger.error(f"Robinhood MFA failed: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/connect/plaid/link-token", response_model=PlaidLinkTokenResponse)
async def create_plaid_link_token(
    current_user: User = Depends(get_current_user),
):
    """Generate a Plaid Link token for the frontend to initiate account linking."""
    try:
        adapter = PlaidAdapter()
        link_token = await adapter.create_link_token(user_id=str(current_user.id))
        return PlaidLinkTokenResponse(link_token=link_token)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/connect/plaid", response_model=APIResponse)
async def connect_plaid(
    payload: PlaidPublicTokenRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Exchange a Plaid public_token and connect the investment account."""
    try:
        service = BrokerService(session)
        connection = await service.connect_plaid(
            user=current_user,
            public_token=payload.public_token,
        )
        return _api_response(
            data={
                "connection_id": connection.id,
                "broker_type": connection.broker_type.value,
                "status": connection.status.value,
            }
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/connect/csv", response_model=APIResponse)
async def connect_csv(
    payload: CSVUploadRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Import portfolio data from a CSV file."""
    try:
        service = BrokerService(session)
        connection = await service.connect_csv(
            user=current_user,
            csv_content=payload.csv_content,
            cash_balance=payload.cash_balance,
            filename=payload.filename,
        )
        return _api_response(
            data={
                "connection_id": connection.id,
                "broker_type": connection.broker_type.value,
                "status": connection.status.value,
            }
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/csv/template", response_model=CSVTemplateResponse)
async def get_csv_template():
    """Download a sample CSV template for portfolio import."""
    return CSVTemplateResponse(
        template=CSVImportAdapter.get_sample_template(),
        columns=[
            "symbol",
            "name",
            "quantity",
            "average_cost",
            "current_price",
            "purchase_date",
            "realized_gains",
            "unrealized_gains",
            "asset_type",
            "sector",
        ],
        required_columns=["symbol", "quantity", "average_cost"],
    )


# ──────────────────────────────── Connection Management ────────────────────────────────


@router.get("/connections", response_model=list[BrokerConnectionResponse])
async def list_connections(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List all broker connections for the authenticated user."""
    service = BrokerService(session)
    connections = await service.get_connections(current_user)
    return [
        BrokerConnectionResponse(
            id=c.id,
            broker_type=c.broker_type.value,
            status=c.status.value,
            last_sync_at=c.last_sync_at,
            created_at=c.created_at,
        )
        for c in connections
    ]


@router.post("/connections/{connection_id}/disconnect", response_model=APIResponse)
async def disconnect_broker(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Disconnect a broker connection and clear stored tokens. Keeps imported data."""
    try:
        service = BrokerService(session)
        await service.disconnect_broker(current_user, connection_id)
        return _api_response(
            data={"disconnected": True, "connection_id": connection_id}
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/connections/{connection_id}", response_model=APIResponse)
async def delete_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Permanently delete a broker connection and all associated data."""
    try:
        service = BrokerService(session)
        await service.delete_connection(current_user, connection_id)
        return _api_response(data={"deleted": True, "connection_id": connection_id})
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/connections/{connection_id}/sync", response_model=SyncStatusResponse)
async def sync_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Re-sync portfolio data from a connected broker."""
    try:
        service = BrokerService(session)
        connection = await service.sync_connection(current_user, connection_id)
        positions = await service.get_positions(current_user, connection_id)
        return SyncStatusResponse(
            broker_type=connection.broker_type.value,
            status=connection.status.value,
            last_sync_at=connection.last_sync_at,
            positions_count=len(positions),
        )
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# ──────────────────────────────── Portfolio Data ────────────────────────────────


@router.get("/positions", response_model=list[PositionResponse])
async def get_positions(
    connection_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get all positions across connected brokers, or filtered by connection."""
    service = BrokerService(session)
    positions = await service.get_positions(current_user, connection_id)

    total_value = sum(p.quantity * (p.current_price or 0) for p in positions)

    return [
        PositionResponse(
            symbol=p.symbol,
            name=p.name or p.symbol,
            quantity=p.quantity,
            average_cost=p.average_cost,
            current_price=p.current_price or 0,
            purchase_date=p.purchase_date,
            realized_gains=p.realized_gains or 0,
            unrealized_gains=p.unrealized_gains or 0,
            asset_type=p.asset_type.value if p.asset_type else "stock",
            sector=p.sector,
            currency=p.currency or "USD",
            total_amount_invested=p.total_amount_invested or 0,
            market_value=p.quantity * (p.current_price or 0),
            weight_percent=(
                round((p.quantity * (p.current_price or 0)) / total_value * 100, 2)
                if total_value > 0
                else 0
            ),
        )
        for p in positions
    ]


@router.get("/transactions", response_model=list[TransactionResponse])
async def get_transactions(
    connection_id: Optional[int] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get transaction history across connected brokers."""
    service = BrokerService(session)
    transactions = await service.get_transactions(current_user, connection_id, limit)

    return [
        TransactionResponse(
            symbol=t.symbol,
            transaction_type=t.transaction_type.value if t.transaction_type else "buy",
            quantity=t.quantity,
            price=t.price,
            total_amount=t.total_amount,
            fees=t.fees or 0,
            executed_at=t.executed_at,
        )
        for t in transactions
    ]


@router.get("/summary", response_model=AccountSummaryResponse)
async def get_account_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get aggregated account summary across all connected brokers."""
    service = BrokerService(session)
    positions = await service.get_positions(current_user)

    total_equity = sum(p.quantity * (p.current_price or 0) for p in positions)
    total_unrealized = sum(p.unrealized_gains or 0 for p in positions)
    total_realized = sum(p.realized_gains or 0 for p in positions)

    connections = await service.get_connections(current_user)
    # Cash balance would be stored in portfolio snapshots — simplified here
    cash_balance = 0.0

    return AccountSummaryResponse(
        total_value=total_equity + cash_balance,
        cash_balance=cash_balance,
        positions_count=len(positions),
        buying_power=cash_balance,
        total_realized_gains=total_realized,
        total_unrealized_gains=total_unrealized,
    )


@router.get("/allocation", response_model=AllocationResponse)
async def get_allocation(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Compute portfolio allocation by sector, asset class, geography, market cap, and risk level."""
    from collections import defaultdict
    from app.utils.symbol_enrichment import get_symbol_profile, classify_risk_bucket

    service = BrokerService(session)
    positions = await service.get_positions(current_user)

    if not positions:
        empty: list[AllocationBreakdown] = []
        return AllocationResponse(
            total_value=0,
            by_sector=empty,
            by_asset_class=empty,
            by_geography=empty,
            by_market_cap=empty,
            by_risk_level=empty,
        )

    sector_val: dict[str, float] = defaultdict(float)
    asset_val: dict[str, float] = defaultdict(float)
    geo_val: dict[str, float] = defaultdict(float)
    cap_val: dict[str, float] = defaultdict(float)
    risk_val: dict[str, float] = defaultdict(float)

    sector_hold: dict[str, list] = defaultdict(list)
    asset_hold: dict[str, list] = defaultdict(list)
    geo_hold: dict[str, list] = defaultdict(list)
    cap_hold: dict[str, list] = defaultdict(list)
    risk_hold: dict[str, list] = defaultdict(list)

    total_value = 0.0

    for pos in positions:
        mv = pos.quantity * (pos.current_price or 0)
        if mv <= 0:
            continue
        total_value += mv

        asset_type_str = pos.asset_type.value if pos.asset_type else "stock"

        profile = await get_symbol_profile(
            symbol=pos.symbol,
            asset_type=asset_type_str,
            session=session,
        )

        holding_info = (pos.symbol, pos.name or pos.symbol, asset_type_str, mv)

        sector_label = pos.sector or profile.sector
        sector_val[sector_label] += mv
        sector_hold[sector_label].append(holding_info)

        asset_key = asset_type_str.upper()
        asset_val[asset_key] += mv
        asset_hold[asset_key].append(holding_info)

        geo_val[profile.country] += mv
        geo_hold[profile.country].append(holding_info)

        cap_val[profile.market_cap_category] += mv
        cap_hold[profile.market_cap_category].append(holding_info)

        risk_key = classify_risk_bucket(sector_label)
        risk_val[risk_key] += mv
        risk_hold[risk_key].append(holding_info)

    def _to_breakdown(
        val_map: dict[str, float],
        hold_map: dict[str, list],
    ) -> list[AllocationBreakdown]:
        items = sorted(val_map.items(), key=lambda x: x[1], reverse=True)
        result = []
        for label, val in items:
            bucket_total = val if val > 0 else 1
            holdings = sorted(hold_map[label], key=lambda h: h[3], reverse=True)
            result.append(AllocationBreakdown(
                label=label,
                value=round(val, 2),
                percent=round(val / total_value * 100, 2) if total_value > 0 else 0,
                holdings=[
                    AllocationHolding(
                        symbol=sym,
                        name=name,
                        asset_type=at,
                        market_value=round(hmv, 2),
                        percent=round(hmv / bucket_total * 100, 2),
                    )
                    for sym, name, at, hmv in holdings
                ],
            ))
        return result

    return AllocationResponse(
        total_value=round(total_value, 2),
        by_sector=_to_breakdown(sector_val, sector_hold),
        by_asset_class=_to_breakdown(asset_val, asset_hold),
        by_geography=_to_breakdown(geo_val, geo_hold),
        by_market_cap=_to_breakdown(cap_val, cap_hold),
        by_risk_level=_to_breakdown(risk_val, risk_hold),
    )
