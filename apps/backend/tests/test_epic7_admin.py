"""
Comprehensive tests for Epic 7: Administrative & Monitoring Interfaces
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

from src.core.admin.admin_dashboard import AdminDashboardService
from src.core.admin.process_monitoring import (
    ProcessMonitoringService, ProcessStatus, AlertSeverity, ProcessMetrics
)
from src.core.admin.failure_management import (
    FailureManagementService, ErrorCategory, RecoveryStrategy, ComplianceSeverity
)
from src.core.admin.scoring_config_ui import (
    ScoringConfigurationService, ScoringComponent, ConfigurationStatus
)


class TestAdminDashboardService:
    """Test administrative dashboard service"""

    @pytest.fixture
    async def service(self):
        service = AdminDashboardService()
        await service.initialize()
        return service

    @pytest.mark.asyncio
    async def test_get_dashboard_overview(self, service):
        """Test dashboard overview retrieval"""
        with patch('src.core.admin.admin_dashboard.get_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()

            overview = await service.get_dashboard_overview()

            assert 'statistics' in overview
            assert 'recent_activity' in overview
            assert 'system_health' in overview
            assert 'alerts' in overview

    @pytest.mark.asyncio
    async def test_user_management(self, service):
        """Test user management operations"""
        # Test user creation
        user_id = await service.create_user(
            username="test_admin",
            email="admin@test.com",
            role="administrator",
            created_by="system"
        )
        assert user_id is not None

        # Test user update
        result = await service.update_user(
            user_id=user_id,
            updates={"role": "viewer"},
            updated_by="admin"
        )
        assert result['status'] == "updated"

        # Test user deactivation
        result = await service.deactivate_user(
            user_id=user_id,
            deactivated_by="admin",
            reason="test"
        )
        assert result['status'] == "deactivated"

    @pytest.mark.asyncio
    async def test_category_configuration(self, service):
        """Test category configuration management"""
        # Test category creation
        category_id = await service.create_category(
            name="Test Category",
            type="pharmaceutical",
            metadata={"key": "value"},
            created_by="admin"
        )
        assert category_id is not None

        # Test category update
        result = await service.update_category(
            category_id=category_id,
            updates={"name": "Updated Category"},
            updated_by="admin"
        )
        assert result['status'] == "updated"

    @pytest.mark.asyncio
    async def test_api_key_management(self, service):
        """Test API key management"""
        # Test API key generation
        api_key = await service.generate_api_key(
            name="Test API Key",
            permissions=["read", "write"],
            expires_in_days=30,
            created_by="admin"
        )
        assert 'key' in api_key
        assert 'id' in api_key

        # Test API key revocation
        result = await service.revoke_api_key(
            key_id=api_key['id'],
            revoked_by="admin",
            reason="test"
        )
        assert result['status'] == "revoked"

    @pytest.mark.asyncio
    async def test_approval_workflow(self, service):
        """Test approval workflow system"""
        # Create approval workflow
        workflow_id = await service.create_approval_workflow(
            request_type="configuration_change",
            requested_by="user",
            changes={"setting": "value"}
        )
        assert workflow_id is not None

        # Process approval
        result = await service.process_approval(
            workflow_id=workflow_id,
            approver="admin",
            decision="approved",
            comments="looks good"
        )
        assert result['status'] == "approved"


class TestProcessMonitoringService:
    """Test process monitoring service"""

    @pytest.fixture
    async def service(self):
        service = ProcessMonitoringService()
        await service.initialize()
        return service

    @pytest.mark.asyncio
    async def test_get_dashboard_metrics(self, service):
        """Test dashboard metrics retrieval"""
        with patch('src.core.admin.process_monitoring.get_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()

            metrics = await service.get_dashboard_metrics()

            assert 'process_metrics' in metrics
            assert 'stage_metrics' in metrics
            assert 'resource_metrics' in metrics
            assert 'active_alerts' in metrics

    @pytest.mark.asyncio
    async def test_monitor_process(self, service):
        """Test individual process monitoring"""
        with patch('src.core.admin.process_monitoring.get_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()

            process_data = await service.monitor_process("test_request_id")

            assert 'request' in process_data
            assert 'stages' in process_data
            assert 'logs' in process_data
            assert 'completion_percentage' in process_data

    @pytest.mark.asyncio
    async def test_create_alert(self, service):
        """Test alert creation"""
        alert_id = await service.create_alert(
            severity=AlertSeverity.WARNING,
            category="PROCESS",
            message="Test alert",
            source="test",
            metadata={"test": "data"}
        )
        assert alert_id is not None

    @pytest.mark.asyncio
    async def test_resolve_alert(self, service):
        """Test alert resolution"""
        # First create an alert
        alert_id = await service.create_alert(
            severity=AlertSeverity.WARNING,
            category="TEST",
            message="Test alert",
            source="test"
        )

        # Then resolve it
        await service.resolve_alert(
            alert_id=alert_id,
            resolved_by="admin",
            resolution="fixed"
        )

    @pytest.mark.asyncio
    async def test_system_health(self, service):
        """Test system health assessment"""
        with patch('src.core.admin.process_monitoring.get_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()

            health = await service.get_system_health()

            assert 'status' in health
            assert 'health_score' in health
            assert 'issues' in health
            assert health['health_score'] >= 0
            assert health['health_score'] <= 100


class TestFailureManagementService:
    """Test failure management service"""

    @pytest.fixture
    async def service(self):
        service = FailureManagementService()
        await service.initialize()
        return service

    @pytest.mark.asyncio
    async def test_handle_failure(self, service):
        """Test failure handling"""
        error = ValueError("Test error")

        with patch('src.core.admin.failure_management.get_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()

            result = await service.handle_failure(
                request_id="test_request",
                error=error,
                stage="processing",
                context={"test": "context"}
            )

            assert 'failure_id' in result
            assert 'analysis' in result
            assert 'recovery_plan' in result

    @pytest.mark.asyncio
    async def test_execute_recovery(self, service):
        """Test recovery execution"""
        with patch('src.core.admin.failure_management.get_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()

            result = await service.execute_recovery(
                recovery_id="test_recovery",
                executor="admin",
                override_strategy=RecoveryStrategy.AUTOMATIC_RETRY
            )

            assert 'status' in result

    @pytest.mark.asyncio
    async def test_failure_trends(self, service):
        """Test failure trend analysis"""
        with patch('src.core.admin.failure_management.get_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()

            trends = await service.get_failure_trends(timeframe_hours=24)

            assert 'by_category' in trends
            assert 'by_stage' in trends
            assert 'trending_issues' in trends
            assert 'recommendations' in trends

    @pytest.mark.asyncio
    async def test_generate_failure_report(self, service):
        """Test failure report generation"""
        with patch('src.core.admin.failure_management.get_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()

            report = await service.generate_failure_report(
                start_date=datetime.utcnow() - timedelta(days=7),
                end_date=datetime.utcnow(),
                include_compliance=True
            )

            assert 'report_period' in report
            assert 'summary' in report
            assert 'recovery_performance' in report
            assert 'compliance' in report

    @pytest.mark.asyncio
    async def test_predict_failures(self, service):
        """Test failure prediction"""
        predictions = await service.predict_failures()

        assert isinstance(predictions, list)
        for prediction in predictions:
            assert 'category' in prediction
            assert 'likelihood' in prediction
            assert 'recommended_action' in prediction


class TestScoringConfigurationService:
    """Test scoring configuration management"""

    @pytest.fixture
    async def service(self):
        service = ScoringConfigurationService()
        await service.initialize()
        return service

    @pytest.mark.asyncio
    async def test_create_configuration(self, service):
        """Test configuration creation"""
        config_id = await service.create_configuration(
            component=ScoringComponent.CHEMICAL_ANALYSIS,
            name="Test Config",
            weights={"factor1": 0.5, "factor2": 0.5},
            rules=[{"condition": "test", "action": "pass"}],
            thresholds={"overall": {"pass": 0.7, "fail": 0.3}},
            created_by="admin"
        )
        assert config_id is not None

    @pytest.mark.asyncio
    async def test_update_configuration(self, service):
        """Test configuration update"""
        # First create a config
        config_id = await service.create_configuration(
            component=ScoringComponent.TECHNOLOGY_SCORING,
            name="Test Config",
            weights={"dose": 0.4, "mw": 0.3, "mp": 0.2, "logp": 0.1},
            rules=[],
            thresholds={"overall": {"pass": 0.7, "fail": 0.3}},
            created_by="admin"
        )

        # Update it
        result = await service.update_configuration(
            config_id=config_id,
            updates={"weights": {"dose": 0.5, "mw": 0.2, "mp": 0.2, "logp": 0.1}},
            updated_by="admin"
        )
        assert result['status'] == "updated"

    @pytest.mark.asyncio
    async def test_approval_workflow(self, service):
        """Test configuration approval workflow"""
        # Create config
        config_id = await service.create_configuration(
            component=ScoringComponent.WEIGHTED_DECISION,
            name="Test Config",
            weights={"factor1": 1.0},
            rules=[],
            thresholds={},
            created_by="user"
        )

        # Submit for approval
        approval_id = await service.submit_for_approval(
            config_id=config_id,
            submitted_by="user",
            justification="test change"
        )
        assert approval_id is not None

        # Approve configuration
        result = await service.approve_configuration(
            approval_id=approval_id,
            approver="admin",
            comments="approved"
        )
        assert 'approval_id' in result

    @pytest.mark.asyncio
    async def test_test_configuration(self, service):
        """Test configuration testing"""
        # Create config
        config_id = await service.create_configuration(
            component=ScoringComponent.CHEMICAL_ANALYSIS,
            name="Test Config",
            weights={"mw": 0.5, "logp": 0.5},
            rules=[],
            thresholds={"overall": {"pass": 0.7, "fail": 0.3}},
            created_by="admin"
        )

        # Test with sample data
        test_result = await service.test_configuration(
            config_id=config_id,
            test_data={"mw": 80, "logp": 60}
        )

        assert 'scores' in test_result
        assert 'weighted_score' in test_result
        assert 'decision' in test_result

    @pytest.mark.asyncio
    async def test_configuration_history(self, service):
        """Test configuration history tracking"""
        # Create and update config
        config_id = await service.create_configuration(
            component=ScoringComponent.MARKET_INTELLIGENCE,
            name="Test Config",
            weights={"price": 1.0},
            rules=[],
            thresholds={},
            created_by="admin"
        )

        # Get history
        history = await service.get_configuration_history(config_id)
        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_export_import_configuration(self, service):
        """Test configuration export and import"""
        # Create config
        config_id = await service.create_configuration(
            component=ScoringComponent.PATENT_ASSESSMENT,
            name="Export Test",
            weights={"novelty": 0.5, "inventive_step": 0.5},
            rules=[{"condition": "test", "action": "pass"}],
            thresholds={"overall": {"pass": 0.8, "fail": 0.2}},
            created_by="admin"
        )

        # Export
        export_data = await service.export_configuration(config_id)
        assert 'configuration' in export_data
        assert 'weights' in export_data
        assert 'rules' in export_data

        # Import
        imported_id = await service.import_configuration(
            import_data=export_data,
            imported_by="admin"
        )
        assert imported_id is not None


class TestIntegration:
    """Integration tests for Epic 7 services"""

    @pytest.mark.asyncio
    async def test_end_to_end_monitoring(self):
        """Test end-to-end monitoring flow"""
        monitoring = ProcessMonitoringService()
        failure_mgmt = FailureManagementService()

        await monitoring.initialize()
        await failure_mgmt.initialize()

        # Create alert
        alert_id = await monitoring.create_alert(
            severity=AlertSeverity.ERROR,
            category="PROCESS",
            message="Process failure",
            source="test"
        )

        # Handle failure
        error = RuntimeError("Process failed")
        failure_result = await failure_mgmt.handle_failure(
            request_id="test_request",
            error=error,
            stage="processing",
            context={"alert_id": alert_id}
        )

        assert failure_result['failure_id'] is not None

    @pytest.mark.asyncio
    async def test_configuration_with_approval(self):
        """Test configuration with full approval flow"""
        admin = AdminDashboardService()
        scoring = ScoringConfigurationService()

        await admin.initialize()
        await scoring.initialize()

        # Create configuration
        config_id = await scoring.create_configuration(
            component=ScoringComponent.CHEMICAL_ANALYSIS,
            name="Production Config",
            weights={"mw": 0.25, "logp": 0.25, "hbd": 0.25, "hba": 0.25},
            rules=[],
            thresholds={"overall": {"pass": 0.75, "fail": 0.25}},
            created_by="developer"
        )

        # Create approval workflow
        workflow_id = await admin.create_approval_workflow(
            request_type="scoring_configuration",
            requested_by="developer",
            changes={"config_id": config_id}
        )

        # Process approval
        approval_result = await admin.process_approval(
            workflow_id=workflow_id,
            approver="admin",
            decision="approved",
            comments="ready for production"
        )

        assert approval_result['status'] == "approved"