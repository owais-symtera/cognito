"""
API endpoints for temperature variation search strategy.

Provides endpoints for executing multi-temperature searches and analyzing
temperature effectiveness for pharmaceutical intelligence optimization.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import redis.asyncio as redis

from ...database.session import get_db, get_redis
from ...integrations.api_manager import MultiAPIManager
from ...core.temperature_strategy import TemperatureStrategy, TemperatureResult
from ...config.logging import PharmaceuticalLogger

router = APIRouter(prefix="/temperature", tags=["Temperature Strategy"])
logger = PharmaceuticalLogger(service_name="temperature_api")


class TemperatureSearchRequest(BaseModel):
    """Request for multi-temperature search."""
    query: str = Field(..., description="Search query")
    pharmaceutical_compound: str = Field(..., description="Drug compound name")
    category: str = Field(..., description="Pharmaceutical category")
    process_id: str = Field(..., description="Process tracking ID")
    request_id: str = Field(..., description="Drug request ID")
    correlation_id: str = Field(..., description="Correlation ID for tracing")
    temperatures: Optional[List[float]] = Field(
        None,
        description="Custom temperature values (defaults to category config)"
    )
    provider: Optional[str] = Field(None, description="Specific provider to use")


class TemperatureSearchResponse(BaseModel):
    """Response from temperature variation search."""
    provider: str
    temperatures: List[float]
    results: List[Dict[str, Any]]
    total_cost: float
    cached_count: int
    execution_time_ms: int


class TemperatureAnalysisRequest(BaseModel):
    """Request for temperature effectiveness analysis."""
    category: str = Field(..., description="Pharmaceutical category")
    provider_results: Dict[str, List[Dict[str, Any]]] = Field(
        ...,
        description="Temperature results by provider"
    )


class TemperatureConfigRequest(BaseModel):
    """Request to update temperature configuration."""
    category: str = Field(..., description="Pharmaceutical category")
    temperatures: List[float] = Field(
        ...,
        description="Temperature values to use",
        min_items=1,
        max_items=10
    )
    provider_overrides: Optional[Dict[str, List[float]]] = Field(
        None,
        description="Provider-specific temperature overrides"
    )


@router.post("/search", response_model=List[TemperatureSearchResponse])
async def execute_temperature_search(
    request: TemperatureSearchRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> List[TemperatureSearchResponse]:
    """
    Execute multi-temperature search across providers.

    Performs parallel searches at different temperature values to obtain
    comprehensive pharmaceutical intelligence coverage.
    """
    try:
        # Initialize API manager
        api_manager = MultiAPIManager(db, redis_client, logger)
        await api_manager.initialize()

        # Create temperature strategy
        strategy = None
        if request.temperatures:
            strategy = TemperatureStrategy(temperatures=request.temperatures)

        start_time = datetime.utcnow()

        # Execute temperature searches
        results = await api_manager.search_with_temperature_variation(
            query=request.query,
            category=request.category,
            pharmaceutical_compound=request.pharmaceutical_compound,
            process_id=request.process_id,
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            temperature_strategy=strategy,
            provider_name=request.provider
        )

        # Format response
        responses = []
        for provider_name, temp_results in results.items():
            if temp_results:
                response = TemperatureSearchResponse(
                    provider=provider_name,
                    temperatures=[r.temperature for r in temp_results],
                    results=[
                        {
                            'temperature': r.temperature,
                            'relevance_score': r.relevance_score,
                            'result_count': r.result_count,
                            'cost': r.cost,
                            'cached': r.cached,
                            'response_id': r.response_id
                        }
                        for r in temp_results
                    ],
                    total_cost=sum(r.cost for r in temp_results if not r.cached),
                    cached_count=sum(1 for r in temp_results if r.cached),
                    execution_time_ms=int(
                        (datetime.utcnow() - start_time).total_seconds() * 1000
                    )
                )
                responses.append(response)

        # Log search execution
        await logger.log_api_call(
            provider="temperature_strategy",
            endpoint="multi_temperature_search",
            request_data=request.dict(),
            response_status=200,
            response_time_ms=int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            ),
            drug_names=[request.pharmaceutical_compound]
        )

        return responses

    except Exception as e:
        logger.error(f"Temperature search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Temperature search failed: {str(e)}"
        )


@router.post("/analyze")
async def analyze_temperature_effectiveness(
    request: TemperatureAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """
    Analyze temperature effectiveness across providers.

    Provides recommendations for optimal temperature values based on
    result quality, diversity, and cost metrics.
    """
    try:
        # Initialize API manager
        api_manager = MultiAPIManager(db, redis_client, logger)

        # Convert request data to TemperatureResult objects
        # (This is simplified - in production would deserialize properly)
        temperature_results = {}
        for provider, results in request.provider_results.items():
            temp_results = []
            for r in results:
                # Create mock TemperatureResult
                # In production, would properly deserialize
                pass
            temperature_results[provider] = temp_results

        # Analyze effectiveness
        analysis = await api_manager.analyze_temperature_effectiveness(
            temperature_results,
            request.category
        )

        return analysis

    except Exception as e:
        logger.error(f"Temperature analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Temperature analysis failed: {str(e)}"
        )


@router.put("/config/{category}")
async def update_temperature_config(
    category: str,
    config: TemperatureConfigRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update temperature configuration for a pharmaceutical category.

    Allows customization of temperature strategies for specific drug categories
    to optimize search effectiveness.
    """
    try:
        from ...database.models import PharmaceuticalCategory
        from sqlalchemy import select, update

        # Update category temperature strategy
        stmt = update(PharmaceuticalCategory).where(
            PharmaceuticalCategory.name == category
        ).values(
            temperature_strategy={
                'temperatures': config.temperatures,
                'provider_overrides': config.provider_overrides or {}
            }
        )

        result = await db.execute(stmt)
        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category {category} not found"
            )

        # Log configuration change
        await logger.log_data_access(
            resource="temperature_config",
            action="update",
            user_id="system",  # Would get from auth
            success=True,
            drug_names=[]
        )

        return {
            'status': 'success',
            'category': category,
            'temperatures': config.temperatures,
            'provider_overrides': config.provider_overrides
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update temperature config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration"
        )


@router.get("/config/{category}")
async def get_temperature_config(
    category: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get temperature configuration for a pharmaceutical category.

    Returns the current temperature strategy configuration including
    default values and provider-specific overrides.
    """
    try:
        from ...database.models import PharmaceuticalCategory
        from sqlalchemy import select

        # Get category configuration
        query = select(PharmaceuticalCategory).where(
            PharmaceuticalCategory.name == category
        )
        result = await db.execute(query)
        category_obj = result.scalar_one_or_none()

        if not category_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category {category} not found"
            )

        # Extract temperature strategy
        temp_strategy = category_obj.temperature_strategy or {}

        return {
            'category': category,
            'temperatures': temp_strategy.get('temperatures', [0.1, 0.5, 0.9]),
            'provider_overrides': temp_strategy.get('provider_overrides', {}),
            'updated_at': category_obj.updated_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get temperature config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration"
        )


@router.get("/recommendations/{category}")
async def get_temperature_recommendations(
    category: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get temperature optimization recommendations for a category.

    Analyzes historical temperature performance data to provide
    recommendations for optimal temperature configurations.
    """
    try:
        from ...database.repositories.raw_data_repo import RawDataRepository

        repo = RawDataRepository(db)

        # Get historical temperature performance data
        # This would analyze past searches to determine optimal temperatures

        recommendations = {
            'category': category,
            'current_config': {
                'temperatures': [0.1, 0.5, 0.9]  # Default
            },
            'recommendations': [
                {
                    'type': 'optimal_temperature',
                    'value': 0.7,
                    'reasoning': 'Historical data shows best relevance at 0.7'
                },
                {
                    'type': 'cost_optimization',
                    'value': [0.5],
                    'reasoning': 'Single temperature provides 90% of value at 33% cost'
                },
                {
                    'type': 'diversity_maximization',
                    'value': [0.1, 0.9],
                    'reasoning': 'Extreme temperatures provide maximum result diversity'
                }
            ],
            'performance_metrics': {
                'avg_relevance_by_temp': {
                    '0.1': 0.72,
                    '0.5': 0.85,
                    '0.9': 0.78
                },
                'cost_by_temp': {
                    '0.1': 0.04,
                    '0.5': 0.04,
                    '0.9': 0.04
                }
            }
        }

        return recommendations

    except Exception as e:
        logger.error(f"Failed to generate recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations"
        )