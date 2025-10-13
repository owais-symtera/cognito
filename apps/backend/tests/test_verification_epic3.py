"""
Comprehensive tests for Epic 3: Data Verification & Quality Assurance
Tests all 5 stories: Source Authentication, Conflict Resolution, Data Validation,
Data Merging, and Verification Reporting
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import all Epic 3 modules
from src.core.verification.source_authenticator import (
    SourceAuthenticator, SourceWeights, AuthenticationResult, SourceHierarchy
)
from src.core.verification.conflict_resolver import (
    ConflictResolver, ConflictType, ResolutionMethod, ConflictDetectionResult,
    ConflictResolutionResult
)
from src.core.verification.data_validator import (
    DataValidator, ValidationLevel, ValidationResult, PharmaceuticalValidationRules,
    ValidationConfig
)
from src.core.verification.data_merger import (
    DataMerger, MergeStrategy, DataType, MergeConfiguration, MergeRecord,
    TemporalData, GeographicData
)
from src.core.verification.verification_reporter import (
    VerificationReporter, ReportType, QualityThreshold, CategoryMetrics,
    VerificationReport, SourceContribution, QualityTrend
)


class TestSourceAuthenticator:
    """Test Story 3.1: Source Authentication & Hierarchy Verification"""

    @pytest.fixture
    def authenticator(self):
        return SourceAuthenticator()

    @pytest.mark.asyncio
    async def test_authenticate_source_paid_api(self, authenticator):
        """Test authentication of paid API sources"""
        result = await authenticator.authenticate_source(
            source_name="OpenAI API",
            source_url="https://api.openai.com",
            source_type="api",
            metadata={"api_key": "test_key", "subscription": "premium"}
        )

        assert result.authenticated is True
        assert result.authentication_level == "PAID_APIS"
        assert result.weight == SourceWeights.PAID_APIS
        assert result.confidence_score > 0.9

    @pytest.mark.asyncio
    async def test_authenticate_source_government(self, authenticator):
        """Test authentication of government sources"""
        result = await authenticator.authenticate_source(
            source_name="FDA",
            source_url="https://www.fda.gov",
            source_type="website",
            metadata={"domain": ".gov"}
        )

        assert result.authenticated is True
        assert result.authentication_level == "GOVERNMENT"
        assert result.weight == SourceWeights.GOVERNMENT

    @pytest.mark.asyncio
    async def test_verify_hierarchy(self, authenticator):
        """Test source hierarchy verification"""
        sources = [
            {"source": "Reuters", "data": {"price": 100}},
            {"source": "FDA", "data": {"price": 105}},
            {"source": "OpenAI", "data": {"price": 102}}
        ]

        hierarchy = await authenticator.verify_hierarchy(sources)

        assert hierarchy.primary_source == "OpenAI"  # Highest weight (PAID_APIS)
        assert hierarchy.source_ranking[0]["source"] == "OpenAI"
        assert hierarchy.hierarchy_score > 0

    @pytest.mark.asyncio
    async def test_cross_validate_sources(self, authenticator):
        """Test cross-validation of multiple sources"""
        sources = [
            AuthenticationResult(
                source_name="Source1",
                authenticated=True,
                authentication_level="PAID_APIS",
                weight=10,
                confidence_score=0.95,
                timestamp=datetime.now()
            ),
            AuthenticationResult(
                source_name="Source2",
                authenticated=True,
                authentication_level="GOVERNMENT",
                weight=8,
                confidence_score=0.90,
                timestamp=datetime.now()
            )
        ]

        validation = await authenticator.cross_validate_sources(sources)

        assert validation["consensus_level"] == "high"
        assert validation["validation_score"] > 0.8

    def test_source_weights_hierarchy(self):
        """Test source weight hierarchy is correctly ordered"""
        assert SourceWeights.PAID_APIS > SourceWeights.GOVERNMENT
        assert SourceWeights.GOVERNMENT > SourceWeights.PEER_REVIEWED
        assert SourceWeights.PEER_REVIEWED > SourceWeights.INDUSTRY
        assert SourceWeights.INDUSTRY > SourceWeights.COMPANY
        assert SourceWeights.COMPANY > SourceWeights.NEWS
        assert SourceWeights.NEWS > SourceWeights.UNKNOWN


class TestConflictResolver:
    """Test Story 3.2: Data Conflict Detection & Resolution"""

    @pytest.fixture
    def resolver(self):
        return ConflictResolver()

    @pytest.mark.asyncio
    async def test_detect_numerical_conflict(self, resolver):
        """Test detection of numerical conflicts"""
        data_sources = [
            {"source": "Source1", "price": 100, "confidence": 0.9},
            {"source": "Source2", "price": 120, "confidence": 0.8}
        ]

        conflict = await resolver.detect_conflicts(data_sources, "drug_info")

        assert conflict is not None
        assert conflict.conflict_type == ConflictType.NUMERICAL_VARIANCE
        assert conflict.field == "price"
        assert conflict.variance == 0.2  # 20% variance

    @pytest.mark.asyncio
    async def test_detect_categorical_conflict(self, resolver):
        """Test detection of categorical conflicts"""
        data_sources = [
            {"source": "Source1", "status": "approved", "confidence": 0.9},
            {"source": "Source2", "status": "pending", "confidence": 0.8},
            {"source": "Source3", "status": "approved", "confidence": 0.85}
        ]

        conflict = await resolver.detect_conflicts(data_sources, "regulatory")

        assert conflict is not None
        assert conflict.conflict_type == ConflictType.CATEGORICAL_MISMATCH
        assert conflict.field == "status"

    @pytest.mark.asyncio
    async def test_resolve_conflict_weighted_consensus(self, resolver):
        """Test conflict resolution using weighted consensus"""
        conflict = ConflictDetectionResult(
            field="price",
            conflict_type=ConflictType.NUMERICAL_VARIANCE,
            conflicting_values=[
                {"value": 100, "source": "Source1", "confidence": 0.9, "weight": 10},
                {"value": 120, "source": "Source2", "confidence": 0.8, "weight": 5}
            ],
            variance=0.2,
            sources=["Source1", "Source2"],
            timestamp=datetime.now()
        )

        resolution = await resolver.resolve_conflict(conflict, "drug_info")

        assert resolution.resolved_value is not None
        assert resolution.resolution_method == ResolutionMethod.WEIGHTED_CONSENSUS
        assert resolution.confidence_score > 0.5

    @pytest.mark.asyncio
    async def test_temporal_conflict_resolution(self, resolver):
        """Test resolution of temporal conflicts"""
        data_sources = [
            {"source": "Source1", "approval_date": "2023-01-01", "timestamp": datetime(2023, 1, 1)},
            {"source": "Source2", "approval_date": "2023-06-01", "timestamp": datetime(2024, 1, 1)}
        ]

        conflicts = []
        async for conflict in resolver.detect_all_conflicts(data_sources, "drug_info"):
            conflicts.append(conflict)

        if conflicts:
            resolution = await resolver.resolve_conflict(conflicts[0], "drug_info")
            assert resolution.resolution_method in [ResolutionMethod.TEMPORAL_PRECEDENCE, ResolutionMethod.MOST_RECENT]


class TestDataValidator:
    """Test Story 3.3: Data Validation & Quality Assurance"""

    @pytest.fixture
    def validator(self):
        return DataValidator()

    @pytest.mark.asyncio
    async def test_validate_completeness(self, validator):
        """Test data completeness validation"""
        data = {
            "drug_name": "TestDrug",
            "active_ingredient": "TestIngredient",
            "manufacturer": "TestMfg"
            # Missing: approval_status (required field)
        }

        results = await validator.validate_completeness(data, "drug_info")

        assert len(results) > 0
        failed_results = [r for r in results if not r.passed]
        assert any(r.field_name == "approval_status" for r in failed_results)
        assert any(r.level == ValidationLevel.CRITICAL for r in failed_results)

    @pytest.mark.asyncio
    async def test_validate_format_ndc(self, validator):
        """Test NDC number format validation"""
        data = {
            "ndc_number": "12345-678-90"  # Valid NDC format
        }

        results = await validator.validate_format(data, "drug_info")

        assert len(results) > 0
        passed_results = [r for r in results if r.passed]
        assert any(r.field_name == "ndc_number" for r in passed_results)

    @pytest.mark.asyncio
    async def test_validate_format_clinical_trial(self, validator):
        """Test clinical trial ID format validation"""
        data = {
            "trial_id": "NCT12345678"  # Valid format
        }

        results = await validator.validate_format(data, "clinical_trials")

        assert len(results) > 0
        passed_results = [r for r in results if r.passed]
        assert any(r.field_name == "trial_id" for r in passed_results)

    @pytest.mark.asyncio
    async def test_detect_anomalies(self, validator):
        """Test anomaly detection in pharmaceutical data"""
        current_data = {"price": 1000}
        historical_data = [
            {"price": 100},
            {"price": 105},
            {"price": 98},
            {"price": 102}
        ]

        results = await validator.detect_anomalies(current_data, historical_data, "drug_info")

        assert len(results) > 0
        anomaly_results = [r for r in results if not r.passed and r.compliance_flag == "STATISTICAL_ANOMALY"]
        assert len(anomaly_results) > 0  # Should detect price anomaly

    @pytest.mark.asyncio
    async def test_validate_compliance(self, validator):
        """Test regulatory compliance validation"""
        data = {
            "fda_compliance_compliant": True,
            "labeling_compliant": False
        }

        results = await validator.validate_compliance(data, "drug_info")

        assert len(results) > 0
        compliance_violations = [r for r in results if r.level == ValidationLevel.CRITICAL and not r.passed]
        assert any("labeling" in r.field_name for r in compliance_violations)

    @pytest.mark.asyncio
    async def test_comprehensive_validation(self, validator):
        """Test complete validation pipeline"""
        data = {
            "drug_name": "TestDrug",
            "active_ingredient": "TestIngredient",
            "manufacturer": "TestMfg",
            "approval_status": "approved",
            "ndc_number": "12345-678-90",
            "dosage": "100 mg"
        }

        report = await validator.validate_data(data, "drug_info")

        assert "quality_metrics" in report
        assert report["quality_metrics"]["quality_score"] >= 0
        assert "compliance_summary" in report
        assert "recommendations" in report


class TestDataMerger:
    """Test Story 3.4: Validated Data Merging & Consolidation"""

    @pytest.fixture
    def merger(self):
        return DataMerger()

    @pytest.mark.asyncio
    async def test_merge_complementary_data(self, merger):
        """Test merging complementary data from multiple sources"""
        data_sources = [
            {
                "source": "Source1",
                "confidence_score": 0.9,
                "drug_name": "TestDrug",
                "price": 100,
                "side_effects": ["headache", "nausea"]
            },
            {
                "source": "Source2",
                "confidence_score": 0.8,
                "drug_name": "TestDrug",
                "price": 105,
                "side_effects": ["headache", "dizziness"]
            }
        ]

        merged_data, merge_records = await merger.merge_complementary_data(data_sources, "drug_info")

        assert "drug_name" in merged_data
        assert merged_data["drug_name"] == "TestDrug"
        assert "price" in merged_data
        assert "side_effects" in merged_data
        assert len(merge_records) > 0

    @pytest.mark.asyncio
    async def test_enrich_incomplete_records(self, merger):
        """Test enrichment of incomplete records"""
        primary_data = {
            "drug_name": "TestDrug",
            "price": None  # Missing price
        }

        supplementary_sources = [
            {"price": 100, "source": "Source1", "confidence_score": 0.9},
            {"price": 105, "source": "Source2", "confidence_score": 0.85}
        ]

        enriched_data, merge_records = await merger.enrich_incomplete_records(
            primary_data, supplementary_sources, "drug_info"
        )

        assert enriched_data["price"] is not None
        assert len(merge_records) > 0
        assert any(r.merge_strategy == "ENRICHMENT" for r in merge_records)

    @pytest.mark.asyncio
    async def test_handle_temporal_data(self, merger):
        """Test handling of time-series pharmaceutical data"""
        temporal_data = [
            TemporalData(
                timestamp=datetime.now() - timedelta(days=30),
                value=100,
                data_type="price",
                confidence=0.9,
                source="Source1"
            ),
            TemporalData(
                timestamp=datetime.now() - timedelta(days=15),
                value=105,
                data_type="price",
                confidence=0.85,
                source="Source2"
            ),
            TemporalData(
                timestamp=datetime.now(),
                value=110,
                data_type="price",
                confidence=0.9,
                source="Source1"
            )
        ]

        temporal_analysis = await merger.handle_temporal_data(temporal_data, "drug_info")

        assert "price" in temporal_analysis
        assert temporal_analysis["price"]["current_value"] == 110
        assert "trend" in temporal_analysis["price"]
        assert temporal_analysis["price"]["data_points"] == 3

    @pytest.mark.asyncio
    async def test_consolidate_geographic_data(self, merger):
        """Test consolidation of geographic pharmaceutical data"""
        regional_data = {
            "US": {"market_size": 1000000, "growth_rate": 5.2, "confidence_score": 0.9},
            "EU": {"market_size": 800000, "growth_rate": 4.8, "confidence_score": 0.85},
            "JP": {"market_size": 300000, "growth_rate": 3.5, "confidence_score": 0.8}
        }

        consolidated = await merger.consolidate_geographic_data(regional_data, "market_analysis")

        assert "global_summary" in consolidated
        assert "regional_data" in consolidated
        assert "market_coverage" in consolidated
        assert len(consolidated["market_coverage"]) == 3
        assert consolidated["coverage_percentage"] > 0

    @pytest.mark.asyncio
    async def test_merge_strategies(self, merger):
        """Test different merge strategies"""
        values = [
            {"value": 100, "source": "Source1", "confidence": 0.9, "timestamp": datetime.now()},
            {"value": 105, "source": "Source2", "confidence": 0.85, "timestamp": datetime.now() - timedelta(days=1)}
        ]

        # Test HIGHEST_CONFIDENCE strategy
        config = MergeConfiguration("test_field", DataType.NUMERIC, MergeStrategy.HIGHEST_CONFIDENCE)
        merged_value, confidence = await merger._apply_merge_strategy(values, config)
        assert merged_value == 100  # Source1 has higher confidence

        # Test MOST_RECENT strategy
        config = MergeConfiguration("test_field", DataType.NUMERIC, MergeStrategy.MOST_RECENT)
        merged_value, confidence = await merger._apply_merge_strategy(values, config)
        assert merged_value == 100  # Source1 is more recent

        # Test WEIGHTED_AVERAGE strategy
        config = MergeConfiguration("test_field", DataType.NUMERIC, MergeStrategy.WEIGHTED_AVERAGE)
        merged_value, confidence = await merger._apply_merge_strategy(values, config)
        assert 100 <= merged_value <= 105  # Should be weighted average


class TestVerificationReporter:
    """Test Story 3.5: Verification Reporting & Quality Metrics"""

    @pytest.fixture
    def reporter(self):
        return VerificationReporter()

    @pytest.mark.asyncio
    async def test_generate_verification_summary(self, reporter):
        """Test generation of verification summary report"""
        verification_data = {
            "source_authentication": {
                "total_sources": 5,
                "authenticated_count": 4,
                "hierarchy_score": 8.5,
                "authenticated_sources": [
                    {"source_name": "FDA", "weight": 8, "authentication_level": "GOVERNMENT"}
                ]
            },
            "conflict_resolution": {
                "conflicts_detected": 2,
                "conflicts_resolved": 2,
                "conflict_rate": 0.1
            },
            "data_validation": {
                "quality_metrics": {
                    "quality_score": 85,
                    "passed_validations": 17,
                    "failed_validations": 3,
                    "completeness_rate": 90
                }
            },
            "data_merge": {
                "merged_data": {"field1": "value1", "field2": "value2"},
                "confidence_scores": {"overall": 0.88}
            }
        }

        report = await reporter.generate_verification_summary(verification_data, "drug_info", "TEST-001")

        assert report.report_type == ReportType.SUMMARY
        assert report.quality_score > 0
        assert report.process_id == "TEST-001"
        assert len(report.recommendations) > 0
        assert "summary" in report.model_dump()

    @pytest.mark.asyncio
    async def test_generate_source_contribution_analysis(self, reporter):
        """Test source contribution analysis"""
        verification_history = [
            {
                "category": "drug_info",
                "source_authentication": {
                    "authenticated_sources": [
                        {"source_name": "FDA", "weight": 8},
                        {"source_name": "OpenAI", "weight": 10}
                    ]
                },
                "conflict_resolution": {
                    "conflicts": [{"sources": ["FDA", "OpenAI"]}]
                },
                "data_merge": {
                    "audit_trail": {
                        "merge_records": [{"sources_used": ["FDA", "OpenAI"]}]
                    }
                }
            }
        ]

        analysis = await reporter.generate_source_contribution_analysis(verification_history, "drug_info")

        assert "top_contributors" in analysis
        assert "source_rankings" in analysis
        assert "recommendations" in analysis
        assert analysis["total_sources"] > 0

    @pytest.mark.asyncio
    async def test_generate_quality_trends(self, reporter):
        """Test quality trend generation"""
        # Add historical reports
        for i in range(10):
            report = VerificationReport(
                report_id=f"TEST-{i}",
                report_type=ReportType.SUMMARY,
                category="drug_info",
                quality_score=75 + i,
                timestamp=datetime.now() - timedelta(days=10-i),
                summary={},
                details={},
                metrics={},
                recommendations=[]
            )
            reporter.report_history.append(report)

        trends = await reporter.generate_quality_trends("drug_info", 30, "daily")

        assert "data_points" in trends
        assert trends["data_points"] > 0
        assert "improvement_rate" in trends
        assert "trend_direction" in trends
        assert "recommendations" in trends

    @pytest.mark.asyncio
    async def test_create_real_time_status(self, reporter):
        """Test real-time status updates"""
        progress_data = {
            "progress": 45,
            "status": "processing",
            "stages_completed": ["authentication", "conflict_detection"],
            "metrics": {
                "sources_processed": 3,
                "conflicts_found": 1,
                "validations_performed": 15,
                "quality_score": 72
            },
            "elapsed_seconds": 30
        }

        status = await reporter.create_real_time_status("TEST-001", "validation", progress_data)

        assert status["process_id"] == "TEST-001"
        assert status["current_stage"] == "validation"
        assert status["progress"] == 45
        assert "current_metrics" in status
        assert "estimated_completion" in status

    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, reporter):
        """Test compliance report generation"""
        verification_data = {
            "source_authentication": {"authenticated_sources": []},
            "data_validation": {
                "quality_metrics": {"accuracy": 85},
                "audit_trail": True
            },
            "audit_trail": True,
            "quality_score": 82
        }

        report = await reporter.generate_compliance_report(verification_data, "drug_info", "FDA")

        assert report.report_type == ReportType.COMPLIANCE
        assert "compliance_status" in report.model_dump()
        assert report.compliance_status["regulatory_body"] == "FDA"
        assert "compliance_score" in report.summary

    @pytest.mark.asyncio
    async def test_quality_thresholds_and_alerts(self, reporter):
        """Test quality threshold checking and alert generation"""
        metrics = {
            "quality_score": 65,  # Below threshold of 75
            "completeness": 70,   # Below threshold of 80
            "source_diversity": 45,
            "conflict_rate": 0.25,
            "validation_rate": 75,
            "merge_confidence": 0.65
        }

        alerts = reporter._check_quality_thresholds(metrics, "drug_info")

        assert len(alerts) > 0
        quality_alerts = [a for a in alerts if a["metric"] == "quality_score"]
        assert len(quality_alerts) > 0
        assert quality_alerts[0]["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    def test_category_metrics_tracking(self, reporter):
        """Test category metrics tracking"""
        metrics = {
            "quality_score": 85,
            "completeness": 90,
            "validation_rate": 88,
            "conflict_rate": 0.1
        }

        summary = {
            "total_sources": 5,
            "validation_passes": 20,
            "validation_failures": 3,
            "conflicts_detected": 2,
            "fields_merged": 15
        }

        reporter._update_category_metrics("drug_info", metrics, summary)

        category_metrics = reporter.get_category_metrics("drug_info")

        assert category_metrics is not None
        assert category_metrics["quality_score"] == 85
        assert category_metrics["source_coverage"] == 5
        assert category_metrics["validation_passes"] == 20


class TestIntegration:
    """Integration tests for complete Epic 3 workflow"""

    @pytest.mark.asyncio
    async def test_complete_verification_pipeline(self):
        """Test complete verification pipeline from authentication to reporting"""
        # Initialize all components
        authenticator = SourceAuthenticator()
        resolver = ConflictResolver()
        validator = DataValidator()
        merger = DataMerger()
        reporter = VerificationReporter()

        # Step 1: Authenticate sources
        sources = [
            {"name": "FDA", "url": "https://www.fda.gov", "type": "website"},
            {"name": "OpenAI", "url": "https://api.openai.com", "type": "api"}
        ]

        auth_results = []
        for source in sources:
            result = await authenticator.authenticate_source(
                source["name"], source["url"], source["type"]
            )
            auth_results.append(result)

        # Step 2: Process data with conflicts
        data_sources = [
            {
                "source": "FDA",
                "drug_name": "TestDrug",
                "price": 100,
                "approval_status": "approved",
                "confidence": 0.9
            },
            {
                "source": "OpenAI",
                "drug_name": "TestDrug",
                "price": 105,
                "approval_status": "approved",
                "confidence": 0.85
            }
        ]

        # Detect and resolve conflicts
        conflicts = await resolver.detect_conflicts(data_sources, "drug_info")
        resolution = None
        if conflicts:
            resolution = await resolver.resolve_conflict(conflicts, "drug_info")

        # Step 3: Validate data
        validation_report = await validator.validate_data(data_sources[0], "drug_info")

        # Step 4: Merge data
        merged_result = await merger.merge_pharmaceutical_data(data_sources, "drug_info")

        # Step 5: Generate report
        verification_data = {
            "source_authentication": {
                "total_sources": len(auth_results),
                "authenticated_count": sum(1 for r in auth_results if r.authenticated),
                "hierarchy_score": 8.5,
                "authenticated_sources": [
                    {"source_name": r.source_name, "weight": r.weight}
                    for r in auth_results
                ]
            },
            "conflict_resolution": {
                "conflicts_detected": 1 if conflicts else 0,
                "conflicts_resolved": 1 if resolution else 0,
                "conflict_rate": 0.1
            },
            "data_validation": validation_report,
            "data_merge": merged_result
        }

        report = await reporter.generate_verification_summary(verification_data, "drug_info")

        # Assertions
        assert report.quality_score > 0
        assert len(report.summary) > 0
        assert len(report.metrics) > 0

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test error handling across all components"""
        authenticator = SourceAuthenticator()
        resolver = ConflictResolver()
        validator = DataValidator()
        merger = DataMerger()

        # Test with invalid/missing data
        invalid_data = {}

        # Should handle gracefully
        auth_result = await authenticator.authenticate_source("", "", "")
        assert auth_result.authenticated is False

        conflicts = await resolver.detect_conflicts([], "drug_info")
        assert conflicts is None

        validation_results = await validator.validate_completeness(invalid_data, "drug_info")
        assert len(validation_results) > 0

        merged_data, records = await merger.merge_complementary_data([], "drug_info")
        assert merged_data == {}
        assert records == []


@pytest.mark.asyncio
async def test_performance_metrics():
    """Test performance of verification pipeline"""
    import time

    authenticator = SourceAuthenticator()
    start_time = time.time()

    # Authenticate 100 sources
    tasks = []
    for i in range(100):
        task = authenticator.authenticate_source(
            f"Source{i}",
            f"https://source{i}.com",
            "api"
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    elapsed_time = time.time() - start_time

    assert elapsed_time < 5  # Should complete within 5 seconds
    assert len(results) == 100
    assert all(isinstance(r, AuthenticationResult) for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])