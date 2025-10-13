"""
API endpoints for hierarchical source priority processing.

Provides endpoints for executing searches with source prioritization,
reliability scoring, and early termination optimization.

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
from ...core.source_priority import SourcePriority
from ...config.logging import PharmaceuticalLogger

router = APIRouter(prefix="/hierarchical", tags=["Hierarchical Processing"])
logger = PharmaceuticalLogger(service_name="hierarchical_api")


class HierarchicalSearchRequest(BaseModel):
    """Request for hierarchical priority search."""
    query: str = Field(..., description="Search query")
    pharmaceutical_compound: str = Field(..., description="Drug compound name")
    category: str = Field(..., description="Pharmaceutical category")
    process_id: str = Field(..., description="Process tracking ID")
    request_id: str = Field(..., description="Drug request ID")
    correlation_id: str = Field(..., description="Correlation ID for tracing")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="Search temperature")
    early_termination: bool = Field(True, description="Enable early termination")
    priority_overrides: Optional[Dict[str, int]] = Field(
        None,
        description="Custom priority overrides"
    )


class SourceClassificationRequest(BaseModel):
    """Request for source classification."""
    url: str = Field(..., description="Source URL to classify")
    title: Optional[str] = Field(None, description="Source title")
    source_type: Optional[str] = Field(None, description="Source type hint")


class ReliabilityUpdateRequest(BaseModel):
    """Request to update source reliability."""
    source_url: str = Field(..., description="Source URL")
    was_accurate: bool = Field(..., description="Whether source was accurate")
    verification_method: str = Field(
        ...,
        description="How accuracy was verified"
    )


class PriorityConfigRequest(BaseModel):
    """Request to update category priority configuration."""
    category: str = Field(..., description="Pharmaceutical category")
    priority_overrides: Dict[str, int] = Field(
        ...,
        description="Priority level overrides by source type"
    )
    min_coverage_threshold: float = Field(
        0.8,
        ge=0.0,
        le=1.0,
        description="Minimum coverage for early termination"
    )
    early_termination_enabled: bool = Field(
        True,
        description="Enable early termination optimization"
    )


@router.post("/search")
async def execute_hierarchical_search(
    request: HierarchicalSearchRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """
    Execute search with hierarchical source prioritization.

    Processes results in priority order (Paid APIs → Government →
    Peer-reviewed → Industry → Company → News) with optional early
    termination when sufficient coverage is achieved.
    """
    try:
        # Initialize API manager
        api_manager = MultiAPIManager(db, redis_client, logger)
        await api_manager.initialize()

        start_time = datetime.utcnow()

        # Execute hierarchical search
        results = await api_manager.search_with_hierarchical_processing(
            query=request.query,
            category=request.category,
            pharmaceutical_compound=request.pharmaceutical_compound,
            process_id=request.process_id,
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            temperature=request.temperature,
            priority_overrides=request.priority_overrides,
            early_termination=request.early_termination
        )

        # Calculate execution time
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log search execution
        await logger.log_api_call(
            provider="hierarchical_search",
            endpoint="execute",
            request_data=request.dict(),
            response_status=200,
            response_time_ms=execution_time,
            drug_names=[request.pharmaceutical_compound]
        )

        # Add execution metrics
        results['execution_metrics'] = {
            'total_execution_time_ms': execution_time,
            'efficiency_score': results['summary']['processing_efficiency'],
            'coverage_achieved': results['summary']['average_coverage_score']
        }

        return results

    except Exception as e:
        logger.error(f"Hierarchical search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hierarchical search failed: {str(e)}"
        )


@router.post("/classify")
async def classify_source(
    request: SourceClassificationRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """
    Classify a source URL to determine its priority level.

    Returns the source priority classification and reliability score.
    """
    try:
        from ...core.source_priority import SourceClassifier, SourceAttribution

        classifier = SourceClassifier()

        # Create source attribution
        from urllib.parse import urlparse
        parsed = urlparse(request.url)

        source = SourceAttribution(
            title=request.title or parsed.netloc,
            url=request.url,
            domain=parsed.netloc,
            source_type=request.source_type or "unknown",
            credibility_score=0.5  # Default
        )

        # Classify source
        classification = classifier.classify_source(source)

        return {
            'url': request.url,
            'domain': classification.domain,
            'priority': {
                'level': classification.priority,
                'name': SourcePriority(classification.priority).name
            },
            'category': classification.category,
            'confidence': classification.confidence,
            'metadata': classification.metadata
        }

    except Exception as e:
        logger.error(f"Source classification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Source classification failed: {str(e)}"
        )


@router.put("/reliability")
async def update_source_reliability(
    request: ReliabilityUpdateRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """
    Update reliability tracking for a source.

    Records whether a source's information was accurate and how it was verified.
    """
    try:
        # Initialize API manager
        api_manager = MultiAPIManager(db, redis_client, logger)

        # Update reliability
        await api_manager.update_source_reliability(
            source_url=request.source_url,
            was_accurate=request.was_accurate,
            verification_method=request.verification_method
        )

        return {
            'status': 'success',
            'source_url': request.source_url,
            'accuracy_recorded': request.was_accurate,
            'verification_method': request.verification_method,
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Reliability update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reliability update failed: {str(e)}"
        )


@router.get("/priority-config/{category}")
async def get_priority_configuration(
    category: str,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """
    Get priority configuration for a pharmaceutical category.

    Returns the current priority overrides and early termination settings.
    """
    try:
        # Initialize API manager
        api_manager = MultiAPIManager(db, redis_client, logger)
        await api_manager.initialize()

        # Get configuration
        config = await api_manager.get_category_priority_config(category)

        return config

    except Exception as e:
        logger.error(f"Failed to get priority config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get priority configuration: {str(e)}"
        )


@router.put("/priority-config")
async def update_priority_configuration(
    request: PriorityConfigRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update priority configuration for a pharmaceutical category.

    Allows customization of source priorities and early termination thresholds.
    """
    try:
        from ...database.models import PharmaceuticalCategory
        from sqlalchemy import update

        # Update category priority configuration
        stmt = update(PharmaceuticalCategory).where(
            PharmaceuticalCategory.name == request.category
        ).values(
            priority_weights={
                'overrides': request.priority_overrides,
                'min_coverage': request.min_coverage_threshold,
                'early_termination': request.early_termination_enabled
            }
        )

        result = await db.execute(stmt)
        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category {request.category} not found"
            )

        # Log configuration change
        await logger.log_data_access(
            resource="priority_config",
            action="update",
            user_id="system",  # Would get from auth
            success=True,
            drug_names=[]
        )

        return {
            'status': 'success',
            'category': request.category,
            'priority_overrides': request.priority_overrides,
            'min_coverage_threshold': request.min_coverage_threshold,
            'early_termination_enabled': request.early_termination_enabled,
            'timestamp': datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update priority config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update priority configuration"
        )


@router.get("/source-hierarchy")
async def get_source_hierarchy() -> Dict[str, Any]:
    """
    Get the complete source priority hierarchy.

    Returns the priority levels and their descriptions for pharmaceutical
    intelligence gathering.
    """
    hierarchy = {
        'priority_levels': [
            {
                'level': SourcePriority.PAID_APIS,
                'name': 'PAID_APIS',
                'description': 'Premium API sources (ChatGPT, Perplexity, Claude)',
                'reliability_score': 0.85
            },
            {
                'level': SourcePriority.GOVERNMENT,
                'name': 'GOVERNMENT',
                'description': 'Government and regulatory sources (FDA, NIH, CDC)',
                'reliability_score': 0.95
            },
            {
                'level': SourcePriority.PEER_REVIEWED,
                'name': 'PEER_REVIEWED',
                'description': 'Peer-reviewed journals and academic sources',
                'reliability_score': 0.90
            },
            {
                'level': SourcePriority.INDUSTRY,
                'name': 'INDUSTRY',
                'description': 'Industry associations and professional organizations',
                'reliability_score': 0.80
            },
            {
                'level': SourcePriority.COMPANY,
                'name': 'COMPANY',
                'description': 'Pharmaceutical company websites',
                'reliability_score': 0.70
            },
            {
                'level': SourcePriority.NEWS,
                'name': 'NEWS',
                'description': 'News and media outlets',
                'reliability_score': 0.60
            },
            {
                'level': SourcePriority.UNKNOWN,
                'name': 'UNKNOWN',
                'description': 'Unclassified or unknown sources',
                'reliability_score': 0.40
            }
        ],
        'processing_order': 'ascending',
        'early_termination_note': 'Processing may stop early if sufficient coverage is achieved from high-priority sources'
    }

    return hierarchy


@router.get("/statistics/{category}")
async def get_hierarchical_statistics(
    category: str,
    lookback_days: int = 30,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get hierarchical processing statistics for a category.

    Returns metrics on source distribution, early termination rates,
    and processing efficiency over the specified period.
    """
    try:
        from ...database.repositories.raw_data_repo import RawDataRepository
        from datetime import timedelta

        repo = RawDataRepository(db)

        # Get responses with hierarchical metadata
        start_date = datetime.utcnow() - timedelta(days=lookback_days)
        responses = await repo.search_by_compound(
            compound="",  # All compounds
            category=category,
            start_date=start_date,
            limit=1000
        )

        # Analyze hierarchical processing patterns
        total_searches = len(responses)
        early_terminations = 0
        total_coverage = 0
        priority_counts = {}

        for response in responses:
            if response.metadata and 'hierarchical_processing' in response.metadata:
                hp_meta = response.metadata['hierarchical_processing']

                if hp_meta.get('early_termination'):
                    early_terminations += 1

                total_coverage += hp_meta.get('coverage_score', 0)

                for priority, count in hp_meta.get('priority_distribution', {}).items():
                    priority_counts[priority] = priority_counts.get(priority, 0) + count

        avg_coverage = total_coverage / max(total_searches, 1)
        early_termination_rate = early_terminations / max(total_searches, 1)

        return {
            'category': category,
            'period_days': lookback_days,
            'total_searches': total_searches,
            'early_termination_rate': early_termination_rate,
            'average_coverage_score': avg_coverage,
            'priority_distribution': priority_counts,
            'efficiency_metrics': {
                'searches_with_early_termination': early_terminations,
                'average_sources_saved': int(early_termination_rate * 5)  # Estimate
            }
        }

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )