"""SQLAlchemy ORM models for users, broker connections, and portfolio data.

Defines schema and relationships consumed by repositories and API layers.
Keep migrations/schema changes aligned with broker sync and auth flows.

Added: 2026-04-03
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Enum,
    Text,
    JSON,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.database.engine import Base


def utcnow():
    # SQLAlchemy defaults alone do not attach timezone info; UTC-aware values avoid naive/aware bugs.
    return datetime.now(timezone.utc)


class BrokerType(str, enum.Enum):
    ROBINHOOD = "robinhood"
    PLAID = "plaid"
    CSV = "csv"


class ConnectionStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    EXPIRED = "expired"


class AssetType(str, enum.Enum):
    STOCK = "stock"
    ETF = "etf"
    CRYPTO = "crypto"
    OPTION = "option"
    MUTUAL_FUND = "mutual_fund"
    BOND = "bond"
    CASH = "cash"


class TransactionType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    TRANSFER = "transfer"
    INTEREST = "interest"
    FEE = "fee"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    # Stores the *hashed* 6-digit OTP from email verification, not the plaintext code.
    email_verification_token = Column(String(255), nullable=True, index=True)
    email_verification_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # cascade="all, delete-orphan": deleting a user removes dependent rows (GDPR-style cleanup path).
    broker_connections = relationship(
        "BrokerConnection", back_populates="user", cascade="all, delete-orphan"
    )
    positions = relationship(
        "Position", back_populates="user", cascade="all, delete-orphan"
    )
    transactions = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    portfolio_snapshots = relationship(
        "PortfolioSnapshot", back_populates="user", cascade="all, delete-orphan"
    )


class BrokerConnection(Base):
    __tablename__ = "broker_connections"
    # One row per (user, broker_type) — prevents duplicate connections for the same integration.
    __table_args__ = (
        UniqueConstraint("user_id", "broker_type", name="uq_user_broker"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    broker_type = Column(Enum(BrokerType), nullable=False)
    status = Column(Enum(ConnectionStatus), default=ConnectionStatus.PENDING)
    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_error_message = Column(Text, nullable=True)
    # Python name metadata_ maps to DB column "metadata" — avoids shadowing SQLAlchemy's reserved ``metadata``.
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="broker_connections")
    positions = relationship(
        "Position", back_populates="broker_connection", cascade="all, delete-orphan"
    )
    transactions = relationship(
        "Transaction", back_populates="broker_connection", cascade="all, delete-orphan"
    )
    portfolio_snapshots = relationship(
        "PortfolioSnapshot",
        back_populates="broker_connection",
        cascade="all, delete-orphan",
    )


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    broker_connection_id = Column(
        Integer, ForeignKey("broker_connections.id", ondelete="CASCADE"), nullable=False
    )
    symbol = Column(String(20), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    quantity = Column(Float, nullable=False)
    average_cost = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    purchase_date = Column(DateTime(timezone=True), nullable=True)
    realized_gains = Column(Float, default=0.0)
    unrealized_gains = Column(Float, default=0.0)
    asset_type = Column(Enum(AssetType), default=AssetType.STOCK)
    sector = Column(String(100), nullable=True)
    currency = Column(String(10), default="USD")
    total_amount_invested = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="positions")
    broker_connection = relationship("BrokerConnection", back_populates="positions")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    broker_connection_id = Column(
        Integer, ForeignKey("broker_connections.id", ondelete="CASCADE"), nullable=False
    )
    symbol = Column(String(20), nullable=False, index=True)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    fees = Column(Float, default=0.0)
    executed_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="transactions")
    broker_connection = relationship("BrokerConnection", back_populates="transactions")


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    broker_connection_id = Column(
        Integer, ForeignKey("broker_connections.id", ondelete="CASCADE"), nullable=False
    )
    total_value = Column(Float, nullable=False)
    cash_balance = Column(Float, default=0.0)
    positions_data = Column(JSON, nullable=False)
    captured_at = Column(DateTime(timezone=True), default=utcnow)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="portfolio_snapshots")
    broker_connection = relationship(
        "BrokerConnection", back_populates="portfolio_snapshots"
    )
