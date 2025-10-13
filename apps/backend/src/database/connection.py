"""
Database connection configuration for CognitoAI Engine.

Provides async database connection management for PostgreSQL with
comprehensive pharmaceutical audit trail and regulatory compliance support.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import os
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
import structlog

logger = structlog.get_logger(__name__)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models in CognitoAI Engine.

    Provides common configuration and metadata for pharmaceutical
    intelligence database models with audit trail support.

    Since:
        Version 1.0.0
    """
    pass


def get_database_url() -> str:
    """
    Get database connection URL from environment variables.

    Constructs PostgreSQL connection URL for pharmaceutical intelligence
    platform with proper async driver configuration.

    Returns:
        str: PostgreSQL async connection URL

    Raises:
        ValueError: If required database environment variables are missing

    Example:
        >>> url = get_database_url()
        >>> print(url)
        postgresql+asyncpg://user:pass@localhost:5432/cognito_ai_engine

    Since:
        Version 1.0.0
    """
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # Convert sync postgres:// to async postgresql+asyncpg://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return database_url

    # Build from individual components
    host = os.getenv("DATABASE_HOST", "localhost")
    port = os.getenv("DATABASE_PORT", "5432")
    name = os.getenv("DATABASE_NAME", "cognito_ai_engine")
    user = os.getenv("DATABASE_USER", "postgres")
    password = os.getenv("DATABASE_PASSWORD")

    if not password:
        raise ValueError("DATABASE_PASSWORD environment variable is required")

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


def create_engine() -> AsyncEngine:
    """
    Create async database engine for pharmaceutical intelligence platform.

    Configures PostgreSQL async engine with appropriate settings for
    pharmaceutical data processing and audit trail requirements.

    Returns:
        AsyncEngine: Configured SQLAlchemy async engine

    Note:
        Uses connection pooling optimized for pharmaceutical processing
        workloads with concurrent category processing.

    Since:
        Version 1.0.0
    """
    database_url = get_database_url()

    engine = create_async_engine(
        database_url,
        echo=os.getenv("DATABASE_DEBUG", "false").lower() == "true",
        pool_size=20,  # Support concurrent pharmaceutical category processing
        max_overflow=30,
        pool_timeout=30,
        pool_recycle=3600,  # Recycle connections every hour
        poolclass=NullPool if os.getenv("TESTING") else None,  # Disable pooling in tests
    )

    logger.info("Database engine created", url=database_url.split("@")[-1])  # Log without credentials
    return engine


# Global engine instance (lazy initialization)
engine: Optional[AsyncEngine] = None

# Session factory for dependency injection (will be initialized when engine is created)
AsyncSessionLocal: Optional[async_sessionmaker] = None

def get_engine() -> AsyncEngine:
    """Get or create the database engine."""
    global engine, AsyncSessionLocal
    if engine is None:
        engine = create_engine()
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )
    return engine


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to get database session.

    Provides async database session for pharmaceutical intelligence
    API endpoints with proper transaction management and audit support.

    Yields:
        AsyncSession: Database session for pharmaceutical operations

    Note:
        Automatically handles session lifecycle including rollback
        on exceptions for pharmaceutical data integrity.

    Example:
        >>> @app.post("/requests/")
        >>> async def create_request(
        ...     request_data: CreateDrugRequestSchema,
        ...     db: AsyncSession = Depends(get_db_session)
        ... ):
        ...     return await create_drug_request(db, request_data)

    Since:
        Version 1.0.0
    """
    get_engine()  # Ensure engine and session factory are initialized
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database session rolled back", error=str(e))
            raise
        finally:
            await session.close()


async def create_tables():
    """
    Create all database tables for pharmaceutical intelligence platform.

    Creates complete PostgreSQL schema including audit trails,
    process tracking, and pharmaceutical category configurations.

    Note:
        Used for testing and initial setup. Production deployments
        should use Alembic migrations for pharmaceutical compliance.

    Since:
        Version 1.0.0
    """
    from .models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("All database tables created for pharmaceutical intelligence platform")


async def drop_tables():
    """
    Drop all database tables.

    WARNING: This will permanently delete all pharmaceutical data
    including audit trails. Use only for testing.

    Since:
        Version 1.0.0
    """
    from .models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All database tables dropped - pharmaceutical data permanently deleted")