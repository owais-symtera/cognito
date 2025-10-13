"""
Database connection utility for CognitoAI Engine.

Provides centralized database connection management using environment variables.
"""
import os
import asyncpg
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


async def get_db_connection() -> asyncpg.Connection:
    """
    Get a database connection using environment variables.

    Reads database credentials from environment variables:
    - DATABASE_HOST or DB_HOST (default: localhost)
    - DATABASE_PORT or DB_PORT (default: 5432)
    - DATABASE_USER or DB_USER (default: cognito)
    - DATABASE_PASSWORD or DB_PASSWORD (default: password)
    - DATABASE_NAME or DB_NAME (default: cognito-engine)

    Returns:
        asyncpg.Connection: Database connection

    Raises:
        ConnectionError: If unable to connect to database
    """
    try:
        # Try both naming conventions for environment variables
        host = os.getenv('DATABASE_HOST') or os.getenv('DB_HOST', 'localhost')
        port = int(os.getenv('DATABASE_PORT') or os.getenv('DB_PORT', '5432'))
        user = os.getenv('DATABASE_USER') or os.getenv('DB_USER', 'cognito')
        password = os.getenv('DATABASE_PASSWORD') or os.getenv('DB_PASSWORD', 'password')
        database = os.getenv('DATABASE_NAME') or os.getenv('DB_NAME', 'cognito-engine')

        logger.info(f"Connecting to database: {database} at {host}:{port} as user {user}")

        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        raise ConnectionError(f"Database connection failed: {str(e)}")


class DatabaseConnection:
    """
    Context manager for database connections.

    Usage:
        async with DatabaseConnection() as conn:
            result = await conn.fetch("SELECT * FROM table")
    """

    def __init__(self):
        self.conn: Optional[asyncpg.Connection] = None

    async def __aenter__(self) -> asyncpg.Connection:
        self.conn = await get_db_connection()
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            await self.conn.close()
