"""
Portfolio engine API — health score and risk alerts.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import get_current_user
from app.database.engine import get_async_session
from app.database.models import User
from app.broker_integrations.service import BrokerService
from app.utils.symbol_enrichment import get_symbol_profile

from .health_score import compute_health_score
from .risk_detection import detect_all_risks
from .schemas import HealthScoreResponse, RiskAlertsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio-engine"])


async def _load_positions_with_profiles(
    user: User,
    session: AsyncSession,
) -> tuple[list[dict], dict[str, str]]:
    """Fetch positions and enrich with sector profiles."""
    service = BrokerService(session)
    positions = await service.get_positions(user)

    sector_profiles: dict[str, str] = {}
    result: list[dict] = []

    for p in positions:
        mv = p.quantity * (p.current_price or 0)
        asset_type_str = p.asset_type.value if p.asset_type else "stock"

        profile = await get_symbol_profile(
            symbol=p.symbol,
            asset_type=asset_type_str,
            session=session,
        )
        sector_profiles[p.symbol] = p.sector or profile.sector

        result.append({
            "symbol": p.symbol,
            "name": p.name or p.symbol,
            "quantity": p.quantity,
            "current_price": p.current_price or 0,
            "asset_type": asset_type_str,
            "sector": p.sector or profile.sector,
        })

    return result, sector_profiles


@router.get("/health-score", response_model=HealthScoreResponse)
async def get_health_score(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Compute the portfolio health score (0-100) with sub-scores."""
    positions, sector_profiles = await _load_positions_with_profiles(
        current_user, session
    )
    return compute_health_score(positions, sector_profiles)


@router.get("/alerts", response_model=RiskAlertsResponse)
async def get_risk_alerts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Detect portfolio risk alerts (sector overweight, concentration, ETF overlap)."""
    positions, sector_profiles = await _load_positions_with_profiles(
        current_user, session
    )
    return detect_all_risks(positions, sector_profiles)
