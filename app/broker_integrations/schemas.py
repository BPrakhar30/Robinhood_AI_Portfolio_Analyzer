"""
Pydantic IO models for broker endpoints: connect payloads, portfolio projections, and envelopes.

``CSVUploadRequest.csv_type`` is constrained to positions vs transactions via regex. ``APIResponse``
is the canonical wrapper for broker mutation endpoints.

Added: 2026-04-03
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RobinhoodConnectRequest(BaseModel):
    username: str
    password: str
    mfa_code: Optional[str] = None
    device_token: Optional[str] = None


class RobinhoodInitiateRequest(BaseModel):
    username: str
    password: str


class RobinhoodMFARequest(BaseModel):
    mfa_code: str = ""


class RobinhoodInitiateResponse(BaseModel):
    status: str  # "authenticated" | "mfa_required"
    mfa_type: Optional[str] = None  # "sms" | "app"
    data: Optional[dict] = None


class PlaidPublicTokenRequest(BaseModel):
    public_token: str


class CSVUploadRequest(BaseModel):
    csv_content: str
    cash_balance: float = 0.0
    filename: Optional[str] = "upload.csv"
    csv_type: str = Field(default="positions", pattern="^(positions|transactions)$")  # strict branch selector


class BrokerConnectionResponse(BaseModel):
    id: int
    broker_type: str
    status: str
    last_sync_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PositionResponse(BaseModel):
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
    total_amount_invested: float = 0.0
    market_value: float = 0.0
    weight_percent: float = 0.0


class TransactionResponse(BaseModel):
    symbol: str
    transaction_type: str
    quantity: float
    price: float
    total_amount: float
    fees: float = 0.0
    executed_at: datetime


class AccountSummaryResponse(BaseModel):
    total_value: float
    cash_balance: float
    positions_count: int
    buying_power: float = 0.0
    total_realized_gains: float = 0.0
    total_unrealized_gains: float = 0.0


class SyncStatusResponse(BaseModel):
    broker_type: str
    status: str
    last_sync_at: Optional[datetime] = None
    positions_count: int = 0
    error_message: Optional[str] = None


class PlaidLinkTokenResponse(BaseModel):
    link_token: str


class CSVTemplateResponse(BaseModel):
    template: str
    columns: list[str]
    required_columns: list[str]


class AllocationHolding(BaseModel):
    symbol: str
    name: str
    asset_type: str
    market_value: float
    percent: float


class AllocationBreakdown(BaseModel):
    label: str
    value: float
    percent: float
    holdings: list[AllocationHolding] = []


class AllocationResponse(BaseModel):
    total_value: float
    by_sector: list[AllocationBreakdown]
    by_asset_class: list[AllocationBreakdown]
    by_geography: list[AllocationBreakdown]
    by_market_cap: list[AllocationBreakdown]
    by_risk_level: list[AllocationBreakdown]


class APIResponse(BaseModel):
    """Standard API response wrapper per developer guidelines."""

    status: str
    data: Optional[dict] = None
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
