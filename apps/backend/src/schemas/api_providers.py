"""
Pydantic schemas for API provider management.

Defines request and response models for API provider configuration
and management endpoints.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator


class APIProviderConfigResponse(BaseModel):
    """
    API provider configuration response.

    Since:
        Version 1.0.0
    """
    provider_name: str = Field(..., description="Provider name (e.g., chatgpt, perplexity)")
    enabled_globally: bool = Field(..., description="Whether provider is enabled globally")
    requests_per_minute: int = Field(..., description="Maximum requests per minute")
    requests_per_hour: int = Field(..., description="Maximum requests per hour")
    daily_quota: Optional[int] = Field(None, description="Daily request quota")
    cost_per_request: float = Field(..., description="Cost per API request in USD")
    cost_per_token: float = Field(..., description="Cost per token if applicable")
    config_json: Dict[str, Any] = Field(..., description="Provider-specific configuration")
    key_version: int = Field(..., description="API key version")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class APIProviderUpdateRequest(BaseModel):
    """
    Request to update API provider configuration.

    Since:
        Version 1.0.0
    """
    enabled_globally: Optional[bool] = Field(None, description="Enable/disable provider")
    requests_per_minute: Optional[int] = Field(None, ge=1, description="Requests per minute")
    requests_per_hour: Optional[int] = Field(None, ge=1, description="Requests per hour")
    daily_quota: Optional[int] = Field(None, ge=1, description="Daily quota")
    cost_per_request: Optional[float] = Field(None, ge=0, description="Cost per request")
    cost_per_token: Optional[float] = Field(None, ge=0, description="Cost per token")
    config_json: Optional[Dict[str, Any]] = Field(None, description="Provider configuration")


class APIKeyRotationRequest(BaseModel):
    """
    Request to rotate API key.

    Since:
        Version 1.0.0
    """
    new_api_key: str = Field(..., min_length=1, description="New API key")

    @validator('new_api_key')
    def validate_api_key(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("API key must be at least 10 characters")
        return v.strip()


class RateLimitUpdateRequest(BaseModel):
    """
    Request to update rate limits.

    Since:
        Version 1.0.0
    """
    requests_per_minute: Optional[int] = Field(None, ge=1, le=1000, description="RPM limit")
    requests_per_hour: Optional[int] = Field(None, ge=1, le=10000, description="RPH limit")
    daily_quota: Optional[int] = Field(None, ge=1, le=100000, description="Daily quota")


class CategoryAPIConfigRequest(BaseModel):
    """
    Request to configure provider for category.

    Since:
        Version 1.0.0
    """
    enabled: bool = Field(..., description="Enable/disable provider for category")
    priority: Optional[int] = Field(0, ge=0, le=100, description="Provider priority")
    custom_config: Optional[Dict[str, Any]] = Field(None, description="Custom configuration")


class ProviderStatusResponse(BaseModel):
    """
    Provider status information.

    Since:
        Version 1.0.0
    """
    healthy: bool = Field(..., description="Whether provider is healthy")
    circuit_breaker: str = Field(..., description="Circuit breaker state (open/closed)")
    recent_failures: int = Field(..., description="Number of recent failures")
    daily_cost: float = Field(..., description="Cost incurred today in USD")
    rate_limits: Dict[str, int] = Field(..., description="Rate limit configuration")


class ProviderCostReport(BaseModel):
    """
    Provider cost report.

    Since:
        Version 1.0.0
    """
    provider_name: str = Field(..., description="Provider name")
    period: str = Field(..., description="Report period (daily/weekly/monthly)")
    total_cost: float = Field(..., description="Total cost in USD")
    request_count: int = Field(..., description="Number of requests")
    average_cost_per_request: float = Field(..., description="Average cost per request")
    breakdown_by_category: Dict[str, float] = Field(..., description="Cost by category")


class APIProviderHealthCheck(BaseModel):
    """
    Provider health check result.

    Since:
        Version 1.0.0
    """
    provider_name: str = Field(..., description="Provider name")
    is_healthy: bool = Field(..., description="Health status")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    last_check: datetime = Field(..., description="Last health check timestamp")