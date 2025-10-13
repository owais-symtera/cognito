"""
Historical accuracy tracking for source classification and predictions.

Tracks and analyzes the accuracy of source classifications, pharmaceutical
predictions, and intelligence quality over time for continuous improvement.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import structlog

logger = structlog.get_logger(__name__)


class PredictionType(Enum):
    """Types of predictions tracked."""
    SOURCE_CLASSIFICATION = "source_classification"
    RELEVANCE_SCORE = "relevance_score"
    CREDIBILITY_SCORE = "credibility_score"
    REGULATORY_STATUS = "regulatory_status"
    CLINICAL_OUTCOME = "clinical_outcome"
    MARKET_PREDICTION = "market_prediction"


@dataclass
class AccuracyRecord:
    """
    Record of a prediction and its actual outcome.

    Since:
        Version 1.0.0
    """
    id: str
    prediction_type: PredictionType
    predicted_value: Any
    actual_value: Optional[Any]
    confidence: float
    timestamp: datetime
    provider: str
    category: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    verified: bool = False
    verified_at: Optional[datetime] = None
    accuracy_score: Optional[float] = None


@dataclass
class AccuracyMetrics:
    """
    Aggregated accuracy metrics.

    Since:
        Version 1.0.0
    """
    prediction_type: PredictionType
    total_predictions: int
    verified_predictions: int
    accuracy_rate: float
    precision: float
    recall: float
    f1_score: float
    mean_confidence: float
    confidence_correlation: float  # Correlation between confidence and accuracy
    time_period: str
    provider_breakdown: Dict[str, float] = field(default_factory=dict)


class HistoricalAccuracyTracker:
    """
    Tracks and analyzes historical accuracy of pharmaceutical intelligence.

    Monitors prediction accuracy over time to improve source classification,
    relevance scoring, and overall intelligence quality.

    Example:
        >>> tracker = HistoricalAccuracyTracker(db_session)
        >>> await tracker.record_prediction(
        ...     prediction_type=PredictionType.SOURCE_CLASSIFICATION,
        ...     predicted_value="regulatory",
        ...     confidence=0.95
        ... )
        >>> metrics = await tracker.get_accuracy_metrics()

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        db_session: AsyncSession,
        retention_days: int = 365
    ):
        """
        Initialize accuracy tracker.

        Args:
            db_session: Database session for persistence
            retention_days: Days to retain accuracy records

        Since:
            Version 1.0.0
        """
        self.db = db_session
        self.retention_days = retention_days
        self.accuracy_cache: Dict[str, AccuracyRecord] = {}
        self.metrics_cache: Dict[str, AccuracyMetrics] = {}
        self.thresholds = self._initialize_thresholds()

    def _initialize_thresholds(self) -> Dict[PredictionType, float]:
        """
        Initialize accuracy thresholds for each prediction type.

        Returns:
            Dictionary of prediction type to minimum acceptable accuracy

        Since:
            Version 1.0.0
        """
        return {
            PredictionType.SOURCE_CLASSIFICATION: 0.85,
            PredictionType.RELEVANCE_SCORE: 0.75,
            PredictionType.CREDIBILITY_SCORE: 0.80,
            PredictionType.REGULATORY_STATUS: 0.90,
            PredictionType.CLINICAL_OUTCOME: 0.70,
            PredictionType.MARKET_PREDICTION: 0.65
        }

    async def record_prediction(
        self,
        prediction_type: PredictionType,
        predicted_value: Any,
        confidence: float,
        provider: str,
        category: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a new prediction for tracking.

        Args:
            prediction_type: Type of prediction
            predicted_value: Predicted value
            confidence: Confidence score (0-1)
            provider: API provider that made prediction
            category: Pharmaceutical category
            metadata: Additional metadata

        Returns:
            Record ID

        Since:
            Version 1.0.0
        """
        from uuid import uuid4

        record = AccuracyRecord(
            id=str(uuid4()),
            prediction_type=prediction_type,
            predicted_value=predicted_value,
            actual_value=None,
            confidence=confidence,
            timestamp=datetime.utcnow(),
            provider=provider,
            category=category,
            metadata=metadata or {},
            verified=False,
            verified_at=None,
            accuracy_score=None
        )

        # Store in cache
        self.accuracy_cache[record.id] = record

        # Persist to database
        await self._persist_record(record)

        logger.info(
            "Prediction recorded",
            record_id=record.id,
            type=prediction_type.value,
            provider=provider
        )

        return record.id

    async def verify_prediction(
        self,
        record_id: str,
        actual_value: Any,
        verification_metadata: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Verify a prediction with actual outcome.

        Args:
            record_id: Record ID to verify
            actual_value: Actual outcome value
            verification_metadata: Additional verification data

        Returns:
            Accuracy score (0-1)

        Since:
            Version 1.0.0
        """
        record = await self._get_record(record_id)

        if not record:
            raise ValueError(f"Record {record_id} not found")

        if record.verified:
            logger.warning(f"Record {record_id} already verified")
            return record.accuracy_score

        # Calculate accuracy based on prediction type
        accuracy_score = self._calculate_accuracy(
            record.prediction_type,
            record.predicted_value,
            actual_value
        )

        # Update record
        record.actual_value = actual_value
        record.verified = True
        record.verified_at = datetime.utcnow()
        record.accuracy_score = accuracy_score

        if verification_metadata:
            record.metadata.update(verification_metadata)

        # Update cache
        self.accuracy_cache[record_id] = record

        # Persist update
        await self._update_record(record)

        # Check if accuracy meets threshold
        threshold = self.thresholds[record.prediction_type]
        if accuracy_score < threshold:
            logger.warning(
                "Prediction accuracy below threshold",
                record_id=record_id,
                accuracy=accuracy_score,
                threshold=threshold,
                type=record.prediction_type.value
            )

        return accuracy_score

    def _calculate_accuracy(
        self,
        prediction_type: PredictionType,
        predicted: Any,
        actual: Any
    ) -> float:
        """
        Calculate accuracy score based on prediction type.

        Args:
            prediction_type: Type of prediction
            predicted: Predicted value
            actual: Actual value

        Returns:
            Accuracy score (0-1)

        Since:
            Version 1.0.0
        """
        if prediction_type == PredictionType.SOURCE_CLASSIFICATION:
            # Binary accuracy for classification
            return 1.0 if predicted == actual else 0.0

        elif prediction_type in [PredictionType.RELEVANCE_SCORE, PredictionType.CREDIBILITY_SCORE]:
            # Calculate error for continuous scores
            if isinstance(predicted, (int, float)) and isinstance(actual, (int, float)):
                error = abs(predicted - actual)
                max_error = 1.0  # Assuming scores are 0-1
                return max(0, 1 - (error / max_error))
            return 0.0

        elif prediction_type == PredictionType.REGULATORY_STATUS:
            # Check if regulatory status matches
            if isinstance(predicted, str) and isinstance(actual, str):
                return 1.0 if predicted.lower() == actual.lower() else 0.0
            return 0.0

        elif prediction_type == PredictionType.CLINICAL_OUTCOME:
            # Complex matching for clinical outcomes
            if isinstance(predicted, dict) and isinstance(actual, dict):
                matches = sum(
                    1 for key in predicted
                    if key in actual and predicted[key] == actual[key]
                )
                total_keys = len(set(predicted.keys()) | set(actual.keys()))
                return matches / total_keys if total_keys > 0 else 0.0
            return 1.0 if predicted == actual else 0.0

        elif prediction_type == PredictionType.MARKET_PREDICTION:
            # Tolerance-based accuracy for market predictions
            if isinstance(predicted, (int, float)) and isinstance(actual, (int, float)):
                tolerance = 0.15  # 15% tolerance
                relative_error = abs(predicted - actual) / max(abs(actual), 1)
                return max(0, 1 - (relative_error / tolerance))
            return 0.0

        return 0.0

    async def get_accuracy_metrics(
        self,
        prediction_type: Optional[PredictionType] = None,
        provider: Optional[str] = None,
        category: Optional[str] = None,
        time_window_days: int = 30
    ) -> List[AccuracyMetrics]:
        """
        Get aggregated accuracy metrics.

        Args:
            prediction_type: Filter by prediction type
            provider: Filter by provider
            category: Filter by category
            time_window_days: Time window for analysis

        Returns:
            List of accuracy metrics

        Since:
            Version 1.0.0
        """
        metrics_list = []

        # Get verified records from database
        records = await self._get_verified_records(
            prediction_type=prediction_type,
            provider=provider,
            category=category,
            time_window_days=time_window_days
        )

        # Group by prediction type
        grouped_records = {}
        for record in records:
            pred_type = record.prediction_type
            if pred_type not in grouped_records:
                grouped_records[pred_type] = []
            grouped_records[pred_type].append(record)

        # Calculate metrics for each type
        for pred_type, type_records in grouped_records.items():
            metrics = self._calculate_metrics(type_records, time_window_days)
            metrics_list.append(metrics)

        return metrics_list

    def _calculate_metrics(
        self,
        records: List[AccuracyRecord],
        time_window_days: int
    ) -> AccuracyMetrics:
        """
        Calculate accuracy metrics from records.

        Args:
            records: List of accuracy records
            time_window_days: Time window used

        Returns:
            Calculated metrics

        Since:
            Version 1.0.0
        """
        if not records:
            return None

        prediction_type = records[0].prediction_type
        total = len(records)
        verified = sum(1 for r in records if r.verified)

        # Calculate accuracy metrics
        accuracy_scores = [r.accuracy_score for r in records if r.accuracy_score is not None]
        accuracy_rate = np.mean(accuracy_scores) if accuracy_scores else 0.0

        # Calculate precision/recall for classification
        if prediction_type == PredictionType.SOURCE_CLASSIFICATION:
            precision, recall, f1 = self._calculate_classification_metrics(records)
        else:
            # For continuous predictions, use accuracy as proxy
            precision = recall = f1 = accuracy_rate

        # Calculate confidence metrics
        confidences = [r.confidence for r in records]
        mean_confidence = np.mean(confidences) if confidences else 0.0

        # Calculate confidence correlation
        if accuracy_scores and len(accuracy_scores) == len(confidences):
            confidence_correlation = np.corrcoef(confidences, accuracy_scores)[0, 1]
        else:
            confidence_correlation = 0.0

        # Provider breakdown
        provider_breakdown = {}
        for provider in set(r.provider for r in records):
            provider_records = [r for r in records if r.provider == provider]
            provider_scores = [r.accuracy_score for r in provider_records if r.accuracy_score is not None]
            provider_breakdown[provider] = np.mean(provider_scores) if provider_scores else 0.0

        return AccuracyMetrics(
            prediction_type=prediction_type,
            total_predictions=total,
            verified_predictions=verified,
            accuracy_rate=accuracy_rate,
            precision=precision,
            recall=recall,
            f1_score=f1,
            mean_confidence=mean_confidence,
            confidence_correlation=confidence_correlation,
            time_period=f"last_{time_window_days}_days",
            provider_breakdown=provider_breakdown
        )

    def _calculate_classification_metrics(
        self,
        records: List[AccuracyRecord]
    ) -> Tuple[float, float, float]:
        """
        Calculate precision, recall, and F1 for classification.

        Args:
            records: Classification records

        Returns:
            Tuple of (precision, recall, f1)

        Since:
            Version 1.0.0
        """
        # Simplified calculation - would need more complex logic for multi-class
        true_positives = sum(1 for r in records if r.accuracy_score == 1.0)
        false_positives = sum(1 for r in records if r.accuracy_score == 0.0 and r.confidence > 0.7)
        false_negatives = sum(1 for r in records if r.accuracy_score == 0.0 and r.confidence <= 0.7)

        if true_positives + false_positives == 0:
            precision = 0.0
        else:
            precision = true_positives / (true_positives + false_positives)

        if true_positives + false_negatives == 0:
            recall = 0.0
        else:
            recall = true_positives / (true_positives + false_negatives)

        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * (precision * recall) / (precision + recall)

        return precision, recall, f1

    async def get_improvement_trends(
        self,
        prediction_type: PredictionType,
        time_windows: List[int] = [7, 30, 90]
    ) -> Dict[str, List[float]]:
        """
        Get accuracy improvement trends over time.

        Args:
            prediction_type: Type of prediction
            time_windows: Time windows to analyze (days)

        Returns:
            Dictionary of time window to accuracy scores

        Since:
            Version 1.0.0
        """
        trends = {}

        for window in time_windows:
            metrics = await self.get_accuracy_metrics(
                prediction_type=prediction_type,
                time_window_days=window
            )

            if metrics:
                trend_data = [m.accuracy_rate for m in metrics]
                trends[f"{window}_days"] = trend_data

        return trends

    async def get_provider_performance(
        self,
        time_window_days: int = 30
    ) -> Dict[str, Dict[str, float]]:
        """
        Get performance metrics by provider.

        Args:
            time_window_days: Time window for analysis

        Returns:
            Dictionary of provider to performance metrics

        Since:
            Version 1.0.0
        """
        performance = {}

        # Get all providers
        records = await self._get_verified_records(time_window_days=time_window_days)
        providers = set(r.provider for r in records)

        for provider in providers:
            provider_records = [r for r in records if r.provider == provider]

            if provider_records:
                accuracy_scores = [r.accuracy_score for r in provider_records if r.accuracy_score is not None]
                confidences = [r.confidence for r in provider_records]

                performance[provider] = {
                    'mean_accuracy': np.mean(accuracy_scores) if accuracy_scores else 0.0,
                    'std_accuracy': np.std(accuracy_scores) if accuracy_scores else 0.0,
                    'mean_confidence': np.mean(confidences) if confidences else 0.0,
                    'total_predictions': len(provider_records),
                    'verified_count': sum(1 for r in provider_records if r.verified)
                }

        return performance

    async def _persist_record(self, record: AccuracyRecord):
        """
        Persist accuracy record to database.

        Args:
            record: Accuracy record to persist

        Since:
            Version 1.0.0
        """
        # This would interact with actual database model
        # For now, we're using the cache
        logger.debug(f"Persisting record {record.id}")

    async def _update_record(self, record: AccuracyRecord):
        """
        Update existing record in database.

        Args:
            record: Updated accuracy record

        Since:
            Version 1.0.0
        """
        logger.debug(f"Updating record {record.id}")

    async def _get_record(self, record_id: str) -> Optional[AccuracyRecord]:
        """
        Get record by ID.

        Args:
            record_id: Record ID

        Returns:
            Accuracy record or None

        Since:
            Version 1.0.0
        """
        # Check cache first
        if record_id in self.accuracy_cache:
            return self.accuracy_cache[record_id]

        # Would load from database
        return None

    async def _get_verified_records(
        self,
        prediction_type: Optional[PredictionType] = None,
        provider: Optional[str] = None,
        category: Optional[str] = None,
        time_window_days: int = 30
    ) -> List[AccuracyRecord]:
        """
        Get verified records from database.

        Args:
            prediction_type: Filter by type
            provider: Filter by provider
            category: Filter by category
            time_window_days: Time window

        Returns:
            List of verified records

        Since:
            Version 1.0.0
        """
        # Filter cached records for now
        cutoff = datetime.utcnow() - timedelta(days=time_window_days)

        records = []
        for record in self.accuracy_cache.values():
            if not record.verified:
                continue

            if record.timestamp < cutoff:
                continue

            if prediction_type and record.prediction_type != prediction_type:
                continue

            if provider and record.provider != provider:
                continue

            if category and record.category != category:
                continue

            records.append(record)

        return records

    async def cleanup_old_records(self):
        """
        Remove old records beyond retention period.

        Since:
            Version 1.0.0
        """
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)

        # Clean cache
        old_ids = [
            record_id for record_id, record in self.accuracy_cache.items()
            if record.timestamp < cutoff
        ]

        for record_id in old_ids:
            del self.accuracy_cache[record_id]

        logger.info(f"Cleaned up {len(old_ids)} old accuracy records")


# Global instance
accuracy_tracker = None


def get_accuracy_tracker(db_session: AsyncSession) -> HistoricalAccuracyTracker:
    """
    Get global accuracy tracker instance.

    Args:
        db_session: Database session

    Returns:
        HistoricalAccuracyTracker instance

    Since:
        Version 1.0.0
    """
    global accuracy_tracker
    if not accuracy_tracker:
        accuracy_tracker = HistoricalAccuracyTracker(db_session)
    return accuracy_tracker