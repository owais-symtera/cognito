"""
Database configuration for CognitoAI Engine pharmaceutical intelligence platform.

Provides database settings, connection pool configuration, and
audit trail settings for pharmaceutical regulatory compliance.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import os
from typing import Dict, Any
from pydantic import BaseSettings, validator
import structlog

logger = structlog.get_logger(__name__)


class DatabaseConfig(BaseSettings):
    """
    Database configuration settings for pharmaceutical intelligence platform.

    Comprehensive database configuration including connection settings,
    audit trail configuration, and performance tuning for pharmaceutical
    data processing requirements.

    Attributes:
        database_url: Complete database connection URL
        database_host: Database server hostname
        database_port: Database server port
        database_name: Database name for pharmaceutical intelligence
        database_user: Database user with pharmaceutical data access
        database_password: Database password for secure connection
        database_debug: Enable SQLAlchemy query logging
        connection_pool_size: Connection pool size for concurrent processing
        connection_max_overflow: Maximum connection overflow
        connection_timeout: Connection timeout in seconds
        connection_recycle: Connection recycle interval in seconds
        audit_retention_years: Audit data retention period in years
        enable_query_logging: Enable database query performance logging
        enable_audit_triggers: Enable automatic audit trail triggers

    Since:
        Version 1.0.0
    """
    # Database Connection Settings
    database_url: str = None
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "cognito_ai_engine"
    database_user: str = "postgres"
    database_password: str = None

    # Development and Debugging
    database_debug: bool = False
    testing: bool = False

    # Connection Pool Configuration
    connection_pool_size: int = 20
    connection_max_overflow: int = 30
    connection_timeout: int = 30
    connection_recycle: int = 3600

    # Pharmaceutical Audit Trail Configuration
    audit_retention_years: int = 7
    enable_query_logging: bool = True
    enable_audit_triggers: bool = True
    audit_batch_size: int = 1000

    # Performance Configuration
    query_timeout: int = 300  # 5 minutes for pharmaceutical processing
    statement_timeout: int = 600  # 10 minutes for complex reports
    lock_timeout: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False

    @validator("database_url", pre=True, always=True)
    def build_database_url(cls, v, values):
        """
        Build database URL from components if not provided directly.

        Args:
            v: Current database_url value
            values: Dict of all configuration values

        Returns:
            str: Complete PostgreSQL connection URL

        Since:
            Version 1.0.0
        """
        if v:
            # Convert sync postgres:// to async postgresql+asyncpg://
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
            return v

        # Build from components
        password = values.get("database_password")
        if not password:
            raise ValueError("DATABASE_PASSWORD is required for pharmaceutical data security")

        user = values.get("database_user", "postgres")
        host = values.get("database_host", "localhost")
        port = values.get("database_port", 5432)
        name = values.get("database_name", "cognito_ai_engine")

        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"

    @validator("audit_retention_years")
    def validate_audit_retention(cls, v):
        """
        Validate audit retention period meets pharmaceutical requirements.

        Args:
            v: Audit retention years value

        Returns:
            int: Validated audit retention years

        Raises:
            ValueError: If retention period is less than 7 years

        Since:
            Version 1.0.0
        """
        if v < 7:
            raise ValueError("Pharmaceutical audit retention must be at least 7 years for regulatory compliance")
        return v

    @validator("connection_pool_size")
    def validate_pool_size(cls, v):
        """
        Validate connection pool size for pharmaceutical processing.

        Args:
            v: Connection pool size value

        Returns:
            int: Validated pool size

        Since:
            Version 1.0.0
        """
        if v < 10:
            logger.warning(f"Connection pool size {v} may be insufficient for pharmaceutical processing")
        return v

    def get_engine_config(self) -> Dict[str, Any]:
        """
        Get SQLAlchemy engine configuration for pharmaceutical platform.

        Returns complete engine configuration optimized for pharmaceutical
        intelligence processing with proper audit trail support.

        Returns:
            Dict[str, Any]: SQLAlchemy engine configuration

        Example:
            >>> config = DatabaseConfig()
            >>> engine_config = config.get_engine_config()
            >>> engine = create_async_engine(**engine_config)

        Since:
            Version 1.0.0
        """
        config = {
            "url": self.database_url,
            "echo": self.database_debug,
            "pool_size": self.connection_pool_size,
            "max_overflow": self.connection_max_overflow,
            "pool_timeout": self.connection_timeout,
            "pool_recycle": self.connection_recycle,
            "pool_pre_ping": True,  # Validate connections before use
            "connect_args": {
                "command_timeout": self.query_timeout,
                "server_settings": {
                    "application_name": "CognitoAI-Engine-Pharmaceutical",
                    "statement_timeout": str(self.statement_timeout * 1000),  # milliseconds
                    "lock_timeout": str(self.lock_timeout * 1000),  # milliseconds
                    "idle_in_transaction_session_timeout": "300000",  # 5 minutes
                }
            }
        }

        # Disable connection pooling in tests
        if self.testing:
            config["poolclass"] = None

        return config

    def get_audit_config(self) -> Dict[str, Any]:
        """
        Get audit trail configuration for pharmaceutical compliance.

        Returns audit configuration settings for regulatory compliance
        including retention policies and trigger settings.

        Returns:
            Dict[str, Any]: Audit trail configuration

        Since:
            Version 1.0.0
        """
        return {
            "retention_years": self.audit_retention_years,
            "enable_triggers": self.enable_audit_triggers,
            "batch_size": self.audit_batch_size,
            "enable_query_logging": self.enable_query_logging,
            "retention_cutoff_date": f"NOW() - INTERVAL '{self.audit_retention_years} years'",
            "partition_by_month": True,  # Partition audit tables by month for performance
        }

    def get_migration_config(self) -> Dict[str, Any]:
        """
        Get database migration configuration for pharmaceutical platform.

        Returns migration settings optimized for pharmaceutical data
        with proper rollback and validation procedures.

        Returns:
            Dict[str, Any]: Migration configuration

        Since:
            Version 1.0.0
        """
        return {
            "script_location": "alembic",
            "file_template": "%%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s",
            "truncate_slug_length": 40,
            "version_table": "alembic_version",
            "version_table_schema": None,
            "compare_type": True,
            "compare_server_default": True,
            "target_metadata": None,  # Will be set by migration environment
            "pharmaceutical_validation": True,
            "require_confirmation": not self.testing,  # Require confirmation in production
        }


# Global database configuration instance
database_config = DatabaseConfig()


def get_database_config() -> DatabaseConfig:
    """
    Get the global database configuration instance.

    Returns:
        DatabaseConfig: Database configuration for pharmaceutical platform

    Since:
        Version 1.0.0
    """
    return database_config


def validate_database_connection() -> bool:
    """
    Validate database connection and pharmaceutical schema requirements.

    Performs comprehensive validation of database connection and
    verifies pharmaceutical intelligence platform requirements.

    Returns:
        bool: True if database connection and schema are valid

    Raises:
        ConnectionError: If database connection fails
        ValueError: If pharmaceutical schema requirements are not met

    Since:
        Version 1.0.0
    """
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.exc import SQLAlchemyError

        # Create sync engine for validation
        sync_url = database_config.database_url.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_url)

        with engine.connect() as conn:
            # Test basic connection
            result = conn.execute(text("SELECT version()"))
            pg_version = result.scalar()
            logger.info("Database connection validated", postgresql_version=pg_version)

            # Check PostgreSQL version (requires 15+)
            version_result = conn.execute(text("SELECT version_num FROM pg_catalog.pg_control_system()"))
            version_num = version_result.scalar()
            if version_num < 150000:  # PostgreSQL 15.0
                raise ValueError(f"PostgreSQL 15+ required for pharmaceutical platform, found version {version_num}")

            # Check required extensions
            extensions_check = conn.execute(text("""
                SELECT extname FROM pg_extension
                WHERE extname IN ('uuid-ossp', 'pg_stat_statements')
            """))
            installed_extensions = [row[0] for row in extensions_check]

            required_extensions = ['uuid-ossp']
            missing_extensions = set(required_extensions) - set(installed_extensions)
            if missing_extensions:
                logger.warning("Missing recommended extensions", missing=list(missing_extensions))

            # Validate audit trail requirements
            if not database_config.enable_audit_triggers:
                logger.warning("Audit triggers disabled - may not meet pharmaceutical compliance requirements")

            return True

    except SQLAlchemyError as e:
        logger.error("Database connection validation failed", error=str(e))
        raise ConnectionError(f"Failed to connect to pharmaceutical database: {e}")

    except Exception as e:
        logger.error("Unexpected database validation error", error=str(e))
        raise


# Pharmaceutical compliance validation
def validate_pharmaceutical_compliance() -> Dict[str, bool]:
    """
    Validate pharmaceutical regulatory compliance requirements.

    Performs comprehensive validation of pharmaceutical intelligence
    platform compliance with regulatory requirements.

    Returns:
        Dict[str, bool]: Compliance validation results

    Since:
        Version 1.0.0
    """
    compliance_checks = {
        "audit_retention_7_years": database_config.audit_retention_years >= 7,
        "audit_triggers_enabled": database_config.enable_audit_triggers,
        "query_logging_enabled": database_config.enable_query_logging,
        "connection_security": database_config.database_url.startswith("postgresql+asyncpg://"),
        "statement_timeout_configured": database_config.statement_timeout > 0,
        "connection_pooling_adequate": database_config.connection_pool_size >= 10,
    }

    # Log compliance status
    compliant = all(compliance_checks.values())
    logger.info(
        "Pharmaceutical compliance validation",
        compliant=compliant,
        checks=compliance_checks
    )

    if not compliant:
        failed_checks = [check for check, passed in compliance_checks.items() if not passed]
        logger.warning("Pharmaceutical compliance issues detected", failed_checks=failed_checks)

    return compliance_checks