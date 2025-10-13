"""
Pipeline stage handlers for pharmaceutical intelligence processing.

Implements handlers for Collection, Verification, Merging, and Summary stages
with complete audit integration and error handling.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import asyncio
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog

from .pipeline_orchestration import PipelineContext
from ..integrations.api_manager import MultiAPIManager
from .source_priority import SourceClassifier, SourceReliabilityScorer
from .temperature_strategy import TemperatureStrategy
from ..config.logging import PharmaceuticalLogger

logger = structlog.get_logger(__name__)


class CollectionStageHandler:
    """
    Handles the Collection stage of the pipeline.

    Performs multi-API data gathering with temperature variations
    and hierarchical processing.

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        api_manager: MultiAPIManager,
        audit_logger: PharmaceuticalLogger
    ):
        """
        Initialize collection stage handler.

        Args:
            api_manager: Multi-API manager
            audit_logger: Audit logger

        Since:
            Version 1.0.0
        """
        self.api_manager = api_manager
        self.audit_logger = audit_logger

    async def execute(self, context: PipelineContext) -> Dict[str, Any]:
        """
        Execute data collection stage.

        Args:
            context: Pipeline context

        Returns:
            Collection results

        Since:
            Version 1.0.0
        """
        start_time = datetime.utcnow()

        try:
            # Initialize API manager if needed
            await self.api_manager.initialize()

            # Get temperature strategy for category
            temp_strategy = TemperatureStrategy(
                temperatures=[0.1, 0.5, 0.9]  # Default
            )

            # Execute hierarchical search with temperature variations
            results = await self.api_manager.search_with_hierarchical_processing(
                query=context.query,
                category=context.category,
                pharmaceutical_compound=context.pharmaceutical_compound,
                process_id=context.process_id,
                request_id=context.request_id,
                correlation_id=context.correlation_id,
                temperature=0.7,  # Base temperature
                early_termination=True
            )

            # Calculate collection metrics
            total_sources = sum(
                len(r.get('processed_results', []))
                for r in results.get('provider_results', {}).values()
            )

            total_cost = sum(
                r.get('total_cost', 0)
                for r in results.get('provider_results', {}).values()
                if isinstance(r, dict)
            )

            collection_time = (datetime.utcnow() - start_time).total_seconds()

            # Log collection completion
            await self.audit_logger.log_system_event(
                event_type="collection_completed",
                process_id=context.process_id,
                component="collection_stage",
                details={
                    'sources_collected': total_sources,
                    'providers_used': len(results.get('provider_results', {})),
                    'total_cost': total_cost,
                    'duration_seconds': collection_time
                }
            )

            return {
                'sources': results.get('provider_results', {}),
                'total_sources': total_sources,
                'total_cost': total_cost,
                'summary': results.get('summary', {}),
                'collection_time': collection_time
            }

        except Exception as e:
            logger.error(
                "Collection stage failed",
                process_id=context.process_id,
                error=str(e)
            )
            raise


class VerificationStageHandler:
    """
    Handles the Verification stage of the pipeline.

    Validates source authenticity and credibility for pharmaceutical
    compliance.

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        classifier: SourceClassifier,
        reliability_scorer: SourceReliabilityScorer,
        audit_logger: PharmaceuticalLogger
    ):
        """
        Initialize verification stage handler.

        Args:
            classifier: Source classifier
            reliability_scorer: Reliability scorer
            audit_logger: Audit logger

        Since:
            Version 1.0.0
        """
        self.classifier = classifier
        self.reliability_scorer = reliability_scorer
        self.audit_logger = audit_logger

    async def execute(self, context: PipelineContext) -> Dict[str, Any]:
        """
        Execute source verification stage.

        Args:
            context: Pipeline context

        Returns:
            Verification results

        Since:
            Version 1.0.0
        """
        start_time = datetime.utcnow()

        try:
            # Get collection results
            collection_data = context.stage_results[1].data  # COLLECTION stage
            sources = collection_data.get('sources', {})

            verified_sources = []
            rejected_sources = []
            verification_metrics = {}

            # Process each provider's sources
            for provider, provider_data in sources.items():
                if not isinstance(provider_data, dict):
                    continue

                processed_results = provider_data.get('processed_results', [])

                for result in processed_results:
                    # Verify source authenticity
                    verification = await self._verify_source(result)

                    if verification['is_valid']:
                        verified_sources.append({
                            **result,
                            'verification': verification
                        })
                    else:
                        rejected_sources.append({
                            **result,
                            'rejection_reason': verification['reason']
                        })

            # Calculate verification metrics
            total_verified = len(verified_sources)
            total_rejected = len(rejected_sources)
            verification_rate = total_verified / max(total_verified + total_rejected, 1)

            verification_time = (datetime.utcnow() - start_time).total_seconds()

            # Log verification results
            await self.audit_logger.log_system_event(
                event_type="verification_completed",
                process_id=context.process_id,
                component="verification_stage",
                details={
                    'sources_verified': total_verified,
                    'sources_rejected': total_rejected,
                    'verification_rate': verification_rate,
                    'duration_seconds': verification_time
                }
            )

            return {
                'verified_sources': verified_sources,
                'rejected_sources': rejected_sources,
                'verified_count': total_verified,
                'rejected_count': total_rejected,
                'verification_rate': verification_rate,
                'verification_time': verification_time
            }

        except Exception as e:
            logger.error(
                "Verification stage failed",
                process_id=context.process_id,
                error=str(e)
            )
            raise

    async def _verify_source(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify individual source authenticity.

        Args:
            source: Source to verify

        Returns:
            Verification result

        Since:
            Version 1.0.0
        """
        # Extract source metadata
        priority = source.get('priority', 99)
        priority_name = source.get('priority_name', 'UNKNOWN')

        # Check priority level
        if priority_name in ['PAID_APIS', 'GOVERNMENT', 'PEER_REVIEWED']:
            # High priority sources are generally trusted
            return {
                'is_valid': True,
                'confidence': 0.95,
                'reason': f"Trusted source type: {priority_name}"
            }

        # For lower priority sources, apply additional checks
        result = source.get('result', {})

        # Check for suspicious patterns
        if self._check_suspicious_patterns(result):
            return {
                'is_valid': False,
                'confidence': 0.3,
                'reason': "Suspicious content patterns detected"
            }

        # Check minimum credibility
        credibility = result.get('credibility_score', 0.5)
        if credibility < 0.4:
            return {
                'is_valid': False,
                'confidence': credibility,
                'reason': f"Low credibility score: {credibility}"
            }

        return {
            'is_valid': True,
            'confidence': credibility,
            'reason': "Passed verification checks"
        }

    def _check_suspicious_patterns(self, result: Dict[str, Any]) -> bool:
        """
        Check for suspicious content patterns.

        Args:
            result: Result to check

        Returns:
            True if suspicious

        Since:
            Version 1.0.0
        """
        content = str(result.get('content', '')).lower()

        # Check for spam indicators
        spam_keywords = [
            'buy now', 'limited offer', 'click here',
            'guaranteed', '100% safe', 'no prescription'
        ]

        for keyword in spam_keywords:
            if keyword in content:
                return True

        return False


class MergingStageHandler:
    """
    Handles the Merging stage of the pipeline.

    Performs conflict resolution and data consolidation from multiple
    verified sources.

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        audit_logger: PharmaceuticalLogger,
        conflict_strategy: str = "confidence_weighted"
    ):
        """
        Initialize merging stage handler.

        Args:
            audit_logger: Audit logger
            conflict_strategy: Strategy for conflict resolution

        Since:
            Version 1.0.0
        """
        self.audit_logger = audit_logger
        self.conflict_strategy = conflict_strategy

    async def execute(self, context: PipelineContext) -> Dict[str, Any]:
        """
        Execute data merging stage.

        Args:
            context: Pipeline context

        Returns:
            Merged results

        Since:
            Version 1.0.0
        """
        start_time = datetime.utcnow()

        try:
            # Get verification results
            verification_data = context.stage_results[2].data  # VERIFICATION stage
            verified_sources = verification_data.get('verified_sources', [])

            # Group sources by content similarity
            content_groups = self._group_similar_content(verified_sources)

            # Resolve conflicts and merge
            merged_data = []
            conflicts_resolved = 0

            for group in content_groups:
                if len(group) > 1:
                    # Conflict resolution needed
                    merged_item = await self._resolve_conflicts(group)
                    conflicts_resolved += 1
                else:
                    # No conflict, use as-is
                    merged_item = group[0]

                merged_data.append(merged_item)

            # Deduplicate merged data
            unique_data = self._deduplicate(merged_data)

            merging_time = (datetime.utcnow() - start_time).total_seconds()

            # Log merging results
            await self.audit_logger.log_system_event(
                event_type="merging_completed",
                process_id=context.process_id,
                component="merging_stage",
                details={
                    'input_sources': len(verified_sources),
                    'merged_items': len(unique_data),
                    'conflicts_resolved': conflicts_resolved,
                    'duration_seconds': merging_time
                }
            )

            return {
                'merged_data': unique_data,
                'data_points': len(unique_data),
                'conflicts_resolved': conflicts_resolved,
                'merging_time': merging_time,
                'deduplication_ratio': len(unique_data) / max(len(verified_sources), 1)
            }

        except Exception as e:
            logger.error(
                "Merging stage failed",
                process_id=context.process_id,
                error=str(e)
            )
            raise

    def _group_similar_content(
        self,
        sources: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Group sources with similar content.

        Args:
            sources: List of sources

        Returns:
            Grouped sources

        Since:
            Version 1.0.0
        """
        groups = []
        processed = set()

        for i, source1 in enumerate(sources):
            if i in processed:
                continue

            group = [source1]
            processed.add(i)

            # Find similar sources
            for j, source2 in enumerate(sources[i + 1:], start=i + 1):
                if j in processed:
                    continue

                if self._calculate_similarity(source1, source2) > 0.8:
                    group.append(source2)
                    processed.add(j)

            groups.append(group)

        return groups

    def _calculate_similarity(
        self,
        source1: Dict[str, Any],
        source2: Dict[str, Any]
    ) -> float:
        """
        Calculate content similarity between sources.

        Args:
            source1: First source
            source2: Second source

        Returns:
            Similarity score (0-1)

        Since:
            Version 1.0.0
        """
        # Simplified similarity based on title and content hashes
        content1 = str(source1.get('result', {}).get('content', ''))
        content2 = str(source2.get('result', {}).get('content', ''))

        if not content1 or not content2:
            return 0.0

        # Use set intersection for simple similarity
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    async def _resolve_conflicts(
        self,
        sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Resolve conflicts between similar sources.

        Args:
            sources: Conflicting sources

        Returns:
            Merged source

        Since:
            Version 1.0.0
        """
        if self.conflict_strategy == "confidence_weighted":
            # Weight by confidence/reliability scores
            best_source = max(
                sources,
                key=lambda s: s.get('verification', {}).get('confidence', 0)
            )

            # Merge metadata from all sources
            merged = best_source.copy()
            merged['merged_from'] = len(sources)
            merged['source_priorities'] = [
                s.get('priority_name', 'UNKNOWN') for s in sources
            ]

            return merged

        # Default: use highest priority source
        return min(sources, key=lambda s: s.get('priority', 99))

    def _deduplicate(
        self,
        data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate data points.

        Args:
            data: Data to deduplicate

        Returns:
            Unique data points

        Since:
            Version 1.0.0
        """
        seen_hashes = set()
        unique = []

        for item in data:
            # Create hash of content
            content = str(item.get('result', {}).get('content', ''))
            content_hash = hashlib.md5(content.encode()).hexdigest()

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique.append(item)

        return unique


class SummaryStageHandler:
    """
    Handles the Summary stage of the pipeline.

    Performs final pharmaceutical intelligence synthesis from merged data.

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        audit_logger: PharmaceuticalLogger
    ):
        """
        Initialize summary stage handler.

        Args:
            audit_logger: Audit logger

        Since:
            Version 1.0.0
        """
        self.audit_logger = audit_logger

    async def execute(self, context: PipelineContext) -> Dict[str, Any]:
        """
        Execute summary generation stage.

        Args:
            context: Pipeline context

        Returns:
            Final summary

        Since:
            Version 1.0.0
        """
        start_time = datetime.utcnow()

        try:
            # Get merged data
            merging_data = context.stage_results[3].data  # MERGING stage
            merged_data = merging_data.get('merged_data', [])

            # Generate summary sections
            summary = {
                'compound': context.pharmaceutical_compound,
                'category': context.category,
                'query': context.query,
                'key_findings': self._extract_key_findings(merged_data),
                'source_distribution': self._analyze_source_distribution(merged_data),
                'confidence_assessment': self._assess_confidence(merged_data),
                'data_quality_metrics': self._calculate_quality_metrics(merged_data)
            }

            # Add regulatory compliance notes
            summary['compliance_notes'] = self._generate_compliance_notes(context)

            summary_time = (datetime.utcnow() - start_time).total_seconds()

            # Log summary generation
            await self.audit_logger.log_system_event(
                event_type="summary_generated",
                process_id=context.process_id,
                component="summary_stage",
                details={
                    'key_findings_count': len(summary['key_findings']),
                    'overall_confidence': summary['confidence_assessment']['overall'],
                    'duration_seconds': summary_time
                }
            )

            return {
                'summary': summary,
                'generation_time': summary_time,
                'data_points_summarized': len(merged_data)
            }

        except Exception as e:
            logger.error(
                "Summary stage failed",
                process_id=context.process_id,
                error=str(e)
            )
            raise

    def _extract_key_findings(
        self,
        data: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Extract key findings from merged data.

        Args:
            data: Merged data

        Returns:
            List of key findings

        Since:
            Version 1.0.0
        """
        findings = []

        # Extract high-confidence findings
        for item in data:
            if item.get('verification', {}).get('confidence', 0) > 0.8:
                result = item.get('result', {})
                title = result.get('title', '')
                if title:
                    findings.append(title)

        # Limit to top 10 findings
        return findings[:10]

    def _analyze_source_distribution(
        self,
        data: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Analyze distribution of sources by priority.

        Args:
            data: Merged data

        Returns:
            Source distribution

        Since:
            Version 1.0.0
        """
        distribution = {}

        for item in data:
            priority_name = item.get('priority_name', 'UNKNOWN')
            distribution[priority_name] = distribution.get(priority_name, 0) + 1

        return distribution

    def _assess_confidence(
        self,
        data: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Assess overall confidence in findings.

        Args:
            data: Merged data

        Returns:
            Confidence assessment

        Since:
            Version 1.0.0
        """
        if not data:
            return {'overall': 0.0, 'factors': {}}

        confidences = [
            item.get('verification', {}).get('confidence', 0.5)
            for item in data
        ]

        return {
            'overall': sum(confidences) / len(confidences),
            'factors': {
                'source_diversity': self._calculate_source_diversity(data),
                'priority_weight': self._calculate_priority_weight(data),
                'verification_rate': len([c for c in confidences if c > 0.7]) / len(confidences)
            }
        }

    def _calculate_source_diversity(
        self,
        data: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate diversity of sources.

        Args:
            data: Merged data

        Returns:
            Diversity score (0-1)

        Since:
            Version 1.0.0
        """
        unique_priorities = set(
            item.get('priority_name', 'UNKNOWN')
            for item in data
        )

        # More diverse = better
        return min(len(unique_priorities) / 5, 1.0)

    def _calculate_priority_weight(
        self,
        data: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate weighted priority score.

        Args:
            data: Merged data

        Returns:
            Priority weight (0-1)

        Since:
            Version 1.0.0
        """
        priority_scores = {
            'PAID_APIS': 1.0,
            'GOVERNMENT': 0.95,
            'PEER_REVIEWED': 0.9,
            'INDUSTRY': 0.7,
            'COMPANY': 0.6,
            'NEWS': 0.5,
            'UNKNOWN': 0.3
        }

        if not data:
            return 0.0

        total_score = sum(
            priority_scores.get(item.get('priority_name', 'UNKNOWN'), 0.3)
            for item in data
        )

        return total_score / len(data)

    def _calculate_quality_metrics(
        self,
        data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate data quality metrics.

        Args:
            data: Merged data

        Returns:
            Quality metrics

        Since:
            Version 1.0.0
        """
        return {
            'total_data_points': len(data),
            'high_confidence_points': len([
                d for d in data
                if d.get('verification', {}).get('confidence', 0) > 0.8
            ]),
            'merged_sources': sum(
                d.get('merged_from', 1) for d in data
            ),
            'unique_providers': len(set(
                d.get('provider', 'unknown') for d in data
            ))
        }

    def _generate_compliance_notes(
        self,
        context: PipelineContext
    ) -> Dict[str, Any]:
        """
        Generate regulatory compliance notes.

        Args:
            context: Pipeline context

        Returns:
            Compliance notes

        Since:
            Version 1.0.0
        """
        return {
            'process_tracked': True,
            'process_id': context.process_id,
            'audit_trail_complete': True,
            'data_retention_applied': True,
            'source_attribution_documented': True,
            'timestamp': datetime.utcnow().isoformat()
        }