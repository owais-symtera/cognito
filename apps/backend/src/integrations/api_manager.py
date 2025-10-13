"""
Multi-API manager for coordinating pharmaceutical intelligence gathering.

Central coordinator for managing multiple API providers, handling rate limiting,
cost tracking, and parallel execution for pharmaceutical data collection.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import structlog

from .providers import (
    APIProvider,
    StandardizedAPIResponse,
    PROVIDER_CLASSES
)
from .rate_limiter import RateLimiter
from ..database.repositories.api_repo import APIProviderConfigRepository
from ..config.logging import PharmaceuticalLogger
from ..core.temperature_strategy import (
    TemperatureStrategy,
    TemperatureSearchManager,
    TemperatureResult
)
from ..core.data_persistence import DataPersistenceManager
from ..core.source_priority import (
    SourceClassifier,
    HierarchicalProcessor,
    SourceReliabilityScorer
)

logger = structlog.get_logger(__name__)


class MultiAPIManager:
    """
    Central coordinator for pharmaceutical intelligence gathering across multiple APIs.

    Manages parallel API execution, rate limiting, cost tracking, and graceful
    degradation for comprehensive pharmaceutical data collection.

    Attributes:
        db: Database session for configuration
        redis_client: Redis client for caching and rate limiting
        audit_logger: Logger for regulatory compliance
        providers: Dictionary of initialized API providers
        rate_limiter: Rate limiting manager
        config_repo: Repository for API configurations

    Example:
        >>> manager = MultiAPIManager(db, redis_client, audit_logger)
        >>> results = await manager.search_all_providers(
        ...     "Metformin drug interactions",
        ...     "Drug Interactions",
        ...     {"temperature": 0.7}
        ... )

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        db: AsyncSession,
        redis_client: redis.Redis,
        audit_logger: PharmaceuticalLogger
    ):
        """
        Initialize Multi-API Manager.

        Args:
            db: Database session
            redis_client: Redis client for caching
            audit_logger: Pharmaceutical compliance logger

        Since:
            Version 1.0.0
        """
        self.db = db
        self.redis_client = redis_client
        self.audit_logger = audit_logger
        self.providers: Dict[str, APIProvider] = {}
        self.rate_limiter = RateLimiter(redis_client)
        self.config_repo = APIProviderConfigRepository(db)
        self._initialized = False
        self.temperature_manager = None  # Initialize when needed
        self.persistence_manager = None  # Initialize when needed
        self.source_classifier = SourceClassifier()
        self.hierarchical_processor = None  # Initialize when needed
        self.reliability_scorer = SourceReliabilityScorer()

    async def initialize(self):
        """
        Initialize API providers from database configuration.

        Loads API configurations and initializes provider instances.

        Since:
            Version 1.0.0
        """
        if self._initialized:
            return

        try:
            # Load API configurations from database
            configs = await self.config_repo.get_all_configs()

            for config in configs:
                if config.enabled_globally and config.provider_name in PROVIDER_CLASSES:
                    provider_class = PROVIDER_CLASSES[config.provider_name]

                    # Decrypt API key (placeholder - implement actual decryption)
                    api_key = await self._decrypt_api_key(config.encrypted_api_key)

                    # Initialize provider
                    provider = provider_class(
                        api_key=api_key,
                        config=config.config_json
                    )

                    # Validate provider configuration
                    if provider.validate_config():
                        self.providers[config.provider_name] = provider
                        logger.info(f"Initialized {config.provider_name} provider")
                    else:
                        logger.warning(f"Invalid configuration for {config.provider_name}")

            self._initialized = True
            logger.info(f"Initialized {len(self.providers)} API providers")

        except Exception as e:
            logger.error(f"Failed to initialize API providers: {e}")
            raise

    async def search_all_providers(
        self,
        query: str,
        category: str,
        config: Optional[Dict[str, Any]] = None
    ) -> List[StandardizedAPIResponse]:
        """
        Execute search across all configured API providers.

        Args:
            query: Search query for pharmaceutical information
            category: Pharmaceutical category being processed
            config: Additional configuration parameters

        Returns:
            List of standardized API responses from all providers

        Since:
            Version 1.0.0
        """
        if not self._initialized:
            await self.initialize()

        config = config or {}

        # Log search initiation for audit trail
        await self.audit_logger.log_processing_start(
            request_id=config.get('request_id', 'unknown'),
            drug_name=query.split()[0] if query else 'unknown'
        )

        # Get active providers for this category
        active_providers = await self._get_active_providers_for_category(category)

        if not active_providers:
            logger.warning(f"No active providers for category: {category}")
            return []

        # Execute parallel searches with rate limiting
        tasks = []
        for provider_name in active_providers:
            if provider_name in self.providers:
                provider = self.providers[provider_name]
                tasks.append(
                    self._search_provider_with_limits(
                        provider,
                        query,
                        category,
                        config
                    )
                )

        # Gather results with timeout
        timeout = config.get('timeout', 30)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle exceptions
        successful_results = []
        for provider_name, result in zip(active_providers, results):
            if isinstance(result, Exception):
                await self.audit_logger.log_api_call(
                    provider=provider_name,
                    endpoint="search",
                    success=False,
                    response_time_ms=0,
                    error=str(result)
                )
                logger.error(f"Provider {provider_name} failed: {result}")
            elif result:
                successful_results.append(result)
                await self.audit_logger.log_api_call(
                    provider=provider_name,
                    endpoint="search",
                    success=True,
                    response_time_ms=result.response_time_ms
                )

                # Track cost
                await self._track_cost(provider_name, category, result.cost)

        return successful_results

    async def search_single_provider(
        self,
        provider_name: str,
        query: str,
        category: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[StandardizedAPIResponse]:
        """
        Execute search using a specific API provider.

        Args:
            provider_name: Name of the provider to use
            query: Search query
            category: Pharmaceutical category
            config: Additional configuration

        Returns:
            Standardized API response or None if failed

        Since:
            Version 1.0.0
        """
        if not self._initialized:
            await self.initialize()

        if provider_name not in self.providers:
            logger.error(f"Provider {provider_name} not available")
            return None

        provider = self.providers[provider_name]
        config = config or {}

        try:
            result = await self._search_provider_with_limits(
                provider,
                query,
                category,
                config
            )

            if result:
                await self._track_cost(provider_name, category, result.cost)

            return result

        except Exception as e:
            logger.error(f"Failed to search with {provider_name}: {e}")
            return None

    async def _search_provider_with_limits(
        self,
        provider: APIProvider,
        query: str,
        category: str,
        config: Dict[str, Any]
    ) -> Optional[StandardizedAPIResponse]:
        """
        Execute provider search with rate limiting and error handling.

        Args:
            provider: API provider instance
            query: Search query
            category: Pharmaceutical category
            config: Search configuration

        Returns:
            Standardized response or None

        Since:
            Version 1.0.0
        """
        provider_name = provider.name

        try:
            # Check rate limits
            allowed, retry_after = await self.rate_limiter.check_rate_limit(
                provider_name,
                category
            )

            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for {provider_name}",
                    retry_after=retry_after
                )
                return None

            # Check provider health with circuit breaker
            if not await self._check_provider_health(provider_name):
                logger.warning(f"Provider {provider_name} is unhealthy")
                return None

            # Enhance query for source diversity (OpenAI and similar providers)
            enhanced_query = self._enhance_query_for_source_diversity(
                query,
                category,
                provider_name
            )

            # Execute search with timeout
            timeout = config.get('timeout', provider.timeout)
            temperature = config.get('temperature', 0.7)
            max_results = config.get('max_results', 10)

            result = await asyncio.wait_for(
                provider.search(
                    query=enhanced_query,
                    temperature=temperature,
                    max_results=max_results
                ),
                timeout=timeout
            )

            # Record successful call for circuit breaker
            await self._record_provider_success(provider_name)

            return result

        except asyncio.TimeoutError:
            logger.error(f"Timeout for provider {provider_name}")
            await self._record_provider_failure(provider_name)
            return None

        except Exception as e:
            logger.error(f"Provider {provider_name} error: {e}")
            await self._record_provider_failure(provider_name)
            return None

    def _enhance_query_for_source_diversity(
        self,
        query: str,
        category: str,
        provider_name: str
    ) -> str:
        """
        Enhance search query to request diverse authoritative sources.

        This addresses the issue where providers (especially OpenAI) may return
        results from limited sources. The enhanced query explicitly requests
        diverse, authoritative pharmaceutical sources.

        Args:
            query: Original search query
            category: Pharmaceutical category
            provider_name: Name of the API provider

        Returns:
            Enhanced query with source diversity instructions

        Since:
            Version 1.0.0
        """
        # Only enhance for providers that support web search (OpenAI, Perplexity)
        web_search_providers = ['openai', 'chatgpt', 'perplexity']

        if provider_name.lower() not in web_search_providers:
            return query

        # Define authoritative pharmaceutical sources by priority
        authoritative_sources = {
            'government': [
                'FDA.gov', 'NIH.gov', 'ClinicalTrials.gov',
                'EMA.europa.eu', 'WHO.int', 'CDC.gov'
            ],
            'peer_reviewed': [
                'PubMed/NCBI', 'New England Journal of Medicine (NEJM)',
                'The Lancet', 'JAMA', 'Nature Medicine',
                'British Medical Journal (BMJ)'
            ],
            'industry': [
                'PhRMA.org', 'BIO.org', 'IFPMA.org',
                'American Chemical Society (ACS)'
            ],
            'clinical': [
                'ClinicalTrials.gov', 'Cochrane Library',
                'UpToDate', 'Drugs.com'
            ]
        }

        enhanced_query = f"""{query}

IMPORTANT SOURCE REQUIREMENTS:
Please search for this information across DIVERSE authoritative pharmaceutical sources including:

1. Government Regulatory Bodies: {', '.join(authoritative_sources['government'])}
2. Peer-Reviewed Journals: {', '.join(authoritative_sources['peer_reviewed'])}
3. Industry Associations: {', '.join(authoritative_sources['industry'])}
4. Clinical Databases: {', '.join(authoritative_sources['clinical'])}

Requirements:
- Provide data from AT LEAST 3 different types of sources (government, peer-reviewed, industry, clinical)
- Include source citations with each piece of information
- Prioritize recent, peer-reviewed, and government-verified data
- Avoid relying on a single source or domain

Category: {category}"""

        logger.debug(
            "Enhanced query for source diversity",
            provider=provider_name,
            category=category,
            original_query_length=len(query),
            enhanced_query_length=len(enhanced_query)
        )

        return enhanced_query

    async def _get_active_providers_for_category(self, category: str) -> List[str]:
        """
        Get list of active providers for a specific category.

        Args:
            category: Pharmaceutical category name

        Returns:
            List of active provider names

        Since:
            Version 1.0.0
        """
        # Check cache first
        cache_key = f"active_providers:{category}"
        cached = await self.redis_client.get(cache_key)

        if cached:
            return cached.split(',')

        # Load from database
        active_providers = await self.config_repo.get_active_providers_for_category(category)

        # Cache for 5 minutes
        if active_providers:
            await self.redis_client.setex(
                cache_key,
                300,
                ','.join(active_providers)
            )

        return active_providers

    async def _check_provider_health(self, provider_name: str) -> bool:
        """
        Check provider health using circuit breaker pattern.

        Args:
            provider_name: Name of provider to check

        Returns:
            True if provider is healthy

        Since:
            Version 1.0.0
        """
        # Check circuit breaker state
        breaker_key = f"circuit_breaker:{provider_name}"
        state = await self.redis_client.get(breaker_key)

        if state == 'open':
            # Check if enough time has passed to retry
            last_check_key = f"circuit_breaker_time:{provider_name}"
            last_check = await self.redis_client.get(last_check_key)

            if last_check:
                last_check_time = datetime.fromisoformat(last_check)
                if datetime.utcnow() - last_check_time < timedelta(minutes=5):
                    return False

        # Provider is healthy or circuit breaker is half-open
        return True

    async def _record_provider_success(self, provider_name: str):
        """
        Record successful provider call for circuit breaker.

        Args:
            provider_name: Name of successful provider

        Since:
            Version 1.0.0
        """
        # Reset failure count
        failure_key = f"provider_failures:{provider_name}"
        await self.redis_client.delete(failure_key)

        # Close circuit breaker if open
        breaker_key = f"circuit_breaker:{provider_name}"
        await self.redis_client.delete(breaker_key)

    async def _record_provider_failure(self, provider_name: str):
        """
        Record provider failure for circuit breaker.

        Args:
            provider_name: Name of failed provider

        Since:
            Version 1.0.0
        """
        failure_key = f"provider_failures:{provider_name}"
        failures = await self.redis_client.incr(failure_key)

        # Set expiry for failure count (reset after 1 hour)
        await self.redis_client.expire(failure_key, 3600)

        # Open circuit breaker if too many failures
        if failures >= 3:
            breaker_key = f"circuit_breaker:{provider_name}"
            await self.redis_client.set(breaker_key, 'open')

            time_key = f"circuit_breaker_time:{provider_name}"
            await self.redis_client.set(time_key, datetime.utcnow().isoformat())

            logger.warning(f"Circuit breaker opened for {provider_name}")

    async def _track_cost(self, provider_name: str, category: str, cost: float):
        """
        Track API call cost for reporting.

        Args:
            provider_name: Provider name
            category: Category name
            cost: Cost in USD

        Since:
            Version 1.0.0
        """
        try:
            # Track daily cost
            daily_key = f"cost:daily:{provider_name}:{datetime.utcnow().date()}"
            await self.redis_client.incrbyfloat(daily_key, cost)
            await self.redis_client.expire(daily_key, 86400 * 7)  # Keep for 7 days

            # Track category cost
            category_key = f"cost:category:{category}:{datetime.utcnow().date()}"
            await self.redis_client.incrbyfloat(category_key, cost)
            await self.redis_client.expire(category_key, 86400 * 7)

            # Log for audit trail
            logger.info(
                "API cost tracked",
                provider=provider_name,
                category=category,
                cost=cost
            )

        except Exception as e:
            logger.error(f"Failed to track cost: {e}")

    async def _decrypt_api_key(self, encrypted_key: str) -> str:
        """
        Decrypt API key (placeholder implementation).

        Args:
            encrypted_key: Encrypted API key

        Returns:
            Decrypted API key

        Since:
            Version 1.0.0
        """
        # TODO: Implement actual decryption using cryptography library
        return encrypted_key

    async def search_with_temperature_variation(
        self,
        query: str,
        category: str,
        pharmaceutical_compound: str,
        process_id: str,
        request_id: str,
        correlation_id: str,
        temperature_strategy: Optional[TemperatureStrategy] = None,
        provider_name: Optional[str] = None
    ) -> Dict[str, List[TemperatureResult]]:
        """
        Execute searches across multiple temperatures for comprehensive results.

        Args:
            query: Search query
            category: Pharmaceutical category
            pharmaceutical_compound: Drug compound name
            process_id: Process tracking ID
            request_id: Drug request ID
            correlation_id: Request correlation ID
            temperature_strategy: Temperature configuration
            provider_name: Optional specific provider

        Returns:
            Dictionary mapping provider names to temperature results

        Since:
            Version 1.0.0
        """
        if not self._initialized:
            await self.initialize()

        # Initialize temperature manager if needed
        if not self.temperature_manager:
            if not self.persistence_manager:
                self.persistence_manager = DataPersistenceManager(
                    self.db,
                    self.audit_logger
                )
            self.temperature_manager = TemperatureSearchManager(
                self.persistence_manager,
                self.audit_logger
            )

        # Use default strategy if none provided
        if not temperature_strategy:
            temperature_strategy = TemperatureStrategy()

        results = {}

        # Determine which providers to use
        providers_to_use = []
        if provider_name and provider_name in self.providers:
            providers_to_use = [(provider_name, self.providers[provider_name])]
        else:
            providers_to_use = list(self.providers.items())

        # Execute temperature searches for each provider
        tasks = []
        for prov_name, provider in providers_to_use:
            # Get temperatures for this provider and category
            temperatures = temperature_strategy.get_temperatures_for_api(
                prov_name,
                category
            )

            # Create task for temperature searches
            task = self.temperature_manager.execute_temperature_searches(
                provider=provider,
                query=query,
                temperatures=temperatures,
                category=category,
                process_id=process_id,
                request_id=request_id,
                correlation_id=f"{correlation_id}_{prov_name}",
                pharmaceutical_compound=pharmaceutical_compound
            )
            tasks.append((prov_name, task))

        # Execute all temperature searches in parallel
        for prov_name, task in tasks:
            try:
                provider_results = await task
                results[prov_name] = provider_results

                # Track costs
                total_cost = sum(r.cost for r in provider_results if not r.cached)
                if total_cost > 0:
                    await self._track_cost(prov_name, category, total_cost)

            except Exception as e:
                logger.error(
                    "Temperature search failed for provider",
                    provider=prov_name,
                    error=str(e)
                )
                results[prov_name] = []

        return results

    async def analyze_temperature_effectiveness(
        self,
        temperature_results: Dict[str, List[TemperatureResult]],
        category: str
    ) -> Dict[str, Any]:
        """
        Analyze effectiveness of temperature variations across providers.

        Args:
            temperature_results: Results from temperature searches
            category: Pharmaceutical category

        Returns:
            Comprehensive effectiveness analysis

        Since:
            Version 1.0.0
        """
        if not self.temperature_manager:
            if not self.persistence_manager:
                self.persistence_manager = DataPersistenceManager(
                    self.db,
                    self.audit_logger
                )
            self.temperature_manager = TemperatureSearchManager(
                self.persistence_manager,
                self.audit_logger
            )

        analysis = {
            'category': category,
            'providers': {},
            'overall_recommendations': []
        }

        # Analyze each provider's results
        for provider_name, results in temperature_results.items():
            if results:
                provider_analysis = await self.temperature_manager.analyze_temperature_effectiveness(
                    results,
                    category
                )
                analysis['providers'][provider_name] = provider_analysis

        # Generate overall recommendations
        if analysis['providers']:
            # Find best performing temperature across all providers
            all_optimal = [
                p['optimal_temperature']
                for p in analysis['providers'].values()
                if 'optimal_temperature' in p
            ]

            if all_optimal:
                avg_optimal = sum(all_optimal) / len(all_optimal)
                analysis['recommended_temperature'] = round(avg_optimal, 2)

            # Check if all providers agree
            if len(set(all_optimal)) == 1:
                analysis['overall_recommendations'].append(
                    f"All providers perform best at temperature {all_optimal[0]}"
                )
            else:
                analysis['overall_recommendations'].append(
                    f"Provider-specific temperatures recommended (range: {min(all_optimal)}-{max(all_optimal)})"
                )

        return analysis

    async def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all configured providers.

        Returns:
            Dictionary with provider status information

        Since:
            Version 1.0.0
        """
        if not self._initialized:
            await self.initialize()

        status = {}

        for name, provider in self.providers.items():
            # Check health
            is_healthy = await provider.health_check()

            # Get circuit breaker state
            breaker_key = f"circuit_breaker:{name}"
            breaker_state = await self.redis_client.get(breaker_key) or 'closed'

            # Get failure count
            failure_key = f"provider_failures:{name}"
            failures = await self.redis_client.get(failure_key) or 0

            # Get today's cost
            daily_key = f"cost:daily:{name}:{datetime.utcnow().date()}"
            daily_cost = float(await self.redis_client.get(daily_key) or 0)

            status[name] = {
                'healthy': is_healthy,
                'circuit_breaker': breaker_state,
                'recent_failures': int(failures),
                'daily_cost': daily_cost,
                'rate_limits': provider.get_rate_limits()
            }

        return status

    async def search_with_hierarchical_processing(
        self,
        query: str,
        category: str,
        pharmaceutical_compound: str,
        process_id: str,
        request_id: str,
        correlation_id: str,
        temperature: float = 0.7,
        priority_overrides: Optional[Dict[str, int]] = None,
        early_termination: bool = True
    ) -> Dict[str, Any]:
        """
        Execute search with hierarchical source prioritization.

        Args:
            query: Search query
            category: Pharmaceutical category
            pharmaceutical_compound: Drug compound name
            process_id: Process tracking ID
            request_id: Drug request ID
            correlation_id: Request correlation ID
            temperature: Temperature value for search
            priority_overrides: Category-specific priority overrides
            early_termination: Enable early termination optimization

        Returns:
            Hierarchically processed results with metadata

        Since:
            Version 1.0.0
        """
        if not self._initialized:
            await self.initialize()

        # Initialize hierarchical processor if needed
        if not self.hierarchical_processor:
            self.hierarchical_processor = HierarchicalProcessor(
                self.source_classifier,
                self.audit_logger,
                min_coverage_threshold=0.8 if early_termination else 1.0
            )

        # Execute searches across all providers
        all_results = await self.search_all_providers(
            query,
            category,
            {'temperature': temperature}
        )

        # Process each provider's results hierarchically
        hierarchical_results = {}

        for response in all_results:
            provider_name = response.provider

            # Process hierarchically
            processed = await self.hierarchical_processor.process_hierarchically(
                response,
                category,
                pharmaceutical_compound,
                priority_overrides
            )

            # Score source reliability
            if response.sources:
                for source in response.sources:
                    classification = self.source_classifier.classify_source(source)
                    reliability_score = await self.reliability_scorer.score_reliability(
                        source,
                        classification
                    )
                    source.metadata = source.metadata or {}
                    source.metadata['reliability_score'] = reliability_score
                    source.metadata['priority'] = classification.priority.name

            hierarchical_results[provider_name] = processed

            # Store response with hierarchical metadata
            if self.persistence_manager:
                response.metadata = response.metadata or {}
                response.metadata['hierarchical_processing'] = {
                    'coverage_score': processed['coverage_score'],
                    'early_termination': processed['early_termination'],
                    'priority_distribution': processed['priority_distribution']
                }

                await self.persistence_manager.store_api_response(
                    response=response,
                    process_id=process_id,
                    request_id=request_id,
                    correlation_id=f"{correlation_id}_{provider_name}_hierarchical",
                    pharmaceutical_compound=pharmaceutical_compound,
                    category=category
                )

        # Generate summary
        summary = self._generate_hierarchical_summary(hierarchical_results)

        # Log hierarchical search
        await self.audit_logger.log_api_call(
            provider="hierarchical_processor",
            endpoint="search",
            request_data={
                'query': query,
                'category': category,
                'compound': pharmaceutical_compound,
                'early_termination': early_termination
            },
            response_status=200,
            response_time_ms=sum(
                r.get('processing_time_ms', 0)
                for r in hierarchical_results.values()
            ),
            drug_names=[pharmaceutical_compound]
        )

        return {
            'query': query,
            'category': category,
            'compound': pharmaceutical_compound,
            'provider_results': hierarchical_results,
            'summary': summary,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _generate_hierarchical_summary(
        self,
        hierarchical_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate summary of hierarchical processing results.

        Args:
            hierarchical_results: Results from hierarchical processing

        Returns:
            Summary statistics

        Since:
            Version 1.0.0
        """
        total_processed = 0
        total_available = 0
        avg_coverage = 0
        early_terminations = 0
        combined_distribution = {}

        for provider, result in hierarchical_results.items():
            total_processed += result['total_processed']
            total_available += result['total_available']
            avg_coverage += result['coverage_score']

            if result['early_termination']:
                early_terminations += 1

            # Combine priority distributions
            for priority, count in result['priority_distribution'].items():
                combined_distribution[priority] = \
                    combined_distribution.get(priority, 0) + count

        num_providers = len(hierarchical_results)

        return {
            'total_sources_processed': total_processed,
            'total_sources_available': total_available,
            'processing_efficiency': total_processed / max(total_available, 1),
            'average_coverage_score': avg_coverage / max(num_providers, 1),
            'early_termination_count': early_terminations,
            'combined_priority_distribution': combined_distribution,
            'providers_count': num_providers
        }

    async def get_category_priority_config(
        self,
        category: str
    ) -> Dict[str, Any]:
        """
        Get priority configuration for a pharmaceutical category.

        Args:
            category: Pharmaceutical category

        Returns:
            Priority configuration

        Since:
            Version 1.0.0
        """
        from ..database.models import PharmaceuticalCategory
        from sqlalchemy import select

        query = select(PharmaceuticalCategory).where(
            PharmaceuticalCategory.name == category
        )
        result = await self.db.execute(query)
        category_obj = result.scalar_one_or_none()

        if not category_obj:
            # Return default configuration
            return {
                'category': category,
                'priority_overrides': {},
                'min_coverage_threshold': 0.8,
                'early_termination_enabled': True
            }

        # Extract priority configuration from category
        priority_config = category_obj.priority_weights or {}

        return {
            'category': category,
            'priority_overrides': priority_config.get('overrides', {}),
            'min_coverage_threshold': priority_config.get('min_coverage', 0.8),
            'early_termination_enabled': priority_config.get('early_termination', True),
            'updated_at': category_obj.updated_at.isoformat()
        }

    async def update_source_reliability(
        self,
        source_url: str,
        was_accurate: bool,
        verification_method: str
    ):
        """
        Update reliability tracking for a source.

        Args:
            source_url: Source URL
            was_accurate: Whether information was accurate
            verification_method: How accuracy was verified

        Since:
            Version 1.0.0
        """
        await self.reliability_scorer.update_accuracy_tracking(
            source_url,
            was_accurate,
            verification_method
        )

        # Log reliability update
        await self.audit_logger.log_data_access(
            resource="source_reliability",
            action="update",
            user_id="system",
            success=True,
            drug_names=[]
        )

    async def shutdown(self):
        """
        Gracefully shutdown API manager.

        Since:
            Version 1.0.0
        """
        logger.info("Shutting down Multi-API Manager")
        self.providers.clear()
        self._initialized = False