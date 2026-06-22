"""SQLAlchemy ORM models: users, broker connections, portfolio data, chat."""

import enum
import uuid
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
    Uuid,
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

    # UUIDv4 primary key  -  opaque, non-sequential, safe to expose in tokens and logs.
    # Generated client-side (Python) so we know the id before the INSERT returns.
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    # Stores an HMAC hash of the 6-digit OTP (never plaintext).
    email_verification_token = Column(String(255), nullable=True, index=True)
    email_verification_expires_at = Column(DateTime(timezone=True), nullable=True)
    # Stores an HMAC hash of the password reset token (never plaintext).
    password_reset_token = Column(String(255), nullable=True, index=True)
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)
    # Stateless JWT revocation version. Increment to invalidate all prior tokens.
    token_version = Column(Integer, nullable=False, default=0)
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
    chat_sessions = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )
    memory = relationship(
        "UserMemory", back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class BrokerConnection(Base):
    __tablename__ = "broker_connections"
    # One row per (user, broker_type)  -  prevents duplicate connections for the same integration.
    __table_args__ = (
        UniqueConstraint("user_id", "broker_type", name="uq_user_broker"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    broker_type = Column(Enum(BrokerType), nullable=False)
    status = Column(Enum(ConnectionStatus), default=ConnectionStatus.PENDING)
    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_error_message = Column(Text, nullable=True)
    # Python name metadata_ maps to DB column "metadata"  -  avoids shadowing SQLAlchemy's reserved ``metadata``.
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
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    broker_connection_id = Column(
        Integer, ForeignKey("broker_connections.id", ondelete="CASCADE"), nullable=False,
        index=True,
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
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    broker_connection_id = Column(
        Integer, ForeignKey("broker_connections.id", ondelete="CASCADE"), nullable=False,
        index=True,
    )
    symbol = Column(String(20), nullable=False, index=True)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    fees = Column(Float, default=0.0)
    executed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="transactions")
    broker_connection = relationship("BrokerConnection", back_populates="transactions")


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    broker_connection_id = Column(
        Integer, ForeignKey("broker_connections.id", ondelete="CASCADE"), nullable=False,
        index=True,
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


class ChatSession(Base):
    """A user's chat thread with the portfolio assistant.

    ``agent_history`` stores the serialized PydanticAI ``ModelMessage`` list
    (the agent's internal view of the conversation, including tool calls and
    responses). It is rewritten with ``result.all_messages_json()`` after every
    turn. ``ChatMessage`` rows are the UI-facing view  -  cheap to list without
    rehydrating the agent blob.
    """

    __tablename__ = "chat_sessions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False, default="New chat")
    starred = Column(Boolean, default=False, nullable=False)
    archived = Column(Boolean, default=False, nullable=False)
    # JSON on SQLAlchemy maps to JSONB on Postgres  -  structured, queryable.
    # Holds the output of ``result.all_messages_json()`` (a list of ModelMessage dicts).
    agent_history = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, index=True)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    """A single UI-facing message in a chat session.

    Role is the wire-level role (``user`` | ``assistant``). Tool usage is kept
    separately so the frontend can show provenance without parsing the agent
    blob.
    """

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False, default="")
    tools_used = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    session = relationship("ChatSession", back_populates="messages")


class UserMemory(Base):
    """Persistent cross-session memory for the AI portfolio assistant.

    Each user has at most one row. ``facts`` is a JSON array of short strings
    (≤ 25 items) extracted by the LLM from completed conversations  -  things
    like investment style, risk tolerance, goals, and frequently discussed
    tickers. They are injected into the system prompt of every future session
    so the assistant feels contextually aware across conversations.

    This intentionally uses a simple, auditable format (list of plain strings)
    rather than a vector embedding store so users can reason about what the
    assistant remembers about them.
    """

    __tablename__ = "user_memory"

    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    facts = Column(JSON, nullable=False, default=list)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="memory")


class SymbolMetadata(Base):
    """Persistent cache for Finnhub symbol profile lookups.

    Keyed by ticker symbol  -  only called once per symbol until the row
    goes stale (checked via ``updated_at``).
    """

    __tablename__ = "symbol_metadata"

    symbol = Column(String(20), primary_key=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    country = Column(String(60), nullable=True)
    market_cap = Column(Float, default=0.0)
    market_cap_category = Column(String(20), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
