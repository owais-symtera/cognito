"""
Comprehensive tests for Epic 6: Integration & Webhook Services
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import aiohttp

from src.core.integration.webhook_delivery import (
    WebhookDeliveryService,
    WebhookEndpoint,
    WebhookPayload,
    WebhookType,
    DeliveryStatus,
    ExponentialBackoffStrategy
)
from src.core.integration.enterprise_integration import (
    EnterpriseIntegrationFramework,
    IntegrationConfig,
    IntegrationType,
    AuthenticationType,
    DataFormat,
    ConnectionStatus,
    SalesforceConnector,
    VeevaConnector,
    SAPConnector,
    OracleConnector,
    DataTransformer,
    TransformationRule,
    RateLimiter
)


class TestWebhookDeliveryService:
    """Test Story 6.1: Reliable Webhook Delivery Service"""

    @pytest.fixture
    async def webhook_service(self):
        db_client = Mock()
        db_client.execute_many = AsyncMock()
        db_client.fetch_all = AsyncMock(return_value=[])
        db_client.fetch_one = AsyncMock(return_value=None)
        db_client.execute = AsyncMock()

        source_tracker = Mock()
        service = WebhookDeliveryService(db_client, source_tracker)
        await service.initialize()
        return service

    @pytest.mark.asyncio
    async def test_webhook_endpoint_registration(self, webhook_service):
        """Test webhook endpoint registration"""
        endpoint = WebhookEndpoint(
            id="test_endpoint",
            url="https://api.example.com/webhook",
            method="POST",
            headers={"X-API-Key": "test_key"},
            authentication={"type": "bearer", "token": "test_token"},
            encryption_enabled=True,
            timeout_seconds=30
        )

        webhook_service.db_client.fetch_one = AsyncMock(
            return_value={'id': 'test_endpoint'}
        )

        endpoint_id = await webhook_service.register_endpoint(endpoint)

        assert endpoint_id == "test_endpoint"
        assert webhook_service.db_client.execute.called

    @pytest.mark.asyncio
    async def test_webhook_scheduling(self, webhook_service):
        """Test webhook scheduling"""
        webhook_service.db_client.fetch_one = AsyncMock(
            return_value={
                'id': 'test_endpoint',
                'url': 'https://api.example.com/webhook',
                'encryption_enabled': True,
                'headers': '{}',
                'authentication': '{}'
            }
        )

        webhook_id = await webhook_service.schedule_webhook(
            request_id="req_123",
            process_id="proc_456",
            endpoint_id="test_endpoint",
            webhook_type=WebhookType.RESULT_READY,
            data={"result": "success"},
            metadata={"timestamp": "2024-01-01"}
        )

        assert webhook_id.startswith("req_123_proc_456_")
        assert webhook_service.db_client.execute.called

    @pytest.mark.asyncio
    async def test_exponential_backoff_strategy(self):
        """Test exponential backoff retry strategy"""
        strategy = ExponentialBackoffStrategy(
            initial_delay=1.0,
            max_delay=10.0,
            multiplier=2.0,
            max_retries=5
        )

        # Test delay calculation
        assert strategy.get_delay(0) == 1.0
        assert strategy.get_delay(1) == 2.0
        assert strategy.get_delay(2) == 4.0
        assert strategy.get_delay(3) == 8.0
        assert strategy.get_delay(4) == 10.0  # Max delay
        assert strategy.get_delay(5) is None  # No more retries

        # Test retry decision
        assert strategy.should_retry(0, 500) is True  # Server error
        assert strategy.should_retry(0, 429) is True  # Rate limit
        assert strategy.should_retry(0, 200) is False  # Success
        assert strategy.should_retry(5, 500) is False  # Max retries

    @pytest.mark.asyncio
    async def test_webhook_delivery_success(self, webhook_service):
        """Test successful webhook delivery"""
        webhook_service.db_client.fetch_one = AsyncMock(side_effect=[
            # Get webhook
            {
                'webhook_id': 'test_webhook',
                'endpoint_id': 'test_endpoint',
                'request_id': 'req_123',
                'process_id': 'proc_456',
                'payload': {'data': 'test'},
                'encrypted_payload': None
            },
            # Get endpoint
            {
                'id': 'test_endpoint',
                'url': 'https://api.example.com/webhook',
                'method': 'POST',
                'headers': '{}',
                'authentication': '{}',
                'timeout_seconds': 30,
                'active': True
            }
        ])

        # Mock successful HTTP response
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"success": true}')
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()

            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            mock_session_class.return_value = mock_session

            success = await webhook_service.deliver_webhook('test_webhook')

            assert success is True
            assert webhook_service.db_client.execute.called

    @pytest.mark.asyncio
    async def test_webhook_delivery_retry(self, webhook_service):
        """Test webhook delivery with retry"""
        webhook_service.db_client.fetch_one = AsyncMock(side_effect=[
            # Get webhook
            {
                'webhook_id': 'test_webhook',
                'endpoint_id': 'test_endpoint',
                'request_id': 'req_123',
                'process_id': 'proc_456',
                'payload': {'data': 'test'},
                'encrypted_payload': None
            },
            # Get endpoint
            {
                'id': 'test_endpoint',
                'url': 'https://api.example.com/webhook',
                'method': 'POST',
                'headers': '{}',
                'authentication': '{}',
                'timeout_seconds': 30,
                'active': True
            }
        ])

        # Mock failed then successful response
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()

            # First attempt fails
            mock_response_fail = MagicMock()
            mock_response_fail.status = 500
            mock_response_fail.text = AsyncMock(return_value='Server error')

            # Second attempt succeeds
            mock_response_success = MagicMock()
            mock_response_success.status = 200
            mock_response_success.text = AsyncMock(return_value='{"success": true}')

            responses = [mock_response_fail, mock_response_success]
            response_iter = iter(responses)

            def get_next_response(*args, **kwargs):
                response = next(response_iter)
                response.__aenter__ = AsyncMock(return_value=response)
                response.__aexit__ = AsyncMock()
                return response

            mock_session.request = MagicMock(side_effect=get_next_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            mock_session_class.return_value = mock_session

            # Set a very short retry delay for testing
            webhook_service.retry_strategy.initial_delay = 0.01

            success = await webhook_service.deliver_webhook('test_webhook')

            assert success is True
            assert mock_session.request.call_count == 2

    @pytest.mark.asyncio
    async def test_dead_letter_queue(self, webhook_service):
        """Test dead letter queue handling"""
        webhook_service.db_client.fetch_one = AsyncMock(side_effect=[
            # Get webhook
            {
                'webhook_id': 'test_webhook',
                'endpoint_id': 'test_endpoint',
                'request_id': 'req_123',
                'process_id': 'proc_456',
                'payload': {'data': 'test'},
                'encrypted_payload': None
            },
            # Get endpoint
            {
                'id': 'test_endpoint',
                'url': 'https://api.example.com/webhook',
                'method': 'POST',
                'headers': '{}',
                'authentication': '{}',
                'timeout_seconds': 30,
                'active': True
            },
            # Get attempt count
            {'count': 10}
        ])

        # Mock all attempts failing
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value='Server error')
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()

            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            mock_session_class.return_value = mock_session

            # Set max retries to 2 for testing
            webhook_service.retry_strategy.max_retries = 2
            webhook_service.retry_strategy.initial_delay = 0.01

            success = await webhook_service.deliver_webhook('test_webhook')

            assert success is False
            # Should have attempted twice (initial + 1 retry)
            assert mock_session.request.call_count == 2

        # Check that dead letter queue was used
        assert not webhook_service.dead_letter_queue.empty()

    @pytest.mark.asyncio
    async def test_payload_encryption(self, webhook_service):
        """Test webhook payload encryption"""
        payload = WebhookPayload(
            webhook_id="test_webhook",
            request_id="req_123",
            process_id="proc_456",
            webhook_type=WebhookType.RESULT_READY,
            timestamp=datetime.utcnow(),
            data={"sensitive": "data"},
            metadata={}
        )

        encrypted = await webhook_service._encrypt_payload(payload)
        assert encrypted is not None
        assert isinstance(encrypted, str)

        # Should be able to decrypt
        decrypted_bytes = webhook_service.fernet.decrypt(encrypted.encode())
        decrypted_json = json.loads(decrypted_bytes.decode())
        assert decrypted_json['data']['sensitive'] == 'data'

    @pytest.mark.asyncio
    async def test_payload_signature(self, webhook_service):
        """Test webhook payload signature generation"""
        payload = WebhookPayload(
            webhook_id="test_webhook",
            request_id="req_123",
            process_id="proc_456",
            webhook_type=WebhookType.RESULT_READY,
            timestamp=datetime.utcnow(),
            data={"data": "test"},
            metadata={}
        )

        signature = await webhook_service._sign_payload(payload)
        assert signature is not None
        assert len(signature) == 64  # SHA256 hex digest

    @pytest.mark.asyncio
    async def test_endpoint_health_check(self, webhook_service):
        """Test endpoint health checking"""
        webhook_service.db_client.fetch_one = AsyncMock(
            return_value={
                'id': 'test_endpoint',
                'url': 'https://api.example.com/webhook',
                'health_check_url': 'https://api.example.com/health'
            }
        )

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()

            mock_session.get = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            mock_session_class.return_value = mock_session

            is_healthy, message = await webhook_service.validate_endpoint('test_endpoint')

            assert is_healthy is True
            assert "healthy" in message.lower()

    @pytest.mark.asyncio
    async def test_performance_metrics(self, webhook_service):
        """Test performance metrics tracking"""
        webhook_service.db_client.fetch_one = AsyncMock(
            return_value={
                'days': 7,
                'total_deliveries': 1000,
                'successful_deliveries': 950,
                'failed_deliveries': 50,
                'avg_delivery_time_ms': 250.5,
                'avg_attempts_per_delivery': 1.2,
                'avg_sla_met_percentage': 95.0
            }
        )

        metrics = await webhook_service.get_performance_metrics(
            endpoint_id="test_endpoint",
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow()
        )

        assert metrics['total_deliveries'] == 1000
        assert metrics['success_rate'] == 95.0
        assert metrics['avg_delivery_time_ms'] == 250.5


class TestEnterpriseIntegration:
    """Test Story 6.2: Enterprise System Integration Framework"""

    @pytest.fixture
    async def integration_framework(self):
        db_client = Mock()
        db_client.execute_many = AsyncMock()
        db_client.fetch_all = AsyncMock(return_value=[])
        db_client.fetch_one = AsyncMock(return_value=None)
        db_client.execute = AsyncMock()

        source_tracker = Mock()
        webhook_service = Mock()
        webhook_service.schedule_webhook = AsyncMock()

        framework = EnterpriseIntegrationFramework(
            db_client, source_tracker, webhook_service
        )
        await framework.initialize()
        return framework

    @pytest.mark.asyncio
    async def test_integration_registration(self, integration_framework):
        """Test enterprise integration registration"""
        config = IntegrationConfig(
            integration_id="salesforce_prod",
            integration_type=IntegrationType.SALESFORCE,
            name="Salesforce Production",
            endpoint="https://login.salesforce.com",
            authentication={
                "client_id": "test_client",
                "client_secret": "test_secret",
                "username": "user@example.com",
                "password": "password"
            },
            data_format=DataFormat.JSON,
            timeout_seconds=30
        )

        integration_framework.db_client.fetch_one = AsyncMock(
            return_value={'integration_id': 'salesforce_prod'}
        )

        integration_id = await integration_framework.register_integration(config)

        assert integration_id == "salesforce_prod"
        assert integration_framework.db_client.execute.called

    @pytest.mark.asyncio
    async def test_salesforce_connector(self):
        """Test Salesforce connector"""
        config = IntegrationConfig(
            integration_id="sf_test",
            integration_type=IntegrationType.SALESFORCE,
            name="Salesforce Test",
            endpoint="https://test.salesforce.com",
            authentication={
                "client_id": "test_client",
                "client_secret": "test_secret",
                "username": "user@example.com",
                "password": "password",
                "security_token": "token"
            },
            data_format=DataFormat.JSON
        )

        connector = SalesforceConnector(config)

        # Mock authentication
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                'access_token': 'test_token',
                'instance_url': 'https://instance.salesforce.com',
                'expires_in': 7200
            })
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()

            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            mock_session_class.return_value = mock_session
            connector.session = mock_session

            success = await connector.authenticate()

            assert success is True
            assert connector.auth_token == 'test_token'
            assert connector.instance_url == 'https://instance.salesforce.com'

    @pytest.mark.asyncio
    async def test_veeva_connector(self):
        """Test Veeva CRM connector"""
        config = IntegrationConfig(
            integration_id="veeva_test",
            integration_type=IntegrationType.VEEVA_CRM,
            name="Veeva CRM Test",
            endpoint="https://api.veeva.com",
            authentication={
                "client_id": "test_client",
                "client_secret": "test_secret"
            },
            data_format=DataFormat.JSON
        )

        connector = VeevaConnector(config)

        # Test data preparation
        veeva_data = connector._prepare_veeva_data({
            'name': 'Test Account',
            'type': 'Hospital',
            'status': 'Active'
        })

        assert 'name__v' in veeva_data
        assert 'type__v' in veeva_data
        assert 'status__v' in veeva_data

    @pytest.mark.asyncio
    async def test_sap_connector(self):
        """Test SAP connector"""
        config = IntegrationConfig(
            integration_id="sap_test",
            integration_type=IntegrationType.SAP,
            name="SAP Test",
            endpoint="https://api.sap.com",
            authentication={
                "type": "basic",
                "username": "user",
                "password": "password"
            },
            data_format=DataFormat.JSON
        )

        connector = SAPConnector(config)
        connector.session = MagicMock()

        success = await connector.authenticate()

        assert success is True
        assert connector.auth_token.startswith("Basic ")

        # Test data preparation
        sap_data = connector._prepare_sap_data({
            'business_partner_id': '123',
            'company_name': 'Test Company'
        })

        assert 'BusinessPartnerId' in sap_data
        assert 'CompanyName' in sap_data

    @pytest.mark.asyncio
    async def test_oracle_connector(self):
        """Test Oracle connector"""
        config = IntegrationConfig(
            integration_id="oracle_test",
            integration_type=IntegrationType.ORACLE,
            name="Oracle Test",
            endpoint="https://api.oracle.com",
            authentication={
                "client_id": "test_client",
                "client_secret": "test_secret"
            },
            data_format=DataFormat.JSON
        )

        connector = OracleConnector(config)

        # Mock authentication
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                'access_token': 'oracle_token',
                'expires_in': 3600
            })
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()

            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            mock_session_class.return_value = mock_session
            connector.session = mock_session

            success = await connector.authenticate()

            assert success is True
            assert connector.auth_token == 'oracle_token'

    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        """Test rate limiting"""
        rate_limiter = RateLimiter(calls_per_second=10)

        start_time = time.time()

        # Make 5 rapid calls
        for _ in range(5):
            await rate_limiter.acquire()

        elapsed = time.time() - start_time

        # Should take at least 0.4 seconds (5 calls at 10/sec = 0.5 sec)
        assert elapsed >= 0.4

    def test_data_transformer_json_to_xml(self):
        """Test JSON to XML transformation"""
        json_data = {
            'patient': {
                'name': 'John Doe',
                'age': 30,
                'diagnosis': 'Test'
            }
        }

        xml_result = DataTransformer.transform(
            json_data,
            DataFormat.JSON,
            DataFormat.XML
        )

        assert '<patient>' in xml_result
        assert '<name>John Doe</name>' in xml_result
        assert '<age>30</age>' in xml_result

    def test_data_transformer_xml_to_json(self):
        """Test XML to JSON transformation"""
        xml_data = """
        <patient>
            <name>John Doe</name>
            <age>30</age>
            <diagnosis>Test</diagnosis>
        </patient>
        """

        json_result = DataTransformer.transform(
            xml_data,
            DataFormat.XML,
            DataFormat.JSON
        )

        assert json_result['name'] == 'John Doe'
        assert json_result['age'] == '30'
        assert json_result['diagnosis'] == 'Test'

    def test_data_transformer_csv_to_json(self):
        """Test CSV to JSON transformation"""
        csv_data = "name,age,diagnosis\nJohn Doe,30,Test\nJane Doe,25,Test2"

        json_result = DataTransformer.transform(
            csv_data,
            DataFormat.CSV,
            DataFormat.JSON
        )

        assert len(json_result) == 2
        assert json_result[0]['name'] == 'John Doe'
        assert json_result[1]['name'] == 'Jane Doe'

    def test_transformation_rules(self):
        """Test transformation rules application"""
        data = {
            'first_name': 'john',
            'last_name': 'doe',
            'birth_date': '2000-01-01',
            'score': 10
        }

        rules = [
            TransformationRule(
                source_field='first_name',
                target_field='firstName',
                transformation='uppercase'
            ),
            TransformationRule(
                source_field='last_name',
                target_field='lastName',
                transformation='uppercase'
            ),
            TransformationRule(
                source_field='score',
                target_field='weighted_score',
                transformation='multiply',
                parameters={'factor': 2.5}
            )
        ]

        result = DataTransformer._apply_rules(data, rules)

        assert result['firstName'] == 'JOHN'
        assert result['lastName'] == 'DOE'
        assert result['weighted_score'] == 25.0
        assert 'first_name' not in result
        assert 'last_name' not in result

    @pytest.mark.asyncio
    async def test_integration_health_monitoring(self, integration_framework):
        """Test integration health monitoring"""
        # Add a mock connector
        mock_config = IntegrationConfig(
            integration_id="test_integration",
            integration_type=IntegrationType.SALESFORCE,
            name="Test Integration",
            endpoint="https://test.com",
            authentication={},
            data_format=DataFormat.JSON
        )

        mock_connector = Mock()
        mock_connector.health_check = AsyncMock(return_value=(True, "Healthy"))
        integration_framework.connectors['test_integration'] = mock_connector

        integration_framework.db_client.fetch_one = AsyncMock(
            return_value={
                'successful_requests': 100,
                'failed_requests': 5
            }
        )

        health = await integration_framework.check_health('test_integration')

        assert health.integration_id == 'test_integration'
        assert health.status == ConnectionStatus.CONNECTED
        assert health.error_message is None

    @pytest.mark.asyncio
    async def test_send_data_with_transformation(self, integration_framework):
        """Test sending data with transformation"""
        # Setup mock connector
        mock_connector = Mock()
        mock_connector.config = IntegrationConfig(
            integration_id="test",
            integration_type=IntegrationType.SALESFORCE,
            name="Test",
            endpoint="https://test.com",
            authentication={},
            data_format=DataFormat.JSON,
            transform_config={
                'source_format': 'json',
                'target_format': 'json',
                'rules': [
                    {
                        'source_field': 'customer_name',
                        'target_field': 'Name',
                        'transformation': 'uppercase'
                    }
                ]
            }
        )
        mock_connector.send_data = AsyncMock(return_value={'success': True, 'id': '123'})

        integration_framework.connectors['test'] = mock_connector

        result = await integration_framework.send_data(
            integration_id='test',
            request_id='req_123',
            process_id='proc_456',
            data={'customer_name': 'john doe'}
        )

        assert result['success'] is True
        assert result['id'] == '123'

    @pytest.mark.asyncio
    async def test_receive_data_with_transformation(self, integration_framework):
        """Test receiving data with transformation"""
        # Setup mock connector
        mock_connector = Mock()
        mock_connector.config = IntegrationConfig(
            integration_id="test",
            integration_type=IntegrationType.SALESFORCE,
            name="Test",
            endpoint="https://test.com",
            authentication={},
            data_format=DataFormat.JSON,
            transform_config={
                'source_format': 'json',
                'target_format': 'json',
                'rules': []
            }
        )
        mock_connector.receive_data = AsyncMock(return_value=[
            {'Id': '1', 'Name': 'Test 1'},
            {'Id': '2', 'Name': 'Test 2'}
        ])

        integration_framework.connectors['test'] = mock_connector

        data = await integration_framework.receive_data(
            integration_id='test',
            request_id='req_123',
            process_id='proc_456',
            query={'object_type': 'Account'}
        )

        assert len(data) == 2
        assert data[0]['Id'] == '1'


class TestIntegration:
    """Integration tests for Epic 6"""

    @pytest.mark.asyncio
    async def test_full_webhook_workflow(self):
        """Test complete webhook delivery workflow"""
        # Initialize services
        db_client = Mock()
        db_client.execute_many = AsyncMock()
        db_client.fetch_all = AsyncMock(return_value=[])
        db_client.fetch_one = AsyncMock(return_value=None)
        db_client.execute = AsyncMock()
        source_tracker = Mock()

        webhook_service = WebhookDeliveryService(db_client, source_tracker)
        await webhook_service.initialize()

        # Register endpoint
        endpoint = WebhookEndpoint(
            id="test_endpoint",
            url="https://api.example.com/webhook",
            encryption_enabled=True
        )

        db_client.fetch_one = AsyncMock(return_value={'id': 'test_endpoint'})
        await webhook_service.register_endpoint(endpoint)

        # Schedule webhook
        db_client.fetch_one = AsyncMock(return_value={
            'id': 'test_endpoint',
            'url': 'https://api.example.com/webhook',
            'encryption_enabled': True,
            'headers': '{}',
            'authentication': '{}',
            'active': True
        })

        webhook_id = await webhook_service.schedule_webhook(
            request_id="req_123",
            process_id="proc_456",
            endpoint_id="test_endpoint",
            webhook_type=WebhookType.COMPLETION,
            data={"status": "completed", "results": {"score": 95}}
        )

        assert webhook_id is not None

        # Get delivery status
        db_client.fetch_one = AsyncMock(return_value={
            'webhook_id': webhook_id,
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'delivered_at': None
        })

        db_client.fetch_all = AsyncMock(return_value=[])

        status = await webhook_service.get_delivery_status(webhook_id)

        assert status['webhook_id'] == webhook_id
        assert status['status'] == 'pending'

    @pytest.mark.asyncio
    async def test_enterprise_integration_workflow(self):
        """Test complete enterprise integration workflow"""
        # Initialize services
        db_client = Mock()
        db_client.execute_many = AsyncMock()
        db_client.fetch_all = AsyncMock(return_value=[])
        db_client.fetch_one = AsyncMock(return_value=None)
        db_client.execute = AsyncMock()

        source_tracker = Mock()
        webhook_service = Mock()
        webhook_service.schedule_webhook = AsyncMock()

        framework = EnterpriseIntegrationFramework(
            db_client, source_tracker, webhook_service
        )
        await framework.initialize()

        # Register Salesforce integration
        config = IntegrationConfig(
            integration_id="sf_test",
            integration_type=IntegrationType.SALESFORCE,
            name="Salesforce Test",
            endpoint="https://test.salesforce.com",
            authentication={
                "client_id": "test",
                "client_secret": "secret",
                "username": "user",
                "password": "pass"
            },
            data_format=DataFormat.JSON,
            rate_limit={"calls_per_second": 5}
        )

        db_client.fetch_one = AsyncMock(return_value={'integration_id': 'sf_test'})

        integration_id = await framework.register_integration(config)

        assert integration_id == "sf_test"

        # Rate limiter should be configured
        if 'sf_test' in framework.rate_limiters:
            assert framework.rate_limiters['sf_test'].calls_per_second == 5

    @pytest.mark.asyncio
    async def test_audit_trail_generation(self):
        """Test audit trail generation for compliance"""
        db_client = Mock()
        db_client.execute_many = AsyncMock()
        db_client.execute = AsyncMock()

        source_tracker = Mock()
        source_tracker.add_source = Mock()

        # Test webhook audit trail
        webhook_service = WebhookDeliveryService(db_client, source_tracker)
        await webhook_service.initialize()

        await webhook_service._add_audit_trail(
            webhook_id="test_webhook",
            request_id="req_123",
            process_id="proc_456",
            action="webhook_delivered",
            details={"status_code": 200, "duration_ms": 250}
        )

        assert db_client.execute.called
        call_args = db_client.execute.call_args[0]
        assert 'webhook_audit_trail' in call_args[0]

        # Test integration audit trail
        webhook_service_mock = Mock()
        integration_framework = EnterpriseIntegrationFramework(
            db_client, source_tracker, webhook_service_mock
        )
        await integration_framework.initialize()

        await integration_framework._add_audit_trail(
            integration_id="sf_test",
            action="data_sent",
            details={"records": 10}
        )

        assert db_client.execute.called
        call_args = db_client.execute.call_args[0]
        assert 'integration_audit_trail' in call_args[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])