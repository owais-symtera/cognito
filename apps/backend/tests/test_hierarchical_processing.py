"""
Tests for hierarchical source priority processing.

Validates source classification, hierarchical execution, early termination,
and reliability scoring for pharmaceutical intelligence gathering.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from typing import List

from src.core.source_priority import (
    SourcePriority,
    SourceClassifier,
    SourceClassification,
    HierarchicalProcessor,
    SourceReliabilityScorer
)
from src.integrations.providers.base import (
    StandardizedAPIResponse,
    SearchResult,
    SourceAttribution
)


@pytest.fixture
def source_classifier():
    """Create source classifier instance."""
    return SourceClassifier()


@pytest.fixture
def mock_audit_logger():
    """Create mock audit logger."""
    logger = AsyncMock()
    logger.log_data_access = AsyncMock()
    logger.log_api_call = AsyncMock()
    return logger


@pytest.fixture
def sample_sources():
    """Create sample sources for testing."""
    return [
        SourceAttribution(
            title="FDA Drug Database",
            url="https://www.fda.gov/drugs",
            domain="fda.gov",
            source_type="government",
            credibility_score=0.98
        ),
        SourceAttribution(
            title="New England Journal of Medicine",
            url="https://www.nejm.org/doi/full/10.1056/NEJMoa2035389",
            domain="nejm.org",
            source_type="research_paper",
            credibility_score=0.95
        ),
        SourceAttribution(
            title="Pfizer Press Release",
            url="https://www.pfizer.com/news",
            domain="pfizer.com",
            source_type="company",
            credibility_score=0.75
        ),
        SourceAttribution(
            title="Reuters Health",
            url="https://www.reuters.com/health",
            domain="reuters.com",
            source_type="news",
            credibility_score=0.70
        ),
        SourceAttribution(
            title="ChatGPT Response",
            url="api://chatgpt",
            domain="openai.com",
            source_type="api",
            credibility_score=0.85
        )
    ]


@pytest.fixture
def sample_api_response(sample_sources):
    """Create sample API response with varied sources."""
    return StandardizedAPIResponse(
        provider="test_provider",
        query="Drug interactions",
        temperature=0.7,
        results=[
            SearchResult(
                title=f"Result from {source.title}",
                content=f"Content from {source.domain}",
                relevance_score=0.8 + i * 0.02,
                source_type=source.source_type,
                metadata={'source_url': source.url}
            )
            for i, source in enumerate(sample_sources)
        ],
        sources=sample_sources,
        total_results=len(sample_sources),
        response_time_ms=1000,
        cost=0.05,
        relevance_score=0.85,
        confidence_score=0.88,
        timestamp=datetime.utcnow()
    )


class TestSourceClassifier:
    """Tests for source classification."""

    def test_government_classification(self, source_classifier):
        """Test classification of government sources."""
        source = SourceAttribution(
            title="FDA Guidance",
            url="https://www.fda.gov/guidance",
            domain="fda.gov",
            source_type="regulatory",
            credibility_score=0.98
        )

        classification = source_classifier.classify_source(source)

        assert classification.priority == SourcePriority.GOVERNMENT
        assert classification.category == "Government"
        assert classification.confidence >= 0.9
        assert classification.metadata.get('regulatory') is True

    def test_peer_reviewed_classification(self, source_classifier):
        """Test classification of peer-reviewed sources."""
        # Test with DOI
        source = SourceAttribution(
            title="Nature Article",
            url="https://doi.org/10.1038/s41586-021-03819-2",
            domain="nature.com",
            source_type="research_paper",
            credibility_score=0.92
        )

        classification = source_classifier.classify_source(source)

        assert classification.priority == SourcePriority.PEER_REVIEWED
        assert classification.category == "Peer-Reviewed"
        assert classification.metadata.get('academic') is True

    def test_api_source_classification(self, source_classifier):
        """Test classification of API sources."""
        source = SourceAttribution(
            title="ChatGPT",
            url="api://chatgpt",
            domain="openai.com",
            source_type="paid_api",
            credibility_score=0.85
        )

        classification = source_classifier.classify_source(source)

        assert classification.priority == SourcePriority.PAID_APIS
        assert classification.category == "Paid API"
        assert classification.confidence == 1.0

    def test_pharma_company_classification(self, source_classifier):
        """Test classification of pharmaceutical company sources."""
        source = SourceAttribution(
            title="Merck Research",
            url="https://www.merck.com/research",
            domain="merck.com",
            source_type="company",
            credibility_score=0.75
        )

        classification = source_classifier.classify_source(source)

        assert classification.priority == SourcePriority.COMPANY
        assert classification.category == "Pharmaceutical Company"
        assert classification.metadata.get('commercial') is True

    def test_batch_classification(self, source_classifier, sample_sources):
        """Test batch classification of multiple sources."""
        classifications = source_classifier.classify_batch(sample_sources)

        assert len(classifications) == len(sample_sources)

        # Check priority distribution
        priorities = [c.priority for c in classifications]
        assert SourcePriority.PAID_APIS in priorities
        assert SourcePriority.GOVERNMENT in priorities
        assert SourcePriority.PEER_REVIEWED in priorities
        assert SourcePriority.COMPANY in priorities
        assert SourcePriority.NEWS in priorities


class TestHierarchicalProcessor:
    """Tests for hierarchical processing."""

    @pytest.mark.asyncio
    async def test_hierarchical_processing_order(
        self,
        source_classifier,
        mock_audit_logger,
        sample_api_response
    ):
        """Test that sources are processed in priority order."""
        processor = HierarchicalProcessor(
            source_classifier,
            mock_audit_logger,
            min_coverage_threshold=1.0,  # Disable early termination
            max_sources_per_priority=10
        )

        result = await processor.process_hierarchically(
            sample_api_response,
            "Test Category",
            "Test Drug"
        )

        # Verify processing order
        processed = result['processed_results']
        assert len(processed) > 0

        # Check that higher priority sources come first
        priorities = [r['priority'] for r in processed]
        assert priorities == sorted(priorities)

    @pytest.mark.asyncio
    async def test_early_termination(
        self,
        source_classifier,
        mock_audit_logger,
        sample_api_response
    ):
        """Test early termination when coverage threshold is met."""
        processor = HierarchicalProcessor(
            source_classifier,
            mock_audit_logger,
            min_coverage_threshold=0.5,  # Low threshold for early termination
            max_sources_per_priority=10
        )

        result = await processor.process_hierarchically(
            sample_api_response,
            "Test Category",
            "Test Drug"
        )

        # Should terminate early
        assert result['early_termination'] is True
        assert result['total_processed'] < result['total_available']
        assert result['coverage_score'] >= 0.5

    @pytest.mark.asyncio
    async def test_coverage_calculation(
        self,
        source_classifier,
        mock_audit_logger
    ):
        """Test coverage score calculation."""
        processor = HierarchicalProcessor(
            source_classifier,
            mock_audit_logger
        )

        # Test with high-priority sources
        high_priority_response = StandardizedAPIResponse(
            provider="test",
            query="test",
            temperature=0.7,
            results=[
                SearchResult(
                    title="FDA Result",
                    content="FDA content",
                    relevance_score=0.9,
                    source_type="government"
                ),
                SearchResult(
                    title="NIH Result",
                    content="NIH content",
                    relevance_score=0.88,
                    source_type="government"
                )
            ],
            sources=[],
            total_results=2,
            response_time_ms=500,
            cost=0.02,
            relevance_score=0.89,
            confidence_score=0.9,
            timestamp=datetime.utcnow()
        )

        result = await processor.process_hierarchically(
            high_priority_response,
            "Test Category",
            "Test Drug"
        )

        # High-priority sources should yield higher coverage
        assert result['coverage_score'] > 0.4

    @pytest.mark.asyncio
    async def test_priority_distribution(
        self,
        source_classifier,
        mock_audit_logger,
        sample_api_response
    ):
        """Test priority distribution reporting."""
        processor = HierarchicalProcessor(
            source_classifier,
            mock_audit_logger
        )

        result = await processor.process_hierarchically(
            sample_api_response,
            "Test Category",
            "Test Drug"
        )

        distribution = result['priority_distribution']
        assert isinstance(distribution, dict)
        assert len(distribution) > 0

        # Should have multiple priority levels
        assert "GOVERNMENT" in distribution or "PEER_REVIEWED" in distribution

    @pytest.mark.asyncio
    async def test_priority_overrides(
        self,
        source_classifier,
        mock_audit_logger,
        sample_api_response
    ):
        """Test category-specific priority overrides."""
        processor = HierarchicalProcessor(
            source_classifier,
            mock_audit_logger
        )

        # Override news to higher priority
        priority_overrides = {
            'news': SourcePriority.PEER_REVIEWED
        }

        result = await processor.process_hierarchically(
            sample_api_response,
            "Test Category",
            "Test Drug",
            priority_overrides
        )

        # News sources should be processed earlier due to override
        processed = result['processed_results']
        news_results = [
            r for r in processed
            if 'reuters' in str(r['result'].content).lower()
        ]

        if news_results:
            # Check that news was given higher priority
            assert news_results[0]['priority'] == SourcePriority.PEER_REVIEWED


class TestSourceReliabilityScorer:
    """Tests for source reliability scoring."""

    @pytest.mark.asyncio
    async def test_reliability_scoring(self):
        """Test reliability score calculation."""
        scorer = SourceReliabilityScorer()

        source = SourceAttribution(
            title="FDA Database",
            url="https://www.fda.gov/drugs",
            domain="fda.gov",
            source_type="government",
            credibility_score=0.95
        )

        classification = SourceClassification(
            url=source.url,
            domain=source.domain,
            priority=SourcePriority.GOVERNMENT,
            category="Government",
            confidence=0.95,
            metadata={}
        )

        score = await scorer.score_reliability(source, classification)

        # Government sources should have high reliability
        assert score > 0.9
        assert score <= 1.0

    @pytest.mark.asyncio
    async def test_reliability_with_credibility(self):
        """Test reliability scoring with credibility adjustment."""
        scorer = SourceReliabilityScorer()

        source = SourceAttribution(
            title="Research Paper",
            url="https://example.com/paper",
            domain="example.com",
            source_type="research",
            credibility_score=0.6
        )

        classification = SourceClassification(
            url=source.url,
            domain=source.domain,
            priority=SourcePriority.UNKNOWN,
            category="Unknown",
            confidence=0.5,
            metadata={}
        )

        score = await scorer.score_reliability(source, classification)

        # Should average base score with credibility
        assert 0.4 <= score <= 0.6

    @pytest.mark.asyncio
    async def test_domain_reputation_adjustment(self):
        """Test reliability adjustment for reputable domains."""
        scorer = SourceReliabilityScorer()

        source = SourceAttribution(
            title="NIH Article",
            url="https://www.nih.gov/article",
            domain="nih.gov",
            source_type="government",
            credibility_score=0.9
        )

        classification = SourceClassification(
            url=source.url,
            domain="nih.gov",
            priority=SourcePriority.GOVERNMENT,
            category="Government",
            confidence=0.95,
            metadata={}
        )

        score = await scorer.score_reliability(source, classification)

        # NIH should get bonus adjustment
        assert score > 0.95

    @pytest.mark.asyncio
    async def test_reliability_caching(self):
        """Test that reliability scores are cached."""
        scorer = SourceReliabilityScorer()

        source = SourceAttribution(
            title="Test Source",
            url="https://test.com",
            domain="test.com",
            source_type="unknown",
            credibility_score=0.5
        )

        classification = SourceClassification(
            url=source.url,
            domain=source.domain,
            priority=SourcePriority.UNKNOWN,
            category="Unknown",
            confidence=0.5,
            metadata={}
        )

        # Score twice
        score1 = await scorer.score_reliability(source, classification)
        score2 = await scorer.score_reliability(source, classification)

        assert score1 == score2

        # Check cache
        assert source.url in scorer.reliability_cache
        cached = scorer.reliability_cache[source.url]
        assert cached['score'] == score1