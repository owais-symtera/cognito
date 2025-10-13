"""
Story 5.7: Technology Scoring Matrix Implementation
Database-driven technology scoring for transdermal and transmucosal delivery routes
Based on Technology_Go_NoGo_Scoring_Detailed_MAIN.md specifications
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


class DeliveryMethod(Enum):
    TRANSDERMAL = "transdermal"
    TRANSMUCOSAL = "transmucosal"


class ParameterName(Enum):
    DOSE = "dose"
    MOLECULAR_WEIGHT = "molecular_weight"
    MELTING_POINT = "melting_point"
    LOG_P = "log_p"


@dataclass
class ParameterWeight:
    """Parameter weight configuration"""
    parameter: ParameterName
    weight: float
    unit: str
    description: str


@dataclass
class ScoringRange:
    """Scoring range for a parameter"""
    score: int
    min_value: Optional[float]
    max_value: Optional[float]
    label: str
    is_exclusion: bool = False


@dataclass
class ParameterScore:
    """Individual parameter scoring result"""
    parameter: ParameterName
    value: float
    unit: str
    score: int
    weighted_score: float
    label: str
    is_exclusion: bool
    range_used: str


@dataclass
class TechnologyScore:
    """Complete technology scoring result"""
    delivery_method: DeliveryMethod
    total_score: float
    weighted_total: float
    parameter_scores: List[ParameterScore]
    exclusions: List[str]
    recommendation: str
    confidence: float
    metadata: Dict[str, Any]
    timestamp: datetime


class TechnologyScoringEngine:
    """
    Technology scoring engine for pharmaceutical Go/No-Go decisions
    Implements weighted scoring: 40% Dose, 30% MW, 20% MP, 10% LogP
    """

    # Default weights as per specification
    DEFAULT_WEIGHTS = {
        ParameterName.DOSE: ParameterWeight(
            parameter=ParameterName.DOSE,
            weight=0.40,
            unit="mg",
            description="Daily dose requirement"
        ),
        ParameterName.MOLECULAR_WEIGHT: ParameterWeight(
            parameter=ParameterName.MOLECULAR_WEIGHT,
            weight=0.30,
            unit="g/mol",
            description="Molecular weight of compound"
        ),
        ParameterName.MELTING_POINT: ParameterWeight(
            parameter=ParameterName.MELTING_POINT,
            weight=0.20,
            unit="°C",
            description="Melting point temperature"
        ),
        ParameterName.LOG_P: ParameterWeight(
            parameter=ParameterName.LOG_P,
            weight=0.10,
            unit="",
            description="Partition coefficient (lipophilicity)"
        )
    }

    def __init__(self, db_client: DatabaseClient, source_tracker: SourceTracker):
        self.db_client = db_client
        self.source_tracker = source_tracker

    async def initialize(self):
        """Initialize technology scoring engine"""
        await self._ensure_tables_exist()
        await self._load_default_ranges()
        logger.info("Technology scoring engine initialized")

    async def _ensure_tables_exist(self):
        """Ensure technology scoring tables exist"""
        await self.db_client.execute_many([
            """
            CREATE TABLE IF NOT EXISTS technology_parameters (
                id SERIAL PRIMARY KEY,
                parameter VARCHAR(50) NOT NULL,
                weight DECIMAL(5,2) NOT NULL,
                unit VARCHAR(20),
                description TEXT,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(parameter)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS technology_scoring_ranges (
                id SERIAL PRIMARY KEY,
                parameter VARCHAR(50) NOT NULL,
                delivery_method VARCHAR(20) NOT NULL,
                score INTEGER NOT NULL,
                min_value DECIMAL(10,2),
                max_value DECIMAL(10,2),
                label VARCHAR(100),
                is_exclusion BOOLEAN DEFAULT FALSE,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(parameter, delivery_method, score)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS technology_scoring_results (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(100) NOT NULL,
                delivery_method VARCHAR(20) NOT NULL,
                parameter VARCHAR(50) NOT NULL,
                value DECIMAL(10,2) NOT NULL,
                unit VARCHAR(20),
                score INTEGER NOT NULL,
                weighted_score DECIMAL(10,4) NOT NULL,
                label VARCHAR(100),
                is_exclusion BOOLEAN DEFAULT FALSE,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS technology_scoring_summary (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(100) NOT NULL,
                delivery_method VARCHAR(20) NOT NULL,
                total_score DECIMAL(10,2) NOT NULL,
                weighted_total DECIMAL(10,2) NOT NULL,
                exclusions TEXT[],
                recommendation VARCHAR(20) NOT NULL,
                confidence DECIMAL(5,2) NOT NULL,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_tech_scoring_results_request
            ON technology_scoring_results(request_id, delivery_method)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_tech_scoring_summary_request
            ON technology_scoring_summary(request_id, created_at DESC)
            """
        ])

    async def _load_default_ranges(self):
        """Load default scoring ranges from specification"""
        # Check if ranges already exist
        query = "SELECT COUNT(*) as count FROM technology_scoring_ranges"
        result = await self.db_client.fetch_one(query)

        if result['count'] > 0:
            logger.info("Scoring ranges already loaded")
            return

        # Load default ranges based on Technology_Go_NoGo_Scoring_Detailed_MAIN.md
        default_ranges = self._get_default_scoring_ranges()

        for param, delivery_ranges in default_ranges.items():
            for delivery_method, ranges in delivery_ranges.items():
                for range_def in ranges:
                    await self._insert_scoring_range(
                        param, delivery_method, range_def
                    )

        # Load parameter weights
        for param_name, weight_def in self.DEFAULT_WEIGHTS.items():
            await self._insert_parameter_weight(weight_def)

        logger.info("Default scoring ranges and weights loaded")

    def _get_default_scoring_ranges(self) -> Dict[str, Dict[str, List[ScoringRange]]]:
        """Get default scoring ranges from specification"""
        return {
            ParameterName.DOSE.value: {
                DeliveryMethod.TRANSDERMAL.value: [
                    ScoringRange(5, None, 10, "≤10mg - Excellent", False),
                    ScoringRange(4, 10, 25, "10-25mg - Good", False),
                    ScoringRange(3, 25, 50, "25-50mg - Fair", False),
                    ScoringRange(2, 50, 100, "50-100mg - Poor", False),
                    ScoringRange(1, 100, 200, "100-200mg - Very Poor", False),
                    ScoringRange(0, 200, None, ">200mg - Exclusion", True)
                ],
                DeliveryMethod.TRANSMUCOSAL.value: [
                    ScoringRange(5, None, 25, "≤25mg - Excellent", False),
                    ScoringRange(4, 25, 50, "25-50mg - Good", False),
                    ScoringRange(3, 50, 100, "50-100mg - Fair", False),
                    ScoringRange(2, 100, 200, "100-200mg - Poor", False),
                    ScoringRange(1, 200, 400, "200-400mg - Very Poor", False),
                    ScoringRange(0, 400, None, ">400mg - Exclusion", True)
                ]
            },
            ParameterName.MOLECULAR_WEIGHT.value: {
                DeliveryMethod.TRANSDERMAL.value: [
                    ScoringRange(5, None, 200, "≤200 g/mol - Excellent", False),
                    ScoringRange(4, 200, 300, "200-300 g/mol - Good", False),
                    ScoringRange(3, 300, 400, "300-400 g/mol - Fair", False),
                    ScoringRange(2, 400, 500, "400-500 g/mol - Poor", False),
                    ScoringRange(1, 500, 600, "500-600 g/mol - Very Poor", False),
                    ScoringRange(0, 600, None, ">600 g/mol - Exclusion", True)
                ],
                DeliveryMethod.TRANSMUCOSAL.value: [
                    ScoringRange(5, None, 300, "≤300 g/mol - Excellent", False),
                    ScoringRange(4, 300, 500, "300-500 g/mol - Good", False),
                    ScoringRange(3, 500, 700, "500-700 g/mol - Fair", False),
                    ScoringRange(2, 700, 900, "700-900 g/mol - Poor", False),
                    ScoringRange(1, 900, 1200, "900-1200 g/mol - Very Poor", False),
                    ScoringRange(0, 1200, None, ">1200 g/mol - Exclusion", True)
                ]
            },
            ParameterName.MELTING_POINT.value: {
                DeliveryMethod.TRANSDERMAL.value: [
                    ScoringRange(5, None, 100, "≤100°C - Excellent", False),
                    ScoringRange(4, 100, 150, "100-150°C - Good", False),
                    ScoringRange(3, 150, 200, "150-200°C - Fair", False),
                    ScoringRange(2, 200, 250, "200-250°C - Poor", False),
                    ScoringRange(1, 250, 300, "250-300°C - Very Poor", False),
                    ScoringRange(0, 300, None, ">300°C - Exclusion", True)
                ],
                DeliveryMethod.TRANSMUCOSAL.value: [
                    ScoringRange(5, None, 150, "≤150°C - Excellent", False),
                    ScoringRange(4, 150, 200, "150-200°C - Good", False),
                    ScoringRange(3, 200, 250, "200-250°C - Fair", False),
                    ScoringRange(2, 250, 300, "250-300°C - Poor", False),
                    ScoringRange(1, 300, 350, "300-350°C - Very Poor", False),
                    ScoringRange(0, 350, None, ">350°C - Exclusion", True)
                ]
            },
            ParameterName.LOG_P.value: {
                DeliveryMethod.TRANSDERMAL.value: [
                    ScoringRange(5, 1, 3, "1-3 - Excellent", False),
                    ScoringRange(4, 0.5, 1, "0.5-1 - Good", False),
                    ScoringRange(4, 3, 4, "3-4 - Good", False),
                    ScoringRange(3, 0, 0.5, "0-0.5 - Fair", False),
                    ScoringRange(3, 4, 5, "4-5 - Fair", False),
                    ScoringRange(2, -0.5, 0, "-0.5-0 - Poor", False),
                    ScoringRange(2, 5, 6, "5-6 - Poor", False),
                    ScoringRange(1, -1, -0.5, "-1--0.5 - Very Poor", False),
                    ScoringRange(1, 6, 7, "6-7 - Very Poor", False),
                    ScoringRange(0, None, -1, "<-1 - Exclusion", True),
                    ScoringRange(0, 7, None, ">7 - Exclusion", True)
                ],
                DeliveryMethod.TRANSMUCOSAL.value: [
                    ScoringRange(5, -0.5, 2, "-0.5-2 - Excellent", False),
                    ScoringRange(4, -1, -0.5, "-1--0.5 - Good", False),
                    ScoringRange(4, 2, 3.5, "2-3.5 - Good", False),
                    ScoringRange(3, -2, -1, "-2--1 - Fair", False),
                    ScoringRange(3, 3.5, 5, "3.5-5 - Fair", False),
                    ScoringRange(2, -3, -2, "-3--2 - Poor", False),
                    ScoringRange(2, 5, 6, "5-6 - Poor", False),
                    ScoringRange(1, -4, -3, "-4--3 - Very Poor", False),
                    ScoringRange(1, 6, 7, "6-7 - Very Poor", False),
                    ScoringRange(0, None, -4, "<-4 - Exclusion", True),
                    ScoringRange(0, 7, None, ">7 - Exclusion", True)
                ]
            }
        }

    async def _insert_scoring_range(self,
                                   parameter: str,
                                   delivery_method: str,
                                   range_def: ScoringRange):
        """Insert a scoring range into database"""
        query = """
            INSERT INTO technology_scoring_ranges
            (parameter, delivery_method, score, min_value, max_value, label, is_exclusion)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (parameter, delivery_method, score) DO NOTHING
        """

        await self.db_client.execute(
            query,
            (
                parameter,
                delivery_method,
                range_def.score,
                range_def.min_value,
                range_def.max_value,
                range_def.label,
                range_def.is_exclusion
            )
        )

    async def _insert_parameter_weight(self, weight_def: ParameterWeight):
        """Insert parameter weight into database"""
        query = """
            INSERT INTO technology_parameters
            (parameter, weight, unit, description)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (parameter) DO UPDATE SET
                weight = EXCLUDED.weight,
                unit = EXCLUDED.unit,
                updated_at = CURRENT_TIMESTAMP
        """

        await self.db_client.execute(
            query,
            (
                weight_def.parameter.value,
                weight_def.weight,
                weight_def.unit,
                weight_def.description
            )
        )

    async def calculate_score(self,
                            request_id: str,
                            parameters: Dict[str, float],
                            delivery_method: DeliveryMethod) -> TechnologyScore:
        """
        Calculate technology score for given parameters

        Args:
            request_id: Unique request identifier
            parameters: Dict with keys 'dose', 'molecular_weight', 'melting_point', 'log_p'
            delivery_method: Transdermal or Transmucosal delivery route

        Returns:
            TechnologyScore with weighted scoring and recommendations
        """
        logger.info(f"Calculating technology score for {delivery_method.value}, request: {request_id}")

        # Validate parameters
        required_params = [p.value for p in ParameterName]
        missing = [p for p in required_params if p not in parameters]
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")

        # Get weights from database
        weights = await self._get_parameter_weights()

        # Calculate scores for each parameter
        parameter_scores = []
        exclusions = []
        total_weighted = 0

        for param_name in ParameterName:
            value = parameters[param_name.value]
            weight = weights.get(param_name.value, self.DEFAULT_WEIGHTS[param_name].weight)

            # Get score for this parameter
            score_result = await self._score_parameter(
                param_name, value, delivery_method
            )

            # Calculate weighted score
            weighted = score_result.score * weight

            parameter_scores.append(ParameterScore(
                parameter=param_name,
                value=value,
                unit=self.DEFAULT_WEIGHTS[param_name].unit,
                score=score_result.score,
                weighted_score=weighted,
                label=score_result.label,
                is_exclusion=score_result.is_exclusion,
                range_used=score_result.label
            ))

            if score_result.is_exclusion:
                exclusions.append(f"{param_name.value}: {value} ({score_result.label})")

            total_weighted += weighted

            # Save individual result
            await self._save_parameter_result(
                request_id, delivery_method, param_name, value, score_result, weighted
            )

        # Calculate total score (out of 5, then convert to percentage)
        total_score = total_weighted * 20  # Convert 0-5 scale to 0-100

        # Determine recommendation
        recommendation = self._determine_recommendation(total_score, exclusions)

        # Calculate confidence based on data completeness and exclusions
        confidence = self._calculate_confidence(parameter_scores, exclusions)

        # Create technology score result
        tech_score = TechnologyScore(
            delivery_method=delivery_method,
            total_score=total_score,
            weighted_total=total_weighted,
            parameter_scores=parameter_scores,
            exclusions=exclusions,
            recommendation=recommendation,
            confidence=confidence,
            metadata={
                'weights_used': {k: v for k, v in weights.items()},
                'parameters_evaluated': len(parameter_scores),
                'exclusion_count': len(exclusions)
            },
            timestamp=datetime.utcnow()
        )

        # Save summary
        await self._save_scoring_summary(request_id, tech_score)

        # Track source
        self.source_tracker.add_source(
            request_id=request_id,
            field_name="technology_score",
            value=total_score,
            source_system="technology_scoring_engine",
            source_detail={
                'delivery_method': delivery_method.value,
                'recommendation': recommendation,
                'exclusions': len(exclusions)
            }
        )

        return tech_score

    async def _get_parameter_weights(self) -> Dict[str, float]:
        """Get parameter weights from database"""
        query = """
            SELECT parameter, weight
            FROM technology_parameters
            WHERE active = TRUE
        """

        results = await self.db_client.fetch_all(query)

        weights = {}
        for row in results:
            weights[row['parameter']] = float(row['weight'])

        # Use defaults for any missing
        for param in ParameterName:
            if param.value not in weights:
                weights[param.value] = self.DEFAULT_WEIGHTS[param].weight

        return weights

    async def _score_parameter(self,
                              parameter: ParameterName,
                              value: float,
                              delivery_method: DeliveryMethod) -> Any:
        """Score individual parameter based on ranges"""
        query = """
            SELECT score, min_value, max_value, label, is_exclusion
            FROM technology_scoring_ranges
            WHERE parameter = %s
              AND delivery_method = %s
              AND active = TRUE
              AND (
                (min_value IS NULL OR min_value <= %s) AND
                (max_value IS NULL OR max_value > %s)
              )
            ORDER BY score DESC
            LIMIT 1
        """

        result = await self.db_client.fetch_one(
            query,
            (parameter.value, delivery_method.value, value, value)
        )

        if result:
            return type('ScoreResult', (), {
                'score': result['score'],
                'label': result['label'],
                'is_exclusion': result['is_exclusion']
            })

        # Default if no range matched
        return type('ScoreResult', (), {
            'score': 0,
            'label': 'Out of defined ranges',
            'is_exclusion': True
        })

    def _determine_recommendation(self, total_score: float, exclusions: List[str]) -> str:
        """Determine Go/No-Go recommendation"""
        if exclusions:
            return "NO-GO"
        elif total_score >= 80:
            return "GO"
        elif total_score >= 60:
            return "CONDITIONAL-GO"
        elif total_score >= 40:
            return "REQUIRES-REVIEW"
        else:
            return "NO-GO"

    def _calculate_confidence(self,
                             parameter_scores: List[ParameterScore],
                             exclusions: List[str]) -> float:
        """Calculate confidence level"""
        base_confidence = 95.0  # High confidence in quantitative scoring

        # Reduce confidence for exclusions
        if exclusions:
            base_confidence -= len(exclusions) * 10

        # Reduce confidence for borderline scores
        borderline_count = sum(
            1 for ps in parameter_scores
            if ps.score in [2, 3]  # Fair to Poor range
        )
        base_confidence -= borderline_count * 5

        return max(50.0, min(100.0, base_confidence))

    async def _save_parameter_result(self,
                                    request_id: str,
                                    delivery_method: DeliveryMethod,
                                    parameter: ParameterName,
                                    value: float,
                                    score_result: Any,
                                    weighted_score: float):
        """Save individual parameter scoring result"""
        query = """
            INSERT INTO technology_scoring_results
            (request_id, delivery_method, parameter, value, unit, score,
             weighted_score, label, is_exclusion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (
                request_id,
                delivery_method.value,
                parameter.value,
                value,
                self.DEFAULT_WEIGHTS[parameter].unit,
                score_result.score,
                weighted_score,
                score_result.label,
                score_result.is_exclusion
            )
        )

    async def _save_scoring_summary(self, request_id: str, tech_score: TechnologyScore):
        """Save technology scoring summary"""
        query = """
            INSERT INTO technology_scoring_summary
            (request_id, delivery_method, total_score, weighted_total,
             exclusions, recommendation, confidence, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (
                request_id,
                tech_score.delivery_method.value,
                tech_score.total_score,
                tech_score.weighted_total,
                tech_score.exclusions,
                tech_score.recommendation,
                tech_score.confidence,
                json.dumps(tech_score.metadata)
            )
        )

    async def compare_delivery_methods(self,
                                      request_id: str,
                                      parameters: Dict[str, float]) -> Dict[str, Any]:
        """Compare both delivery methods for given parameters"""
        transdermal = await self.calculate_score(
            request_id + "_TD",
            parameters,
            DeliveryMethod.TRANSDERMAL
        )

        transmucosal = await self.calculate_score(
            request_id + "_TM",
            parameters,
            DeliveryMethod.TRANSMUCOSAL
        )

        # Determine best method
        if transdermal.recommendation == "GO" and transmucosal.recommendation != "GO":
            best_method = "transdermal"
        elif transmucosal.recommendation == "GO" and transdermal.recommendation != "GO":
            best_method = "transmucosal"
        elif transdermal.total_score > transmucosal.total_score:
            best_method = "transdermal"
        else:
            best_method = "transmucosal"

        return {
            'transdermal': {
                'score': transdermal.total_score,
                'recommendation': transdermal.recommendation,
                'exclusions': transdermal.exclusions,
                'confidence': transdermal.confidence
            },
            'transmucosal': {
                'score': transmucosal.total_score,
                'recommendation': transmucosal.recommendation,
                'exclusions': transmucosal.exclusions,
                'confidence': transmucosal.confidence
            },
            'recommended_method': best_method,
            'comparison_summary': self._generate_comparison_summary(
                transdermal, transmucosal
            )
        }

    def _generate_comparison_summary(self,
                                    transdermal: TechnologyScore,
                                    transmucosal: TechnologyScore) -> str:
        """Generate comparison summary text"""
        if transdermal.recommendation == "GO" and transmucosal.recommendation == "GO":
            return "Both delivery methods are viable. Choose based on clinical preferences."
        elif transdermal.recommendation == "GO":
            return "Transdermal delivery is recommended as the optimal route."
        elif transmucosal.recommendation == "GO":
            return "Transmucosal delivery is recommended as the optimal route."
        elif transdermal.recommendation == "CONDITIONAL-GO" or transmucosal.recommendation == "CONDITIONAL-GO":
            return "One or both methods may be viable with modifications."
        else:
            return "Neither delivery method meets the required criteria."

    async def get_scoring_history(self,
                                 request_id: str) -> List[Dict[str, Any]]:
        """Get scoring history for a request"""
        query = """
            SELECT
                delivery_method,
                total_score,
                recommendation,
                confidence,
                exclusions,
                created_at
            FROM technology_scoring_summary
            WHERE request_id = %s OR request_id LIKE %s
            ORDER BY created_at DESC
        """

        results = await self.db_client.fetch_all(
            query,
            (request_id, f"{request_id}_%")
        )

        history = []
        for row in results:
            history.append({
                'delivery_method': row['delivery_method'],
                'total_score': float(row['total_score']),
                'recommendation': row['recommendation'],
                'confidence': float(row['confidence']),
                'exclusions': row['exclusions'],
                'timestamp': row['created_at'].isoformat()
            })

        return history

    async def update_scoring_range(self,
                                  parameter: str,
                                  delivery_method: str,
                                  score: int,
                                  min_value: Optional[float],
                                  max_value: Optional[float],
                                  label: str,
                                  is_exclusion: bool = False):
        """Update or create a scoring range (for admin UI)"""
        query = """
            INSERT INTO technology_scoring_ranges
            (parameter, delivery_method, score, min_value, max_value, label, is_exclusion)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (parameter, delivery_method, score)
            DO UPDATE SET
                min_value = EXCLUDED.min_value,
                max_value = EXCLUDED.max_value,
                label = EXCLUDED.label,
                is_exclusion = EXCLUDED.is_exclusion,
                active = TRUE
        """

        await self.db_client.execute(
            query,
            (parameter, delivery_method, score, min_value, max_value, label, is_exclusion)
        )

        logger.info(f"Updated scoring range: {parameter}/{delivery_method}/score={score}")

    async def update_parameter_weight(self,
                                     parameter: str,
                                     weight: float):
        """Update parameter weight (for admin UI)"""
        query = """
            UPDATE technology_parameters
            SET weight = %s, updated_at = CURRENT_TIMESTAMP
            WHERE parameter = %s
        """

        await self.db_client.execute(query, (weight, parameter))

        logger.info(f"Updated weight for {parameter}: {weight}")

    async def export_configuration(self) -> Dict[str, Any]:
        """Export current scoring configuration"""
        # Get parameters and weights
        params_query = """
            SELECT parameter, weight, unit, description
            FROM technology_parameters
            WHERE active = TRUE
        """
        parameters = await self.db_client.fetch_all(params_query)

        # Get scoring ranges
        ranges_query = """
            SELECT parameter, delivery_method, score, min_value, max_value,
                   label, is_exclusion
            FROM technology_scoring_ranges
            WHERE active = TRUE
            ORDER BY parameter, delivery_method, score DESC
        """
        ranges = await self.db_client.fetch_all(ranges_query)

        return {
            'parameters': [dict(row) for row in parameters],
            'scoring_ranges': [dict(row) for row in ranges],
            'export_timestamp': datetime.utcnow().isoformat()
        }