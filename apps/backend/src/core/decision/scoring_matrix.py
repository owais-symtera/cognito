"""
Story 5.3: Parameter-Based Scoring Matrix
Database-driven scoring matrices for pharmaceutical evaluation
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from ...utils.database import DatabaseClient
from ...utils.tracking import SourceTracker
from ...utils.logging import get_logger

logger = get_logger(__name__)


class ParameterType(Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    TEXT = "text"
    DATE = "date"


@dataclass
class ScoringParameter:
    """Scoring parameter configuration from database"""
    id: int
    name: str
    type: ParameterType
    weight: float
    category: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None
    scoring_method: str = "linear"
    is_critical: bool = False
    active: bool = True


@dataclass
class ScoreRange:
    """Score range definition"""
    min_value: float
    max_value: float
    score: float
    label: str
    color: str
    is_exclusion: bool = False


@dataclass
class ScoringResult:
    """Individual parameter scoring result"""
    parameter: str
    value: Any
    raw_score: float
    weighted_score: float
    range_label: str
    is_exclusion: bool
    details: Dict


class ScoringMatrixEngine:
    """Database-driven parameter-based scoring matrix engine"""

    def __init__(self, db_client: DatabaseClient, source_tracker: SourceTracker):
        self.db_client = db_client
        self.source_tracker = source_tracker

    async def initialize(self):
        """Initialize scoring matrix engine"""
        await self._ensure_tables_exist()
        logger.info("Scoring matrix engine initialized")

    async def _ensure_tables_exist(self):
        """Ensure scoring matrix tables exist in database"""
        await self.db_client.execute_many([
            """
            CREATE TABLE IF NOT EXISTS scoring_parameters (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                type VARCHAR(50) NOT NULL,
                weight DECIMAL(5,2) NOT NULL DEFAULT 1.0,
                category VARCHAR(100) NOT NULL,
                min_value DECIMAL(10,2),
                max_value DECIMAL(10,2),
                allowed_values TEXT,
                scoring_method VARCHAR(50) DEFAULT 'linear',
                is_critical BOOLEAN DEFAULT FALSE,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS score_ranges (
                id SERIAL PRIMARY KEY,
                parameter_id INTEGER REFERENCES scoring_parameters(id),
                min_value DECIMAL(10,2),
                max_value DECIMAL(10,2),
                score DECIMAL(5,2) NOT NULL,
                label VARCHAR(100) NOT NULL,
                color VARCHAR(20) NOT NULL,
                is_exclusion BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS scoring_history (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(100) NOT NULL,
                parameter_id INTEGER REFERENCES scoring_parameters(id),
                value TEXT NOT NULL,
                raw_score DECIMAL(5,2) NOT NULL,
                weighted_score DECIMAL(5,2) NOT NULL,
                range_label VARCHAR(100),
                is_exclusion BOOLEAN DEFAULT FALSE,
                details JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS scoring_templates (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                category VARCHAR(100) NOT NULL,
                description TEXT,
                parameter_ids INTEGER[],
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_scoring_history_request
            ON scoring_history(request_id, created_at DESC)
            """
        ])

    async def get_scoring_parameters(self, category: str) -> List[ScoringParameter]:
        """Get active scoring parameters for a category"""
        query = """
            SELECT id, name, type, weight, category, min_value, max_value,
                   allowed_values, scoring_method, is_critical, active
            FROM scoring_parameters
            WHERE category = %s AND active = TRUE
            ORDER BY weight DESC, name
        """

        results = await self.db_client.fetch_all(query, (category,))
        parameters = []

        for row in results:
            parameters.append(ScoringParameter(
                id=row['id'],
                name=row['name'],
                type=ParameterType(row['type']),
                weight=float(row['weight']),
                category=row['category'],
                min_value=float(row['min_value']) if row['min_value'] else None,
                max_value=float(row['max_value']) if row['max_value'] else None,
                allowed_values=row['allowed_values'].split(',') if row['allowed_values'] else None,
                scoring_method=row['scoring_method'],
                is_critical=row['is_critical'],
                active=row['active']
            ))

        logger.info(f"Retrieved {len(parameters)} parameters for category: {category}")
        return parameters

    async def get_score_ranges(self, parameter_id: int) -> List[ScoreRange]:
        """Get score ranges for a parameter"""
        query = """
            SELECT min_value, max_value, score, label, color, is_exclusion
            FROM score_ranges
            WHERE parameter_id = %s
            ORDER BY min_value
        """

        results = await self.db_client.fetch_all(query, (parameter_id,))
        ranges = []

        for row in results:
            ranges.append(ScoreRange(
                min_value=float(row['min_value']) if row['min_value'] else float('-inf'),
                max_value=float(row['max_value']) if row['max_value'] else float('inf'),
                score=float(row['score']),
                label=row['label'],
                color=row['color'],
                is_exclusion=row['is_exclusion']
            ))

        return ranges

    async def calculate_score(self,
                            category: str,
                            data: Dict[str, Any],
                            request_id: str) -> Dict[str, Any]:
        """Calculate scoring matrix for provided data"""
        logger.info(f"Calculating score for category: {category}, request: {request_id}")

        # Get parameters for category
        parameters = await self.get_scoring_parameters(category)
        if not parameters:
            logger.warning(f"No scoring parameters found for category: {category}")
            return {
                'total_score': 0,
                'results': [],
                'has_exclusions': False,
                'message': f"No scoring parameters configured for category: {category}"
            }

        # Calculate scores
        results = []
        total_weighted = 0
        total_weight = 0
        has_exclusions = False
        exclusion_reasons = []

        for param in parameters:
            if param.name not in data:
                if param.is_critical:
                    logger.warning(f"Critical parameter missing: {param.name}")
                    exclusion_reasons.append(f"Critical parameter '{param.name}' is missing")
                    has_exclusions = True
                continue

            # Calculate score for this parameter
            result = await self._score_parameter(param, data[param.name], request_id)
            results.append(result)

            if result.is_exclusion:
                has_exclusions = True
                exclusion_reasons.append(
                    f"{param.name}: {result.value} ({result.range_label})"
                )
            else:
                total_weighted += result.weighted_score
                total_weight += param.weight

            # Track in history
            await self._save_scoring_history(
                request_id, param.id, result
            )

        # Calculate final score
        final_score = (total_weighted / total_weight * 100) if total_weight > 0 else 0

        # Track source
        self.source_tracker.add_source(
            request_id=request_id,
            field_name="scoring_matrix",
            value=final_score,
            source_system="scoring_matrix_engine",
            source_detail={
                'category': category,
                'parameters_evaluated': len(results),
                'total_weight': total_weight
            }
        )

        return {
            'total_score': final_score,
            'results': results,
            'has_exclusions': has_exclusions,
            'exclusion_reasons': exclusion_reasons,
            'parameters_evaluated': len(results),
            'parameters_total': len(parameters),
            'timestamp': datetime.utcnow().isoformat()
        }

    async def _score_parameter(self,
                              parameter: ScoringParameter,
                              value: Any,
                              request_id: str) -> ScoringResult:
        """Score individual parameter value"""
        # Get score ranges
        ranges = await self.get_score_ranges(parameter.id)

        # Convert value to appropriate type
        if parameter.type == ParameterType.NUMERIC:
            try:
                numeric_value = float(value)
            except (ValueError, TypeError):
                logger.error(f"Invalid numeric value for {parameter.name}: {value}")
                return ScoringResult(
                    parameter=parameter.name,
                    value=value,
                    raw_score=0,
                    weighted_score=0,
                    range_label="Invalid Value",
                    is_exclusion=True,
                    details={'error': 'Invalid numeric value'}
                )

            # Find matching range
            for range_def in ranges:
                if range_def.min_value <= numeric_value <= range_def.max_value:
                    raw_score = range_def.score
                    weighted_score = raw_score * parameter.weight

                    return ScoringResult(
                        parameter=parameter.name,
                        value=numeric_value,
                        raw_score=raw_score,
                        weighted_score=weighted_score,
                        range_label=range_def.label,
                        is_exclusion=range_def.is_exclusion,
                        details={
                            'range': f"{range_def.min_value}-{range_def.max_value}",
                            'color': range_def.color
                        }
                    )

        elif parameter.type == ParameterType.CATEGORICAL:
            # Handle categorical scoring
            for range_def in ranges:
                if str(value).lower() == range_def.label.lower():
                    raw_score = range_def.score
                    weighted_score = raw_score * parameter.weight

                    return ScoringResult(
                        parameter=parameter.name,
                        value=value,
                        raw_score=raw_score,
                        weighted_score=weighted_score,
                        range_label=range_def.label,
                        is_exclusion=range_def.is_exclusion,
                        details={'color': range_def.color}
                    )

        # Default if no range matched
        return ScoringResult(
            parameter=parameter.name,
            value=value,
            raw_score=0,
            weighted_score=0,
            range_label="Out of Range",
            is_exclusion=True,
            details={'message': 'Value outside defined ranges'}
        )

    async def _save_scoring_history(self,
                                   request_id: str,
                                   parameter_id: int,
                                   result: ScoringResult):
        """Save scoring result to history"""
        import json

        query = """
            INSERT INTO scoring_history
            (request_id, parameter_id, value, raw_score, weighted_score,
             range_label, is_exclusion, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (
                request_id,
                parameter_id,
                str(result.value),
                result.raw_score,
                result.weighted_score,
                result.range_label,
                result.is_exclusion,
                json.dumps(result.details)
            )
        )

    async def create_scoring_template(self,
                                    name: str,
                                    category: str,
                                    parameter_ids: List[int],
                                    description: Optional[str] = None):
        """Create a scoring template for reuse"""
        query = """
            INSERT INTO scoring_templates (name, category, description, parameter_ids)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name)
            DO UPDATE SET
                category = EXCLUDED.category,
                description = EXCLUDED.description,
                parameter_ids = EXCLUDED.parameter_ids,
                updated_at = CURRENT_TIMESTAMP
        """

        await self.db_client.execute(
            query,
            (name, category, description, parameter_ids)
        )

        logger.info(f"Created scoring template: {name} for category: {category}")

    async def apply_template(self,
                           template_name: str,
                           data: Dict[str, Any],
                           request_id: str) -> Dict[str, Any]:
        """Apply a scoring template to data"""
        # Get template
        query = """
            SELECT category, parameter_ids
            FROM scoring_templates
            WHERE name = %s AND active = TRUE
        """

        result = await self.db_client.fetch_one(query, (template_name,))
        if not result:
            raise ValueError(f"Template not found: {template_name}")

        # Apply scoring with template's category
        return await self.calculate_score(
            result['category'],
            data,
            request_id
        )

    async def get_scoring_trends(self,
                                category: str,
                                days: int = 30) -> Dict[str, Any]:
        """Get scoring trends for analysis"""
        query = """
            WITH daily_scores AS (
                SELECT
                    DATE(sh.created_at) as score_date,
                    sp.name as parameter,
                    AVG(sh.weighted_score) as avg_score,
                    COUNT(*) as count,
                    SUM(CASE WHEN sh.is_exclusion THEN 1 ELSE 0 END) as exclusions
                FROM scoring_history sh
                JOIN scoring_parameters sp ON sh.parameter_id = sp.id
                WHERE sp.category = %s
                  AND sh.created_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(sh.created_at), sp.name
            )
            SELECT * FROM daily_scores
            ORDER BY score_date DESC, parameter
        """

        results = await self.db_client.fetch_all(query, (category, days))

        # Process into trends
        trends = {}
        for row in results:
            date = row['score_date'].isoformat()
            if date not in trends:
                trends[date] = {}
            trends[date][row['parameter']] = {
                'avg_score': float(row['avg_score']),
                'count': row['count'],
                'exclusions': row['exclusions']
            }

        return {
            'category': category,
            'period_days': days,
            'trends': trends
        }