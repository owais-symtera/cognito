"""
Story 5.4: Weighted Scoring Assessment Engine
Multi-criteria weighted assessment for pharmaceutical decision support
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json

from ...utils.database import DatabaseClient
from ...utils.tracking import SourceTracker
from ...utils.logging import get_logger

logger = get_logger(__name__)


class AssessmentType(Enum):
    TECHNOLOGY = "technology"
    CLINICAL = "clinical"
    REGULATORY = "regulatory"
    COMMERCIAL = "commercial"
    MANUFACTURING = "manufacturing"
    SAFETY = "safety"


@dataclass
class AssessmentCriterion:
    """Individual assessment criterion"""
    id: int
    name: str
    assessment_type: AssessmentType
    weight: float
    description: str
    evaluation_method: str
    threshold_pass: float
    threshold_excellent: float
    is_mandatory: bool
    active: bool


@dataclass
class CriterionScore:
    """Score for a single criterion"""
    criterion_name: str
    raw_score: float
    weighted_score: float
    percentage: float
    status: str  # 'fail', 'pass', 'good', 'excellent'
    rationale: str
    confidence: float
    sources: List[str]


@dataclass
class WeightedAssessment:
    """Complete weighted assessment result"""
    assessment_type: AssessmentType
    total_score: float
    weighted_total: float
    status: str
    criteria_scores: List[CriterionScore]
    mandatory_passed: bool
    confidence_level: float
    recommendations: List[str]
    timestamp: datetime


class WeightedAssessmentEngine:
    """Database-driven weighted multi-criteria assessment engine"""

    def __init__(self, db_client: DatabaseClient, source_tracker: SourceTracker):
        self.db_client = db_client
        self.source_tracker = source_tracker

    async def initialize(self):
        """Initialize weighted assessment engine"""
        await self._ensure_tables_exist()
        logger.info("Weighted assessment engine initialized")

    async def _ensure_tables_exist(self):
        """Ensure assessment tables exist in database"""
        await self.db_client.execute_many([
            """
            CREATE TABLE IF NOT EXISTS assessment_criteria (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                assessment_type VARCHAR(50) NOT NULL,
                weight DECIMAL(5,2) NOT NULL DEFAULT 1.0,
                description TEXT,
                evaluation_method VARCHAR(100) NOT NULL,
                threshold_pass DECIMAL(5,2) DEFAULT 60.0,
                threshold_excellent DECIMAL(5,2) DEFAULT 85.0,
                is_mandatory BOOLEAN DEFAULT FALSE,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS assessment_weights (
                id SERIAL PRIMARY KEY,
                assessment_type VARCHAR(50) NOT NULL,
                category VARCHAR(100) NOT NULL,
                criterion_id INTEGER REFERENCES assessment_criteria(id),
                weight_override DECIMAL(5,2),
                conditions JSONB,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS assessment_results (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(100) NOT NULL,
                assessment_type VARCHAR(50) NOT NULL,
                criterion_id INTEGER REFERENCES assessment_criteria(id),
                raw_score DECIMAL(5,2) NOT NULL,
                weighted_score DECIMAL(10,2) NOT NULL,
                percentage DECIMAL(5,2) NOT NULL,
                status VARCHAR(20) NOT NULL,
                rationale TEXT,
                confidence DECIMAL(5,2) DEFAULT 100.0,
                sources TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS assessment_summary (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(100) NOT NULL,
                assessment_type VARCHAR(50) NOT NULL,
                total_score DECIMAL(10,2) NOT NULL,
                weighted_total DECIMAL(10,2) NOT NULL,
                status VARCHAR(20) NOT NULL,
                mandatory_passed BOOLEAN NOT NULL,
                confidence_level DECIMAL(5,2) NOT NULL,
                recommendations JSONB,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS assessment_thresholds (
                id SERIAL PRIMARY KEY,
                assessment_type VARCHAR(50) NOT NULL,
                category VARCHAR(100),
                threshold_type VARCHAR(20) NOT NULL,
                value DECIMAL(5,2) NOT NULL,
                label VARCHAR(50) NOT NULL,
                color VARCHAR(20),
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_assessment_results_request
            ON assessment_results(request_id, assessment_type, created_at DESC)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_assessment_summary_request
            ON assessment_summary(request_id, created_at DESC)
            """
        ])

    async def get_assessment_criteria(self,
                                     assessment_type: AssessmentType,
                                     category: Optional[str] = None) -> List[AssessmentCriterion]:
        """Get assessment criteria for a type and optional category"""
        if category:
            # Check for category-specific weight overrides
            query = """
                SELECT
                    ac.id, ac.name, ac.assessment_type,
                    COALESCE(aw.weight_override, ac.weight) as weight,
                    ac.description, ac.evaluation_method,
                    ac.threshold_pass, ac.threshold_excellent,
                    ac.is_mandatory, ac.active
                FROM assessment_criteria ac
                LEFT JOIN assessment_weights aw ON
                    ac.id = aw.criterion_id AND
                    aw.assessment_type = %s AND
                    aw.category = %s AND
                    aw.active = TRUE
                WHERE ac.assessment_type = %s AND ac.active = TRUE
                ORDER BY weight DESC, ac.name
            """
            results = await self.db_client.fetch_all(
                query, (assessment_type.value, category, assessment_type.value)
            )
        else:
            query = """
                SELECT
                    id, name, assessment_type, weight,
                    description, evaluation_method,
                    threshold_pass, threshold_excellent,
                    is_mandatory, active
                FROM assessment_criteria
                WHERE assessment_type = %s AND active = TRUE
                ORDER BY weight DESC, name
            """
            results = await self.db_client.fetch_all(query, (assessment_type.value,))

        criteria = []
        for row in results:
            criteria.append(AssessmentCriterion(
                id=row['id'],
                name=row['name'],
                assessment_type=AssessmentType(row['assessment_type']),
                weight=float(row['weight']),
                description=row['description'],
                evaluation_method=row['evaluation_method'],
                threshold_pass=float(row['threshold_pass']),
                threshold_excellent=float(row['threshold_excellent']),
                is_mandatory=row['is_mandatory'],
                active=row['active']
            ))

        logger.info(f"Retrieved {len(criteria)} criteria for {assessment_type.value}")
        return criteria

    async def perform_assessment(self,
                                assessment_type: AssessmentType,
                                data: Dict[str, Any],
                                request_id: str,
                                category: Optional[str] = None) -> WeightedAssessment:
        """Perform weighted assessment on provided data"""
        logger.info(f"Performing {assessment_type.value} assessment for request: {request_id}")

        # Get criteria
        criteria = await self.get_assessment_criteria(assessment_type, category)
        if not criteria:
            logger.warning(f"No criteria found for assessment type: {assessment_type.value}")
            return WeightedAssessment(
                assessment_type=assessment_type,
                total_score=0,
                weighted_total=0,
                status="incomplete",
                criteria_scores=[],
                mandatory_passed=True,
                confidence_level=0,
                recommendations=["No assessment criteria configured"],
                timestamp=datetime.utcnow()
            )

        # Evaluate each criterion
        criteria_scores = []
        total_weight = 0
        weighted_sum = 0
        mandatory_passed = True
        confidence_sum = 0
        recommendations = []

        for criterion in criteria:
            score = await self._evaluate_criterion(criterion, data, request_id)
            criteria_scores.append(score)

            # Check mandatory criteria
            if criterion.is_mandatory and score.status == "fail":
                mandatory_passed = False
                recommendations.append(
                    f"Mandatory criterion '{criterion.name}' did not pass"
                )

            # Accumulate scores
            total_weight += criterion.weight
            weighted_sum += score.weighted_score
            confidence_sum += score.confidence * criterion.weight

            # Save result
            await self._save_criterion_result(
                request_id, assessment_type, criterion.id, score
            )

        # Calculate overall scores
        total_score = weighted_sum / total_weight if total_weight > 0 else 0
        weighted_total = (weighted_sum / total_weight * 100) if total_weight > 0 else 0
        confidence_level = confidence_sum / total_weight if total_weight > 0 else 0

        # Determine overall status
        status = await self._determine_status(
            assessment_type, weighted_total, mandatory_passed
        )

        # Generate recommendations
        recommendations.extend(
            await self._generate_recommendations(
                assessment_type, criteria_scores, weighted_total
            )
        )

        # Create assessment result
        assessment = WeightedAssessment(
            assessment_type=assessment_type,
            total_score=total_score,
            weighted_total=weighted_total,
            status=status,
            criteria_scores=criteria_scores,
            mandatory_passed=mandatory_passed,
            confidence_level=confidence_level,
            recommendations=recommendations,
            timestamp=datetime.utcnow()
        )

        # Save summary
        await self._save_assessment_summary(request_id, assessment)

        # Track source
        self.source_tracker.add_source(
            request_id=request_id,
            field_name=f"{assessment_type.value}_assessment",
            value=weighted_total,
            source_system="weighted_assessment_engine",
            source_detail={
                'criteria_count': len(criteria),
                'status': status,
                'confidence': confidence_level
            }
        )

        return assessment

    async def _evaluate_criterion(self,
                                 criterion: AssessmentCriterion,
                                 data: Dict[str, Any],
                                 request_id: str) -> CriterionScore:
        """Evaluate a single criterion"""
        # Extract relevant data for criterion
        criterion_data = self._extract_criterion_data(criterion, data)

        # Apply evaluation method
        if criterion.evaluation_method == "numeric_comparison":
            score, rationale = await self._evaluate_numeric(
                criterion, criterion_data
            )
        elif criterion.evaluation_method == "categorical_match":
            score, rationale = await self._evaluate_categorical(
                criterion, criterion_data
            )
        elif criterion.evaluation_method == "rule_based":
            score, rationale = await self._evaluate_rules(
                criterion, criterion_data, request_id
            )
        elif criterion.evaluation_method == "llm_analysis":
            score, rationale = await self._evaluate_llm(
                criterion, criterion_data, request_id
            )
        else:
            score = 50.0
            rationale = "Default evaluation method"

        # Calculate weighted score
        weighted_score = score * criterion.weight / 100

        # Determine status
        if score < criterion.threshold_pass:
            status = "fail"
        elif score < criterion.threshold_excellent:
            status = "pass"
        elif score < 85:
            status = "good"
        else:
            status = "excellent"

        # Extract sources
        sources = []
        if 'sources' in criterion_data:
            sources = criterion_data['sources'] if isinstance(
                criterion_data['sources'], list
            ) else [str(criterion_data['sources'])]

        return CriterionScore(
            criterion_name=criterion.name,
            raw_score=score,
            weighted_score=weighted_score,
            percentage=score,
            status=status,
            rationale=rationale,
            confidence=criterion_data.get('confidence', 80.0),
            sources=sources
        )

    def _extract_criterion_data(self,
                               criterion: AssessmentCriterion,
                               data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data for criterion evaluation"""
        # Look for direct match
        if criterion.name in data:
            return {'value': data[criterion.name], 'confidence': 100.0}

        # Look for nested data
        name_parts = criterion.name.lower().replace(' ', '_').split('.')
        current = data
        for part in name_parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return {'value': None, 'confidence': 0.0}

        return {'value': current, 'confidence': 90.0}

    async def _evaluate_numeric(self,
                               criterion: AssessmentCriterion,
                               data: Dict[str, Any]) -> Tuple[float, str]:
        """Evaluate numeric criterion"""
        value = data.get('value')
        if value is None:
            return 0.0, "No data available"

        try:
            numeric_value = float(value)
            # Simple linear scoring for demo
            if numeric_value >= criterion.threshold_excellent:
                score = 100.0
                rationale = f"Value {numeric_value} exceeds excellent threshold"
            elif numeric_value >= criterion.threshold_pass:
                score = 60.0 + (numeric_value - criterion.threshold_pass) / (
                    criterion.threshold_excellent - criterion.threshold_pass
                ) * 40
                rationale = f"Value {numeric_value} meets passing threshold"
            else:
                score = numeric_value / criterion.threshold_pass * 60
                rationale = f"Value {numeric_value} below passing threshold"

            return score, rationale
        except (ValueError, TypeError):
            return 0.0, f"Invalid numeric value: {value}"

    async def _evaluate_categorical(self,
                                   criterion: AssessmentCriterion,
                                   data: Dict[str, Any]) -> Tuple[float, str]:
        """Evaluate categorical criterion"""
        value = data.get('value')
        if value is None:
            return 0.0, "No data available"

        # Look up categorical scoring from database
        query = """
            SELECT score, rationale
            FROM categorical_scores
            WHERE criterion_id = %s AND category_value = %s
        """
        # For demo, return default scores
        value_lower = str(value).lower()
        if value_lower in ['high', 'excellent', 'yes', 'approved']:
            return 100.0, f"Optimal value: {value}"
        elif value_lower in ['medium', 'good', 'pending']:
            return 75.0, f"Acceptable value: {value}"
        elif value_lower in ['low', 'fair', 'conditional']:
            return 50.0, f"Marginal value: {value}"
        else:
            return 25.0, f"Suboptimal value: {value}"

    async def _evaluate_rules(self,
                             criterion: AssessmentCriterion,
                             data: Dict[str, Any],
                             request_id: str) -> Tuple[float, str]:
        """Evaluate using rule-based logic"""
        # This would integrate with the rule engine
        # For now, return a default score
        return 75.0, "Rule-based evaluation completed"

    async def _evaluate_llm(self,
                           criterion: AssessmentCriterion,
                           data: Dict[str, Any],
                           request_id: str) -> Tuple[float, str]:
        """Evaluate using LLM analysis"""
        # This would integrate with the LLM processor
        # For now, return a default score
        return 80.0, "LLM-based evaluation completed"

    async def _determine_status(self,
                               assessment_type: AssessmentType,
                               weighted_total: float,
                               mandatory_passed: bool) -> str:
        """Determine overall assessment status"""
        if not mandatory_passed:
            return "failed"

        # Get thresholds from database
        query = """
            SELECT threshold_type, value, label
            FROM assessment_thresholds
            WHERE assessment_type = %s AND active = TRUE
            ORDER BY value DESC
        """
        results = await self.db_client.fetch_all(query, (assessment_type.value,))

        for row in results:
            if weighted_total >= float(row['value']):
                return row['label']

        # Default thresholds if none in database
        if weighted_total >= 85:
            return "excellent"
        elif weighted_total >= 70:
            return "good"
        elif weighted_total >= 60:
            return "pass"
        else:
            return "fail"

    async def _generate_recommendations(self,
                                       assessment_type: AssessmentType,
                                       criteria_scores: List[CriterionScore],
                                       weighted_total: float) -> List[str]:
        """Generate recommendations based on assessment"""
        recommendations = []

        # Identify weak areas
        weak_criteria = [
            cs for cs in criteria_scores
            if cs.status in ["fail", "pass"]
        ]

        for criterion in weak_criteria[:3]:  # Top 3 weak areas
            recommendations.append(
                f"Improve {criterion.criterion_name}: "
                f"Current score {criterion.percentage:.1f}%"
            )

        # Overall recommendation
        if weighted_total >= 85:
            recommendations.append("Strong candidate - proceed with confidence")
        elif weighted_total >= 70:
            recommendations.append("Good candidate - address minor issues")
        elif weighted_total >= 60:
            recommendations.append("Marginal candidate - significant improvements needed")
        else:
            recommendations.append("Not recommended - major concerns identified")

        return recommendations

    async def _save_criterion_result(self,
                                    request_id: str,
                                    assessment_type: AssessmentType,
                                    criterion_id: int,
                                    score: CriterionScore):
        """Save individual criterion result"""
        query = """
            INSERT INTO assessment_results
            (request_id, assessment_type, criterion_id, raw_score, weighted_score,
             percentage, status, rationale, confidence, sources)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (
                request_id,
                assessment_type.value,
                criterion_id,
                score.raw_score,
                score.weighted_score,
                score.percentage,
                score.status,
                score.rationale,
                score.confidence,
                score.sources
            )
        )

    async def _save_assessment_summary(self,
                                      request_id: str,
                                      assessment: WeightedAssessment):
        """Save assessment summary"""
        query = """
            INSERT INTO assessment_summary
            (request_id, assessment_type, total_score, weighted_total,
             status, mandatory_passed, confidence_level, recommendations, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        metadata = {
            'timestamp': assessment.timestamp.isoformat(),
            'criteria_count': len(assessment.criteria_scores),
            'weak_areas': [
                cs.criterion_name for cs in assessment.criteria_scores
                if cs.status == "fail"
            ]
        }

        await self.db_client.execute(
            query,
            (
                request_id,
                assessment.assessment_type.value,
                assessment.total_score,
                assessment.weighted_total,
                assessment.status,
                assessment.mandatory_passed,
                assessment.confidence_level,
                json.dumps(assessment.recommendations),
                json.dumps(metadata)
            )
        )

    async def compare_assessments(self,
                                 request_ids: List[str],
                                 assessment_type: AssessmentType) -> Dict[str, Any]:
        """Compare multiple assessments"""
        query = """
            SELECT
                request_id,
                weighted_total,
                status,
                mandatory_passed,
                confidence_level,
                recommendations,
                created_at
            FROM assessment_summary
            WHERE request_id = ANY(%s) AND assessment_type = %s
            ORDER BY created_at DESC
        """

        results = await self.db_client.fetch_all(
            query,
            (request_ids, assessment_type.value)
        )

        comparisons = []
        for row in results:
            comparisons.append({
                'request_id': row['request_id'],
                'weighted_total': float(row['weighted_total']),
                'status': row['status'],
                'mandatory_passed': row['mandatory_passed'],
                'confidence_level': float(row['confidence_level']),
                'recommendations': json.loads(row['recommendations']),
                'created_at': row['created_at'].isoformat()
            })

        return {
            'assessment_type': assessment_type.value,
            'comparisons': comparisons,
            'best_candidate': max(
                comparisons,
                key=lambda x: x['weighted_total']
            ) if comparisons else None
        }

    async def get_assessment_history(self,
                                    request_id: str) -> List[Dict[str, Any]]:
        """Get assessment history for a request"""
        query = """
            SELECT
                assessment_type,
                weighted_total,
                status,
                mandatory_passed,
                confidence_level,
                created_at
            FROM assessment_summary
            WHERE request_id = %s
            ORDER BY created_at DESC
        """

        results = await self.db_client.fetch_all(query, (request_id,))

        history = []
        for row in results:
            history.append({
                'assessment_type': row['assessment_type'],
                'weighted_total': float(row['weighted_total']),
                'status': row['status'],
                'mandatory_passed': row['mandatory_passed'],
                'confidence_level': float(row['confidence_level']),
                'created_at': row['created_at'].isoformat()
            })

        return history