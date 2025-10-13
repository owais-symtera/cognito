"""
Story 6.2: Enterprise System Integration Framework
Standardized pharmaceutical enterprise system integration with comprehensive audit compliance
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import aiohttp
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
import pandas as pd

from ...utils.database import DatabaseClient
from ...utils.tracking import SourceTracker
from ...utils.logging import get_logger
from .webhook_delivery import WebhookDeliveryService, WebhookType

logger = get_logger(__name__)


class IntegrationType(Enum):
    SALESFORCE = "salesforce"
    SAP = "sap"
    VEEVA_CRM = "veeva_crm"
    ORACLE = "oracle"
    MICROSOFT_DYNAMICS = "microsoft_dynamics"
    CUSTOM = "custom"


class AuthenticationType(Enum):
    OAUTH2 = "oauth2"
    SAML = "saml"
    API_KEY = "api_key"
    BASIC = "basic"
    JWT = "jwt"
    CERTIFICATE = "certificate"


class DataFormat(Enum):
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    HL7 = "hl7"
    FHIR = "fhir"
    EDI = "edi"


class ConnectionStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMITED = "rate_limited"


@dataclass
class IntegrationConfig:
    """Integration configuration"""
    integration_id: str
    integration_type: IntegrationType
    name: str
    endpoint: str
    authentication: Dict[str, Any]
    data_format: DataFormat
    rate_limit: Optional[Dict[str, Any]] = None
    timeout_seconds: int = 30
    retry_config: Optional[Dict[str, Any]] = None
    transform_config: Optional[Dict[str, Any]] = None
    active: bool = True


@dataclass
class IntegrationHealth:
    """Integration health status"""
    integration_id: str
    status: ConnectionStatus
    last_check: datetime
    response_time_ms: Optional[int]
    error_message: Optional[str]
    successful_requests: int
    failed_requests: int
    uptime_percentage: float


@dataclass
class TransformationRule:
    """Data transformation rule"""
    source_field: str
    target_field: str
    transformation: str  # e.g., "uppercase", "date_format", "custom_function"
    parameters: Optional[Dict[str, Any]] = None


class EnterpriseConnector(ABC):
    """Base class for enterprise system connectors"""

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to enterprise system"""
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with enterprise system"""
        pass

    @abstractmethod
    async def send_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send data to enterprise system"""
        pass

    @abstractmethod
    async def receive_data(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Receive data from enterprise system"""
        pass

    @abstractmethod
    async def health_check(self) -> Tuple[bool, str]:
        """Check connection health"""
        pass

    async def disconnect(self):
        """Disconnect from enterprise system"""
        if self.session:
            await self.session.close()
            self.session = None


class SalesforceConnector(EnterpriseConnector):
    """Salesforce integration connector"""

    async def connect(self) -> bool:
        """Connect to Salesforce"""
        self.session = aiohttp.ClientSession()
        return await self.authenticate()

    async def authenticate(self) -> bool:
        """Authenticate using OAuth2 with Salesforce"""
        try:
            auth_config = self.config.authentication

            # OAuth2 flow for Salesforce
            token_url = urljoin(self.config.endpoint, '/services/oauth2/token')

            data = {
                'grant_type': 'password',
                'client_id': auth_config['client_id'],
                'client_secret': auth_config['client_secret'],
                'username': auth_config['username'],
                'password': auth_config['password'] + auth_config.get('security_token', '')
            }

            async with self.session.post(token_url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.auth_token = result['access_token']
                    self.instance_url = result['instance_url']

                    # Calculate token expiry
                    expires_in = result.get('expires_in', 7200)
                    self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

                    logger.info("Successfully authenticated with Salesforce")
                    return True
                else:
                    error = await response.text()
                    logger.error(f"Salesforce authentication failed: {error}")
                    return False

        except Exception as e:
            logger.error(f"Salesforce authentication error: {e}")
            return False

    async def send_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send data to Salesforce"""
        if not self.auth_token or datetime.utcnow() >= self.token_expiry:
            await self.authenticate()

        try:
            # Determine Salesforce object and action
            object_type = data.get('object_type', 'Lead')
            action = data.get('action', 'create')
            record_data = data.get('data', {})

            headers = {
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }

            if action == 'create':
                url = f"{self.instance_url}/services/data/v55.0/sobjects/{object_type}"
                async with self.session.post(
                    url,
                    json=record_data,
                    headers=headers
                ) as response:
                    result = await response.json()

                    if response.status in [200, 201]:
                        return {
                            'success': True,
                            'id': result.get('id'),
                            'response': result
                        }
                    else:
                        return {
                            'success': False,
                            'error': result
                        }

            elif action == 'update':
                record_id = data.get('record_id')
                url = f"{self.instance_url}/services/data/v55.0/sobjects/{object_type}/{record_id}"

                async with self.session.patch(
                    url,
                    json=record_data,
                    headers=headers
                ) as response:
                    if response.status == 204:
                        return {'success': True}
                    else:
                        return {
                            'success': False,
                            'error': await response.text()
                        }

        except Exception as e:
            logger.error(f"Salesforce send_data error: {e}")
            return {'success': False, 'error': str(e)}

    async def receive_data(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query data from Salesforce"""
        if not self.auth_token or datetime.utcnow() >= self.token_expiry:
            await self.authenticate()

        try:
            # Build SOQL query
            soql = query.get('soql') or self._build_soql_query(query)

            headers = {
                'Authorization': f'Bearer {self.auth_token}'
            }

            url = f"{self.instance_url}/services/data/v55.0/query"
            params = {'q': soql}

            async with self.session.get(
                url,
                params=params,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('records', [])
                else:
                    error = await response.text()
                    logger.error(f"Salesforce query error: {error}")
                    return []

        except Exception as e:
            logger.error(f"Salesforce receive_data error: {e}")
            return []

    def _build_soql_query(self, query: Dict[str, Any]) -> str:
        """Build SOQL query from parameters"""
        object_type = query.get('object_type', 'Lead')
        fields = query.get('fields', ['Id', 'Name'])
        conditions = query.get('conditions', {})
        limit = query.get('limit', 100)

        soql = f"SELECT {', '.join(fields)} FROM {object_type}"

        if conditions:
            where_clauses = []
            for field, value in conditions.items():
                if isinstance(value, str):
                    where_clauses.append(f"{field} = '{value}'")
                else:
                    where_clauses.append(f"{field} = {value}")
            soql += f" WHERE {' AND '.join(where_clauses)}"

        soql += f" LIMIT {limit}"

        return soql

    async def health_check(self) -> Tuple[bool, str]:
        """Check Salesforce connection health"""
        try:
            if not self.auth_token or datetime.utcnow() >= self.token_expiry:
                success = await self.authenticate()
                if not success:
                    return False, "Authentication failed"

            # Test with a simple query
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            url = f"{self.instance_url}/services/data/v55.0/limits"

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return True, "Salesforce connection healthy"
                else:
                    return False, f"Health check failed: HTTP {response.status}"

        except Exception as e:
            return False, f"Health check error: {e}"


class VeevaConnector(EnterpriseConnector):
    """Veeva CRM integration connector"""

    async def connect(self) -> bool:
        """Connect to Veeva CRM"""
        self.session = aiohttp.ClientSession()
        return await self.authenticate()

    async def authenticate(self) -> bool:
        """Authenticate with Veeva CRM"""
        try:
            auth_config = self.config.authentication

            # Veeva uses similar auth to Salesforce
            auth_url = f"{self.config.endpoint}/auth/oauth2/token"

            data = {
                'grant_type': 'client_credentials',
                'client_id': auth_config['client_id'],
                'client_secret': auth_config['client_secret'],
                'scope': auth_config.get('scope', 'api')
            }

            async with self.session.post(auth_url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.auth_token = result['access_token']
                    expires_in = result.get('expires_in', 3600)
                    self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

                    logger.info("Successfully authenticated with Veeva CRM")
                    return True
                else:
                    logger.error(f"Veeva authentication failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Veeva authentication error: {e}")
            return False

    async def send_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send data to Veeva CRM"""
        if not self.auth_token or datetime.utcnow() >= self.token_expiry:
            await self.authenticate()

        try:
            # Veeva-specific data handling
            object_type = data.get('object_type', 'Account')
            record_data = self._prepare_veeva_data(data.get('data', {}))

            headers = {
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }

            url = f"{self.config.endpoint}/api/v21.0/vobjects/{object_type}"

            async with self.session.post(
                url,
                json=record_data,
                headers=headers
            ) as response:
                result = await response.json()

                if response.status in [200, 201]:
                    return {
                        'success': True,
                        'id': result.get('data', {}).get('id'),
                        'response': result
                    }
                else:
                    return {
                        'success': False,
                        'error': result
                    }

        except Exception as e:
            logger.error(f"Veeva send_data error: {e}")
            return {'success': False, 'error': str(e)}

    def _prepare_veeva_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for Veeva CRM format"""
        # Veeva requires specific field naming
        veeva_data = {}

        field_mapping = {
            'name': 'name__v',
            'type': 'type__v',
            'status': 'status__v',
            'account': 'account__v'
        }

        for key, value in data.items():
            veeva_key = field_mapping.get(key, f"{key}__c")
            veeva_data[veeva_key] = value

        return veeva_data

    async def receive_data(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query data from Veeva CRM"""
        if not self.auth_token or datetime.utcnow() >= self.token_expiry:
            await self.authenticate()

        try:
            object_type = query.get('object_type', 'Account')
            vql = query.get('vql') or self._build_vql_query(query)

            headers = {
                'Authorization': f'Bearer {self.auth_token}'
            }

            url = f"{self.config.endpoint}/api/v21.0/query"
            params = {'q': vql}

            async with self.session.get(
                url,
                params=params,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('data', [])
                else:
                    logger.error(f"Veeva query error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Veeva receive_data error: {e}")
            return []

    def _build_vql_query(self, query: Dict[str, Any]) -> str:
        """Build VQL (Veeva Query Language) query"""
        object_type = query.get('object_type', 'Account')
        fields = query.get('fields', ['id', 'name__v'])
        conditions = query.get('conditions', {})
        limit = query.get('limit', 100)

        vql = f"SELECT {', '.join(fields)} FROM {object_type}"

        if conditions:
            where_clauses = []
            for field, value in conditions.items():
                veeva_field = f"{field}__v" if not field.endswith('__v') else field
                if isinstance(value, str):
                    where_clauses.append(f"{veeva_field} = '{value}'")
                else:
                    where_clauses.append(f"{veeva_field} = {value}")
            vql += f" WHERE {' AND '.join(where_clauses)}"

        vql += f" LIMIT {limit}"

        return vql

    async def health_check(self) -> Tuple[bool, str]:
        """Check Veeva CRM connection health"""
        try:
            if not self.auth_token or datetime.utcnow() >= self.token_expiry:
                success = await self.authenticate()
                if not success:
                    return False, "Authentication failed"

            # Test API endpoint
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            url = f"{self.config.endpoint}/api/v21.0/metadata/vobjects"

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return True, "Veeva CRM connection healthy"
                else:
                    return False, f"Health check failed: HTTP {response.status}"

        except Exception as e:
            return False, f"Health check error: {e}"


class SAPConnector(EnterpriseConnector):
    """SAP integration connector"""

    async def connect(self) -> bool:
        """Connect to SAP"""
        self.session = aiohttp.ClientSession()
        return await self.authenticate()

    async def authenticate(self) -> bool:
        """Authenticate with SAP"""
        try:
            auth_config = self.config.authentication
            auth_type = auth_config.get('type', 'basic')

            if auth_type == 'basic':
                # Basic authentication for SAP
                import base64
                username = auth_config['username']
                password = auth_config['password']
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                self.auth_token = f"Basic {credentials}"

            elif auth_type == 'oauth2':
                # OAuth2 for SAP
                token_url = f"{self.config.endpoint}/oauth/token"
                data = {
                    'grant_type': 'client_credentials',
                    'client_id': auth_config['client_id'],
                    'client_secret': auth_config['client_secret']
                }

                async with self.session.post(token_url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.auth_token = f"Bearer {result['access_token']}"
                        expires_in = result.get('expires_in', 3600)
                        self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
                    else:
                        return False

            logger.info("Successfully authenticated with SAP")
            return True

        except Exception as e:
            logger.error(f"SAP authentication error: {e}")
            return False

    async def send_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send data to SAP via OData service"""
        try:
            entity_set = data.get('entity_set', 'BusinessPartners')
            sap_data = self._prepare_sap_data(data.get('data', {}))

            headers = {
                'Authorization': self.auth_token,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            # SAP OData endpoint
            url = f"{self.config.endpoint}/odata/v4/{entity_set}"

            async with self.session.post(
                url,
                json=sap_data,
                headers=headers
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    return {
                        'success': True,
                        'id': result.get('ID'),
                        'response': result
                    }
                else:
                    error = await response.text()
                    return {
                        'success': False,
                        'error': error
                    }

        except Exception as e:
            logger.error(f"SAP send_data error: {e}")
            return {'success': False, 'error': str(e)}

    def _prepare_sap_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for SAP format"""
        # SAP often uses specific naming conventions
        sap_data = {}

        for key, value in data.items():
            # Convert to SAP field naming (PascalCase)
            sap_key = ''.join(word.capitalize() for word in key.split('_'))
            sap_data[sap_key] = value

        return sap_data

    async def receive_data(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query data from SAP OData service"""
        try:
            entity_set = query.get('entity_set', 'BusinessPartners')
            filters = query.get('filters', {})
            select_fields = query.get('select', [])
            top = query.get('top', 100)

            headers = {
                'Authorization': self.auth_token,
                'Accept': 'application/json'
            }

            # Build OData query parameters
            params = {'$top': top}

            if select_fields:
                params['$select'] = ','.join(select_fields)

            if filters:
                filter_clauses = []
                for field, value in filters.items():
                    if isinstance(value, str):
                        filter_clauses.append(f"{field} eq '{value}'")
                    else:
                        filter_clauses.append(f"{field} eq {value}")
                params['$filter'] = ' and '.join(filter_clauses)

            url = f"{self.config.endpoint}/odata/v4/{entity_set}"

            async with self.session.get(
                url,
                params=params,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('value', [])
                else:
                    logger.error(f"SAP query error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"SAP receive_data error: {e}")
            return []

    async def health_check(self) -> Tuple[bool, str]:
        """Check SAP connection health"""
        try:
            headers = {'Authorization': self.auth_token}
            url = f"{self.config.endpoint}/odata/v4/$metadata"

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return True, "SAP connection healthy"
                else:
                    return False, f"Health check failed: HTTP {response.status}"

        except Exception as e:
            return False, f"Health check error: {e}"


class OracleConnector(EnterpriseConnector):
    """Oracle integration connector"""

    async def connect(self) -> bool:
        """Connect to Oracle"""
        self.session = aiohttp.ClientSession()
        return await self.authenticate()

    async def authenticate(self) -> bool:
        """Authenticate with Oracle"""
        try:
            auth_config = self.config.authentication

            # Oracle REST API authentication
            auth_url = f"{self.config.endpoint}/auth/token"

            data = {
                'grant_type': 'client_credentials',
                'client_id': auth_config['client_id'],
                'client_secret': auth_config['client_secret']
            }

            async with self.session.post(auth_url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.auth_token = result['access_token']
                    expires_in = result.get('expires_in', 3600)
                    self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

                    logger.info("Successfully authenticated with Oracle")
                    return True
                else:
                    logger.error(f"Oracle authentication failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Oracle authentication error: {e}")
            return False

    async def send_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send data to Oracle"""
        if not self.auth_token or datetime.utcnow() >= self.token_expiry:
            await self.authenticate()

        try:
            resource = data.get('resource', 'items')
            oracle_data = data.get('data', {})

            headers = {
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }

            url = f"{self.config.endpoint}/api/{resource}"

            async with self.session.post(
                url,
                json=oracle_data,
                headers=headers
            ) as response:
                result = await response.json()

                if response.status in [200, 201]:
                    return {
                        'success': True,
                        'id': result.get('id'),
                        'response': result
                    }
                else:
                    return {
                        'success': False,
                        'error': result
                    }

        except Exception as e:
            logger.error(f"Oracle send_data error: {e}")
            return {'success': False, 'error': str(e)}

    async def receive_data(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query data from Oracle"""
        if not self.auth_token or datetime.utcnow() >= self.token_expiry:
            await self.authenticate()

        try:
            resource = query.get('resource', 'items')
            params = query.get('params', {})

            headers = {
                'Authorization': f'Bearer {self.auth_token}',
                'Accept': 'application/json'
            }

            url = f"{self.config.endpoint}/api/{resource}"

            async with self.session.get(
                url,
                params=params,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('items', result if isinstance(result, list) else [])
                else:
                    logger.error(f"Oracle query error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Oracle receive_data error: {e}")
            return []

    async def health_check(self) -> Tuple[bool, str]:
        """Check Oracle connection health"""
        try:
            if not self.auth_token or datetime.utcnow() >= self.token_expiry:
                success = await self.authenticate()
                if not success:
                    return False, "Authentication failed"

            headers = {'Authorization': f'Bearer {self.auth_token}'}
            url = f"{self.config.endpoint}/api/health"

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return True, "Oracle connection healthy"
                else:
                    return False, f"Health check failed: HTTP {response.status}"

        except Exception as e:
            return False, f"Health check error: {e}"


class RateLimiter:
    """Rate limiting for API calls"""

    def __init__(self, calls_per_second: float = 10):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Acquire rate limit slot"""
        async with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_call_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                await asyncio.sleep(sleep_time)

            self.last_call_time = time.time()


class DataTransformer:
    """Data transformation between formats"""

    @staticmethod
    def transform(data: Any,
                  source_format: DataFormat,
                  target_format: DataFormat,
                  rules: Optional[List[TransformationRule]] = None) -> Any:
        """Transform data between formats"""
        # First convert to common format (dict)
        common_data = DataTransformer._to_common_format(data, source_format)

        # Apply transformation rules
        if rules:
            common_data = DataTransformer._apply_rules(common_data, rules)

        # Convert to target format
        return DataTransformer._from_common_format(common_data, target_format)

    @staticmethod
    def _to_common_format(data: Any, format: DataFormat) -> Dict[str, Any]:
        """Convert from specific format to common dict"""
        if format == DataFormat.JSON:
            return data if isinstance(data, dict) else json.loads(data)

        elif format == DataFormat.XML:
            if isinstance(data, str):
                root = ET.fromstring(data)
            else:
                root = data
            return DataTransformer._xml_to_dict(root)

        elif format == DataFormat.CSV:
            if isinstance(data, str):
                import io
                df = pd.read_csv(io.StringIO(data))
            else:
                df = data
            return df.to_dict('records')

        elif format == DataFormat.HL7:
            # Simplified HL7 parsing
            return DataTransformer._parse_hl7(data)

        elif format == DataFormat.FHIR:
            # FHIR is JSON-based
            return data if isinstance(data, dict) else json.loads(data)

        else:
            return data

    @staticmethod
    def _from_common_format(data: Dict[str, Any], format: DataFormat) -> Any:
        """Convert from common dict to specific format"""
        if format == DataFormat.JSON:
            return data

        elif format == DataFormat.XML:
            root = ET.Element('root')
            DataTransformer._dict_to_xml(data, root)
            return ET.tostring(root, encoding='unicode')

        elif format == DataFormat.CSV:
            df = pd.DataFrame(data if isinstance(data, list) else [data])
            return df.to_csv(index=False)

        elif format == DataFormat.HL7:
            return DataTransformer._generate_hl7(data)

        elif format == DataFormat.FHIR:
            # Add FHIR resource wrapper
            return {
                'resourceType': data.get('resourceType', 'Bundle'),
                'entry': data if isinstance(data, list) else [data]
            }

        else:
            return data

    @staticmethod
    def _xml_to_dict(element):
        """Convert XML element to dictionary"""
        result = {}

        for child in element:
            if len(child) == 0:
                result[child.tag] = child.text
            else:
                result[child.tag] = DataTransformer._xml_to_dict(child)

        return result

    @staticmethod
    def _dict_to_xml(data, parent):
        """Convert dictionary to XML elements"""
        if isinstance(data, dict):
            for key, value in data.items():
                child = ET.SubElement(parent, key)
                if isinstance(value, dict):
                    DataTransformer._dict_to_xml(value, child)
                else:
                    child.text = str(value)
        else:
            parent.text = str(data)

    @staticmethod
    def _parse_hl7(message: str) -> Dict[str, Any]:
        """Parse HL7 message to dict"""
        lines = message.strip().split('\n')
        result = {'segments': []}

        for line in lines:
            fields = line.split('|')
            segment_type = fields[0] if fields else ''
            result['segments'].append({
                'type': segment_type,
                'fields': fields
            })

        return result

    @staticmethod
    def _generate_hl7(data: Dict[str, Any]) -> str:
        """Generate HL7 message from dict"""
        segments = []

        # Generate MSH header
        msh = f"MSH|^~\\&|{data.get('sending_app', 'COGNITOAI')}|"
        msh += f"{data.get('sending_facility', 'PHARMA')}|"
        msh += f"{data.get('receiving_app', '')}|"
        msh += f"{data.get('receiving_facility', '')}|"
        msh += f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}||"
        msh += f"{data.get('message_type', 'ORU^R01')}|"
        msh += f"{data.get('message_id', '')}|P|2.5"

        segments.append(msh)

        # Add other segments from data
        if 'segments' in data:
            for segment in data['segments']:
                segments.append('|'.join(segment.get('fields', [])))

        return '\n'.join(segments)

    @staticmethod
    def _apply_rules(data: Dict[str, Any],
                     rules: List[TransformationRule]) -> Dict[str, Any]:
        """Apply transformation rules to data"""
        result = data.copy()

        for rule in rules:
            source_value = result.get(rule.source_field)

            if source_value is not None:
                # Apply transformation
                if rule.transformation == 'uppercase':
                    transformed = str(source_value).upper()
                elif rule.transformation == 'lowercase':
                    transformed = str(source_value).lower()
                elif rule.transformation == 'date_format':
                    # Parse and format date
                    from dateutil import parser
                    dt = parser.parse(str(source_value))
                    format_str = rule.parameters.get('format', '%Y-%m-%d')
                    transformed = dt.strftime(format_str)
                elif rule.transformation == 'multiply':
                    factor = rule.parameters.get('factor', 1)
                    transformed = float(source_value) * factor
                elif rule.transformation == 'concatenate':
                    fields = rule.parameters.get('fields', [])
                    values = [str(result.get(f, '')) for f in fields]
                    separator = rule.parameters.get('separator', ' ')
                    transformed = separator.join(values)
                else:
                    transformed = source_value

                # Set transformed value
                result[rule.target_field] = transformed

                # Remove source field if different from target
                if rule.source_field != rule.target_field:
                    del result[rule.source_field]

        return result


class EnterpriseIntegrationFramework:
    """Main enterprise integration framework"""

    CONNECTOR_CLASSES: Dict[IntegrationType, Type[EnterpriseConnector]] = {
        IntegrationType.SALESFORCE: SalesforceConnector,
        IntegrationType.SAP: SAPConnector,
        IntegrationType.VEEVA_CRM: VeevaConnector,
        IntegrationType.ORACLE: OracleConnector
    }

    def __init__(self,
                 db_client: DatabaseClient,
                 source_tracker: SourceTracker,
                 webhook_service: WebhookDeliveryService):
        self.db_client = db_client
        self.source_tracker = source_tracker
        self.webhook_service = webhook_service
        self.connectors: Dict[str, EnterpriseConnector] = {}
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.transformer = DataTransformer()
        self.monitoring_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize integration framework"""
        await self._ensure_tables_exist()
        await self._load_integrations()
        await self.start_monitoring()
        logger.info("Enterprise integration framework initialized")

    async def _ensure_tables_exist(self):
        """Ensure integration tables exist"""
        await self.db_client.execute_many([
            """
            CREATE TABLE IF NOT EXISTS enterprise_integrations (
                integration_id VARCHAR(100) PRIMARY KEY,
                integration_type VARCHAR(50) NOT NULL,
                name VARCHAR(200) NOT NULL,
                endpoint TEXT NOT NULL,
                authentication JSONB NOT NULL,
                data_format VARCHAR(20) NOT NULL,
                rate_limit JSONB,
                timeout_seconds INTEGER DEFAULT 30,
                retry_config JSONB,
                transform_config JSONB,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS integration_health (
                id SERIAL PRIMARY KEY,
                integration_id VARCHAR(100) REFERENCES enterprise_integrations(integration_id),
                status VARCHAR(50) NOT NULL,
                last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_time_ms INTEGER,
                error_message TEXT,
                successful_requests INTEGER DEFAULT 0,
                failed_requests INTEGER DEFAULT 0,
                uptime_percentage DECIMAL(5,2)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS integration_data_flows (
                id SERIAL PRIMARY KEY,
                flow_id VARCHAR(100) NOT NULL UNIQUE,
                integration_id VARCHAR(100) REFERENCES enterprise_integrations(integration_id),
                request_id VARCHAR(100) NOT NULL,
                process_id VARCHAR(100) NOT NULL,
                direction VARCHAR(20) NOT NULL,
                data_format VARCHAR(20) NOT NULL,
                data_size_bytes INTEGER,
                transformation_applied BOOLEAN DEFAULT FALSE,
                status VARCHAR(50) NOT NULL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS integration_audit_trail (
                id SERIAL PRIMARY KEY,
                integration_id VARCHAR(100),
                request_id VARCHAR(100),
                process_id VARCHAR(100),
                action VARCHAR(100) NOT NULL,
                details JSONB,
                user_id VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS transformation_templates (
                id SERIAL PRIMARY KEY,
                template_id VARCHAR(100) NOT NULL UNIQUE,
                name VARCHAR(200) NOT NULL,
                source_format VARCHAR(20) NOT NULL,
                target_format VARCHAR(20) NOT NULL,
                rules JSONB NOT NULL,
                description TEXT,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_integration_data_flows_request
            ON integration_data_flows(request_id, process_id);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_integration_audit_trail_request
            ON integration_audit_trail(request_id, process_id, created_at DESC);
            """
        ])

    async def _load_integrations(self):
        """Load configured integrations"""
        query = """
            SELECT * FROM enterprise_integrations
            WHERE active = TRUE
        """

        results = await self.db_client.fetch_all(query)

        for row in results:
            config = IntegrationConfig(
                integration_id=row['integration_id'],
                integration_type=IntegrationType(row['integration_type']),
                name=row['name'],
                endpoint=row['endpoint'],
                authentication=json.loads(row['authentication']),
                data_format=DataFormat(row['data_format']),
                rate_limit=json.loads(row['rate_limit']) if row['rate_limit'] else None,
                timeout_seconds=row['timeout_seconds'],
                retry_config=json.loads(row['retry_config']) if row['retry_config'] else None,
                transform_config=json.loads(row['transform_config']) if row['transform_config'] else None,
                active=row['active']
            )

            await self._create_connector(config)

    async def _create_connector(self, config: IntegrationConfig):
        """Create and initialize connector"""
        connector_class = self.CONNECTOR_CLASSES.get(config.integration_type)

        if not connector_class:
            logger.warning(f"No connector class for {config.integration_type}")
            return

        connector = connector_class(config)

        # Try to connect
        try:
            success = await connector.connect()
            if success:
                self.connectors[config.integration_id] = connector

                # Setup rate limiter if configured
                if config.rate_limit:
                    calls_per_second = config.rate_limit.get('calls_per_second', 10)
                    self.rate_limiters[config.integration_id] = RateLimiter(calls_per_second)

                logger.info(f"Successfully connected to {config.name}")
            else:
                logger.error(f"Failed to connect to {config.name}")

        except Exception as e:
            logger.error(f"Error connecting to {config.name}: {e}")

    async def register_integration(self, config: IntegrationConfig) -> str:
        """Register new integration"""
        query = """
            INSERT INTO enterprise_integrations
            (integration_id, integration_type, name, endpoint, authentication,
             data_format, rate_limit, timeout_seconds, retry_config,
             transform_config, active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (integration_id) DO UPDATE SET
                endpoint = EXCLUDED.endpoint,
                authentication = EXCLUDED.authentication,
                updated_at = CURRENT_TIMESTAMP
            RETURNING integration_id
        """

        result = await self.db_client.fetch_one(
            query,
            (
                config.integration_id,
                config.integration_type.value,
                config.name,
                config.endpoint,
                json.dumps(config.authentication),
                config.data_format.value,
                json.dumps(config.rate_limit) if config.rate_limit else None,
                config.timeout_seconds,
                json.dumps(config.retry_config) if config.retry_config else None,
                json.dumps(config.transform_config) if config.transform_config else None,
                config.active
            )
        )

        # Create connector
        await self._create_connector(config)

        # Audit trail
        await self._add_audit_trail(
            integration_id=config.integration_id,
            action="integration_registered",
            details={"name": config.name, "type": config.integration_type.value}
        )

        return result['integration_id']

    async def send_data(self,
                       integration_id: str,
                       request_id: str,
                       process_id: str,
                       data: Dict[str, Any]) -> Dict[str, Any]:
        """Send data to enterprise system"""
        flow_id = f"{request_id}_{process_id}_{int(time.time() * 1000)}"

        connector = self.connectors.get(integration_id)
        if not connector:
            return {'success': False, 'error': 'Integration not found or not connected'}

        try:
            # Apply rate limiting
            if integration_id in self.rate_limiters:
                await self.rate_limiters[integration_id].acquire()

            # Record data flow start
            await self._record_data_flow_start(
                flow_id, integration_id, request_id, process_id, 'outbound'
            )

            # Transform data if needed
            if connector.config.transform_config:
                data = await self._transform_data(
                    data,
                    connector.config.transform_config
                )

            # Send data
            result = await connector.send_data(data)

            # Record completion
            await self._record_data_flow_completion(
                flow_id,
                'completed' if result.get('success') else 'failed',
                error_message=result.get('error')
            )

            # Update health metrics
            await self._update_health_metrics(
                integration_id,
                success=result.get('success', False)
            )

            # Send webhook if configured
            if result.get('success'):
                await self.webhook_service.schedule_webhook(
                    request_id=request_id,
                    process_id=process_id,
                    endpoint_id=f"{integration_id}_webhook",
                    webhook_type=WebhookType.STATUS_UPDATE,
                    data={
                        'integration_id': integration_id,
                        'flow_id': flow_id,
                        'result': result
                    }
                )

            # Audit trail
            await self._add_audit_trail(
                integration_id=integration_id,
                request_id=request_id,
                process_id=process_id,
                action="data_sent",
                details={'flow_id': flow_id, 'success': result.get('success')}
            )

            # Track source
            self.source_tracker.add_source(
                request_id=request_id,
                field_name="integration_send",
                value=flow_id,
                source_system="enterprise_integration",
                source_detail={
                    "integration_id": integration_id,
                    "success": result.get('success')
                }
            )

            return result

        except Exception as e:
            logger.error(f"Error sending data to {integration_id}: {e}")

            await self._record_data_flow_completion(
                flow_id, 'error', str(e)
            )

            return {'success': False, 'error': str(e)}

    async def receive_data(self,
                          integration_id: str,
                          request_id: str,
                          process_id: str,
                          query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Receive data from enterprise system"""
        flow_id = f"{request_id}_{process_id}_{int(time.time() * 1000)}"

        connector = self.connectors.get(integration_id)
        if not connector:
            return []

        try:
            # Apply rate limiting
            if integration_id in self.rate_limiters:
                await self.rate_limiters[integration_id].acquire()

            # Record data flow start
            await self._record_data_flow_start(
                flow_id, integration_id, request_id, process_id, 'inbound'
            )

            # Receive data
            data = await connector.receive_data(query)

            # Transform data if needed
            if connector.config.transform_config and data:
                transformed_data = []
                for item in data:
                    transformed_item = await self._transform_data(
                        item,
                        connector.config.transform_config
                    )
                    transformed_data.append(transformed_item)
                data = transformed_data

            # Record completion
            await self._record_data_flow_completion(
                flow_id, 'completed'
            )

            # Update health metrics
            await self._update_health_metrics(
                integration_id, success=True
            )

            # Audit trail
            await self._add_audit_trail(
                integration_id=integration_id,
                request_id=request_id,
                process_id=process_id,
                action="data_received",
                details={'flow_id': flow_id, 'records': len(data)}
            )

            return data

        except Exception as e:
            logger.error(f"Error receiving data from {integration_id}: {e}")

            await self._record_data_flow_completion(
                flow_id, 'error', str(e)
            )

            return []

    async def _transform_data(self,
                             data: Any,
                             transform_config: Dict[str, Any]) -> Any:
        """Apply data transformation"""
        source_format = DataFormat(transform_config.get('source_format', 'json'))
        target_format = DataFormat(transform_config.get('target_format', 'json'))
        rules = transform_config.get('rules', [])

        # Convert rules to TransformationRule objects
        transformation_rules = []
        for rule in rules:
            transformation_rules.append(TransformationRule(
                source_field=rule['source_field'],
                target_field=rule['target_field'],
                transformation=rule['transformation'],
                parameters=rule.get('parameters')
            ))

        return self.transformer.transform(
            data, source_format, target_format, transformation_rules
        )

    async def check_health(self, integration_id: str) -> IntegrationHealth:
        """Check integration health"""
        connector = self.connectors.get(integration_id)

        if not connector:
            return IntegrationHealth(
                integration_id=integration_id,
                status=ConnectionStatus.DISCONNECTED,
                last_check=datetime.utcnow(),
                response_time_ms=None,
                error_message="Connector not found",
                successful_requests=0,
                failed_requests=0,
                uptime_percentage=0
            )

        start_time = time.time()
        is_healthy, message = await connector.health_check()
        response_time_ms = int((time.time() - start_time) * 1000)

        # Get metrics
        metrics = await self._get_health_metrics(integration_id)

        status = ConnectionStatus.CONNECTED if is_healthy else ConnectionStatus.ERROR

        health = IntegrationHealth(
            integration_id=integration_id,
            status=status,
            last_check=datetime.utcnow(),
            response_time_ms=response_time_ms,
            error_message=None if is_healthy else message,
            successful_requests=metrics.get('successful_requests', 0),
            failed_requests=metrics.get('failed_requests', 0),
            uptime_percentage=metrics.get('uptime_percentage', 0)
        )

        # Record health check
        await self._record_health_check(health)

        return health

    async def start_monitoring(self):
        """Start health monitoring"""
        self.monitoring_task = asyncio.create_task(self._monitor_health())
        logger.info("Started integration health monitoring")

    async def stop_monitoring(self):
        """Stop health monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            await asyncio.gather(self.monitoring_task, return_exceptions=True)
            self.monitoring_task = None
        logger.info("Stopped integration health monitoring")

    async def _monitor_health(self):
        """Monitor integration health periodically"""
        while True:
            try:
                for integration_id in list(self.connectors.keys()):
                    await self.check_health(integration_id)

                # Check every 5 minutes
                await asyncio.sleep(300)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(60)

    # Database helper methods

    async def _record_data_flow_start(self,
                                     flow_id: str,
                                     integration_id: str,
                                     request_id: str,
                                     process_id: str,
                                     direction: str):
        """Record start of data flow"""
        query = """
            INSERT INTO integration_data_flows
            (flow_id, integration_id, request_id, process_id, direction,
             data_format, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        connector = self.connectors.get(integration_id)
        data_format = connector.config.data_format.value if connector else 'json'

        await self.db_client.execute(
            query,
            (
                flow_id,
                integration_id,
                request_id,
                process_id,
                direction,
                data_format,
                'in_progress'
            )
        )

    async def _record_data_flow_completion(self,
                                          flow_id: str,
                                          status: str,
                                          error_message: Optional[str] = None):
        """Record completion of data flow"""
        query = """
            UPDATE integration_data_flows
            SET status = %s,
                error_message = %s,
                completed_at = %s
            WHERE flow_id = %s
        """

        await self.db_client.execute(
            query,
            (status, error_message, datetime.utcnow(), flow_id)
        )

    async def _record_health_check(self, health: IntegrationHealth):
        """Record health check result"""
        query = """
            INSERT INTO integration_health
            (integration_id, status, response_time_ms, error_message,
             successful_requests, failed_requests, uptime_percentage)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (
                health.integration_id,
                health.status.value,
                health.response_time_ms,
                health.error_message,
                health.successful_requests,
                health.failed_requests,
                health.uptime_percentage
            )
        )

    async def _get_health_metrics(self, integration_id: str) -> Dict[str, Any]:
        """Get health metrics for integration"""
        query = """
            SELECT
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_requests,
                COUNT(CASE WHEN status IN ('failed', 'error') THEN 1 END) as failed_requests
            FROM integration_data_flows
            WHERE integration_id = %s
                AND created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
        """

        result = await self.db_client.fetch_one(query, (integration_id,))

        if result:
            total = result['successful_requests'] + result['failed_requests']
            uptime_percentage = (
                (result['successful_requests'] / total * 100)
                if total > 0 else 100
            )

            return {
                'successful_requests': result['successful_requests'],
                'failed_requests': result['failed_requests'],
                'uptime_percentage': uptime_percentage
            }

        return {
            'successful_requests': 0,
            'failed_requests': 0,
            'uptime_percentage': 100
        }

    async def _update_health_metrics(self,
                                    integration_id: str,
                                    success: bool):
        """Update health metrics after operation"""
        # This is handled by the data flow recording
        pass

    async def _add_audit_trail(self,
                              integration_id: str,
                              action: str,
                              details: Dict[str, Any],
                              request_id: str = "",
                              process_id: str = "",
                              user_id: Optional[str] = None):
        """Add audit trail entry"""
        query = """
            INSERT INTO integration_audit_trail
            (integration_id, request_id, process_id, action, details, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (
                integration_id,
                request_id,
                process_id,
                action,
                json.dumps(details),
                user_id
            )
        )