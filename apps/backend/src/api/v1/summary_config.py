"""
Summary Configuration API Endpoints
Provides REST API for managing summary styles, category mappings, and provider configuration
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from src.services.summary_config_service import SummaryConfigService
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/summary", tags=["Summary Configuration"])

# Dependency to get summary config service
def get_summary_config():
    return SummaryConfigService()


# ==================== Request/Response Models ====================

class SummaryStyleCreate(BaseModel):
    style_name: str
    display_name: str
    description: Optional[str] = None
    system_prompt: str
    user_prompt_template: str
    length_type: str = "STANDARD"
    target_word_count: int = 500
    enabled: bool = True


class SummaryStyleUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    length_type: Optional[str] = None
    target_word_count: Optional[int] = None
    enabled: Optional[bool] = None


class CategoryStyleMapping(BaseModel):
    category_name: str
    summary_style_id: str
    enabled: bool = True
    custom_instructions: Optional[str] = None


class ProviderUpdate(BaseModel):
    provider_key: str
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


# ==================== Provider Configuration ====================

@router.get("/providers")
async def get_summary_providers(
    config_service: SummaryConfigService = Depends(get_summary_config)
):
    """Get all providers that support summary generation"""
    try:
        providers = config_service.get_summary_providers()
        return {
            "success": True,
            "providers": providers
        }
    except Exception as e:
        logger.error("Failed to get summary providers", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers/active")
async def get_active_provider(
    config_service: SummaryConfigService = Depends(get_summary_config)
):
    """Get the currently active summary provider"""
    try:
        provider = await config_service.get_active_summary_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No active provider configured")

        return {
            "success": True,
            "provider": provider
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get active provider", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/providers/active")
async def update_active_provider(
    provider_update: ProviderUpdate,
    config_service: SummaryConfigService = Depends(get_summary_config)
):
    """Update the active summary provider"""
    try:
        success = await config_service.update_active_summary_provider(
            provider_key=provider_update.provider_key,
            model=provider_update.model,
            temperature=provider_update.temperature,
            max_tokens=provider_update.max_tokens
        )

        if not success:
            raise HTTPException(status_code=400, detail="Invalid provider configuration")

        return {
            "success": True,
            "message": f"Active provider updated to {provider_update.provider_key}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update active provider", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Summary Styles ====================

@router.get("/styles")
async def get_summary_styles(
    enabled_only: bool = Query(False, description="Return only enabled styles"),
    config_service: SummaryConfigService = Depends(get_summary_config)
):
    """Get all summary styles"""
    try:
        styles = await config_service.get_summary_styles(enabled_only=enabled_only)
        return {
            "success": True,
            "styles": styles
        }
    except Exception as e:
        logger.error("Failed to get summary styles", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/styles/{style_id}")
async def get_summary_style(
    style_id: str,
    config_service: SummaryConfigService = Depends(get_summary_config)
):
    """Get a specific summary style by ID"""
    try:
        style = await config_service.get_summary_style(style_id)
        if not style:
            raise HTTPException(status_code=404, detail=f"Style {style_id} not found")

        return {
            "success": True,
            "style": style
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get summary style", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/styles")
async def create_summary_style(
    style: SummaryStyleCreate,
    config_service: SummaryConfigService = Depends(get_summary_config)
):
    """Create a new summary style"""
    try:
        style_id = await config_service.create_summary_style(
            style_name=style.style_name,
            display_name=style.display_name,
            system_prompt=style.system_prompt,
            user_prompt_template=style.user_prompt_template,
            description=style.description,
            length_type=style.length_type,
            target_word_count=style.target_word_count,
            enabled=style.enabled
        )

        return {
            "success": True,
            "style_id": style_id,
            "message": f"Summary style '{style.style_name}' created"
        }
    except Exception as e:
        logger.error("Failed to create summary style", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/styles/{style_id}")
async def update_summary_style(
    style_id: str,
    style_update: SummaryStyleUpdate,
    config_service: SummaryConfigService = Depends(get_summary_config)
):
    """Update a summary style"""
    try:
        # Filter out None values
        updates = {k: v for k, v in style_update.dict().items() if v is not None}

        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")

        success = await config_service.update_summary_style(style_id, **updates)

        if not success:
            raise HTTPException(status_code=404, detail=f"Style {style_id} not found")

        return {
            "success": True,
            "message": f"Summary style {style_id} updated"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update summary style", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Category Mappings ====================

@router.get("/categories")
async def get_category_configs(
    config_service: SummaryConfigService = Depends(get_summary_config)
):
    """Get all category-to-style mappings"""
    try:
        configs = await config_service.get_all_category_configs()
        return {
            "success": True,
            "category_configs": configs
        }
    except Exception as e:
        logger.error("Failed to get category configs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories/{category_name}")
async def get_category_config(
    category_name: str,
    config_service: SummaryConfigService = Depends(get_summary_config)
):
    """Get summary configuration for a specific category"""
    try:
        config = await config_service.get_category_summary_config(category_name)
        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"No summary configuration found for category '{category_name}'"
            )

        return {
            "success": True,
            "config": config
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get category config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/categories/{category_name}")
async def set_category_style(
    category_name: str,
    mapping: CategoryStyleMapping,
    config_service: SummaryConfigService = Depends(get_summary_config)
):
    """Map a category to a summary style"""
    try:
        success = await config_service.set_category_summary_style(
            category_name=category_name,
            summary_style_id=mapping.summary_style_id,
            enabled=mapping.enabled,
            custom_instructions=mapping.custom_instructions
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to set category style")

        return {
            "success": True,
            "message": f"Category '{category_name}' mapped to style"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to set category style", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Summary History ====================

@router.get("/history")
async def get_summary_history(
    request_id: Optional[str] = Query(None, description="Filter by request ID"),
    category_name: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000, description="Limit results"),
    config_service: SummaryConfigService = Depends(get_summary_config)
):
    """Get summary generation history"""
    try:
        history = await config_service.get_summary_history(
            request_id=request_id,
            category_name=category_name,
            limit=limit
        )

        return {
            "success": True,
            "count": len(history),
            "history": history
        }
    except Exception as e:
        logger.error("Failed to get summary history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Prompt Variables ====================

@router.get("/variables")
async def get_prompt_variables(
    config_service: SummaryConfigService = Depends(get_summary_config)
):
    """Get all available prompt template variables"""
    try:
        variables = await config_service.get_prompt_variables()
        return {
            "success": True,
            "variables": variables
        }
    except Exception as e:
        logger.error("Failed to get prompt variables", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
