"""
Alembic migration environment for CognitoAI Engine pharmaceutical platform.

Manages database schema migrations for comprehensive pharmaceutical
intelligence system with audit trail and regulatory compliance support.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os
from pathlib import Path

# Add the src directory to the path so we can import our models
sys.path.append(str(Path(__file__).parent.parent))

from src.database.models import Base
from src.database.connection import get_database_url as get_db_url

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for migrations
target_metadata = Base.metadata

def get_database_url() -> str:
    """
    Get database URL for migrations.

    Converts async URL to sync URL for Alembic.
    """
    # Try to get from environment first
    url = os.getenv('DATABASE_URL')
    if url:
        # Convert async to sync URL
        if 'asyncpg' in url:
            url = url.replace('postgresql+asyncpg://', 'postgresql://')
        return url

    # Fallback to getting from connection module
    try:
        url = get_db_url()
        # Convert async to sync URL
        if 'asyncpg' in url:
            url = url.replace('postgresql+asyncpg://', 'postgresql://')
        return url
    except:
        # If all else fails, build a default URL
        return "postgresql://cognito:cognito@localhost:5432/cognito_pharma"

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

# Run migrations
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()