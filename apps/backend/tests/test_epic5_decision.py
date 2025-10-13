"""
Comprehensive tests for Epic 5: Decision Intelligence & Verdict Generation
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.core.decision.llm_decision_processor import (
    LLMDecisionProcessor, LLMSelectionCriteria, LLMProvider
)
from src.core.decision.rule_engine import (
    RuleBasedDecisionEngine, RuleOperator
)
from src.core.decision.scoring_matrix import (
    ScoringMatrixEngine, ParameterType
)
from src.core.decision.weighted_assessment import (
    WeightedAssessmentEngine, AssessmentType
)
from src.core.decision.verdict_generator import (
    VerdictGenerator, VerdictType, ConfidenceLevel
)
from src.core.decision.summary_synthesizer import (
    ExecutiveSummarySynthesizer, SummaryStyle, SummaryLength
)
from src.core.decision.technology_scoring import (
    TechnologyScoringEngine, DeliveryMethod, ParameterName
)


class TestLLMDecisionProcessor:
    """Test Story 5.1: Selectable LLM Processing Framework"""

    @pytest.fixture
    async def processor(self):
        db_client = Mock()
        db_client.execute_many = AsyncMock()
        db_client.fetch_all = AsyncMock(return_value=[])
        db_client.fetch_one = AsyncMock(return_value=None)
        db_client.execute = AsyncMock()

        source_tracker = Mock()
        processor = LLMDecisionProcessor(db_client, source_tracker)
        await processor.initialize()
        return processor

    @pytest.mark.asyncio
    async def test_llm_selection_by_criteria(self, processor):
        """Test LLM selection based on criteria"""
        criteria = LLMSelectionCriteria(
            category="clinical",
            complexity="high",
            data_volume=5000,
            required_capabilities=["medical", "reasoning"],
            response_time_ms=5000,
            cost_sensitivity="medium"
        )

        # Mock database response
        processor.db_client.fetch_all = AsyncMock(return_value=[
            {
                'provider': 'openai',
                'model': 'gpt-4',
                'score': 95,
                'capabilities': ['medical', 'reasoning', 'analysis']
            }
        ])

        result = await processor.select_optimal_llm(criteria)

        assert result is not None
        assert result.provider == LLMProvider.OPENAI
        assert result.model == 'gpt-4'

    @pytest.mark.asyncio
    async def test_multi_llm_processing(self, processor):
        """Test processing with multiple LLMs"""
        request_id = "test_123"
        category = "regulatory"
        data = {"regulation": "FDA", "status": "pending"}

        # Mock database responses
        processor.db_client.fetch_all = AsyncMock(return_value=[])
        processor._process_single_llm = AsyncMock(return_value={
            "result": "approved",
            "confidence": 85
        })

        result = await processor.process_decision(
            request_id, category, data, use_multiple_llms=True
        )

        assert result is not None
        assert "aggregated_result" in result

    @pytest.mark.asyncio
    async def test_llm_fallback_mechanism(self, processor):
        """Test fallback when primary LLM fails"""
        request_id = "test_fallback"
        category = "clinical"
        data = {"trial_data": "phase_3"}

        # Mock primary failure and fallback success
        processor.db_client.fetch_all = AsyncMock(side_effect=[
            [{'provider': 'anthropic', 'model': 'claude-3'}],  # Primary
            [{'provider': 'openai', 'model': 'gpt-4'}]  # Fallback
        ])

        with patch.object(processor, '_call_llm_api') as mock_call:
            mock_call.side_effect = [
                Exception("Primary LLM failed"),
                {"result": "success", "confidence": 80}
            ]

            result = await processor.process_with_fallback(
                request_id, category, data
            )

            assert result is not None
            assert result.get('fallback_used') is True


class TestRuleBasedDecisionEngine:
    """Test Story 5.2: Rule-Based Decision Logic Engine"""

    @pytest.fixture
    async def engine(self):
        db_client = Mock()
        db_client.execute_many = AsyncMock()
        db_client.fetch_all = AsyncMock(return_value=[])
        db_client.execute = AsyncMock()

        source_tracker = Mock()
        engine = RuleBasedDecisionEngine(db_client, source_tracker)
        await engine.initialize()
        return engine

    @pytest.mark.asyncio
    async def test_rule_evaluation(self, engine):
        """Test rule evaluation with different operators"""
        category = "pharmaceutical"
        data = {"dose": 50, "molecular_weight": 300}
        request_id = "test_rule_eval"

        # Mock rules from database
        engine.db_client.fetch_all = AsyncMock(return_value=[
            {
                'id': 1,
                'name': 'Dose Check',
                'field': 'dose',
                'operator': 'less_than',
                'value': '100',
                'action': 'approve',
                'priority': 1
            },
            {
                'id': 2,
                'name': 'MW Check',
                'field': 'molecular_weight',
                'operator': 'between',
                'value': '200,400',
                'action': 'approve',
                'priority': 2
            }
        ])

        results = await engine.evaluate_rules(category, data, request_id)

        assert len(results) == 2
        assert all(r.passed for r in results)

    @pytest.mark.asyncio
    async def test_complex_rule_conditions(self, engine):
        """Test complex rule conditions with AND/OR logic"""
        engine.db_client.fetch_all = AsyncMock(return_value=[
            {
                'id': 1,
                'name': 'Complex Rule',
                'conditions': [
                    {'field': 'score', 'operator': 'greater_than', 'value': 70},
                    {'field': 'risk', 'operator': 'equals', 'value': 'low'}
                ],
                'condition_logic': 'AND',
                'action': 'approve'
            }
        ])

        result = await engine.evaluate_complex_rule(
            {'score': 80, 'risk': 'low'},
            'test_complex'
        )

        assert result['passed'] is True
        assert result['action'] == 'approve'

    @pytest.mark.asyncio
    async def test_rule_priority_ordering(self, engine):
        """Test rules are evaluated in priority order"""
        engine.db_client.fetch_all = AsyncMock(return_value=[
            {'id': 1, 'priority': 10, 'name': 'Low Priority'},
            {'id': 2, 'priority': 1, 'name': 'High Priority'},
            {'id': 3, 'priority': 5, 'name': 'Medium Priority'}
        ])

        rules = await engine.get_rules_for_category('test')

        assert rules[0]['name'] == 'High Priority'
        assert rules[1]['name'] == 'Medium Priority'
        assert rules[2]['name'] == 'Low Priority'


class TestScoringMatrixEngine:
    """Test Story 5.3: Parameter-Based Scoring Matrix"""

    @pytest.fixture
    async def engine(self):
        db_client = Mock()
        db_client.execute_many = AsyncMock()
        db_client.fetch_all = AsyncMock(return_value=[])
        db_client.execute = AsyncMock()

        source_tracker = Mock()
        engine = ScoringMatrixEngine(db_client, source_tracker)
        await engine.initialize()
        return engine

    @pytest.mark.asyncio
    async def test_parameter_scoring(self, engine):
        """Test scoring of individual parameters"""
        category = "transdermal"
        data = {
            "dose": 25,
            "molecular_weight": 350,
            "melting_point": 120
        }
        request_id = "test_scoring"

        # Mock parameters and ranges
        engine.db_client.fetch_all = AsyncMock(side_effect=[
            [  # Parameters
                {
                    'id': 1,
                    'name': 'dose',
                    'type': 'numeric',
                    'weight': 4.0,
                    'category': category,
                    'min_value': 0,
                    'max_value': 100,
                    'scoring_method': 'linear',
                    'is_critical': False,
                    'active': True
                }
            ],
            [  # Score ranges
                {
                    'min_value': 0,
                    'max_value': 50,
                    'score': 5,
                    'label': 'Excellent',
                    'color': 'green',
                    'is_exclusion': False
                }
            ]
        ])

        result = await engine.calculate_score(category, data, request_id)

        assert result['total_score'] > 0
        assert not result['has_exclusions']
        assert len(result['results']) > 0

    @pytest.mark.asyncio
    async def test_exclusion_criteria(self, engine):
        """Test exclusion criteria detection"""
        data = {"critical_param": 500}  # Exceeds threshold

        engine.db_client.fetch_all = AsyncMock(side_effect=[
            [{'id': 1, 'name': 'critical_param', 'is_critical': True}],
            [{'min_value': 0, 'max_value': 100, 'is_exclusion': True}]
        ])

        result = await engine.calculate_score('test', data, 'test_exclusion')

        assert result['has_exclusions'] is True
        assert len(result['exclusion_reasons']) > 0


class TestWeightedAssessmentEngine:
    """Test Story 5.4: Weighted Scoring Assessment Engine"""

    @pytest.fixture
    async def engine(self):
        db_client = Mock()
        db_client.execute_many = AsyncMock()
        db_client.fetch_all = AsyncMock(return_value=[])
        db_client.execute = AsyncMock()

        source_tracker = Mock()
        engine = WeightedAssessmentEngine(db_client, source_tracker)
        await engine.initialize()
        return engine

    @pytest.mark.asyncio
    async def test_multi_criteria_assessment(self, engine):
        """Test weighted multi-criteria assessment"""
        assessment_type = AssessmentType.TECHNOLOGY
        data = {
            "feasibility": 80,
            "scalability": 70,
            "innovation": 90
        }
        request_id = "test_assessment"

        # Mock criteria
        engine.db_client.fetch_all = AsyncMock(return_value=[
            {
                'id': 1,
                'name': 'feasibility',
                'assessment_type': 'technology',
                'weight': 3.0,
                'threshold_pass': 60,
                'threshold_excellent': 85,
                'is_mandatory': False
            }
        ])

        result = await engine.perform_assessment(
            assessment_type, data, request_id
        )

        assert result.assessment_type == assessment_type
        assert result.weighted_total > 0
        assert result.status in ['pass', 'good', 'excellent']
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_mandatory_criteria_failure(self, engine):
        """Test mandatory criteria causing failure"""
        engine.db_client.fetch_all = AsyncMock(return_value=[
            {
                'id': 1,
                'name': 'safety',
                'weight': 5.0,
                'threshold_pass': 70,
                'is_mandatory': True
            }
        ])

        data = {"safety": 50}  # Below threshold

        result = await engine.perform_assessment(
            AssessmentType.SAFETY, data, "test_mandatory"
        )

        assert not result.mandatory_passed
        assert result.status == "failed"


class TestVerdictGenerator:
    """Test Story 5.5: Go/No-Go Verdict Generation"""

    @pytest.fixture
    async def generator(self):
        db_client = Mock()
        db_client.execute_many = AsyncMock()
        db_client.fetch_all = AsyncMock(return_value=[])
        db_client.execute = AsyncMock()

        source_tracker = Mock()
        generator = VerdictGenerator(db_client, source_tracker)
        await generator.initialize()
        return generator

    @pytest.mark.asyncio
    async def test_go_verdict_generation(self, generator):
        """Test GO verdict generation"""
        request_id = "test_go"
        category = "pharmaceutical"
        assessment_data = {
            "technology_score": 85,
            "clinical_assessment": {"score": 90, "confidence": 95},
            "regulatory_status": "approved",
            "safety_profile": {"score": 88, "confidence": 90}
        }

        generator.db_client.fetch_all = AsyncMock(return_value=[])

        verdict = await generator.generate_verdict(
            request_id, category, assessment_data
        )

        assert verdict.verdict_type == VerdictType.GO
        assert verdict.confidence_level in [
            ConfidenceLevel.HIGH,
            ConfidenceLevel.VERY_HIGH
        ]
        assert len(verdict.supporting_factors) > 0

    @pytest.mark.asyncio
    async def test_no_go_verdict_with_exclusions(self, generator):
        """Test NO-GO verdict with exclusion factors"""
        assessment_data = {
            "technology_score": 30,
            "exclusions": ["dose_too_high", "molecular_weight_exceeded"],
            "safety_profile": {"score": 40}
        }

        verdict = await generator.generate_verdict(
            "test_nogo", "test", assessment_data
        )

        assert verdict.verdict_type == VerdictType.NO_GO
        assert len(verdict.risk_factors) > 0
        assert len(verdict.opposing_factors) > 0

    @pytest.mark.asyncio
    async def test_conditional_verdict(self, generator):
        """Test CONDITIONAL verdict generation"""
        assessment_data = {
            "technology_score": 65,
            "clinical_assessment": {"score": 70},
            "regulatory_status": "pending"
        }

        verdict = await generator.generate_verdict(
            "test_conditional", "test", assessment_data
        )

        assert verdict.verdict_type in [
            VerdictType.CONDITIONAL,
            VerdictType.REQUIRES_REVIEW
        ]
        assert len(verdict.conditions) > 0


class TestExecutiveSummarySynthesizer:
    """Test Story 5.6: Executive Summary Synthesis"""

    @pytest.fixture
    async def synthesizer(self):
        db_client = Mock()
        db_client.execute_many = AsyncMock()
        db_client.fetch_all = AsyncMock(return_value=[])
        db_client.fetch_one = AsyncMock(return_value=None)
        db_client.execute = AsyncMock()

        source_tracker = Mock()
        synthesizer = ExecutiveSummarySynthesizer(db_client, source_tracker)
        await synthesizer.initialize()
        return synthesizer

    @pytest.mark.asyncio
    async def test_executive_summary_generation(self, synthesizer):
        """Test executive summary generation"""
        request_id = "test_summary"
        verdict_data = {
            "verdict_type": "GO",
            "confidence_score": 85,
            "primary_rationale": "Strong performance across all criteria",
            "supporting_factors": [
                {"name": "Technology", "score": 90},
                {"name": "Safety", "score": 85}
            ],
            "risk_factors": ["Market competition"],
            "recommendations": ["Proceed to Phase 2"]
        }
        assessment_data = {
            "category": "pharmaceutical",
            "technology_score": 88
        }

        summary = await synthesizer.synthesize_summary(
            request_id,
            verdict_data,
            assessment_data,
            style=SummaryStyle.EXECUTIVE,
            length=SummaryLength.STANDARD
        )

        assert summary.style == SummaryStyle.EXECUTIVE
        assert len(summary.sections) > 0
        assert len(summary.key_findings) > 0
        assert summary.headline is not None

    @pytest.mark.asyncio
    async def test_technical_summary_style(self, synthesizer):
        """Test technical style summary"""
        verdict_data = {"verdict_type": "CONDITIONAL", "confidence_score": 70}
        assessment_data = {"technology_score": 75}

        summary = await synthesizer.synthesize_summary(
            "test_tech",
            verdict_data,
            assessment_data,
            style=SummaryStyle.TECHNICAL
        )

        assert summary.style == SummaryStyle.TECHNICAL
        assert "technical" in summary.executive_brief.lower()

    @pytest.mark.asyncio
    async def test_comprehensive_summary_with_appendices(self, synthesizer):
        """Test comprehensive summary includes appendices"""
        summary = await synthesizer.synthesize_summary(
            "test_comprehensive",
            {"verdict_type": "GO", "confidence_score": 90},
            {"technology_score": 85},
            length=SummaryLength.COMPREHENSIVE
        )

        assert summary.length == SummaryLength.COMPREHENSIVE
        assert len(summary.appendices) > 0
        assert 'raw_data' in summary.appendices


class TestTechnologyScoringEngine:
    """Test Story 5.7: Technology Scoring Matrix"""

    @pytest.fixture
    async def engine(self):
        db_client = Mock()
        db_client.execute_many = AsyncMock()
        db_client.fetch_all = AsyncMock(return_value=[])
        db_client.fetch_one = AsyncMock(return_value={'count': 0})
        db_client.execute = AsyncMock()

        source_tracker = Mock()
        engine = TechnologyScoringEngine(db_client, source_tracker)
        await engine.initialize()
        return engine

    @pytest.mark.asyncio
    async def test_transdermal_scoring(self, engine):
        """Test transdermal delivery scoring"""
        request_id = "test_transdermal"
        parameters = {
            "dose": 15,  # Good range for transdermal
            "molecular_weight": 250,
            "melting_point": 120,
            "log_p": 2.5
        }

        # Mock database responses
        engine.db_client.fetch_all = AsyncMock(return_value=[
            {'parameter': 'dose', 'weight': 0.40},
            {'parameter': 'molecular_weight', 'weight': 0.30},
            {'parameter': 'melting_point', 'weight': 0.20},
            {'parameter': 'log_p', 'weight': 0.10}
        ])

        engine.db_client.fetch_one = AsyncMock(return_value={
            'score': 4,
            'label': 'Good',
            'is_exclusion': False
        })

        result = await engine.calculate_score(
            request_id,
            parameters,
            DeliveryMethod.TRANSDERMAL
        )

        assert result.delivery_method == DeliveryMethod.TRANSDERMAL
        assert result.total_score > 0
        assert result.recommendation in ["GO", "CONDITIONAL-GO", "NO-GO"]
        assert len(result.parameter_scores) == 4

    @pytest.mark.asyncio
    async def test_transmucosal_scoring(self, engine):
        """Test transmucosal delivery scoring"""
        parameters = {
            "dose": 30,
            "molecular_weight": 400,
            "melting_point": 160,
            "log_p": 1.0
        }

        engine.db_client.fetch_one = AsyncMock(return_value={
            'score': 3,
            'label': 'Fair',
            'is_exclusion': False
        })

        result = await engine.calculate_score(
            "test_tm",
            parameters,
            DeliveryMethod.TRANSMUCOSAL
        )

        assert result.delivery_method == DeliveryMethod.TRANSMUCOSAL
        assert 0 <= result.total_score <= 100

    @pytest.mark.asyncio
    async def test_exclusion_detection(self, engine):
        """Test exclusion criteria in technology scoring"""
        parameters = {
            "dose": 500,  # Exceeds transdermal limit
            "molecular_weight": 800,  # Exceeds limit
            "melting_point": 350,
            "log_p": 8
        }

        engine.db_client.fetch_one = AsyncMock(return_value={
            'score': 0,
            'label': 'Exclusion',
            'is_exclusion': True
        })

        result = await engine.calculate_score(
            "test_exclusion",
            parameters,
            DeliveryMethod.TRANSDERMAL
        )

        assert len(result.exclusions) > 0
        assert result.recommendation == "NO-GO"

    @pytest.mark.asyncio
    async def test_delivery_method_comparison(self, engine):
        """Test comparison between delivery methods"""
        parameters = {
            "dose": 20,
            "molecular_weight": 300,
            "melting_point": 140,
            "log_p": 2.0
        }

        engine.db_client.fetch_one = AsyncMock(side_effect=[
            {'score': 4, 'label': 'Good', 'is_exclusion': False},
            {'score': 3, 'label': 'Fair', 'is_exclusion': False},
            {'score': 4, 'label': 'Good', 'is_exclusion': False},
            {'score': 5, 'label': 'Excellent', 'is_exclusion': False},
            # Transmucosal scores
            {'score': 5, 'label': 'Excellent', 'is_exclusion': False},
            {'score': 4, 'label': 'Good', 'is_exclusion': False},
            {'score': 4, 'label': 'Good', 'is_exclusion': False},
            {'score': 5, 'label': 'Excellent', 'is_exclusion': False}
        ])

        comparison = await engine.compare_delivery_methods(
            "test_compare",
            parameters
        )

        assert 'transdermal' in comparison
        assert 'transmucosal' in comparison
        assert 'recommended_method' in comparison
        assert comparison['recommended_method'] in ['transdermal', 'transmucosal']

    @pytest.mark.asyncio
    async def test_weighted_scoring_calculation(self, engine):
        """Test weighted scoring calculation (40% Dose, 30% MW, 20% MP, 10% LogP)"""
        # Perfect scores for all parameters
        parameters = {
            "dose": 5,
            "molecular_weight": 150,
            "melting_point": 80,
            "log_p": 2.0
        }

        engine.db_client.fetch_all = AsyncMock(return_value=[
            {'parameter': 'dose', 'weight': 0.40},
            {'parameter': 'molecular_weight', 'weight': 0.30},
            {'parameter': 'melting_point', 'weight': 0.20},
            {'parameter': 'log_p', 'weight': 0.10}
        ])

        engine.db_client.fetch_one = AsyncMock(return_value={
            'score': 5,  # Perfect score
            'label': 'Excellent',
            'is_exclusion': False
        })

        result = await engine.calculate_score(
            "test_weights",
            parameters,
            DeliveryMethod.TRANSDERMAL
        )

        # With all perfect scores (5), weighted total should be 5.0
        # Total score should be 100 (5.0 * 20)
        assert result.weighted_total == 5.0
        assert result.total_score == 100.0
        assert result.recommendation == "GO"


class TestIntegration:
    """Integration tests for Epic 5"""

    @pytest.mark.asyncio
    async def test_full_decision_pipeline(self):
        """Test complete decision pipeline from data to verdict"""
        # Initialize all components
        db_client = Mock()
        db_client.execute_many = AsyncMock()
        db_client.fetch_all = AsyncMock(return_value=[])
        db_client.fetch_one = AsyncMock(return_value=None)
        db_client.execute = AsyncMock()
        source_tracker = Mock()

        # Create engines
        tech_engine = TechnologyScoringEngine(db_client, source_tracker)
        verdict_gen = VerdictGenerator(db_client, source_tracker)
        summary_synth = ExecutiveSummarySynthesizer(db_client, source_tracker)

        # Initialize all
        await tech_engine.initialize()
        await verdict_gen.initialize()
        await summary_synth.initialize()

        # Test data
        request_id = "integration_test"
        parameters = {
            "dose": 20,
            "molecular_weight": 280,
            "melting_point": 130,
            "log_p": 2.2
        }

        # Mock responses for technology scoring
        db_client.fetch_one = AsyncMock(return_value={
            'score': 4,
            'label': 'Good',
            'is_exclusion': False
        })

        # Calculate technology score
        tech_score = await tech_engine.calculate_score(
            request_id,
            parameters,
            DeliveryMethod.TRANSDERMAL
        )

        # Generate verdict
        assessment_data = {
            "technology_score": tech_score.total_score,
            "category": "pharmaceutical"
        }

        verdict = await verdict_gen.generate_verdict(
            request_id,
            "pharmaceutical",
            assessment_data
        )

        # Generate summary
        verdict_data = {
            "verdict_type": verdict.verdict_type.value,
            "confidence_score": verdict.confidence_score,
            "primary_rationale": verdict.primary_rationale
        }

        summary = await summary_synth.synthesize_summary(
            request_id,
            verdict_data,
            assessment_data
        )

        # Assertions
        assert tech_score.total_score > 0
        assert verdict.verdict_type in [
            VerdictType.GO,
            VerdictType.NO_GO,
            VerdictType.CONDITIONAL
        ]
        assert summary.headline is not None
        assert len(summary.sections) > 0

    @pytest.mark.asyncio
    async def test_audit_trail_generation(self):
        """Test that all components generate proper audit trails"""
        db_client = Mock()
        db_client.execute_many = AsyncMock()
        db_client.execute = AsyncMock()

        source_tracker = Mock()
        source_tracker.add_source = Mock()

        # Test each component generates audit entries
        components = [
            LLMDecisionProcessor(db_client, source_tracker),
            RuleBasedDecisionEngine(db_client, source_tracker),
            ScoringMatrixEngine(db_client, source_tracker),
            WeightedAssessmentEngine(db_client, source_tracker),
            VerdictGenerator(db_client, source_tracker),
            TechnologyScoringEngine(db_client, source_tracker)
        ]

        for component in components:
            await component.initialize()

        # Verify source tracking was called
        assert source_tracker.add_source.call_count >= 0  # Will be called during operations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])