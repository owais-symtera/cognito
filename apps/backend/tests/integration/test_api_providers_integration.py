"""
Integration tests for API providers with real API calls.

Tests actual API integration with proper error handling, rate limiting,
and response validation. Requires API keys to be configured.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
import asyncio
import os
from typing import Dict, Any
from datetime import datetime
from unittest.mock import patch

from src.integrations.providers import (
    ChatGPTProvider,
    AnthropicProvider,
    GeminiProvider,
    GrokProvider,
    PerplexityProvider,
    TavilyProvider
)
from src.integrations.connection_pool import ConnectionPool
from src.config.llm_config import get_llm_config


# Skip integration tests if not explicitly enabled
INTEGRATION_TESTS_ENABLED = os.getenv('RUN_INTEGRATION_TESTS', 'false').lower() == 'true'
SKIP_MESSAGE = "Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to enable."


@pytest.fixture
async def connection_pool():
    """Create connection pool for tests."""
    pool = ConnectionPool(
        max_connections=10,
        max_keepalive_connections=5,
        timeout=60  # Longer timeout for API calls
    )

    yield pool

    await pool.close_all()


@pytest.fixture
def test_query():
    """Standard test query for pharmaceutical intelligence."""
    return "What are the latest FDA-approved treatments for Type 2 diabetes in 2024?"


@pytest.fixture
def validation_keywords():
    """Keywords to validate in responses."""
    return ["FDA", "diabetes", "treatment", "approved", "2024"]


@pytest.mark.skipif(not INTEGRATION_TESTS_ENABLED, reason=SKIP_MESSAGE)
class TestChatGPTIntegration:
    """Integration tests for ChatGPT/OpenAI provider."""

    @pytest.mark.asyncio
    async def test_chatgpt_search(self, test_query, validation_keywords):
        """Test ChatGPT search functionality."""
        llm_config = get_llm_config()

        if not llm_config.is_provider_configured('openai'):
            pytest.skip("OpenAI API key not configured")

        provider = ChatGPTProvider()

        response = await provider.search(
            query=test_query,
            temperature=0.7,
            max_results=5
        )

        # Validate response structure
        assert response.provider == "chatgpt"
        assert response.query == test_query
        assert response.total_results > 0
        assert len(response.results) > 0
        assert response.cost > 0
        assert response.response_time_ms > 0

        # Validate content
        content = " ".join([r.content for r in response.results]).lower()
        for keyword in validation_keywords:
            assert keyword.lower() in content

    @pytest.mark.asyncio
    async def test_chatgpt_rate_limiting(self):
        """Test rate limiting handling."""
        llm_config = get_llm_config()

        if not llm_config.is_provider_configured('openai'):
            pytest.skip("OpenAI API key not configured")

        provider = ChatGPTProvider()

        # Make multiple rapid requests
        queries = [
            "Diabetes medication",
            "Cancer treatments",
            "Vaccine development"
        ]

        tasks = []
        for query in queries:
            tasks.append(provider.search(query, temperature=0.5))

        # Should handle rate limiting gracefully
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check all requests completed
        for result in results:
            if not isinstance(result, Exception):
                assert result.total_results > 0

    @pytest.mark.asyncio
    async def test_chatgpt_error_handling(self):
        """Test error handling with invalid parameters."""
        provider = ChatGPTProvider(api_key="invalid_key_test")

        with pytest.raises(Exception):
            await provider.search(
                query="Test query",
                temperature=2.0  # Invalid temperature
            )


@pytest.mark.skipif(not INTEGRATION_TESTS_ENABLED, reason=SKIP_MESSAGE)
class TestAnthropicIntegration:
    """Integration tests for Anthropic Claude provider."""

    @pytest.mark.asyncio
    async def test_claude_search(self, test_query, validation_keywords):
        """Test Claude search functionality."""
        llm_config = get_llm_config()

        if not llm_config.is_provider_configured('anthropic'):
            pytest.skip("Anthropic API key not configured")

        provider = AnthropicProvider()

        response = await provider.search(
            query=test_query,
            temperature=0.7,
            max_results=5
        )

        # Validate response
        assert response.provider == "anthropic"
        assert response.total_results > 0
        assert response.confidence_score > 0.8  # Claude typically has high confidence

        # Validate sections
        sections = [r.metadata.get('section_type') for r in response.results]
        assert 'clinical_analysis' in sections or 'regulatory_analysis' in sections

    @pytest.mark.asyncio
    async def test_claude_complex_analysis(self):
        """Test Claude's complex pharmaceutical analysis."""
        llm_config = get_llm_config()

        if not llm_config.is_provider_configured('anthropic'):
            pytest.skip("Anthropic API key not configured")

        provider = AnthropicProvider()

        complex_query = """
        Compare the efficacy and safety profiles of SGLT2 inhibitors versus
        GLP-1 receptor agonists for Type 2 diabetes management, including
        cardiovascular outcomes and renal benefits.
        """

        response = await provider.search(
            query=complex_query,
            temperature=0.5  # Lower temperature for more focused analysis
        )

        # Should have comprehensive analysis
        assert response.total_results >= 3
        assert any("cardiovascular" in r.content.lower() for r in response.results)
        assert any("renal" in r.content.lower() or "kidney" in r.content.lower() for r in response.results)


@pytest.mark.skipif(not INTEGRATION_TESTS_ENABLED, reason=SKIP_MESSAGE)
class TestGeminiIntegration:
    """Integration tests for Google Gemini provider."""

    @pytest.mark.asyncio
    async def test_gemini_search(self, test_query):
        """Test Gemini search functionality."""
        llm_config = get_llm_config()

        if not llm_config.is_provider_configured('google'):
            pytest.skip("Gemini API key not configured")

        provider = GeminiProvider()

        response = await provider.search(
            query=test_query,
            temperature=0.7
        )

        # Validate response
        assert response.provider == "gemini"
        assert response.total_results > 0
        assert not response.metadata.get('safety_filtered', False)

    @pytest.mark.asyncio
    async def test_gemini_safety_settings(self):
        """Test Gemini safety settings for medical content."""
        llm_config = get_llm_config()

        if not llm_config.is_provider_configured('google'):
            pytest.skip("Gemini API key not configured")

        provider = GeminiProvider()

        # Medical query should not be filtered
        medical_query = "What are the side effects of chemotherapy drugs?"

        response = await provider.search(
            query=medical_query,
            temperature=0.5
        )

        # Medical content should pass safety filters
        assert not response.metadata.get('safety_filtered', False)
        assert response.total_results > 0


@pytest.mark.skipif(not INTEGRATION_TESTS_ENABLED, reason=SKIP_MESSAGE)
class TestPerplexityIntegration:
    """Integration tests for Perplexity provider."""

    @pytest.mark.asyncio
    async def test_perplexity_real_time_search(self, test_query):
        """Test Perplexity real-time search capabilities."""
        llm_config = get_llm_config()

        if not llm_config.is_provider_configured('perplexity'):
            pytest.skip("Perplexity API key not configured")

        provider = PerplexityProvider()

        response = await provider.search(
            query=test_query,
            temperature=0.5
        )

        # Validate response
        assert response.provider == "perplexity"
        assert response.total_results > 0

        # Should have citations
        assert len(response.sources) > 0
        assert any(s.source_type in ["regulatory", "clinical_trial"] for s in response.sources)

    @pytest.mark.asyncio
    async def test_perplexity_domain_filtering(self):
        """Test Perplexity domain filtering for pharmaceutical sources."""
        llm_config = get_llm_config()

        if not llm_config.is_provider_configured('perplexity'):
            pytest.skip("Perplexity API key not configured")

        provider = PerplexityProvider()

        response = await provider.search(
            query="Clinical trials for Alzheimer's disease 2024",
            temperature=0.3
        )

        # Check for pharmaceutical domains in sources
        domains = [s.domain for s in response.sources]
        pharma_domains = ["fda.gov", "clinicaltrials.gov", "pubmed.ncbi.nlm.nih.gov"]

        assert any(domain in domains for domain in pharma_domains)


@pytest.mark.skipif(not INTEGRATION_TESTS_ENABLED, reason=SKIP_MESSAGE)
class TestTavilyIntegration:
    """Integration tests for Tavily search provider."""

    @pytest.mark.asyncio
    async def test_tavily_deep_search(self, test_query):
        """Test Tavily deep web search."""
        llm_config = get_llm_config()

        if not llm_config.is_provider_configured('tavily'):
            pytest.skip("Tavily API key not configured")

        provider = TavilyProvider()

        response = await provider.search(
            query=test_query,
            max_results=10
        )

        # Validate response
        assert response.provider == "tavily"
        assert response.total_results > 0
        assert response.temperature == 0.0  # Search doesn't use temperature

        # Should have answer synthesis
        assert any(r.metadata.get('is_answer', False) for r in response.results)

    @pytest.mark.asyncio
    async def test_tavily_pharmaceutical_domains(self):
        """Test Tavily focus on pharmaceutical domains."""
        llm_config = get_llm_config()

        if not llm_config.is_provider_configured('tavily'):
            pytest.skip("Tavily API key not configured")

        provider = TavilyProvider()

        response = await provider.search(
            query="FDA drug recalls 2024",
            max_results=5
        )

        # Should prioritize FDA and regulatory sources
        source_types = [s.source_type for s in response.sources]
        assert "regulatory" in source_types


@pytest.mark.skipif(not INTEGRATION_TESTS_ENABLED, reason=SKIP_MESSAGE)
class TestConnectionPoolIntegration:
    """Integration tests for connection pooling."""

    @pytest.mark.asyncio
    async def test_connection_pool_multiple_providers(self, connection_pool):
        """Test connection pool with multiple providers."""
        llm_config = get_llm_config()

        # Initialize pools for configured providers
        if llm_config.is_provider_configured('openai'):
            await connection_pool.initialize_provider(
                'openai',
                'https://api.openai.com/v1',
                {'Authorization': f'Bearer {llm_config.get_provider_config("openai").api_key}'}
            )

        if llm_config.is_provider_configured('anthropic'):
            await connection_pool.initialize_provider(
                'anthropic',
                'https://api.anthropic.com',
                {'x-api-key': llm_config.get_provider_config('anthropic').api_key}
            )

        # Check health
        health_status = await connection_pool.check_all_health()

        assert len(health_status) > 0
        # At least one provider should be healthy
        assert any(status for status in health_status.values())

    @pytest.mark.asyncio
    async def test_connection_pool_metrics(self, connection_pool):
        """Test connection pool metrics collection."""
        llm_config = get_llm_config()

        if not llm_config.is_provider_configured('openai'):
            pytest.skip("No providers configured")

        await connection_pool.initialize_provider(
            'openai',
            'https://api.openai.com/v1',
            {'Authorization': f'Bearer {llm_config.get_provider_config("openai").api_key}'}
        )

        # Make a request
        try:
            await connection_pool.execute_request(
                'openai',
                'GET',
                '/models'
            )
        except:
            pass  # We're testing metrics, not the request itself

        # Get metrics
        metrics = connection_pool.get_metrics('openai')

        assert metrics['metrics']['requests_total'] > 0
        assert 'success_rate' in metrics['metrics']
        assert 'health' in metrics


@pytest.mark.skipif(not INTEGRATION_TESTS_ENABLED, reason=SKIP_MESSAGE)
class TestMultiProviderComparison:
    """Test comparing results across multiple providers."""

    @pytest.mark.asyncio
    async def test_multi_provider_consensus(self, test_query):
        """Test getting consensus from multiple providers."""
        llm_config = get_llm_config()

        providers = []

        if llm_config.is_provider_configured('openai'):
            providers.append(ChatGPTProvider())

        if llm_config.is_provider_configured('anthropic'):
            providers.append(AnthropicProvider())

        if llm_config.is_provider_configured('perplexity'):
            providers.append(PerplexityProvider())

        if len(providers) < 2:
            pytest.skip("Need at least 2 configured providers for comparison")

        # Get responses from all providers
        tasks = [p.search(test_query, temperature=0.5) for p in providers]
        responses = await asyncio.gather(*tasks)

        # Compare relevance scores
        relevance_scores = [r.relevance_score for r in responses]

        # All providers should give reasonably high relevance
        assert all(score > 0.7 for score in relevance_scores)

        # Check for common topics across providers
        all_content = []
        for response in responses:
            all_content.extend([r.content.lower() for r in response.results])

        # Common pharmaceutical terms should appear across providers
        common_terms = ["fda", "diabetes", "treatment", "medication"]
        for term in common_terms:
            assert sum(1 for content in all_content if term in content) >= len(providers)

    @pytest.mark.asyncio
    async def test_cost_comparison(self, test_query):
        """Compare costs across providers."""
        llm_config = get_llm_config()

        costs = {}

        if llm_config.is_provider_configured('openai'):
            provider = ChatGPTProvider()
            response = await provider.search(test_query, temperature=0.5)
            costs['openai'] = response.cost

        if llm_config.is_provider_configured('anthropic'):
            provider = AnthropicProvider()
            response = await provider.search(test_query, temperature=0.5)
            costs['anthropic'] = response.cost

        if llm_config.is_provider_configured('tavily'):
            provider = TavilyProvider()
            response = await provider.search(test_query)
            costs['tavily'] = response.cost

        if len(costs) < 2:
            pytest.skip("Need at least 2 providers for cost comparison")

        # All costs should be reasonable (< $1 per query)
        assert all(cost < 1.0 for cost in costs.values())

        # Log cost comparison for analysis
        print(f"Cost comparison: {costs}")


# Performance benchmarking tests
@pytest.mark.skipif(not INTEGRATION_TESTS_ENABLED, reason=SKIP_MESSAGE)
class TestPerformanceBenchmark:
    """Performance benchmarking for API providers."""

    @pytest.mark.asyncio
    async def test_response_time_benchmark(self, test_query):
        """Benchmark response times across providers."""
        llm_config = get_llm_config()

        benchmarks = {}

        providers = [
            ('openai', ChatGPTProvider),
            ('anthropic', AnthropicProvider),
            ('perplexity', PerplexityProvider),
            ('tavily', TavilyProvider)
        ]

        for name, ProviderClass in providers:
            if llm_config.is_provider_configured(name):
                provider = ProviderClass()
                start = datetime.utcnow()

                try:
                    response = await provider.search(test_query, temperature=0.5)
                    elapsed = (datetime.utcnow() - start).total_seconds()

                    benchmarks[name] = {
                        'response_time_ms': response.response_time_ms,
                        'total_time_s': elapsed,
                        'results_count': response.total_results
                    }
                except Exception as e:
                    benchmarks[name] = {'error': str(e)}

        # Log benchmarks
        print(f"Performance benchmarks: {benchmarks}")

        # At least one provider should respond within reasonable time
        if benchmarks:
            valid_times = [
                b['total_time_s'] for b in benchmarks.values()
                if 'total_time_s' in b
            ]
            if valid_times:
                assert min(valid_times) < 30  # Should respond within 30 seconds