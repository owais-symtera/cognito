"""
Data Conflict Detection & Resolution Module

Implements Story 3.2: Intelligent conflict detection and resolution
with complete decision audit trails for pharmaceutical intelligence.

This module provides:
- Conflict detection across pharmaceutical categories
- Weighted resolution using source hierarchy
- Threshold-based consensus building
- Conflict documentation for manual review
- Statistical analysis for numerical data
- Expert review workflow integration
- Complete audit trails for all resolutions

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import statistics
import hashlib
import json
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
import structlog

from .source_authenticator import SourceWeights, SourceAuthenticationResult
from ...database.models import (
    DataConflict,
    ConflictResolution,
    CategoryResult,
    SourceReference,
    AuditLog
)

logger = structlog.get_logger(__name__)


class ConflictType(str, Enum):
    """Types of data conflicts in pharmaceutical intelligence."""
    NUMERICAL_VARIANCE = "numerical_variance"
    CATEGORICAL_MISMATCH = "categorical_mismatch"
    DATE_DISCREPANCY = "date_discrepancy"
    BOOLEAN_CONTRADICTION = "boolean_contradiction"
    TEXT_INCONSISTENCY = "text_inconsistency"
    MISSING_DATA = "missing_data"


class ResolutionStrategy(str, Enum):
    """Conflict resolution strategies."""
    HIGHEST_AUTHORITY = "highest_authority"
    CONSENSUS_MAJORITY = "consensus_majority"
    WEIGHTED_AVERAGE = "weighted_average"
    MOST_RECENT = "most_recent"
    MANUAL_REVIEW = "manual_review"
    STATISTICAL_MEDIAN = "statistical_median"


@dataclass
class DataPoint:
    """
    Represents a single data point from a source.

    Attributes:
        value: The actual data value
        source_id: Source reference ID
        authority_score: Source authority score
        confidence_score: Source confidence score
        timestamp: When data was extracted
        metadata: Additional context

    Since:
        Version 1.0.0
    """
    value: Any
    source_id: str
    authority_score: int
    confidence_score: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConflictDetectionResult:
    """
    Result of conflict detection analysis.

    Attributes:
        conflict_id: Unique identifier for the conflict
        conflict_type: Type of conflict detected
        data_points: List of conflicting data points
        severity: Conflict severity (0.0-1.0)
        requires_manual_review: Whether manual review is needed
        statistical_analysis: Statistical metrics for numerical conflicts
        recommendation: Recommended resolution strategy

    Since:
        Version 1.0.0
    """
    conflict_id: str
    conflict_type: ConflictType
    data_points: List[DataPoint]
    severity: float
    requires_manual_review: bool
    statistical_analysis: Optional[Dict[str, float]]
    recommendation: ResolutionStrategy


@dataclass
class ConflictResolutionResult:
    """
    Result of conflict resolution process.

    Attributes:
        resolution_id: Unique identifier for the resolution
        conflict_id: Reference to the conflict
        resolved_value: Final resolved value
        resolution_strategy: Strategy used for resolution
        confidence_score: Confidence in resolution (0.0-1.0)
        contributing_sources: Sources that contributed to resolution
        audit_trail: Complete decision audit trail

    Since:
        Version 1.0.0
    """
    resolution_id: str
    conflict_id: str
    resolved_value: Any
    resolution_strategy: ResolutionStrategy
    confidence_score: float
    contributing_sources: List[str]
    audit_trail: Dict[str, Any]


class ConflictResolver:
    """
    Data conflict detection and resolution engine.

    Implements intelligent conflict detection and resolution with
    complete decision audit trails for pharmaceutical compliance.

    Since:
        Version 1.0.0
    """

    # Thresholds for conflict detection
    NUMERICAL_VARIANCE_THRESHOLD = 0.15  # 15% variance
    CONSENSUS_THRESHOLD = 0.6  # 60% agreement required
    HIGH_SEVERITY_THRESHOLD = 0.7
    CONFIDENCE_THRESHOLD = 0.5

    def __init__(
        self,
        db_session: AsyncSession,
        source_authenticator: Optional[Any] = None,
        audit_logger: Optional[Any] = None
    ):
        """
        Initialize conflict resolver.

        Args:
            db_session: Database session for persistence
            source_authenticator: Source authentication engine
            audit_logger: Optional audit logger for compliance

        Since:
            Version 1.0.0
        """
        self.db = db_session
        self.source_authenticator = source_authenticator
        self.audit_logger = audit_logger or logger

    async def detect_conflicts(
        self,
        category_name: str,
        data_field: str,
        data_points: List[DataPoint],
        process_id: str
    ) -> Optional[ConflictDetectionResult]:
        """
        Detect conflicts in pharmaceutical category data.

        Analyzes data points from multiple sources to identify
        contradictory or inconsistent information.

        Args:
            category_name: Pharmaceutical category name
            data_field: Field being analyzed
            data_points: List of data points to analyze
            process_id: Process ID for audit trail

        Returns:
            ConflictDetectionResult if conflicts found, None otherwise

        Since:
            Version 1.0.0
        """
        if len(data_points) < 2:
            return None  # No conflict possible with single source

        # Determine conflict type based on data
        conflict_type = self._determine_conflict_type(data_points)

        # Check if there's actually a conflict
        has_conflict = await self._check_for_conflict(
            data_points,
            conflict_type
        )

        if not has_conflict:
            return None

        # Calculate conflict severity
        severity = self._calculate_conflict_severity(
            data_points,
            conflict_type
        )

        # Perform statistical analysis for numerical data
        statistical_analysis = None
        if conflict_type == ConflictType.NUMERICAL_VARIANCE:
            statistical_analysis = self._perform_statistical_analysis(data_points)

        # Determine if manual review is needed
        requires_manual = self._requires_manual_review(
            severity,
            conflict_type,
            data_points
        )

        # Recommend resolution strategy
        recommendation = self._recommend_strategy(
            conflict_type,
            data_points,
            severity
        )

        # Create conflict detection result
        result = ConflictDetectionResult(
            conflict_id=self._generate_conflict_id(category_name, data_field),
            conflict_type=conflict_type,
            data_points=data_points,
            severity=severity,
            requires_manual_review=requires_manual,
            statistical_analysis=statistical_analysis,
            recommendation=recommendation
        )

        # Persist conflict detection
        await self._persist_conflict(result, category_name, data_field, process_id)

        # Create audit trail
        await self._audit_conflict_detection(result, process_id)

        return result

    async def resolve_conflict(
        self,
        conflict: ConflictDetectionResult,
        strategy_override: Optional[ResolutionStrategy] = None,
        process_id: Optional[str] = None
    ) -> ConflictResolutionResult:
        """
        Resolve detected conflict using appropriate strategy.

        Applies weighted resolution using source hierarchy or
        other strategies based on conflict type and severity.

        Args:
            conflict: Detected conflict to resolve
            strategy_override: Optional strategy override
            process_id: Process ID for audit trail

        Returns:
            ConflictResolutionResult with resolved value and audit trail

        Since:
            Version 1.0.0
        """
        # Determine resolution strategy
        strategy = strategy_override or conflict.recommendation

        # Apply resolution strategy
        resolved_value = None
        contributing_sources = []
        confidence_score = 0.0

        if strategy == ResolutionStrategy.HIGHEST_AUTHORITY:
            resolved_value, contributing_sources, confidence_score = \
                await self._resolve_by_authority(conflict.data_points)

        elif strategy == ResolutionStrategy.CONSENSUS_MAJORITY:
            resolved_value, contributing_sources, confidence_score = \
                self._resolve_by_consensus(conflict.data_points)

        elif strategy == ResolutionStrategy.WEIGHTED_AVERAGE:
            resolved_value, contributing_sources, confidence_score = \
                self._resolve_by_weighted_average(conflict.data_points)

        elif strategy == ResolutionStrategy.MOST_RECENT:
            resolved_value, contributing_sources, confidence_score = \
                self._resolve_by_recency(conflict.data_points)

        elif strategy == ResolutionStrategy.STATISTICAL_MEDIAN:
            resolved_value, contributing_sources, confidence_score = \
                self._resolve_by_statistical_median(conflict.data_points)

        else:  # MANUAL_REVIEW
            resolved_value = None
            contributing_sources = [dp.source_id for dp in conflict.data_points]
            confidence_score = 0.0

        # Create audit trail
        audit_trail = self._create_resolution_audit_trail(
            conflict,
            strategy,
            resolved_value,
            contributing_sources
        )

        # Create resolution result
        result = ConflictResolutionResult(
            resolution_id=self._generate_resolution_id(conflict.conflict_id),
            conflict_id=conflict.conflict_id,
            resolved_value=resolved_value,
            resolution_strategy=strategy,
            confidence_score=confidence_score,
            contributing_sources=contributing_sources,
            audit_trail=audit_trail
        )

        # Persist resolution
        await self._persist_resolution(result, process_id)

        # Audit resolution
        await self._audit_conflict_resolution(result, process_id)

        return result

    def _determine_conflict_type(self, data_points: List[DataPoint]) -> ConflictType:
        """
        Determine the type of conflict based on data points.

        Args:
            data_points: List of data points to analyze

        Returns:
            Detected conflict type

        Since:
            Version 1.0.0
        """
        if not data_points:
            return ConflictType.MISSING_DATA

        # Get sample value
        sample_value = data_points[0].value

        # Check data type
        if sample_value is None:
            return ConflictType.MISSING_DATA
        elif isinstance(sample_value, (int, float)):
            return ConflictType.NUMERICAL_VARIANCE
        elif isinstance(sample_value, bool):
            return ConflictType.BOOLEAN_CONTRADICTION
        elif isinstance(sample_value, datetime):
            return ConflictType.DATE_DISCREPANCY
        elif isinstance(sample_value, str):
            # Check if it's a categorical value
            unique_values = set(dp.value for dp in data_points)
            if len(unique_values) <= 10:  # Likely categorical
                return ConflictType.CATEGORICAL_MISMATCH
            else:
                return ConflictType.TEXT_INCONSISTENCY
        else:
            return ConflictType.TEXT_INCONSISTENCY

    async def _check_for_conflict(
        self,
        data_points: List[DataPoint],
        conflict_type: ConflictType
    ) -> bool:
        """
        Check if data points actually have a conflict.

        Args:
            data_points: List of data points
            conflict_type: Type of conflict to check

        Returns:
            True if conflict exists, False otherwise

        Since:
            Version 1.0.0
        """
        values = [dp.value for dp in data_points if dp.value is not None]

        if not values:
            return False

        if conflict_type == ConflictType.NUMERICAL_VARIANCE:
            # Check if variance exceeds threshold
            if len(values) > 1:
                mean_val = statistics.mean(values)
                if mean_val != 0:
                    variance = statistics.stdev(values) / abs(mean_val)
                    return variance > self.NUMERICAL_VARIANCE_THRESHOLD
            return False

        elif conflict_type == ConflictType.BOOLEAN_CONTRADICTION:
            # Check if both True and False exist
            return len(set(values)) > 1

        elif conflict_type == ConflictType.CATEGORICAL_MISMATCH:
            # Check if multiple categories exist
            return len(set(values)) > 1

        elif conflict_type == ConflictType.DATE_DISCREPANCY:
            # Check if dates differ by more than 30 days
            if len(values) > 1:
                date_range = max(values) - min(values)
                return date_range.days > 30
            return False

        else:  # Text inconsistency
            # Check if texts are significantly different
            return len(set(values)) > 1

    def _calculate_conflict_severity(
        self,
        data_points: List[DataPoint],
        conflict_type: ConflictType
    ) -> float:
        """
        Calculate severity of detected conflict.

        Args:
            data_points: List of conflicting data points
            conflict_type: Type of conflict

        Returns:
            Severity score between 0.0 and 1.0

        Since:
            Version 1.0.0
        """
        values = [dp.value for dp in data_points if dp.value is not None]

        if not values:
            return 0.0

        if conflict_type == ConflictType.NUMERICAL_VARIANCE:
            # Severity based on coefficient of variation
            mean_val = statistics.mean(values)
            if mean_val != 0:
                cv = statistics.stdev(values) / abs(mean_val)
                return min(1.0, cv)
            return 0.5

        elif conflict_type == ConflictType.BOOLEAN_CONTRADICTION:
            # High severity for boolean contradictions
            return 0.9

        elif conflict_type == ConflictType.CATEGORICAL_MISMATCH:
            # Severity based on number of different categories
            unique_ratio = len(set(values)) / len(values)
            return min(1.0, unique_ratio * 1.5)

        elif conflict_type == ConflictType.DATE_DISCREPANCY:
            # Severity based on date range
            date_range = (max(values) - min(values)).days
            if date_range > 365:
                return 0.9
            elif date_range > 180:
                return 0.7
            elif date_range > 90:
                return 0.5
            else:
                return 0.3

        else:  # Text inconsistency
            # Moderate severity for text conflicts
            return 0.6

    def _perform_statistical_analysis(
        self,
        data_points: List[DataPoint]
    ) -> Dict[str, float]:
        """
        Perform statistical analysis on numerical data.

        Args:
            data_points: List of numerical data points

        Returns:
            Dictionary of statistical metrics

        Since:
            Version 1.0.0
        """
        values = [dp.value for dp in data_points
                 if dp.value is not None and isinstance(dp.value, (int, float))]

        if len(values) < 2:
            return {}

        # Calculate statistics
        analysis = {
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'stdev': statistics.stdev(values),
            'min': min(values),
            'max': max(values),
            'range': max(values) - min(values),
            'coefficient_variation': 0.0
        }

        # Add coefficient of variation if mean is non-zero
        if analysis['mean'] != 0:
            analysis['coefficient_variation'] = analysis['stdev'] / abs(analysis['mean'])

        # Calculate confidence intervals (95%)
        if len(values) >= 3:
            confidence_interval = 1.96 * analysis['stdev'] / (len(values) ** 0.5)
            analysis['ci_lower'] = analysis['mean'] - confidence_interval
            analysis['ci_upper'] = analysis['mean'] + confidence_interval

        return analysis

    def _requires_manual_review(
        self,
        severity: float,
        conflict_type: ConflictType,
        data_points: List[DataPoint]
    ) -> bool:
        """
        Determine if manual review is required.

        Args:
            severity: Conflict severity
            conflict_type: Type of conflict
            data_points: Conflicting data points

        Returns:
            True if manual review required

        Since:
            Version 1.0.0
        """
        # High severity always needs review
        if severity >= self.HIGH_SEVERITY_THRESHOLD:
            return True

        # Boolean contradictions need review
        if conflict_type == ConflictType.BOOLEAN_CONTRADICTION:
            return True

        # Low confidence sources need review
        avg_confidence = statistics.mean([dp.confidence_score for dp in data_points])
        if avg_confidence < self.CONFIDENCE_THRESHOLD:
            return True

        # High authority conflicts need review
        high_authority_sources = [
            dp for dp in data_points
            if dp.authority_score >= SourceWeights.GOVERNMENT
        ]
        if len(high_authority_sources) > 1:
            # Multiple high authority sources disagree
            values = set(dp.value for dp in high_authority_sources)
            if len(values) > 1:
                return True

        return False

    def _recommend_strategy(
        self,
        conflict_type: ConflictType,
        data_points: List[DataPoint],
        severity: float
    ) -> ResolutionStrategy:
        """
        Recommend resolution strategy based on conflict characteristics.

        Args:
            conflict_type: Type of conflict
            data_points: Conflicting data points
            severity: Conflict severity

        Returns:
            Recommended resolution strategy

        Since:
            Version 1.0.0
        """
        # Manual review for high severity
        if severity >= self.HIGH_SEVERITY_THRESHOLD:
            return ResolutionStrategy.MANUAL_REVIEW

        # Check authority scores
        max_authority = max(dp.authority_score for dp in data_points)
        authority_variance = statistics.stdev([dp.authority_score for dp in data_points])

        # Use highest authority if there's clear leader
        if authority_variance > 2 and max_authority >= SourceWeights.GOVERNMENT:
            return ResolutionStrategy.HIGHEST_AUTHORITY

        # Strategy by conflict type
        if conflict_type == ConflictType.NUMERICAL_VARIANCE:
            # Use weighted average for numerical data
            if authority_variance < 2:
                return ResolutionStrategy.WEIGHTED_AVERAGE
            else:
                return ResolutionStrategy.STATISTICAL_MEDIAN

        elif conflict_type == ConflictType.BOOLEAN_CONTRADICTION:
            return ResolutionStrategy.CONSENSUS_MAJORITY

        elif conflict_type == ConflictType.CATEGORICAL_MISMATCH:
            return ResolutionStrategy.CONSENSUS_MAJORITY

        elif conflict_type == ConflictType.DATE_DISCREPANCY:
            return ResolutionStrategy.MOST_RECENT

        else:  # Text inconsistency
            return ResolutionStrategy.HIGHEST_AUTHORITY

    async def _resolve_by_authority(
        self,
        data_points: List[DataPoint]
    ) -> Tuple[Any, List[str], float]:
        """
        Resolve conflict using highest authority source.

        Args:
            data_points: Conflicting data points

        Returns:
            Tuple of (resolved_value, contributing_sources, confidence)

        Since:
            Version 1.0.0
        """
        # Sort by authority score (descending)
        sorted_points = sorted(
            data_points,
            key=lambda dp: (dp.authority_score, dp.confidence_score),
            reverse=True
        )

        # Use highest authority value
        best_point = sorted_points[0]
        resolved_value = best_point.value
        contributing_sources = [best_point.source_id]

        # Calculate confidence based on authority gap
        if len(sorted_points) > 1:
            authority_gap = best_point.authority_score - sorted_points[1].authority_score
            confidence = min(1.0, 0.5 + (authority_gap / 10.0))
        else:
            confidence = best_point.confidence_score

        return resolved_value, contributing_sources, confidence

    def _resolve_by_consensus(
        self,
        data_points: List[DataPoint]
    ) -> Tuple[Any, List[str], float]:
        """
        Resolve conflict using consensus majority.

        Args:
            data_points: Conflicting data points

        Returns:
            Tuple of (resolved_value, contributing_sources, confidence)

        Since:
            Version 1.0.0
        """
        # Count weighted votes for each value
        value_weights = {}
        value_sources = {}

        for dp in data_points:
            value = dp.value
            weight = dp.authority_score * dp.confidence_score

            if value not in value_weights:
                value_weights[value] = 0
                value_sources[value] = []

            value_weights[value] += weight
            value_sources[value].append(dp.source_id)

        # Find value with highest weighted votes
        best_value = max(value_weights, key=value_weights.get)
        total_weight = sum(value_weights.values())

        # Calculate consensus percentage
        consensus_pct = value_weights[best_value] / total_weight if total_weight > 0 else 0

        # Only use consensus if above threshold
        if consensus_pct >= self.CONSENSUS_THRESHOLD:
            confidence = consensus_pct
            return best_value, value_sources[best_value], confidence
        else:
            # No clear consensus, fall back to highest authority
            return self._resolve_by_authority(data_points)

    def _resolve_by_weighted_average(
        self,
        data_points: List[DataPoint]
    ) -> Tuple[Any, List[str], float]:
        """
        Resolve numerical conflict using weighted average.

        Args:
            data_points: Conflicting numerical data points

        Returns:
            Tuple of (resolved_value, contributing_sources, confidence)

        Since:
            Version 1.0.0
        """
        # Filter numerical values
        numerical_points = [
            dp for dp in data_points
            if dp.value is not None and isinstance(dp.value, (int, float))
        ]

        if not numerical_points:
            return None, [], 0.0

        # Calculate weighted average
        weighted_sum = 0
        weight_total = 0

        for dp in numerical_points:
            weight = dp.authority_score * dp.confidence_score
            weighted_sum += dp.value * weight
            weight_total += weight

        if weight_total > 0:
            resolved_value = weighted_sum / weight_total
            contributing_sources = [dp.source_id for dp in numerical_points]

            # Calculate confidence based on agreement
            values = [dp.value for dp in numerical_points]
            if len(values) > 1:
                cv = statistics.stdev(values) / abs(statistics.mean(values)) if statistics.mean(values) != 0 else 1
                confidence = max(0.1, 1.0 - cv)
            else:
                confidence = numerical_points[0].confidence_score

            return resolved_value, contributing_sources, confidence

        return None, [], 0.0

    def _resolve_by_recency(
        self,
        data_points: List[DataPoint]
    ) -> Tuple[Any, List[str], float]:
        """
        Resolve conflict using most recent data.

        Args:
            data_points: Conflicting data points

        Returns:
            Tuple of (resolved_value, contributing_sources, confidence)

        Since:
            Version 1.0.0
        """
        # Sort by timestamp (most recent first)
        sorted_points = sorted(
            data_points,
            key=lambda dp: dp.timestamp,
            reverse=True
        )

        # Use most recent value
        most_recent = sorted_points[0]
        resolved_value = most_recent.value
        contributing_sources = [most_recent.source_id]

        # Adjust confidence based on recency and authority
        base_confidence = most_recent.confidence_score
        authority_bonus = most_recent.authority_score / 20.0  # Max 0.5 bonus
        confidence = min(1.0, base_confidence + authority_bonus)

        return resolved_value, contributing_sources, confidence

    def _resolve_by_statistical_median(
        self,
        data_points: List[DataPoint]
    ) -> Tuple[Any, List[str], float]:
        """
        Resolve numerical conflict using statistical median.

        Args:
            data_points: Conflicting numerical data points

        Returns:
            Tuple of (resolved_value, contributing_sources, confidence)

        Since:
            Version 1.0.0
        """
        # Filter numerical values
        numerical_points = [
            dp for dp in data_points
            if dp.value is not None and isinstance(dp.value, (int, float))
        ]

        if not numerical_points:
            return None, [], 0.0

        # Calculate median
        values = [dp.value for dp in numerical_points]
        resolved_value = statistics.median(values)

        # Find sources closest to median
        contributing_sources = []
        tolerance = statistics.stdev(values) * 0.5 if len(values) > 1 else 0

        for dp in numerical_points:
            if abs(dp.value - resolved_value) <= tolerance:
                contributing_sources.append(dp.source_id)

        # Calculate confidence based on data spread
        if len(values) > 1:
            iqr = np.percentile(values, 75) - np.percentile(values, 25)
            range_val = max(values) - min(values)
            if range_val > 0:
                confidence = max(0.3, 1.0 - (iqr / range_val))
            else:
                confidence = 1.0
        else:
            confidence = numerical_points[0].confidence_score

        return resolved_value, contributing_sources, confidence

    def _create_resolution_audit_trail(
        self,
        conflict: ConflictDetectionResult,
        strategy: ResolutionStrategy,
        resolved_value: Any,
        contributing_sources: List[str]
    ) -> Dict[str, Any]:
        """
        Create comprehensive audit trail for resolution.

        Args:
            conflict: Original conflict
            strategy: Resolution strategy used
            resolved_value: Final resolved value
            contributing_sources: Sources that contributed

        Returns:
            Audit trail dictionary

        Since:
            Version 1.0.0
        """
        audit_trail = {
            'timestamp': datetime.utcnow().isoformat(),
            'conflict_type': conflict.conflict_type.value,
            'severity': conflict.severity,
            'resolution_strategy': strategy.value,
            'resolved_value': str(resolved_value) if resolved_value is not None else None,
            'contributing_sources': contributing_sources,
            'sources_compared': len(conflict.data_points),
            'data_points': []
        }

        # Add data point details
        for dp in conflict.data_points:
            audit_trail['data_points'].append({
                'source_id': dp.source_id,
                'value': str(dp.value),
                'authority_score': dp.authority_score,
                'confidence_score': dp.confidence_score,
                'timestamp': dp.timestamp.isoformat()
            })

        # Add statistical analysis if available
        if conflict.statistical_analysis:
            audit_trail['statistical_analysis'] = conflict.statistical_analysis

        # Add recommendation vs actual strategy
        audit_trail['recommended_strategy'] = conflict.recommendation.value
        audit_trail['strategy_override'] = strategy != conflict.recommendation

        return audit_trail

    def _generate_conflict_id(self, category: str, field: str) -> str:
        """Generate unique conflict ID."""
        timestamp = datetime.utcnow().isoformat()
        content = f"{category}:{field}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _generate_resolution_id(self, conflict_id: str) -> str:
        """Generate unique resolution ID."""
        timestamp = datetime.utcnow().isoformat()
        content = f"{conflict_id}:resolution:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def _persist_conflict(
        self,
        result: ConflictDetectionResult,
        category: str,
        field: str,
        process_id: str
    ):
        """Persist conflict detection to database."""
        conflict = DataConflict(
            id=result.conflict_id,
            process_id=process_id,
            category_name=category,
            field_name=field,
            conflict_type=result.conflict_type.value,
            severity=result.severity,
            requires_manual_review=result.requires_manual_review,
            data_points=[asdict(dp) for dp in result.data_points],
            statistical_analysis=result.statistical_analysis,
            recommendation=result.recommendation.value,
            detected_at=datetime.utcnow()
        )

        self.db.add(conflict)
        await self.db.commit()

    async def _persist_resolution(
        self,
        result: ConflictResolutionResult,
        process_id: str
    ):
        """Persist conflict resolution to database."""
        resolution = ConflictResolution(
            id=result.resolution_id,
            conflict_id=result.conflict_id,
            process_id=process_id,
            resolved_value=str(result.resolved_value) if result.resolved_value else None,
            resolution_strategy=result.resolution_strategy.value,
            confidence_score=result.confidence_score,
            contributing_sources=result.contributing_sources,
            audit_trail=result.audit_trail,
            resolved_at=datetime.utcnow()
        )

        self.db.add(resolution)
        await self.db.commit()

    async def _audit_conflict_detection(
        self,
        result: ConflictDetectionResult,
        process_id: str
    ):
        """Create audit log for conflict detection."""
        await self.audit_logger.log_conflict_detection(
            process_id=process_id,
            conflict_id=result.conflict_id,
            conflict_type=result.conflict_type.value,
            severity=result.severity,
            data_points_count=len(result.data_points)
        )

    async def _audit_conflict_resolution(
        self,
        result: ConflictResolutionResult,
        process_id: str
    ):
        """Create audit log for conflict resolution."""
        await self.audit_logger.log_conflict_resolution(
            process_id=process_id,
            resolution_id=result.resolution_id,
            strategy=result.resolution_strategy.value,
            confidence=result.confidence_score,
            audit_trail=result.audit_trail
        )