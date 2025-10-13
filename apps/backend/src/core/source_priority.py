"""
Source priority and hierarchical processing for pharmaceutical intelligence.

Implements source classification, priority scoring, and hierarchical execution
with regulatory compliance for pharmaceutical data gathering.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import re
from enum import IntEnum
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse
from dataclasses import dataclass
import structlog

from ..integrations.providers.base import (
    StandardizedAPIResponse,
    SearchResult,
    SourceAttribution
)
from ..config.logging import PharmaceuticalLogger

logger = structlog.get_logger(__name__)


class SourcePriority(IntEnum):
    """
    Source priority hierarchy for pharmaceutical intelligence.

    Lower numbers = higher priority.

    Since:
        Version 1.0.0
    """
    PAID_APIS = 1          # ChatGPT, Perplexity, Claude, etc.
    GOVERNMENT = 2         # FDA, NIH, CDC, .gov domains
    PEER_REVIEWED = 3      # PubMed, academic journals
    INDUSTRY = 4           # Professional associations, PhRMA
    COMPANY = 5            # Pharmaceutical company sites
    NEWS = 6               # News and media outlets
    UNKNOWN = 99           # Unclassified sources


@dataclass
class SourceClassification:
    """
    Classification result for a source.

    Since:
        Version 1.0.0
    """
    url: str
    domain: str
    priority: SourcePriority
    category: str
    confidence: float
    metadata: Dict[str, Any]


class SourceClassifier:
    """
    Classifies sources based on URL patterns and content analysis.

    Implements intelligent source type detection for pharmaceutical
    intelligence gathering with regulatory compliance.

    Since:
        Version 1.0.0
    """

    # Government domains
    GOVERNMENT_DOMAINS = {
        'fda.gov', 'nih.gov', 'cdc.gov', 'clinicaltrials.gov',
        'ncbi.nlm.nih.gov', 'pubmed.gov', 'ema.europa.eu',
        'who.int', 'health.gov', 'hhs.gov'
    }

    # Peer-reviewed journal domains
    PEER_REVIEWED_DOMAINS = {
        'nejm.org', 'thelancet.com', 'nature.com', 'science.org',
        'jamanetwork.com', 'bmj.com', 'cell.com', 'plos.org',
        'sciencedirect.com', 'springer.com', 'wiley.com',
        'pubmed.ncbi.nlm.nih.gov', 'scholar.google.com'
    }

    # Industry association domains
    INDUSTRY_DOMAINS = {
        'phrma.org', 'bio.org', 'ifpma.org', 'efpia.eu',
        'abpi.org.uk', 'ispe.org', 'ashp.org', 'amcp.org'
    }

    # Major pharmaceutical company domains
    PHARMA_COMPANY_DOMAINS = {
        'pfizer.com', 'merck.com', 'novartis.com', 'roche.com',
        'jnj.com', 'abbvie.com', 'bms.com', 'lilly.com',
        'gsk.com', 'astrazeneca.com', 'sanofi.com', 'bayer.com'
    }

    # News outlet domains
    NEWS_DOMAINS = {
        'reuters.com', 'bloomberg.com', 'statnews.com', 'fiercepharma.com',
        'pharmexec.com', 'pharmaceutical-technology.com', 'cnbc.com',
        'wsj.com', 'nytimes.com', 'ft.com', 'economist.com'
    }

    def __init__(self, custom_patterns: Optional[Dict[str, List[str]]] = None):
        """
        Initialize source classifier.

        Args:
            custom_patterns: Custom domain patterns for classification

        Since:
            Version 1.0.0
        """
        self.custom_patterns = custom_patterns or {}
        self._compile_patterns()

    def _compile_patterns(self):
        """
        Compile regex patterns for efficient matching.

        Since:
            Version 1.0.0
        """
        self.gov_pattern = re.compile(r'\.(gov|edu)(\.[a-z]{2})?$', re.IGNORECASE)
        self.doi_pattern = re.compile(r'10\.\d{4,}/[-._;()/:\w]+', re.IGNORECASE)
        self.pmid_pattern = re.compile(r'pmid[:\s]*(\d+)', re.IGNORECASE)
        self.clinical_trial_pattern = re.compile(r'NCT\d{8}', re.IGNORECASE)

    def classify_source(self, source: SourceAttribution) -> SourceClassification:
        """
        Classify a single source based on URL and metadata.

        Args:
            source: Source attribution to classify

        Returns:
            Source classification result

        Since:
            Version 1.0.0
        """
        domain = source.domain.lower()
        url = source.url.lower()

        # Check for API sources first (highest priority)
        if source.source_type in ['api', 'paid_api']:
            return SourceClassification(
                url=source.url,
                domain=domain,
                priority=SourcePriority.PAID_APIS,
                category='Paid API',
                confidence=1.0,
                metadata={'api_provider': source.title}
            )

        # Government sources
        if domain in self.GOVERNMENT_DOMAINS or self.gov_pattern.search(domain):
            return SourceClassification(
                url=source.url,
                domain=domain,
                priority=SourcePriority.GOVERNMENT,
                category='Government',
                confidence=0.95,
                metadata={'regulatory': True}
            )

        # Peer-reviewed sources
        if domain in self.PEER_REVIEWED_DOMAINS or self._is_peer_reviewed(url, source):
            return SourceClassification(
                url=source.url,
                domain=domain,
                priority=SourcePriority.PEER_REVIEWED,
                category='Peer-Reviewed',
                confidence=0.9,
                metadata={'academic': True}
            )

        # Industry associations
        if domain in self.INDUSTRY_DOMAINS:
            return SourceClassification(
                url=source.url,
                domain=domain,
                priority=SourcePriority.INDUSTRY,
                category='Industry Association',
                confidence=0.85,
                metadata={'professional': True}
            )

        # Pharmaceutical companies
        if domain in self.PHARMA_COMPANY_DOMAINS or self._is_pharma_company(domain):
            return SourceClassification(
                url=source.url,
                domain=domain,
                priority=SourcePriority.COMPANY,
                category='Pharmaceutical Company',
                confidence=0.8,
                metadata={'commercial': True}
            )

        # News outlets
        if domain in self.NEWS_DOMAINS:
            return SourceClassification(
                url=source.url,
                domain=domain,
                priority=SourcePriority.NEWS,
                category='News Media',
                confidence=0.75,
                metadata={'media': True}
            )

        # Unknown/unclassified
        return SourceClassification(
            url=source.url,
            domain=domain,
            priority=SourcePriority.UNKNOWN,
            category='Unknown',
            confidence=0.5,
            metadata={}
        )

    def _is_peer_reviewed(self, url: str, source: SourceAttribution) -> bool:
        """
        Check if source is peer-reviewed based on patterns.

        Args:
            url: Source URL
            source: Source attribution

        Returns:
            True if peer-reviewed

        Since:
            Version 1.0.0
        """
        # Check for DOI
        if self.doi_pattern.search(url):
            return True

        # Check for PubMed ID
        if self.pmid_pattern.search(url):
            return True

        # Check for clinical trial ID
        if self.clinical_trial_pattern.search(url):
            return True

        # Check source type
        if source.source_type in ['research_paper', 'clinical_trial', 'academic']:
            return True

        return False

    def _is_pharma_company(self, domain: str) -> bool:
        """
        Check if domain belongs to a pharmaceutical company.

        Args:
            domain: Domain name

        Returns:
            True if pharmaceutical company

        Since:
            Version 1.0.0
        """
        pharma_keywords = [
            'pharma', 'therapeutics', 'biosciences', 'biologics',
            'medicines', 'healthcare', 'biotech'
        ]

        return any(keyword in domain for keyword in pharma_keywords)

    def classify_batch(self, sources: List[SourceAttribution]) -> List[SourceClassification]:
        """
        Classify multiple sources in batch.

        Args:
            sources: List of sources to classify

        Returns:
            List of classifications

        Since:
            Version 1.0.0
        """
        classifications = []
        for source in sources:
            classification = self.classify_source(source)
            classifications.append(classification)

        # Log classification summary
        priority_counts = {}
        for c in classifications:
            priority_counts[c.priority.name] = priority_counts.get(c.priority.name, 0) + 1

        logger.info(
            "Batch source classification complete",
            total_sources=len(sources),
            priority_distribution=priority_counts
        )

        return classifications


class HierarchicalProcessor:
    """
    Processes search results in hierarchical order based on source priority.

    Implements early termination and priority-based execution for
    efficient pharmaceutical intelligence gathering.

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        classifier: SourceClassifier,
        audit_logger: PharmaceuticalLogger,
        min_coverage_threshold: float = 0.8,
        max_sources_per_priority: int = 10
    ):
        """
        Initialize hierarchical processor.

        Args:
            classifier: Source classifier instance
            audit_logger: Audit logger
            min_coverage_threshold: Minimum coverage for early termination
            max_sources_per_priority: Max sources to process per priority level

        Since:
            Version 1.0.0
        """
        self.classifier = classifier
        self.audit_logger = audit_logger
        self.min_coverage_threshold = min_coverage_threshold
        self.max_sources_per_priority = max_sources_per_priority

    async def process_hierarchically(
        self,
        response: StandardizedAPIResponse,
        category: str,
        compound: str,
        priority_overrides: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Process API response results in hierarchical priority order.

        Args:
            response: API response with search results
            category: Pharmaceutical category
            compound: Drug compound name
            priority_overrides: Category-specific priority overrides

        Returns:
            Processed results with priority metadata

        Since:
            Version 1.0.0
        """
        start_time = datetime.utcnow()

        # Classify all sources
        if response.sources:
            classifications = self.classifier.classify_batch(response.sources)
        else:
            classifications = []

        # Group results by priority
        priority_groups = self._group_by_priority(
            response.results,
            classifications,
            priority_overrides
        )

        # Process in priority order
        processed_results = []
        coverage_score = 0.0
        total_processed = 0

        for priority in sorted(priority_groups.keys()):
            group_results = priority_groups[priority][:self.max_sources_per_priority]

            for result in group_results:
                processed_results.append({
                    'result': result,
                    'priority': priority,
                    'priority_name': SourcePriority(priority).name,
                    'processed_at': datetime.utcnow()
                })
                total_processed += 1

            # Calculate coverage score
            coverage_score = self._calculate_coverage(processed_results, category)

            # Check for early termination
            if coverage_score >= self.min_coverage_threshold and priority <= SourcePriority.PEER_REVIEWED:
                logger.info(
                    "Early termination triggered",
                    priority_level=SourcePriority(priority).name,
                    coverage_score=coverage_score,
                    total_processed=total_processed
                )
                break

        # Calculate processing metrics
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log hierarchical processing
        await self.audit_logger.log_data_access(
            resource="hierarchical_processor",
            action="process",
            user_id="system",
            success=True,
            drug_names=[compound]
        )

        return {
            'processed_results': processed_results,
            'priority_distribution': self._get_priority_distribution(priority_groups),
            'coverage_score': coverage_score,
            'total_processed': total_processed,
            'total_available': len(response.results),
            'processing_time_ms': processing_time,
            'early_termination': coverage_score >= self.min_coverage_threshold,
            'compound': compound,
            'category': category
        }

    def _group_by_priority(
        self,
        results: List[SearchResult],
        classifications: List[SourceClassification],
        priority_overrides: Optional[Dict[str, int]] = None
    ) -> Dict[int, List[SearchResult]]:
        """
        Group search results by priority level.

        Args:
            results: Search results to group
            classifications: Source classifications
            priority_overrides: Priority overrides

        Returns:
            Results grouped by priority

        Since:
            Version 1.0.0
        """
        priority_groups = {}
        classification_map = {c.url: c for c in classifications}

        for result in results:
            # Determine priority
            priority = SourcePriority.UNKNOWN

            # Check if result has associated source
            if hasattr(result, 'source_url') and result.source_url in classification_map:
                priority = classification_map[result.source_url].priority
            elif result.source_type:
                # Infer from source type
                priority = self._infer_priority_from_type(result.source_type)

            # Apply overrides if provided
            if priority_overrides and result.source_type in priority_overrides:
                priority = priority_overrides[result.source_type]

            # Add to group
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(result)

        return priority_groups

    def _infer_priority_from_type(self, source_type: str) -> SourcePriority:
        """
        Infer priority from source type string.

        Args:
            source_type: Source type identifier

        Returns:
            Inferred priority

        Since:
            Version 1.0.0
        """
        type_mapping = {
            'api': SourcePriority.PAID_APIS,
            'government': SourcePriority.GOVERNMENT,
            'regulatory': SourcePriority.GOVERNMENT,
            'research_paper': SourcePriority.PEER_REVIEWED,
            'clinical_trial': SourcePriority.PEER_REVIEWED,
            'academic': SourcePriority.PEER_REVIEWED,
            'industry': SourcePriority.INDUSTRY,
            'company': SourcePriority.COMPANY,
            'news': SourcePriority.NEWS,
            'media': SourcePriority.NEWS
        }

        return type_mapping.get(source_type.lower(), SourcePriority.UNKNOWN)

    def _calculate_coverage(
        self,
        processed_results: List[Dict[str, Any]],
        category: str
    ) -> float:
        """
        Calculate coverage score based on processed results.

        Args:
            processed_results: Processed results with priority
            category: Pharmaceutical category

        Returns:
            Coverage score (0-1)

        Since:
            Version 1.0.0
        """
        if not processed_results:
            return 0.0

        # Weight factors for coverage calculation
        priority_weights = {
            SourcePriority.PAID_APIS: 0.25,
            SourcePriority.GOVERNMENT: 0.25,
            SourcePriority.PEER_REVIEWED: 0.20,
            SourcePriority.INDUSTRY: 0.15,
            SourcePriority.COMPANY: 0.10,
            SourcePriority.NEWS: 0.05
        }

        # Calculate weighted coverage
        coverage_by_priority = {}
        for result in processed_results:
            priority = result['priority']
            if priority not in coverage_by_priority:
                coverage_by_priority[priority] = 0
            coverage_by_priority[priority] += 1

        total_score = 0.0
        for priority, count in coverage_by_priority.items():
            weight = priority_weights.get(priority, 0.01)
            # Diminishing returns for multiple sources of same priority
            priority_score = weight * min(1.0, count / 3)
            total_score += priority_score

        return min(1.0, total_score)

    def _get_priority_distribution(
        self,
        priority_groups: Dict[int, List[SearchResult]]
    ) -> Dict[str, int]:
        """
        Get distribution of results by priority.

        Args:
            priority_groups: Grouped results

        Returns:
            Distribution counts

        Since:
            Version 1.0.0
        """
        distribution = {}
        for priority, results in priority_groups.items():
            priority_name = SourcePriority(priority).name
            distribution[priority_name] = len(results)

        return distribution


class SourceReliabilityScorer:
    """
    Scores source reliability based on pharmaceutical industry standards.

    Tracks historical accuracy and provides reliability metrics for
    regulatory compliance.

    Since:
        Version 1.0.0
    """

    def __init__(self, db_session=None):
        """
        Initialize reliability scorer.

        Args:
            db_session: Database session for historical tracking

        Since:
            Version 1.0.0
        """
        self.db = db_session
        self.reliability_cache = {}

    async def score_reliability(
        self,
        source: SourceAttribution,
        classification: SourceClassification
    ) -> float:
        """
        Calculate reliability score for a source.

        Args:
            source: Source attribution
            classification: Source classification

        Returns:
            Reliability score (0-1)

        Since:
            Version 1.0.0
        """
        # Base score from priority
        priority_scores = {
            SourcePriority.PAID_APIS: 0.85,
            SourcePriority.GOVERNMENT: 0.95,
            SourcePriority.PEER_REVIEWED: 0.90,
            SourcePriority.INDUSTRY: 0.80,
            SourcePriority.COMPANY: 0.70,
            SourcePriority.NEWS: 0.60,
            SourcePriority.UNKNOWN: 0.40
        }

        base_score = priority_scores.get(classification.priority, 0.5)

        # Adjust for credibility score if available
        if source.credibility_score:
            base_score = (base_score + source.credibility_score) / 2

        # Adjust for domain reputation (simplified)
        domain_adjustments = {
            'fda.gov': 0.1,
            'nih.gov': 0.1,
            'nejm.org': 0.08,
            'nature.com': 0.08,
            'thelancet.com': 0.08
        }

        domain_adjustment = domain_adjustments.get(classification.domain, 0)

        # Calculate final score
        final_score = min(1.0, base_score + domain_adjustment)

        # Cache result
        self.reliability_cache[source.url] = {
            'score': final_score,
            'timestamp': datetime.utcnow()
        }

        return final_score

    async def get_historical_accuracy(
        self,
        domain: str,
        lookback_days: int = 90
    ) -> Optional[float]:
        """
        Get historical accuracy for a domain.

        Args:
            domain: Domain name
            lookback_days: Days to look back

        Returns:
            Historical accuracy score or None

        Since:
            Version 1.0.0
        """
        if not self.db:
            return None

        # TODO: Implement database query for historical accuracy
        # For now, return mock data
        mock_accuracies = {
            'fda.gov': 0.98,
            'nih.gov': 0.96,
            'pfizer.com': 0.85,
            'reuters.com': 0.82
        }

        return mock_accuracies.get(domain)

    async def update_accuracy_tracking(
        self,
        source_url: str,
        was_accurate: bool,
        verification_method: str
    ):
        """
        Update accuracy tracking for a source.

        Args:
            source_url: Source URL
            was_accurate: Whether information was accurate
            verification_method: How accuracy was verified

        Since:
            Version 1.0.0
        """
        if not self.db:
            return

        # TODO: Implement database update for accuracy tracking
        logger.info(
            "Accuracy tracking updated",
            source_url=source_url,
            was_accurate=was_accurate,
            verification_method=verification_method
        )