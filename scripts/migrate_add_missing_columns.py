"""
One-time migration: add columns introduced during the security hardening pass
that do not yet exist in the live database.

Safe to run multiple times  -  each ALTER uses IF NOT EXISTS.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.database.engine import async_engine


MIGRATIONS = [
    # JWT stateless revocation (token_version bump on logout / password reset)
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0",
    # Password reset tokens (hashed, never plaintext)
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_expires_at TIMESTAMPTZ",
    # Indexes introduced for query performance
    "CREATE INDEX IF NOT EXISTS ix_users_password_reset_token ON users (password_reset_token)",
    "CREATE INDEX IF NOT EXISTS ix_broker_connections_user_id ON broker_connections (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_positions_broker_connection_id ON positions (broker_connection_id)",
    "CREATE INDEX IF NOT EXISTS ix_transactions_broker_connection_id ON transactions (broker_connection_id)",
    "CREATE INDEX IF NOT EXISTS ix_transactions_executed_at ON transactions (executed_at)",
    "CREATE INDEX IF NOT EXISTS ix_portfolio_snapshots_broker_connection_id ON portfolio_snapshots (broker_connection_id)",
    "CREATE INDEX IF NOT EXISTS ix_chat_sessions_updated_at ON chat_sessions (updated_at)",
]


async def run():
    async with async_engine.begin() as conn:
        for sql in MIGRATIONS:
            print(f"  Running: {sql[:80]}...")
            await conn.execute(text(sql))
    print("\nAll migrations applied successfully.")


if __name__ == "__main__":
    asyncio.run(run())
