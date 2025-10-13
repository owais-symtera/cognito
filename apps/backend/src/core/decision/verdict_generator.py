"""
Story 5.5: Go/No-Go Verdict Generation
Comprehensive verdict generation combining all decision factors
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json

from ...utils.database import DatabaseClient
from ...utils.tracking import SourceTracker
from ...utils.logging import get_logger

logger = get_logger(__name__)


class VerdictType(Enum):
    GO = "GO"
    NO_GO = "NO-GO"
    CONDITIONAL = "CONDITIONAL"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ConfidenceLevel(Enum):
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"


@dataclass
class DecisionFactor:
    """Individual factor contributing to verdict"""
    name: str
    category: str
    value: Any
    score: float
    weight: float
    impact: str  # positive, negative, neutral
    confidence: float
    source: str


@dataclass
class Verdict:
    """Comprehensive Go/No-Go verdict"""
    verdict_type: VerdictType
    confidence_level: ConfidenceLevel
    confidence_score: float
    primary_rationale: str
    supporting_factors: List[DecisionFactor]
    opposing_factors: List[DecisionFactor]
    conditions: List[str]
    recommendations: List[str]
    risk_factors: List[str]
    opportunities: List[str]
    decision_path: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime


class VerdictGenerator:
    """Database-driven verdict generation engine"""

    def __init__(self, db_client: DatabaseClient, source_tracker: SourceTracker):
        self.db_client = db_client
        self.source_tracker = source_tracker

    async def initialize(self):
        """Initialize verdict generator"""
        await self._ensure_tables_exist()
        logger.info("Verdict generator initialized")

    async def _ensure_tables_exist(self):
        """Ensure verdict-related tables exist"""
        await self.db_client.execute_many([
            """
            CREATE TABLE IF NOT EXISTS verdict_criteria (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                category VARCHAR(100) NOT NULL,
                threshold_go DECIMAL(5,2) NOT NULL,
                threshold_no_go DECIMAL(5,2) NOT NULL,
                weight DECIMAL(5,2) DEFAULT 1.0,
                is_critical BOOLEAN DEFAULT FALSE,
                description TEXT,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS verdict_rules (
                id SERIAL PRIMARY KEY,
                rule_name VARCHAR(200) NOT NULL,
                rule_type VARCHAR(50) NOT NULL,
                conditions JSONB NOT NULL,
                verdict_override VARCHAR(20),
                confidence_modifier DECIMAL(5,2),
                priority INTEGER DEFAULT 100,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS verdict_history (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(100) NOT NULL,
                verdict VARCHAR(20) NOT NULL,
                confidence_level VARCHAR(20) NOT NULL,
                confidence_score DECIMAL(5,2) NOT NULL,
                primary_rationale TEXT,
                supporting_factors JSONB,
                opposing_factors JSONB,
                conditions TEXT[],
                recommendations TEXT[],
                risk_factors TEXT[],
                opportunities TEXT[],
                decision_path JSONB,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS verdict_factors (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(100) NOT NULL,
                factor_name VARCHAR(200) NOT NULL,
                category VARCHAR(100) NOT NULL,
                value TEXT,
                score DECIMAL(5,2),
                weight DECIMAL(5,2),
                impact VARCHAR(20),
                confidence DECIMAL(5,2),
                source VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS verdict_templates (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                category VARCHAR(100) NOT NULL,
                criteria_ids INTEGER[],
                rule_ids INTEGER[],
                minimum_confidence DECIMAL(5,2) DEFAULT 60.0,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_verdict_history_request
            ON verdict_history(request_id, created_at DESC)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_verdict_factors_request
            ON verdict_factors(request_id, category)
            """
        ])

    async def generate_verdict(self,
                              request_id: str,
                              category: str,
                              assessment_data: Dict[str, Any]) -> Verdict:
        """Generate comprehensive Go/No-Go verdict"""
        logger.info(f"Generating verdict for request: {request_id}, category: {category}")

        # Collect all decision factors
        factors = await self._collect_decision_factors(
            request_id, category, assessment_data
        )

        # Evaluate verdict criteria
        criteria_result = await self._evaluate_criteria(factors, category)

        # Apply verdict rules
        rules_result = await self._apply_verdict_rules(
            factors, criteria_result, category
        )

        # Calculate confidence
        confidence = await self._calculate_confidence(factors, rules_result)

        # Determine final verdict
        verdict_type = await self._determine_verdict(
            criteria_result, rules_result, confidence
        )

        # Separate supporting and opposing factors
        supporting_factors = [f for f in factors if f.impact == "positive"]
        opposing_factors = [f for f in factors if f.impact == "negative"]

        # Generate recommendations
        recommendations = await self._generate_recommendations(
            verdict_type, factors, assessment_data
        )

        # Identify risks and opportunities
        risk_factors = await self._identify_risks(factors, assessment_data)
        opportunities = await self._identify_opportunities(factors, assessment_data)

        # Generate conditions for conditional verdicts
        conditions = []
        if verdict_type == VerdictType.CONDITIONAL:
            conditions = await self._generate_conditions(factors, assessment_data)

        # Create decision path
        decision_path = {
            'criteria_evaluated': len(criteria_result.get('criteria', [])),
            'rules_applied': len(rules_result.get('rules', [])),
            'factors_considered': len(factors),
            'primary_driver': criteria_result.get('primary_driver'),
            'critical_factors': [f.name for f in factors if f.weight > 3]
        }

        # Generate primary rationale
        primary_rationale = await self._generate_rationale(
            verdict_type, criteria_result, rules_result, factors
        )

        # Create verdict
        verdict = Verdict(
            verdict_type=verdict_type,
            confidence_level=self._get_confidence_level(confidence['score']),
            confidence_score=confidence['score'],
            primary_rationale=primary_rationale,
            supporting_factors=supporting_factors,
            opposing_factors=opposing_factors,
            conditions=conditions,
            recommendations=recommendations,
            risk_factors=risk_factors,
            opportunities=opportunities,
            decision_path=decision_path,
            metadata={
                'category': category,
                'factors_count': len(factors),
                'confidence_details': confidence['details']
            },
            timestamp=datetime.utcnow()
        )

        # Save verdict
        await self._save_verdict(request_id, verdict)

        # Track source
        self.source_tracker.add_source(
            request_id=request_id,
            field_name="verdict",
            value=verdict_type.value,
            source_system="verdict_generator",
            source_detail={
                'confidence': confidence['score'],
                'factors': len(factors)
            }
        )

        return verdict

    async def _collect_decision_factors(self,
                                       request_id: str,
                                       category: str,
                                       assessment_data: Dict[str, Any]) -> List[DecisionFactor]:
        """Collect all decision factors from various sources"""
        factors = []

        # Technology scores
        if 'technology_score' in assessment_data:
            factors.append(DecisionFactor(
                name="Technology Score",
                category="technology",
                value=assessment_data['technology_score'],
                score=assessment_data['technology_score'],
                weight=4.0,
                impact=self._determine_impact(assessment_data['technology_score'], 70),
                confidence=95.0,
                source="technology_scoring_engine"
            ))

        # Clinical assessment
        if 'clinical_assessment' in assessment_data:
            clinical = assessment_data['clinical_assessment']
            factors.append(DecisionFactor(
                name="Clinical Viability",
                category="clinical",
                value=clinical.get('score', 0),
                score=clinical.get('score', 0),
                weight=5.0,
                impact=self._determine_impact(clinical.get('score', 0), 60),
                confidence=clinical.get('confidence', 80),
                source="clinical_assessment"
            ))

        # Regulatory compliance
        if 'regulatory_status' in assessment_data:
            reg_status = assessment_data['regulatory_status']
            score = 100 if reg_status == 'approved' else 50 if reg_status == 'pending' else 0
            factors.append(DecisionFactor(
                name="Regulatory Compliance",
                category="regulatory",
                value=reg_status,
                score=score,
                weight=5.0,
                impact=self._determine_impact(score, 50),
                confidence=100.0,
                source="regulatory_database"
            ))

        # Commercial viability
        if 'market_assessment' in assessment_data:
            market = assessment_data['market_assessment']
            factors.append(DecisionFactor(
                name="Market Potential",
                category="commercial",
                value=market.get('potential', 'unknown'),
                score=market.get('score', 50),
                weight=3.0,
                impact=self._determine_impact(market.get('score', 50), 60),
                confidence=market.get('confidence', 70),
                source="market_analysis"
            ))

        # Manufacturing feasibility
        if 'manufacturing' in assessment_data:
            mfg = assessment_data['manufacturing']
            factors.append(DecisionFactor(
                name="Manufacturing Feasibility",
                category="manufacturing",
                value=mfg.get('feasibility', 'unknown'),
                score=mfg.get('score', 50),
                weight=3.5,
                impact=self._determine_impact(mfg.get('score', 50), 65),
                confidence=mfg.get('confidence', 85),
                source="manufacturing_assessment"
            ))

        # Safety profile
        if 'safety_profile' in assessment_data:
            safety = assessment_data['safety_profile']
            factors.append(DecisionFactor(
                name="Safety Profile",
                category="safety",
                value=safety.get('rating', 'unknown'),
                score=safety.get('score', 50),
                weight=5.0,
                impact=self._determine_impact(safety.get('score', 50), 70),
                confidence=safety.get('confidence', 90),
                source="safety_database"
            ))

        # Add any custom factors from database
        custom_factors = await self._get_custom_factors(request_id, category)
        factors.extend(custom_factors)

        # Save factors to database
        for factor in factors:
            await self._save_factor(request_id, factor)

        logger.info(f"Collected {len(factors)} decision factors")
        return factors

    def _determine_impact(self, score: float, threshold: float) -> str:
        """Determine impact of a score"""
        if score >= threshold + 15:
            return "positive"
        elif score <= threshold - 15:
            return "negative"
        else:
            return "neutral"

    async def _evaluate_criteria(self,
                                factors: List[DecisionFactor],
                                category: str) -> Dict[str, Any]:
        """Evaluate verdict criteria"""
        query = """
            SELECT name, threshold_go, threshold_no_go, weight, is_critical
            FROM verdict_criteria
            WHERE category = %s AND active = TRUE
            ORDER BY weight DESC
        """

        criteria_results = await self.db_client.fetch_all(query, (category,))

        evaluation = {
            'criteria': [],
            'go_count': 0,
            'no_go_count': 0,
            'critical_failures': [],
            'primary_driver': None
        }

        for criterion in criteria_results:
            # Find matching factor
            matching_factor = next(
                (f for f in factors if f.name == criterion['name']),
                None
            )

            if matching_factor:
                if matching_factor.score >= criterion['threshold_go']:
                    evaluation['go_count'] += 1
                    if not evaluation['primary_driver']:
                        evaluation['primary_driver'] = matching_factor.name
                elif matching_factor.score <= criterion['threshold_no_go']:
                    evaluation['no_go_count'] += 1
                    if criterion['is_critical']:
                        evaluation['critical_failures'].append(matching_factor.name)

                evaluation['criteria'].append({
                    'name': criterion['name'],
                    'score': matching_factor.score,
                    'threshold_go': criterion['threshold_go'],
                    'threshold_no_go': criterion['threshold_no_go'],
                    'passed': matching_factor.score >= criterion['threshold_go']
                })

        return evaluation

    async def _apply_verdict_rules(self,
                                  factors: List[DecisionFactor],
                                  criteria_result: Dict[str, Any],
                                  category: str) -> Dict[str, Any]:
        """Apply verdict rules"""
        query = """
            SELECT rule_name, rule_type, conditions, verdict_override,
                   confidence_modifier, priority
            FROM verdict_rules
            WHERE active = TRUE
            ORDER BY priority ASC
        """

        rules = await self.db_client.fetch_all(query)

        results = {
            'rules': [],
            'overrides': [],
            'confidence_modifiers': []
        }

        for rule in rules:
            conditions = json.loads(rule['conditions'])
            if await self._check_rule_conditions(conditions, factors, criteria_result):
                results['rules'].append(rule['rule_name'])

                if rule['verdict_override']:
                    results['overrides'].append({
                        'rule': rule['rule_name'],
                        'verdict': rule['verdict_override'],
                        'priority': rule['priority']
                    })

                if rule['confidence_modifier']:
                    results['confidence_modifiers'].append(
                        float(rule['confidence_modifier'])
                    )

        return results

    async def _check_rule_conditions(self,
                                    conditions: Dict[str, Any],
                                    factors: List[DecisionFactor],
                                    criteria_result: Dict[str, Any]) -> bool:
        """Check if rule conditions are met"""
        # Simple condition checking for demo
        for key, value in conditions.items():
            if key == "min_factors":
                if len(factors) < value:
                    return False
            elif key == "has_critical_failure":
                if value and not criteria_result['critical_failures']:
                    return False
            elif key == "min_go_count":
                if criteria_result['go_count'] < value:
                    return False

        return True

    async def _calculate_confidence(self,
                                   factors: List[DecisionFactor],
                                   rules_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate confidence score"""
        # Base confidence from factors
        if factors:
            total_weight = sum(f.weight for f in factors)
            weighted_confidence = sum(
                f.confidence * f.weight for f in factors
            ) / total_weight if total_weight > 0 else 0
        else:
            weighted_confidence = 0

        # Apply confidence modifiers from rules
        for modifier in rules_result.get('confidence_modifiers', []):
            weighted_confidence *= (1 + modifier / 100)

        # Ensure within bounds
        confidence_score = min(100, max(0, weighted_confidence))

        return {
            'score': confidence_score,
            'details': {
                'base_confidence': weighted_confidence,
                'modifiers_applied': len(rules_result.get('confidence_modifiers', [])),
                'factors_count': len(factors)
            }
        }

    async def _determine_verdict(self,
                                criteria_result: Dict[str, Any],
                                rules_result: Dict[str, Any],
                                confidence: Dict[str, Any]) -> VerdictType:
        """Determine final verdict"""
        # Check for rule overrides
        if rules_result['overrides']:
            # Use highest priority override
            override = min(rules_result['overrides'], key=lambda x: x['priority'])
            return VerdictType(override['verdict'])

        # Check for critical failures
        if criteria_result['critical_failures']:
            return VerdictType.NO_GO

        # Insufficient data check
        if confidence['score'] < 30:
            return VerdictType.INSUFFICIENT_DATA

        # Calculate verdict from criteria
        total_criteria = len(criteria_result['criteria'])
        if total_criteria == 0:
            return VerdictType.REQUIRES_REVIEW

        go_ratio = criteria_result['go_count'] / total_criteria

        if go_ratio >= 0.8:
            return VerdictType.GO
        elif go_ratio >= 0.6:
            return VerdictType.CONDITIONAL
        elif go_ratio >= 0.4:
            return VerdictType.REQUIRES_REVIEW
        else:
            return VerdictType.NO_GO

    def _get_confidence_level(self, score: float) -> ConfidenceLevel:
        """Convert confidence score to level"""
        if score >= 90:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 75:
            return ConfidenceLevel.HIGH
        elif score >= 60:
            return ConfidenceLevel.MEDIUM
        elif score >= 40:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    async def _generate_rationale(self,
                                 verdict_type: VerdictType,
                                 criteria_result: Dict[str, Any],
                                 rules_result: Dict[str, Any],
                                 factors: List[DecisionFactor]) -> str:
        """Generate primary rationale for verdict"""
        if verdict_type == VerdictType.GO:
            positive = [f.name for f in factors if f.impact == "positive"][:3]
            return f"Strong performance across key criteria: {', '.join(positive)}"
        elif verdict_type == VerdictType.NO_GO:
            if criteria_result['critical_failures']:
                return f"Critical failures in: {', '.join(criteria_result['critical_failures'])}"
            negative = [f.name for f in factors if f.impact == "negative"][:3]
            return f"Significant concerns in: {', '.join(negative)}"
        elif verdict_type == VerdictType.CONDITIONAL:
            return "Mixed performance requires addressing specific conditions"
        elif verdict_type == VerdictType.REQUIRES_REVIEW:
            return "Additional expert review needed for final determination"
        else:
            return "Insufficient data for comprehensive assessment"

    async def _generate_recommendations(self,
                                       verdict_type: VerdictType,
                                       factors: List[DecisionFactor],
                                       assessment_data: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on verdict"""
        recommendations = []

        if verdict_type == VerdictType.GO:
            recommendations.append("Proceed with implementation planning")
            recommendations.append("Monitor identified risk factors during development")
        elif verdict_type == VerdictType.NO_GO:
            negative_factors = [f for f in factors if f.impact == "negative"]
            for factor in negative_factors[:3]:
                recommendations.append(f"Address {factor.name} concerns before reconsideration")
        elif verdict_type == VerdictType.CONDITIONAL:
            recommendations.append("Complete required conditions before proceeding")
            recommendations.append("Schedule review after condition compliance")
        elif verdict_type == VerdictType.REQUIRES_REVIEW:
            recommendations.append("Gather additional data for informed decision")
            recommendations.append("Consult subject matter experts")
        else:
            recommendations.append("Collect missing critical data points")

        return recommendations

    async def _identify_risks(self,
                            factors: List[DecisionFactor],
                            assessment_data: Dict[str, Any]) -> List[str]:
        """Identify risk factors"""
        risks = []

        # Low scoring critical factors
        critical_low = [
            f for f in factors
            if f.weight >= 4 and f.score < 60
        ]
        for factor in critical_low:
            risks.append(f"{factor.name}: {factor.value} (Score: {factor.score:.1f})")

        # Add specific risks from assessment data
        if 'risks' in assessment_data:
            risks.extend(assessment_data['risks'][:3])

        return risks[:5]  # Limit to top 5 risks

    async def _identify_opportunities(self,
                                    factors: List[DecisionFactor],
                                    assessment_data: Dict[str, Any]) -> List[str]:
        """Identify opportunities"""
        opportunities = []

        # High scoring factors
        strong_factors = [
            f for f in factors
            if f.score >= 80
        ]
        for factor in strong_factors[:3]:
            opportunities.append(f"Leverage strong {factor.name}")

        # Add specific opportunities from assessment data
        if 'opportunities' in assessment_data:
            opportunities.extend(assessment_data['opportunities'][:2])

        return opportunities

    async def _generate_conditions(self,
                                  factors: List[DecisionFactor],
                                  assessment_data: Dict[str, Any]) -> List[str]:
        """Generate conditions for conditional verdict"""
        conditions = []

        # Factors needing improvement
        weak_factors = [
            f for f in factors
            if 50 <= f.score < 70 and f.weight >= 3
        ]
        for factor in weak_factors:
            conditions.append(f"Improve {factor.name} to acceptable threshold (≥70)")

        # Add specific conditions from assessment
        if 'required_conditions' in assessment_data:
            conditions.extend(assessment_data['required_conditions'])

        return conditions[:5]  # Limit to 5 conditions

    async def _get_custom_factors(self,
                                 request_id: str,
                                 category: str) -> List[DecisionFactor]:
        """Get any custom factors from database"""
        query = """
            SELECT factor_name, category, value, score, weight,
                   impact, confidence, source
            FROM verdict_factors
            WHERE request_id = %s AND category = %s
        """

        results = await self.db_client.fetch_all(query, (request_id, category))

        factors = []
        for row in results:
            factors.append(DecisionFactor(
                name=row['factor_name'],
                category=row['category'],
                value=row['value'],
                score=float(row['score']) if row['score'] else 0,
                weight=float(row['weight']) if row['weight'] else 1,
                impact=row['impact'] or 'neutral',
                confidence=float(row['confidence']) if row['confidence'] else 50,
                source=row['source'] or 'custom'
            ))

        return factors

    async def _save_factor(self, request_id: str, factor: DecisionFactor):
        """Save decision factor"""
        query = """
            INSERT INTO verdict_factors
            (request_id, factor_name, category, value, score, weight,
             impact, confidence, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (
                request_id,
                factor.name,
                factor.category,
                str(factor.value),
                factor.score,
                factor.weight,
                factor.impact,
                factor.confidence,
                factor.source
            )
        )

    async def _save_verdict(self, request_id: str, verdict: Verdict):
        """Save verdict to database"""
        query = """
            INSERT INTO verdict_history
            (request_id, verdict, confidence_level, confidence_score,
             primary_rationale, supporting_factors, opposing_factors,
             conditions, recommendations, risk_factors, opportunities,
             decision_path, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        supporting_factors = [
            {
                'name': f.name,
                'score': f.score,
                'confidence': f.confidence
            } for f in verdict.supporting_factors
        ]

        opposing_factors = [
            {
                'name': f.name,
                'score': f.score,
                'confidence': f.confidence
            } for f in verdict.opposing_factors
        ]

        await self.db_client.execute(
            query,
            (
                request_id,
                verdict.verdict_type.value,
                verdict.confidence_level.value,
                verdict.confidence_score,
                verdict.primary_rationale,
                json.dumps(supporting_factors),
                json.dumps(opposing_factors),
                verdict.conditions,
                verdict.recommendations,
                verdict.risk_factors,
                verdict.opportunities,
                json.dumps(verdict.decision_path),
                json.dumps(verdict.metadata)
            )
        )

    async def get_verdict_history(self,
                                 request_id: str) -> List[Dict[str, Any]]:
        """Get verdict history for a request"""
        query = """
            SELECT verdict, confidence_level, confidence_score,
                   primary_rationale, created_at
            FROM verdict_history
            WHERE request_id = %s
            ORDER BY created_at DESC
        """

        results = await self.db_client.fetch_all(query, (request_id,))

        history = []
        for row in results:
            history.append({
                'verdict': row['verdict'],
                'confidence_level': row['confidence_level'],
                'confidence_score': float(row['confidence_score']),
                'rationale': row['primary_rationale'],
                'timestamp': row['created_at'].isoformat()
            })

        return history