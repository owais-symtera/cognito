"""
Connection pooling for API providers.

Manages HTTP connection pools for efficient API communication with
connection reuse, limits, and health monitoring.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import asyncio
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import httpx
import structlog

logger = structlog.get_logger(__name__)


class ConnectionPool:
    """
    Manages connection pools for multiple API providers.

    Provides efficient connection reuse, automatic retries, health checks,
    and connection limits for pharmaceutical intelligence API calls.

    Example:
        >>> pool = ConnectionPool()
        >>> async with pool.get_client('openai') as client:
        ...     response = await client.post(...)

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: int = 300,  # 5 minutes
        timeout: int = 30,
        enable_http2: bool = True
    ):
        """
        Initialize connection pool manager.

        Args:
            max_connections: Maximum total connections
            max_keepalive_connections: Maximum idle connections to keep
            keepalive_expiry: Seconds before closing idle connections
            timeout: Default timeout for requests
            enable_http2: Enable HTTP/2 support

        Since:
            Version 1.0.0
        """
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.keepalive_expiry = keepalive_expiry
        self.timeout = timeout
        self.enable_http2 = enable_http2

        # Provider-specific clients
        self._clients: Dict[str, httpx.AsyncClient] = {}
        self._client_config: Dict[str, Dict[str, Any]] = {}
        self._health_status: Dict[str, Dict[str, Any]] = {}
        self._connection_metrics: Dict[str, Dict[str, Any]] = {}

        # Lock for thread-safe client creation
        self._lock = asyncio.Lock()

    async def initialize_provider(
        self,
        provider: str,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """
        Initialize connection pool for a specific provider.

        Args:
            provider: Provider name
            base_url: Base URL for the provider
            headers: Default headers for requests
            **kwargs: Additional client configuration

        Since:
            Version 1.0.0
        """
        config = {
            'base_url': base_url,
            'headers': headers or {},
            'timeout': httpx.Timeout(
                timeout=kwargs.get('timeout', self.timeout),
                connect=kwargs.get('connect_timeout', 10.0),
                read=kwargs.get('read_timeout', 30.0),
                write=kwargs.get('write_timeout', 30.0)
            ),
            'limits': httpx.Limits(
                max_connections=kwargs.get('max_connections', self.max_connections),
                max_keepalive_connections=kwargs.get('max_keepalive', self.max_keepalive_connections),
                keepalive_expiry=kwargs.get('keepalive_expiry', self.keepalive_expiry)
            ),
            'http2': kwargs.get('http2', self.enable_http2)
        }

        self._client_config[provider] = config

        # Initialize metrics
        self._connection_metrics[provider] = {
            'requests_total': 0,
            'requests_success': 0,
            'requests_failed': 0,
            'total_response_time': 0,
            'active_connections': 0
        }

        # Initialize health status
        self._health_status[provider] = {
            'healthy': True,
            'last_check': datetime.utcnow(),
            'consecutive_failures': 0
        }

        logger.info(f"Initialized connection pool for {provider}", config=config)

    @asynccontextmanager
    async def get_client(self, provider: str):
        """
        Get HTTP client for a provider with connection pooling.

        Args:
            provider: Provider name

        Yields:
            httpx.AsyncClient instance

        Since:
            Version 1.0.0
        """
        async with self._lock:
            if provider not in self._clients:
                if provider not in self._client_config:
                    raise ValueError(f"Provider {provider} not initialized")

                config = self._client_config[provider]
                self._clients[provider] = httpx.AsyncClient(**config)

        client = self._clients[provider]

        # Track active connections
        self._connection_metrics[provider]['active_connections'] += 1

        try:
            yield client
        finally:
            self._connection_metrics[provider]['active_connections'] -= 1

    async def execute_request(
        self,
        provider: str,
        method: str,
        url: str,
        retry_count: int = 3,
        **kwargs
    ) -> httpx.Response:
        """
        Execute HTTP request with retries and metrics.

        Args:
            provider: Provider name
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            retry_count: Number of retry attempts
            **kwargs: Additional request parameters

        Returns:
            HTTP response

        Since:
            Version 1.0.0
        """
        metrics = self._connection_metrics[provider]
        metrics['requests_total'] += 1

        start_time = datetime.utcnow()
        last_exception = None

        for attempt in range(retry_count):
            try:
                async with self.get_client(provider) as client:
                    response = await client.request(method, url, **kwargs)
                    response.raise_for_status()

                    # Update metrics
                    elapsed = (datetime.utcnow() - start_time).total_seconds()
                    metrics['requests_success'] += 1
                    metrics['total_response_time'] += elapsed

                    # Update health status
                    self._update_health(provider, success=True)

                    return response

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e
                logger.warning(f"Connection error for {provider} (attempt {attempt + 1}): {e}")

                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code in [429, 503]:  # Rate limit or service unavailable
                    if attempt < retry_count - 1:
                        await asyncio.sleep(2 ** attempt)
                else:
                    break  # Don't retry on client errors

            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error for {provider}: {e}")
                break

        # Request failed after all retries
        metrics['requests_failed'] += 1
        self._update_health(provider, success=False)

        raise last_exception

    async def check_health(self, provider: str) -> bool:
        """
        Check health of provider connection.

        Args:
            provider: Provider name

        Returns:
            True if healthy

        Since:
            Version 1.0.0
        """
        try:
            async with self.get_client(provider) as client:
                # Perform lightweight health check (HEAD or GET)
                response = await client.head("/", timeout=5.0)
                is_healthy = response.status_code < 500

                self._update_health(provider, success=is_healthy)
                return is_healthy

        except Exception as e:
            logger.error(f"Health check failed for {provider}: {e}")
            self._update_health(provider, success=False)
            return False

    async def check_all_health(self) -> Dict[str, bool]:
        """
        Check health of all configured providers.

        Returns:
            Dictionary of provider -> health status

        Since:
            Version 1.0.0
        """
        results = {}

        for provider in self._client_config.keys():
            results[provider] = await self.check_health(provider)

        return results

    def _update_health(self, provider: str, success: bool):
        """
        Update health status for a provider.

        Args:
            provider: Provider name
            success: Whether last request succeeded

        Since:
            Version 1.0.0
        """
        health = self._health_status[provider]

        if success:
            health['consecutive_failures'] = 0
            health['healthy'] = True
        else:
            health['consecutive_failures'] += 1
            if health['consecutive_failures'] >= 3:
                health['healthy'] = False

        health['last_check'] = datetime.utcnow()

    def get_metrics(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Get connection metrics.

        Args:
            provider: Specific provider or None for all

        Returns:
            Metrics dictionary

        Since:
            Version 1.0.0
        """
        if provider:
            metrics = self._connection_metrics.get(provider, {})
            health = self._health_status.get(provider, {})

            if metrics:
                # Calculate averages
                total_requests = metrics['requests_total']
                if total_requests > 0:
                    metrics['success_rate'] = metrics['requests_success'] / total_requests
                    metrics['avg_response_time'] = metrics['total_response_time'] / metrics['requests_success'] if metrics['requests_success'] > 0 else 0
                else:
                    metrics['success_rate'] = 0
                    metrics['avg_response_time'] = 0

            return {
                'provider': provider,
                'metrics': metrics,
                'health': health
            }

        # Return all metrics
        all_metrics = {}
        for p in self._connection_metrics.keys():
            all_metrics[p] = self.get_metrics(p)

        return all_metrics

    async def close_provider(self, provider: str):
        """
        Close connection pool for a provider.

        Args:
            provider: Provider name

        Since:
            Version 1.0.0
        """
        if provider in self._clients:
            await self._clients[provider].aclose()
            del self._clients[provider]

            logger.info(f"Closed connection pool for {provider}")

    async def close_all(self):
        """
        Close all connection pools.

        Since:
            Version 1.0.0
        """
        for provider in list(self._clients.keys()):
            await self.close_provider(provider)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_all()

    def configure_circuit_breaker(
        self,
        provider: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ):
        """
        Configure circuit breaker for a provider.

        Args:
            provider: Provider name
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery

        Since:
            Version 1.0.0
        """
        if provider not in self._health_status:
            self._health_status[provider] = {}

        self._health_status[provider].update({
            'circuit_breaker_enabled': True,
            'failure_threshold': failure_threshold,
            'recovery_timeout': recovery_timeout,
            'circuit_state': 'closed',  # closed, open, half-open
            'circuit_opened_at': None
        })

    def _check_circuit_breaker(self, provider: str) -> bool:
        """
        Check if circuit breaker allows request.

        Args:
            provider: Provider name

        Returns:
            True if request allowed

        Since:
            Version 1.0.0
        """
        health = self._health_status.get(provider, {})

        if not health.get('circuit_breaker_enabled', False):
            return True

        state = health.get('circuit_state', 'closed')

        if state == 'closed':
            return True

        if state == 'open':
            # Check if recovery timeout has passed
            opened_at = health.get('circuit_opened_at')
            if opened_at:
                elapsed = (datetime.utcnow() - opened_at).total_seconds()
                if elapsed > health.get('recovery_timeout', 60):
                    # Move to half-open state
                    health['circuit_state'] = 'half-open'
                    logger.info(f"Circuit breaker for {provider} moved to half-open")
                    return True
            return False

        if state == 'half-open':
            # Allow one request to test
            return True

        return False


# Global connection pool instance
global_connection_pool = ConnectionPool()


def get_connection_pool() -> ConnectionPool:
    """
    Get global connection pool instance.

    Returns:
        ConnectionPool instance

    Since:
        Version 1.0.0
    """
    return global_connection_pool