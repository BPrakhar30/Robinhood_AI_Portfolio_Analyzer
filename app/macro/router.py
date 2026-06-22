"""Macro Pulse HTTP endpoints.

Provides macro indicator data, portfolio exposure analysis, and
AI-generated summaries connecting macro conditions to the user's
holdings.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import get_current_user
from app.database.engine import get_async_session
from app.database.models import Position, User

from .ai_service import generate_detailed_macro_summary, generate_macro_summary
from .schemas import MacroPulseResponse
from .service import build_macro_pulse

router = APIRouter(prefix="/macro", tags=["macro"])


@router.get("/pulse", response_model=MacroPulseResponse)
async def get_macro_pulse(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Macro Pulse dashboard: indicators + portfolio exposure + alerts.

    Fetches macro indicators (globally cached for 5 min), computes the
    signed-in user's portfolio exposure scores, generates alerts based
    on threshold crossings, and optionally attaches an AI summary.
    """
    stmt = select(Position).where(Position.user_id == current_user.id)
    rows = (await db.execute(stmt)).scalars().all()

    positions = [
        {
            "symbol": (p.symbol or "").upper(),
            "quantity": p.quantity or 0,
            "current_price": p.current_price or 0,
            "average_cost": p.average_cost or 0,
            "sector": getattr(p, "sector", None) or "",
            "asset_type": getattr(p, "asset_type", "stock"),
        }
        for p in rows
        if (p.quantity or 0) > 0
    ]

    payload = await build_macro_pulse(positions)

    # Run summaries sequentially  -  both call the same Gemini model and firing
    # them in parallel doubles the load, causing 503s under moderate traffic.
    ai_summary = await generate_macro_summary(
        payload["indicators"],
        payload["exposure"],
    )
    detailed_summary = await generate_detailed_macro_summary(
        payload["indicators"],
        payload["exposure"],
        positions,
    )
    payload["ai_summary"] = ai_summary
    payload["detailed_summary"] = detailed_summary

    return payload


@router.get("/alerts")
async def get_macro_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Lightweight endpoint returning only active macro alerts.

    Used by the dashboard to show/hide the macro alert banner without
    loading the full pulse payload.
    """
    stmt = select(Position).where(Position.user_id == current_user.id)
    rows = (await db.execute(stmt)).scalars().all()

    positions = [
        {
            "symbol": (p.symbol or "").upper(),
            "quantity": p.quantity or 0,
            "current_price": p.current_price or 0,
            "sector": getattr(p, "sector", None) or "",
        }
        for p in rows
        if (p.quantity or 0) > 0
    ]

    payload = await build_macro_pulse(positions)
    return {"alerts": payload["alerts"]}
