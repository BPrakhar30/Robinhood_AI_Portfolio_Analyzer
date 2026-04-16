from fastapi import APIRouter, Depends, Query

from app.auth.service import get_current_user
from app.database.models import User
from .service import fetch_market_news, fetch_earnings_calendar, fetch_earnings_for_date
from .schemas import (
    MarketSummaryResponse,
    RecentDevelopmentsResponse,
    EarningsCalendarResponse,
    EarningsListResponse,
)

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("/news")
async def get_market_news(current_user: User = Depends(get_current_user)):
    """Market summary headlines and recent development articles."""
    data = await fetch_market_news()
    return {
        "summary": {
            "headlines": data["headlines"],
            "updated_at": data["updated_at"],
        },
        "developments": {
            "articles": data["articles"],
            "updated_at": data["updated_at"],
        },
        "sources": data.get("sources", []),
    }


@router.get("/earnings/calendar", response_model=EarningsCalendarResponse)
async def get_earnings_calendar(
    date: str | None = Query(None, description="Center date YYYY-MM-DD; defaults to today"),
    current_user: User = Depends(get_current_user),
):
    """Weekly earnings calendar strip."""
    return await fetch_earnings_calendar(date)


@router.get("/earnings/date", response_model=EarningsListResponse)
async def get_earnings_for_date(
    date: str = Query(..., description="Date YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
):
    """Detailed earnings entries for a given date."""
    return await fetch_earnings_for_date(date)
