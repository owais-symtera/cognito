"""Provider schema definitions."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class TemperatureConfig(BaseModel):
    """Temperature configuration model."""
    id: str
    value: float = Field(ge=0.0, le=2.0)
    enabled: bool = True
    label: str
    description: Optional[str] = None


class ProviderConfig(BaseModel):
    """Provider configuration model."""
    id: str
    name: str
    enabled: bool = False
    apiKey: Optional[str] = None
    model: str
    temperatures: List[TemperatureConfig]
    rateLimit: int = 100
    lastTested: Optional[str] = None
    status: str = "inactive"
    description: Optional[str] = None
    maxTokens: Optional[int] = 4096
    timeout: Optional[int] = 30
    baseUrl: Optional[str] = None

    class Config:
        extra = "allow"  # Allow additional fields


class ProviderConfigUpdate(BaseModel):
    """Provider configuration update model."""
    enabled: Optional[bool] = None
    apiKey: Optional[str] = None
    model: Optional[str] = None
    temperatures: Optional[List[Dict[str, Any]]] = None
    rateLimit: Optional[int] = None
    maxTokens: Optional[int] = None
    timeout: Optional[int] = None
    baseUrl: Optional[str] = None

    class Config:
        extra = "allow"  # Allow additional fields