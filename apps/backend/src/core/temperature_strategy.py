"""
Temperature variation search strategy for pharmaceutical intelligence.

Implements multi-temperature search execution with complete audit tracking
for comprehensive pharmaceutical intelligence coverage.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import asyncio
import hashlib
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from pydantic import BaseModel, Field
import structlog

from ..integrations.providers.base import APIProvider, StandardizedAPIResponse
from ..database.models import APIResponse, PharmaceuticalCategory
from ..core.data_persistence import DataPersistenceManager
from ..config.logging import PharmaceuticalLogger

logger = structlog.get_logger(__name__)


class TemperatureStrategy(BaseModel):
    """
    Temperature configuration for pharmaceutical intelligence gathering.

    Defines temperature variations for comprehensive search coverage.

    Since:
        Version 1.0.0
    """

    temperatures: List[float] = Field(
        default=[0.1, 0.5, 0.9],
        description="Default temperature values for searches"
    )
    category_overrides: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Category-specific temperature overrides"
    )
    api_specific: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="API provider-specific temperature configurations"
    )
    min_temperature: float = Field(0.0, description="Minimum allowed temperature")
    max_temperature: float = Field(1.0, description="Maximum allowed temperature")

    def get_temperatures_for_category(self, category: str) -> List[float]:
        """
        Get temperature values for a specific pharmaceutical category.

        Args:
            category: Pharmaceutical category name

        Returns:
            List of temperature values

        Since:
            Version 1.0.0
        """
        if category in self.category_overrides:
            return self.category_overrides[category]
        return self.temperatures

    def get_temperatures_for_api(self, provider: str, category: str) -> List[float]:
        """
        Get temperature values for specific API provider and category.

        Args:
            provider: API provider name
            category: Pharmaceutical category

        Returns:
            List of temperature values

        Since:
            Version 1.0.0
        """
        # Check API-specific first
        if provider in self.api_specific:
            return self.api_specific[provider]

        # Then category-specific
        return self.get_temperatures_for_category(category)


@dataclass
class TemperatureResult:
    """
    Result from temperature variation search.

    Since:
        Version 1.0.0
    """
    temperature: float
    response: StandardizedAPIResponse
    response_id: str
    execution_time_ms: int
    cost: float
    relevance_score: float
    result_count: int
    cached: bool = False


class TemperatureSearchManager:
    """
    Manages multi-temperature search execution and optimization.

    Handles parallel execution, caching, and performance optimization
    for pharmaceutical intelligence gathering.

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        persistence_manager: DataPersistenceManager,
        audit_logger: PharmaceuticalLogger,
        cache_ttl_minutes: int = 60
    ):
        """
        Initialize temperature search manager.

        Args:
            persistence_manager: Data persistence service
            audit_logger: Audit logging service
            cache_ttl_minutes: Cache TTL in minutes

        Since:
            Version 1.0.0
        """
        self.persistence = persistence_manager
        self.audit_logger = audit_logger
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.query_cache = {}

    async def execute_temperature_searches(
        self,
        provider: APIProvider,
        query: str,
        temperatures: List[float],
        category: str,
        process_id: str,
        request_id: str,
        correlation_id: str,
        pharmaceutical_compound: str
    ) -> List[TemperatureResult]:
        """
        Execute searches across multiple temperatures in parallel.

        Args:
            provider: API provider instance
            query: Search query
            temperatures: List of temperature values
            category: Pharmaceutical category
            process_id: Process tracking ID
            request_id: Drug request ID
            correlation_id: Request correlation ID
            pharmaceutical_compound: Drug compound name

        Returns:
            List of temperature results

        Since:
            Version 1.0.0
        """
        start_time = datetime.utcnow()
        results = []

        # Log strategy execution
        await self.audit_logger.log_api_call(
            provider=provider.name,
            endpoint="temperature_strategy",
            request_data={
                "query": query,
                "temperatures": temperatures,
                "category": category
            },
            response_status=200,
            response_time_ms=0,
            drug_names=[pharmaceutical_compound]
        )

        # Check cache and prepare tasks
        tasks = []
        cached_results = []

        for temp in temperatures:
            cache_key = self._generate_cache_key(provider.name, query, temp, category)

            # Check if we have a recent cached result
            cached = await self._check_cache(cache_key)
            if cached:
                cached_results.append((temp, cached))
                logger.info(
                    "Using cached result",
                    provider=provider.name,
                    temperature=temp,
                    query=query[:50]
                )
            else:
                # Add to parallel execution
                tasks.append(self._execute_single_temperature(
                    provider,
                    query,
                    temp,
                    category,
                    process_id,
                    request_id,
                    correlation_id,
                    pharmaceutical_compound
                ))

        # Execute parallel searches for non-cached
        if tasks:
            new_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in new_results:
                if isinstance(result, Exception):
                    logger.error(
                        "Temperature search failed",
                        error=str(result)
                    )
                else:
                    results.append(result)
                    # Update cache
                    await self._update_cache(result)

        # Add cached results
        for temp, cached_data in cached_results:
            results.append(TemperatureResult(
                temperature=temp,
                response=cached_data['response'],
                response_id=cached_data['response_id'],
                execution_time_ms=0,
                cost=0,  # No cost for cached
                relevance_score=cached_data['relevance_score'],
                result_count=cached_data['result_count'],
                cached=True
            ))

        # Sort by temperature
        results.sort(key=lambda x: x.temperature)

        # Calculate total execution time
        total_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log completion
        logger.info(
            "Temperature strategy completed",
            provider=provider.name,
            temperatures=temperatures,
            total_results=len(results),
            cached_count=len(cached_results),
            execution_time_ms=total_time
        )

        return results

    async def _execute_single_temperature(
        self,
        provider: APIProvider,
        query: str,
        temperature: float,
        category: str,
        process_id: str,
        request_id: str,
        correlation_id: str,
        pharmaceutical_compound: str
    ) -> TemperatureResult:
        """
        Execute a single temperature search.

        Args:
            provider: API provider
            query: Search query
            temperature: Temperature value
            category: Pharmaceutical category
            process_id: Process tracking ID
            request_id: Request ID
            correlation_id: Correlation ID
            pharmaceutical_compound: Drug compound

        Returns:
            Temperature result

        Since:
            Version 1.0.0
        """
        start_time = datetime.utcnow()

        try:
            # Execute search with specific temperature
            response = await provider.search(
                query=query,
                temperature=temperature,
                max_results=10
            )

            # Add temperature metadata
            response.temperature = temperature
            response.metadata = response.metadata or {}
            response.metadata['temperature_strategy'] = 'multi_temp_parallel'
            response.metadata['category'] = category

            # Store in persistence layer
            response_id = await self.persistence.store_api_response(
                response=response,
                process_id=process_id,
                request_id=request_id,
                correlation_id=f"{correlation_id}_temp_{temperature}",
                pharmaceutical_compound=pharmaceutical_compound,
                category=category
            )

            # Calculate execution time
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Create result
            result = TemperatureResult(
                temperature=temperature,
                response=response,
                response_id=response_id,
                execution_time_ms=execution_time,
                cost=response.cost,
                relevance_score=response.relevance_score,
                result_count=response.total_results,
                cached=False
            )

            return result

        except Exception as e:
            logger.error(
                "Temperature search execution failed",
                provider=provider.name,
                temperature=temperature,
                error=str(e)
            )
            raise

    def _generate_cache_key(
        self,
        provider: str,
        query: str,
        temperature: float,
        category: str
    ) -> str:
        """
        Generate cache key for temperature search.

        Args:
            provider: Provider name
            query: Search query
            temperature: Temperature value
            category: Pharmaceutical category

        Returns:
            Cache key

        Since:
            Version 1.0.0
        """
        key_data = f"{provider}:{query}:{temperature}:{category}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def _check_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Check if a cached result exists and is valid.

        Args:
            cache_key: Cache key

        Returns:
            Cached data or None

        Since:
            Version 1.0.0
        """
        if cache_key in self.query_cache:
            cached = self.query_cache[cache_key]

            # Check if still valid
            if datetime.utcnow() - cached['timestamp'] <= self.cache_ttl:
                return cached
            else:
                # Expired, remove from cache
                del self.query_cache[cache_key]

        return None

    async def _update_cache(self, result: TemperatureResult):
        """
        Update cache with new result.

        Args:
            result: Temperature result to cache

        Since:
            Version 1.0.0
        """
        cache_key = self._generate_cache_key(
            result.response.provider,
            result.response.query,
            result.temperature,
            result.response.metadata.get('category', '')
        )

        self.query_cache[cache_key] = {
            'response': result.response,
            'response_id': result.response_id,
            'relevance_score': result.relevance_score,
            'result_count': result.result_count,
            'timestamp': datetime.utcnow()
        }

    async def analyze_temperature_effectiveness(
        self,
        results: List[TemperatureResult],
        category: str
    ) -> Dict[str, Any]:
        """
        Analyze effectiveness of different temperatures.

        Args:
            results: Temperature results to analyze
            category: Pharmaceutical category

        Returns:
            Effectiveness analysis

        Since:
            Version 1.0.0
        """
        if not results:
            return {
                'status': 'no_data',
                'recommendations': []
            }

        analysis = {
            'category': category,
            'temperature_count': len(results),
            'temperatures': [r.temperature for r in results],
            'metrics': []
        }

        for result in results:
            metrics = {
                'temperature': result.temperature,
                'relevance_score': result.relevance_score,
                'result_count': result.result_count,
                'cost': result.cost,
                'execution_time_ms': result.execution_time_ms,
                'cached': result.cached,
                'diversity_score': self._calculate_diversity_score(result.response)
            }
            analysis['metrics'].append(metrics)

        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)

        # Find optimal temperature
        analysis['optimal_temperature'] = self._find_optimal_temperature(analysis['metrics'])

        return analysis

    def _calculate_diversity_score(self, response: StandardizedAPIResponse) -> float:
        """
        Calculate diversity score for response results.

        Args:
            response: API response

        Returns:
            Diversity score (0-1)

        Since:
            Version 1.0.0
        """
        if not response.results:
            return 0.0

        # Calculate based on unique sources and content variety
        unique_sources = set()
        unique_types = set()

        for result in response.results:
            if result.metadata:
                unique_sources.add(result.metadata.get('source', ''))
                unique_types.add(result.source_type)

        source_diversity = len(unique_sources) / max(len(response.results), 1)
        type_diversity = len(unique_types) / max(len(response.results), 1)

        return (source_diversity + type_diversity) / 2

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate temperature optimization recommendations.

        Args:
            analysis: Temperature analysis data

        Returns:
            List of recommendations

        Since:
            Version 1.0.0
        """
        recommendations = []
        metrics = analysis['metrics']

        # Check relevance scores
        avg_relevance = sum(m['relevance_score'] for m in metrics) / len(metrics)
        if avg_relevance < 0.7:
            recommendations.append(
                "Consider adjusting query formulation for better relevance"
            )

        # Check result diversity
        diversity_scores = [m['diversity_score'] for m in metrics]
        if max(diversity_scores) - min(diversity_scores) > 0.3:
            best_temp = metrics[diversity_scores.index(max(diversity_scores))]['temperature']
            recommendations.append(
                f"Temperature {best_temp} provides best result diversity"
            )

        # Check cost efficiency
        costs = [m['cost'] for m in metrics if not m['cached']]
        if costs:
            avg_cost = sum(costs) / len(costs)
            if avg_cost > 0.1:
                recommendations.append(
                    "Consider reducing temperature variations to control costs"
                )

        # Check for minimal differences
        relevance_variance = max(m['relevance_score'] for m in metrics) - \
                           min(m['relevance_score'] for m in metrics)
        if relevance_variance < 0.1:
            recommendations.append(
                "Minimal variation in results; consider using single temperature"
            )

        return recommendations

    def _find_optimal_temperature(self, metrics: List[Dict[str, Any]]) -> float:
        """
        Find optimal temperature based on metrics.

        Args:
            metrics: Temperature metrics

        Returns:
            Optimal temperature value

        Since:
            Version 1.0.0
        """
        if not metrics:
            return 0.5

        # Score each temperature
        scores = []
        for m in metrics:
            # Weight factors: relevance (40%), diversity (30%), cost (30%)
            score = (
                m['relevance_score'] * 0.4 +
                m['diversity_score'] * 0.3 +
                (1 - min(m['cost'] / 0.2, 1)) * 0.3  # Normalize cost
            )
            scores.append((m['temperature'], score))

        # Return temperature with highest score
        return max(scores, key=lambda x: x[1])[0]