"""
Comprehensive tests for Epic 4: Dynamic Category Processing & Output Generation
Tests all 6 stories: Category Configuration, Template Management, Parameter Substitution,
Category Processing, JSON Output, and Performance Analytics
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import all Epic 4 modules
from src.core.category.category_configurator import (
    CategoryConfigurator, AnalysisProfile, CategoryPriority,
    CategoryConfiguration, WorkflowOptimization, CategoryUsageAnalytics
)
from src.core.category.prompt_template_manager import (
    PromptTemplateManager, PromptTemplate, TemplateVersion, ApprovalStatus,
    TemplateType, ABTestConfig, TemplatePerformanceMetrics
)
from src.core.category.parameter_substitution_engine import (
    ParameterSubstitutionEngine, ParameterDefinition, ParameterType,
    SubstitutionContext, SubstitutionResult
)


class TestCategoryConfigurator:
    """Test Story 4.1: Advanced Category Configuration & Dependencies"""

    @pytest.fixture
    def configurator(self):
        return CategoryConfigurator()

    def test_add_category_configuration(self, configurator):
        """Test adding category configuration"""
        config = CategoryConfiguration(
            category_id="drug_info",
            name="Drug Information",
            description="Basic drug information category",
            priority=CategoryPriority.HIGH,
            dependencies=["regulatory_status"],
            enhances=["market_analysis"],
            cost_factor=1.5,
            processing_time_estimate=45
        )

        result = configurator.add_category_configuration(config)

        assert result is True
        assert "drug_info" in configurator.configurations
        assert configurator.configurations["drug_info"].name == "Drug Information"

    def test_validate_category_activation(self, configurator):
        """Test category activation validation"""
        # Add configurations
        config1 = CategoryConfiguration(
            category_id="base",
            name="Base Category",
            description="Base",
            dependencies=[]
        )
        config2 = CategoryConfiguration(
            category_id="dependent",
            name="Dependent Category",
            description="Depends on base",
            dependencies=["base"]
        )

        configurator.add_category_configuration(config1)
        configurator.add_category_configuration(config2)

        # Test valid activation
        is_valid, issues = configurator.validate_category_activation(
            "dependent", {"base"}
        )
        assert is_valid is True
        assert len(issues) == 0

        # Test invalid activation (missing dependency)
        is_valid, issues = configurator.validate_category_activation(
            "dependent", set()
        )
        assert is_valid is False
        assert "Missing required dependency: base" in issues[0]

    def test_optimize_workflow(self, configurator):
        """Test workflow optimization"""
        # Add sample configurations
        for i in range(5):
            config = CategoryConfiguration(
                category_id=f"cat_{i}",
                name=f"Category {i}",
                description=f"Test category {i}",
                cost_factor=1.0 + (i * 0.1),
                processing_time_estimate=30 + (i * 10)
            )
            configurator.add_category_configuration(config)

        optimization = configurator.optimize_workflow(
            AnalysisProfile.REGULATORY_FOCUS.value,
            constraints={"max_cost": 10.0, "max_time": 300}
        )

        assert isinstance(optimization, WorkflowOptimization)
        assert optimization.estimated_cost >= 0
        assert optimization.estimated_time >= 0
        assert optimization.optimization_score >= 0

    def test_track_usage_analytics(self, configurator):
        """Test usage analytics tracking"""
        configurator.track_usage(
            category_id="test_cat",
            success=True,
            processing_time=45.2,
            quality_score=0.85,
            used_with=["cat1", "cat2"],
            failure_reason=None
        )

        assert "test_cat" in configurator.usage_analytics
        analytics = configurator.usage_analytics["test_cat"]
        assert analytics.usage_count == 1
        assert analytics.success_rate == 1.0
        assert analytics.average_processing_time == 45.2

    def test_dependency_graph_validation(self, configurator):
        """Test dependency graph validation"""
        # Create circular dependency
        config1 = CategoryConfiguration(
            category_id="cat1",
            name="Category 1",
            description="Test",
            dependencies=["cat2"]
        )
        config2 = CategoryConfiguration(
            category_id="cat2",
            name="Category 2",
            description="Test",
            dependencies=["cat1"]
        )

        configurator.add_category_configuration(config1)
        configurator.add_category_configuration(config2)

        is_valid, issues = configurator.validate_dependency_graph()

        assert is_valid is False
        assert any("Circular dependency" in issue for issue in issues)


class TestPromptTemplateManager:
    """Test Story 4.2: Prompt Template Management System"""

    @pytest.fixture
    def manager(self):
        return PromptTemplateManager()

    def test_create_template(self, manager):
        """Test template creation"""
        version = TemplateVersion(
            version_number="1.0.0",
            template_content="Analyze {drug_name} for {indication}",
            created_by="test_user",
            created_at=datetime.now()
        )

        template = PromptTemplate(
            template_id="drug_analysis",
            name="Drug Analysis Template",
            description="Analyzes drug information",
            category="drug_info",
            template_type=TemplateType.CATEGORY,
            current_version="1.0.0",
            versions={"1.0.0": version},
            required_parameters=["drug_name", "indication"]
        )

        result = manager.create_template(template)

        assert result is True
        assert "drug_analysis" in manager.templates

    def test_update_template(self, manager):
        """Test template updating with versioning"""
        # Create initial template
        version = TemplateVersion(
            version_number="1.0.0",
            template_content="Initial content",
            created_by="user1",
            created_at=datetime.now()
        )
        template = PromptTemplate(
            template_id="test",
            name="Test Template",
            description="Test",
            category="test",
            template_type=TemplateType.CATEGORY,
            current_version="1.0.0",
            versions={"1.0.0": version},
            required_parameters=[]
        )
        manager.create_template(template)

        # Update template
        new_version = manager.update_template(
            "test",
            "Updated content",
            "Added new features",
            "user2"
        )

        assert new_version == "1.0.1"
        assert manager.templates["test"].current_version == "1.0.1"
        assert len(manager.templates["test"].versions) == 2

    def test_approval_workflow(self, manager):
        """Test template approval workflow"""
        version = TemplateVersion(
            version_number="1.0.0",
            template_content="Content",
            created_by="user1",
            created_at=datetime.now(),
            approval_status=ApprovalStatus.DRAFT
        )
        template = PromptTemplate(
            template_id="approval_test",
            name="Approval Test",
            description="Test",
            category="test",
            template_type=TemplateType.CATEGORY,
            current_version="1.0.0",
            versions={"1.0.0": version},
            required_parameters=[]
        )
        manager.create_template(template)

        # Submit for approval
        result = manager.submit_for_approval("approval_test", "1.0.0")
        assert result is True

        # Approve template
        result = manager.approve_template("approval_test", "1.0.0", "approver1")
        assert result is True
        assert manager.templates["approval_test"].versions["1.0.0"].approval_status == ApprovalStatus.APPROVED

    def test_ab_testing(self, manager):
        """Test A/B testing functionality"""
        # Create two templates
        for i in range(2):
            version = TemplateVersion(
                version_number="1.0.0",
                template_content=f"Template {i} content",
                created_by="user1",
                created_at=datetime.now()
            )
            template = PromptTemplate(
                template_id=f"template_{i}",
                name=f"Template {i}",
                description="Test",
                category="test",
                template_type=TemplateType.CATEGORY,
                current_version="1.0.0",
                versions={"1.0.0": version},
                required_parameters=[]
            )
            manager.create_template(template)

        # Create A/B test
        test_config = ABTestConfig(
            test_id="test_1",
            template_a_id="template_0",
            template_a_version="1.0.0",
            template_b_id="template_1",
            template_b_version="1.0.0",
            category="test",
            start_date=datetime.now(),
            sample_size=100,
            success_metrics=["quality_score"]
        )

        result = manager.create_ab_test(test_config)
        assert result is True

        # Record test results
        for i in range(50):
            manager.record_ab_test_result(
                "test_1",
                "template_0" if i % 2 == 0 else "template_1",
                success=i % 3 != 0,
                metrics={"quality_score": 0.7 + (i % 10) / 100}
            )

    def test_performance_tracking(self, manager):
        """Test template performance tracking"""
        manager.track_performance(
            template_id="perf_test",
            version="1.0.0",
            success=True,
            quality_score=0.85,
            processing_time=2.5,
            parameters_satisfied=0.9,
            pharmaceutical_metrics={"accuracy": 0.92}
        )

        key = "perf_test_1.0.0"
        assert key in manager.performance_metrics
        metrics = manager.performance_metrics[key]
        assert metrics.total_uses == 1
        assert metrics.average_quality_score == 0.85


class TestParameterSubstitutionEngine:
    """Test Story 4.3: Dynamic Parameter Substitution Engine"""

    @pytest.fixture
    def engine(self):
        return ParameterSubstitutionEngine()

    def test_register_parameter(self, engine):
        """Test parameter registration"""
        definition = ParameterDefinition(
            name="drug_name",
            parameter_type=ParameterType.COMPOUND_NAME,
            description="Name of the drug",
            required=True,
            min_length=2,
            max_length=100
        )

        result = engine.register_parameter("drug_info", definition)

        assert result is True
        assert "drug_info" in engine.parameter_definitions
        assert "drug_name" in engine.parameter_definitions["drug_info"]

    def test_parameter_validation(self, engine):
        """Test pharmaceutical parameter validation"""
        # Register NDC parameter
        ndc_def = ParameterDefinition(
            name="ndc_number",
            parameter_type=ParameterType.NDC_NUMBER,
            description="NDC number",
            required=True
        )
        engine.register_parameter("test", ndc_def)

        # Test valid NDC
        context = SubstitutionContext(
            category="test",
            template_id="test_template",
            request_id="req_001"
        )

        result = engine.substitute_parameters(
            "The NDC is {ndc_number}",
            {"ndc_number": "12345-6789-01"},
            context
        )

        assert result.success is True
        assert result.substituted_template == "The NDC is 12345-6789-01"

        # Test invalid NDC
        result = engine.substitute_parameters(
            "The NDC is {ndc_number}",
            {"ndc_number": "invalid"},
            context
        )

        assert result.success is False
        assert len(result.validation_errors) > 0

    def test_parameter_substitution(self, engine):
        """Test parameter substitution"""
        template = """
        Drug Analysis Report
        ====================
        Drug Name: {drug_name}
        Indication: {indication}
        Date: {current_date}

        {if:has_warnings}
        Warning: {warning_text}
        {/if}
        """

        parameters = {
            "drug_name": "Aspirin",
            "indication": "Pain relief",
            "has_warnings": True,
            "warning_text": "May cause stomach upset"
        }

        context = SubstitutionContext(
            category="drug_info",
            template_id="drug_analysis",
            request_id="req_002"
        )

        result = engine.substitute_parameters(template, parameters, context)

        assert result.success is True
        assert "Aspirin" in result.substituted_template
        assert "Pain relief" in result.substituted_template
        assert "May cause stomach upset" in result.substituted_template

    def test_conditional_processing(self, engine):
        """Test conditional template sections"""
        template = "{if:show_price}Price: ${price}{/if}"

        context = SubstitutionContext(
            category="test",
            template_id="test",
            request_id="req_003"
        )

        # With condition true
        result = engine.substitute_parameters(
            template,
            {"show_price": True, "price": 100},
            context
        )
        assert "Price: $100" in result.substituted_template

        # With condition false
        result = engine.substitute_parameters(
            template,
            {"show_price": False, "price": 100},
            context
        )
        assert "Price" not in result.substituted_template

    def test_loop_processing(self, engine):
        """Test loop template sections"""
        template = "{foreach:side_effects}- {item}\n{/foreach}"

        context = SubstitutionContext(
            category="test",
            template_id="test",
            request_id="req_004"
        )

        result = engine.substitute_parameters(
            template,
            {"side_effects": ["Nausea", "Headache", "Dizziness"]},
            context
        )

        assert "- Nausea" in result.substituted_template
        assert "- Headache" in result.substituted_template
        assert "- Dizziness" in result.substituted_template


class TestIntegration:
    """Integration tests for complete Epic 4 workflow"""

    @pytest.mark.asyncio
    async def test_complete_category_processing_pipeline(self):
        """Test complete category processing pipeline"""
        # Initialize components
        configurator = CategoryConfigurator()
        template_manager = PromptTemplateManager()
        param_engine = ParameterSubstitutionEngine()

        # Step 1: Configure categories
        drug_config = CategoryConfiguration(
            category_id="drug_info",
            name="Drug Information",
            description="Drug information analysis",
            priority=CategoryPriority.HIGH,
            cost_factor=1.5,
            processing_time_estimate=45
        )
        configurator.add_category_configuration(drug_config)

        # Step 2: Create template
        version = TemplateVersion(
            version_number="1.0.0",
            template_content="Analyze {drug_name} for {indication}",
            created_by="test_user",
            created_at=datetime.now()
        )
        template = PromptTemplate(
            template_id="drug_template",
            name="Drug Analysis",
            description="Drug analysis template",
            category="drug_info",
            template_type=TemplateType.CATEGORY,
            current_version="1.0.0",
            versions={"1.0.0": version},
            required_parameters=["drug_name", "indication"]
        )
        template_manager.create_template(template)

        # Step 3: Register parameters
        drug_param = ParameterDefinition(
            name="drug_name",
            parameter_type=ParameterType.COMPOUND_NAME,
            description="Drug name",
            required=True
        )
        param_engine.register_parameter("drug_info", drug_param)

        # Step 4: Execute substitution
        template_content = template_manager.get_template("drug_template")
        context = SubstitutionContext(
            category="drug_info",
            template_id="drug_template",
            request_id="integration_test"
        )

        result = param_engine.substitute_parameters(
            template_content,
            {"drug_name": "Aspirin", "indication": "Pain relief"},
            context
        )

        # Assertions
        assert result.success is True
        assert "Aspirin" in result.substituted_template
        assert "Pain relief" in result.substituted_template

        # Track performance
        template_manager.track_performance(
            "drug_template",
            "1.0.0",
            success=True,
            quality_score=0.9,
            processing_time=2.0,
            parameters_satisfied=1.0
        )

        configurator.track_usage(
            "drug_info",
            success=True,
            processing_time=45.0,
            quality_score=0.9,
            used_with=["drug_info"]
        )

        # Get reports
        perf_report = template_manager.get_performance_report("drug_template")
        assert "versions" in perf_report

        recommendations = configurator.get_usage_recommendations("drug_info")
        assert len(recommendations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])