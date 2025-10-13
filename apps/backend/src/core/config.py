"""
Configuration management for CognitoAI Engine.

Centralized configuration using Pydantic settings for
environment variable management and validation.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings
import os
from pathlib import Path


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Since:
        Version 1.0.0
    """
    
    # Application Settings
    APP_NAME: str = Field("CognitoAI Engine", env="APP_NAME")
    APP_VERSION: str = Field("1.0.0", env="APP_VERSION")
    DEBUG: bool = Field(False, env="DEBUG")
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    
    # Database Settings
    POSTGRES_HOST: str = Field("localhost", env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    POSTGRES_USER: str = Field("cognitoai_user", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field("cognitoai_pharma", env="POSTGRES_DB")
    
    # Redis Settings
    REDIS_HOST: str = Field("localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    
    # Security Settings
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_MINUTES: int = Field(30, env="JWT_EXPIRATION_MINUTES")
    
    # API Settings
    API_KEY_LENGTH: int = Field(32, env="API_KEY_LENGTH")
    RATE_LIMIT_REQUESTS: int = Field(100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(60, env="RATE_LIMIT_WINDOW")
    
    # OpenAI Settings
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field("gpt-4-turbo-preview", env="OPENAI_MODEL")
    OPENAI_MAX_TOKENS: int = Field(4000, env="OPENAI_MAX_TOKENS")
    OPENAI_TEMPERATURE: float = Field(0.7, env="OPENAI_TEMPERATURE")
    
    # Anthropic Settings
    ANTHROPIC_API_KEY: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = Field("claude-3-opus-20240229", env="ANTHROPIC_MODEL")
    ANTHROPIC_MAX_TOKENS: int = Field(4000, env="ANTHROPIC_MAX_TOKENS")
    
    # Google Settings
    GOOGLE_API_KEY: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    GOOGLE_CUSTOM_SEARCH_ENGINE_ID: Optional[str] = Field(None, env="GOOGLE_CSE_ID")
    
    # PubMed Settings
    PUBMED_API_KEY: Optional[str] = Field(None, env="PUBMED_API_KEY")
    PUBMED_EMAIL: Optional[str] = Field(None, env="PUBMED_EMAIL")
    
    # Processing Settings
    MAX_CONCURRENT_REQUESTS: int = Field(10, env="MAX_CONCURRENT_REQUESTS")
    REQUEST_TIMEOUT: int = Field(30, env="REQUEST_TIMEOUT")
    BACKGROUND_TASK_WORKERS: int = Field(4, env="BACKGROUND_TASK_WORKERS")
    
    # Logging Settings
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field("json", env="LOG_FORMAT")
    
    # Audit Settings
    AUDIT_RETENTION_YEARS: int = Field(7, env="AUDIT_RETENTION_YEARS")
    AUDIT_BATCH_SIZE: int = Field(100, env="AUDIT_BATCH_SIZE")
    
    @property
    def database_url(self) -> str:
        """Generate PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    @property
    def redis_url(self) -> str:
        """Generate Redis connection URL."""
        if self.REDIS_PASSWORD:
            return (
                f"redis://:{self.REDIS_PASSWORD}@"
                f"{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @validator("JWT_SECRET_KEY")
    def validate_jwt_secret(cls, v):
        """Ensure JWT secret is strong enough."""
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_environments = ["development", "staging", "production"]
        if v not in valid_environments:
            raise ValueError(
                f"ENVIRONMENT must be one of: {', '.join(valid_environments)}"
            )
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True
    }


# Create settings instance
settings = Settings(
    _env_file=os.getenv("ENV_FILE", ".env"),
    POSTGRES_PASSWORD=os.getenv("POSTGRES_PASSWORD", "default_password"),
    JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", "your-secret-key-at-least-32-characters-long-here")
)