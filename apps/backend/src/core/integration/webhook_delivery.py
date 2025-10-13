"""
Story 6.1: Reliable Webhook Delivery Service
Guaranteed webhook delivery with comprehensive pharmaceutical audit compliance
"""

import asyncio
import hashlib
import hmac
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse
import aiohttp
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

from ...utils.database import DatabaseClient
from ...utils.tracking import SourceTracker
from ...utils.logging import get_logger

logger = get_logger(__name__)


class DeliveryStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    RETRYING = "retrying"


class WebhookType(Enum):
    RESULT_READY = "result_ready"
    STATUS_UPDATE = "status_update"
    ERROR_NOTIFICATION = "error_notification"
    COMPLETION = "completion"
    PARTIAL_RESULT = "partial_result"


@dataclass
class WebhookPayload:
    """Webhook payload structure"""
    webhook_id: str
    request_id: str
    process_id: str
    webhook_type: WebhookType
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    signature: Optional[str] = None
    encrypted: bool = False


@dataclass
class DeliveryAttempt:
    """Record of a delivery attempt"""
    attempt_number: int
    timestamp: datetime
    status_code: Optional[int]
    response_body: Optional[str]
    error_message: Optional[str]
    duration_ms: int
    success: bool


@dataclass
class WebhookEndpoint:
    """Webhook endpoint configuration"""
    id: str
    url: str
    method: str = "POST"
    headers: Dict[str, str] = None
    authentication: Dict[str, Any] = None
    encryption_enabled: bool = True
    retry_config: Dict[str, Any] = None
    timeout_seconds: int = 30
    active: bool = True
    health_check_url: Optional[str] = None


class ExponentialBackoffStrategy:
    """Exponential backoff retry strategy"""

    def __init__(self,
                 initial_delay: float = 1.0,
                 max_delay: float = 300.0,
                 multiplier: float = 2.0,
                 max_retries: int = 10):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.max_retries = max_retries

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        if attempt >= self.max_retries:
            return None  # No more retries

        delay = self.initial_delay * (self.multiplier ** attempt)
        return min(delay, self.max_delay)

    def should_retry(self, attempt: int, status_code: Optional[int]) -> bool:
        """Determine if should retry based on attempt and status"""
        if attempt >= self.max_retries:
            return False

        # Retry on network errors or 5xx status codes
        if status_code is None or status_code >= 500:
            return True

        # Retry on specific 4xx codes that might be temporary
        if status_code in [408, 429, 503, 504]:
            return True

        return False


class WebhookDeliveryService:
    """Reliable webhook delivery service with audit compliance"""

    def __init__(self,
                 db_client: DatabaseClient,
                 source_tracker: SourceTracker,
                 encryption_key: Optional[bytes] = None):
        self.db_client = db_client
        self.source_tracker = source_tracker
        self.retry_strategy = ExponentialBackoffStrategy()
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.fernet = Fernet(self.encryption_key)
        self.delivery_queue = asyncio.Queue()
        self.dead_letter_queue = asyncio.Queue()
        self.workers = []
        self.is_running = False

    async def initialize(self):
        """Initialize webhook delivery service"""
        await self._ensure_tables_exist()
        logger.info("Webhook delivery service initialized")

    async def _ensure_tables_exist(self):
        """Ensure webhook-related tables exist"""
        await self.db_client.execute_many([
            """
            CREATE TABLE IF NOT EXISTS webhook_endpoints (
                id VARCHAR(100) PRIMARY KEY,
                url TEXT NOT NULL,
                method VARCHAR(10) DEFAULT 'POST',
                headers JSONB,
                authentication JSONB,
                encryption_enabled BOOLEAN DEFAULT TRUE,
                retry_config JSONB,
                timeout_seconds INTEGER DEFAULT 30,
                active BOOLEAN DEFAULT TRUE,
                health_check_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS webhook_deliveries (
                id SERIAL PRIMARY KEY,
                webhook_id VARCHAR(100) NOT NULL UNIQUE,
                request_id VARCHAR(100) NOT NULL,
                process_id VARCHAR(100) NOT NULL,
                endpoint_id VARCHAR(100) REFERENCES webhook_endpoints(id),
                webhook_type VARCHAR(50) NOT NULL,
                payload JSONB NOT NULL,
                encrypted_payload TEXT,
                status VARCHAR(20) NOT NULL,
                attempts INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scheduled_at TIMESTAMP,
                delivered_at TIMESTAMP,
                next_retry_at TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS webhook_attempts (
                id SERIAL PRIMARY KEY,
                webhook_id VARCHAR(100) NOT NULL,
                attempt_number INTEGER NOT NULL,
                status_code INTEGER,
                response_body TEXT,
                error_message TEXT,
                duration_ms INTEGER,
                success BOOLEAN DEFAULT FALSE,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS webhook_audit_trail (
                id SERIAL PRIMARY KEY,
                webhook_id VARCHAR(100) NOT NULL,
                request_id VARCHAR(100) NOT NULL,
                process_id VARCHAR(100) NOT NULL,
                action VARCHAR(50) NOT NULL,
                details JSONB,
                user_id VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS dead_letter_webhooks (
                id SERIAL PRIMARY KEY,
                webhook_id VARCHAR(100) NOT NULL,
                original_payload JSONB NOT NULL,
                failure_reason TEXT,
                attempts_made INTEGER,
                last_attempt_at TIMESTAMP,
                manual_intervention_required BOOLEAN DEFAULT TRUE,
                resolved BOOLEAN DEFAULT FALSE,
                resolved_at TIMESTAMP,
                resolved_by VARCHAR(100),
                resolution_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS webhook_performance_metrics (
                id SERIAL PRIMARY KEY,
                endpoint_id VARCHAR(100),
                date DATE NOT NULL,
                total_deliveries INTEGER DEFAULT 0,
                successful_deliveries INTEGER DEFAULT 0,
                failed_deliveries INTEGER DEFAULT 0,
                avg_delivery_time_ms INTEGER,
                avg_attempts_per_delivery DECIMAL(5,2),
                sla_met_percentage DECIMAL(5,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(endpoint_id, date)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS endpoint_health_checks (
                id SERIAL PRIMARY KEY,
                endpoint_id VARCHAR(100) REFERENCES webhook_endpoints(id),
                check_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_healthy BOOLEAN,
                response_time_ms INTEGER,
                status_code INTEGER,
                error_message TEXT
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status
            ON webhook_deliveries(status, scheduled_at);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_request
            ON webhook_deliveries(request_id, process_id);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_webhook_audit_trail_request
            ON webhook_audit_trail(request_id, process_id, created_at DESC);
            """
        ])

    async def register_endpoint(self, endpoint: WebhookEndpoint) -> str:
        """Register a webhook endpoint"""
        query = """
            INSERT INTO webhook_endpoints
            (id, url, method, headers, authentication, encryption_enabled,
             retry_config, timeout_seconds, active, health_check_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                url = EXCLUDED.url,
                headers = EXCLUDED.headers,
                authentication = EXCLUDED.authentication,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """

        result = await self.db_client.fetch_one(
            query,
            (
                endpoint.id,
                endpoint.url,
                endpoint.method,
                json.dumps(endpoint.headers or {}),
                json.dumps(endpoint.authentication or {}),
                endpoint.encryption_enabled,
                json.dumps(endpoint.retry_config or {}),
                endpoint.timeout_seconds,
                endpoint.active,
                endpoint.health_check_url
            )
        )

        # Audit trail
        await self._add_audit_trail(
            webhook_id="",
            request_id="",
            process_id="",
            action="endpoint_registered",
            details={"endpoint_id": endpoint.id, "url": endpoint.url}
        )

        logger.info(f"Registered webhook endpoint: {endpoint.id}")
        return result['id']

    async def schedule_webhook(self,
                              request_id: str,
                              process_id: str,
                              endpoint_id: str,
                              webhook_type: WebhookType,
                              data: Dict[str, Any],
                              metadata: Optional[Dict[str, Any]] = None,
                              scheduled_at: Optional[datetime] = None) -> str:
        """Schedule a webhook for delivery"""
        webhook_id = f"{request_id}_{process_id}_{int(time.time() * 1000)}"

        # Create payload
        payload = WebhookPayload(
            webhook_id=webhook_id,
            request_id=request_id,
            process_id=process_id,
            webhook_type=webhook_type,
            timestamp=datetime.utcnow(),
            data=data,
            metadata=metadata or {}
        )

        # Get endpoint configuration
        endpoint = await self._get_endpoint(endpoint_id)
        if not endpoint:
            raise ValueError(f"Endpoint not found: {endpoint_id}")

        # Encrypt payload if required
        encrypted_payload = None
        if endpoint['encryption_enabled']:
            encrypted_payload = await self._encrypt_payload(payload)
            payload.encrypted = True

        # Sign payload
        payload.signature = await self._sign_payload(payload)

        # Store in database
        query = """
            INSERT INTO webhook_deliveries
            (webhook_id, request_id, process_id, endpoint_id, webhook_type,
             payload, encrypted_payload, status, scheduled_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (
                webhook_id,
                request_id,
                process_id,
                endpoint_id,
                webhook_type.value,
                json.dumps(self._payload_to_dict(payload)),
                encrypted_payload,
                DeliveryStatus.PENDING.value,
                scheduled_at or datetime.utcnow()
            )
        )

        # Add to delivery queue
        await self.delivery_queue.put(webhook_id)

        # Audit trail
        await self._add_audit_trail(
            webhook_id=webhook_id,
            request_id=request_id,
            process_id=process_id,
            action="webhook_scheduled",
            details={
                "endpoint_id": endpoint_id,
                "webhook_type": webhook_type.value
            }
        )

        # Track source
        self.source_tracker.add_source(
            request_id=request_id,
            field_name="webhook_scheduled",
            value=webhook_id,
            source_system="webhook_delivery_service",
            source_detail={
                "endpoint_id": endpoint_id,
                "webhook_type": webhook_type.value
            }
        )

        logger.info(f"Scheduled webhook: {webhook_id}")
        return webhook_id

    async def deliver_webhook(self, webhook_id: str) -> bool:
        """Deliver a specific webhook"""
        # Get webhook details
        webhook = await self._get_webhook(webhook_id)
        if not webhook:
            logger.error(f"Webhook not found: {webhook_id}")
            return False

        # Get endpoint details
        endpoint = await self._get_endpoint(webhook['endpoint_id'])
        if not endpoint or not endpoint['active']:
            logger.error(f"Endpoint not active: {webhook['endpoint_id']}")
            await self._move_to_dead_letter(webhook_id, "Endpoint not active")
            return False

        # Update status to in_progress
        await self._update_webhook_status(webhook_id, DeliveryStatus.IN_PROGRESS)

        # Prepare payload
        payload = webhook['payload']
        if webhook['encrypted_payload']:
            # Use encrypted version
            payload_data = webhook['encrypted_payload']
        else:
            payload_data = json.dumps(payload)

        # Attempt delivery with retries
        attempt = 0
        success = False

        while not success and self.retry_strategy.should_retry(attempt, None):
            attempt += 1
            start_time = time.time()

            try:
                # Prepare headers
                headers = json.loads(endpoint['headers'] or '{}')
                headers['Content-Type'] = 'application/json'
                headers['X-Webhook-Id'] = webhook_id
                headers['X-Request-Id'] = webhook['request_id']
                headers['X-Process-Id'] = webhook['process_id']
                headers['X-Webhook-Signature'] = payload.get('signature', '')

                # Add authentication
                auth = await self._prepare_authentication(
                    json.loads(endpoint['authentication'] or '{}')
                )
                if auth:
                    headers.update(auth)

                # Make HTTP request
                async with aiohttp.ClientSession() as session:
                    timeout = aiohttp.ClientTimeout(
                        total=endpoint['timeout_seconds']
                    )

                    async with session.request(
                        method=endpoint['method'],
                        url=endpoint['url'],
                        data=payload_data,
                        headers=headers,
                        timeout=timeout
                    ) as response:
                        status_code = response.status
                        response_body = await response.text()

                        # Check if successful
                        if 200 <= status_code < 300:
                            success = True
                            duration_ms = int((time.time() - start_time) * 1000)

                            # Record successful attempt
                            await self._record_attempt(
                                webhook_id,
                                DeliveryAttempt(
                                    attempt_number=attempt,
                                    timestamp=datetime.utcnow(),
                                    status_code=status_code,
                                    response_body=response_body[:1000],  # Truncate
                                    error_message=None,
                                    duration_ms=duration_ms,
                                    success=True
                                )
                            )

                            # Update webhook status
                            await self._update_webhook_status(
                                webhook_id,
                                DeliveryStatus.DELIVERED,
                                delivered_at=datetime.utcnow()
                            )

                            # Update performance metrics
                            await self._update_performance_metrics(
                                endpoint['id'],
                                success=True,
                                duration_ms=duration_ms,
                                attempts=attempt
                            )

                            # Audit trail
                            await self._add_audit_trail(
                                webhook_id=webhook_id,
                                request_id=webhook['request_id'],
                                process_id=webhook['process_id'],
                                action="webhook_delivered",
                                details={
                                    "status_code": status_code,
                                    "attempts": attempt,
                                    "duration_ms": duration_ms
                                }
                            )

                            logger.info(f"Webhook delivered: {webhook_id}")
                        else:
                            # Non-success status code
                            raise Exception(f"HTTP {status_code}: {response_body}")

            except asyncio.TimeoutError as e:
                error_msg = f"Timeout after {endpoint['timeout_seconds']}s"
                await self._handle_delivery_failure(
                    webhook_id, attempt, None, error_msg
                )

            except aiohttp.ClientError as e:
                error_msg = f"Connection error: {str(e)}"
                await self._handle_delivery_failure(
                    webhook_id, attempt, None, error_msg
                )

            except Exception as e:
                error_msg = f"Delivery error: {str(e)}"
                await self._handle_delivery_failure(
                    webhook_id, attempt, None, error_msg
                )

            # Wait before retry
            if not success and attempt < self.retry_strategy.max_retries:
                delay = self.retry_strategy.get_delay(attempt)
                if delay:
                    await self._update_webhook_status(
                        webhook_id,
                        DeliveryStatus.RETRYING,
                        next_retry_at=datetime.utcnow() + timedelta(seconds=delay)
                    )
                    await asyncio.sleep(delay)

        # If all retries failed, move to dead letter queue
        if not success:
            await self._move_to_dead_letter(
                webhook_id,
                f"Failed after {attempt} attempts"
            )

            # Update performance metrics
            await self._update_performance_metrics(
                endpoint['id'],
                success=False,
                duration_ms=0,
                attempts=attempt
            )

        return success

    async def _handle_delivery_failure(self,
                                      webhook_id: str,
                                      attempt: int,
                                      status_code: Optional[int],
                                      error_message: str):
        """Handle delivery failure"""
        # Record failed attempt
        await self._record_attempt(
            webhook_id,
            DeliveryAttempt(
                attempt_number=attempt,
                timestamp=datetime.utcnow(),
                status_code=status_code,
                response_body=None,
                error_message=error_message,
                duration_ms=0,
                success=False
            )
        )

        # Audit trail
        await self._add_audit_trail(
            webhook_id=webhook_id,
            request_id="",
            process_id="",
            action="delivery_failed",
            details={
                "attempt": attempt,
                "error": error_message
            }
        )

        logger.warning(f"Webhook delivery failed (attempt {attempt}): {error_message}")

    async def _move_to_dead_letter(self, webhook_id: str, reason: str):
        """Move failed webhook to dead letter queue"""
        webhook = await self._get_webhook(webhook_id)
        if not webhook:
            return

        query = """
            INSERT INTO dead_letter_webhooks
            (webhook_id, original_payload, failure_reason, attempts_made,
             last_attempt_at, manual_intervention_required)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        attempts = await self._get_attempt_count(webhook_id)

        await self.db_client.execute(
            query,
            (
                webhook_id,
                json.dumps(webhook['payload']),
                reason,
                attempts,
                datetime.utcnow(),
                True
            )
        )

        # Update webhook status
        await self._update_webhook_status(webhook_id, DeliveryStatus.DEAD_LETTER)

        # Add to dead letter queue
        await self.dead_letter_queue.put(webhook_id)

        # Audit trail
        await self._add_audit_trail(
            webhook_id=webhook_id,
            request_id=webhook['request_id'],
            process_id=webhook['process_id'],
            action="moved_to_dead_letter",
            details={"reason": reason, "attempts": attempts}
        )

        logger.error(f"Webhook moved to dead letter queue: {webhook_id}")

    async def process_dead_letter_queue(self):
        """Process webhooks in dead letter queue"""
        while True:
            try:
                webhook_id = await self.dead_letter_queue.get()

                # Check if manual intervention has resolved the issue
                dead_letter = await self._get_dead_letter_webhook(webhook_id)
                if dead_letter and not dead_letter['resolved']:
                    # Attempt redelivery if configured
                    if await self._should_retry_dead_letter(dead_letter):
                        success = await self.deliver_webhook(webhook_id)
                        if success:
                            await self._mark_dead_letter_resolved(
                                webhook_id,
                                "Automatic retry successful"
                            )

            except Exception as e:
                logger.error(f"Error processing dead letter queue: {e}")
                await asyncio.sleep(60)  # Wait before continuing

    async def validate_endpoint(self, endpoint_id: str) -> Tuple[bool, str]:
        """Validate webhook endpoint health"""
        endpoint = await self._get_endpoint(endpoint_id)
        if not endpoint:
            return False, "Endpoint not found"

        # Perform health check
        health_check_url = endpoint['health_check_url'] or endpoint['url']

        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10)
                start_time = time.time()

                async with session.get(
                    health_check_url,
                    timeout=timeout
                ) as response:
                    status_code = response.status
                    response_time_ms = int((time.time() - start_time) * 1000)

                    is_healthy = 200 <= status_code < 300

                    # Record health check
                    await self._record_health_check(
                        endpoint_id,
                        is_healthy,
                        response_time_ms,
                        status_code,
                        None
                    )

                    if is_healthy:
                        return True, f"Endpoint healthy (Response time: {response_time_ms}ms)"
                    else:
                        return False, f"Endpoint unhealthy (Status: {status_code})"

        except Exception as e:
            error_msg = str(e)
            await self._record_health_check(
                endpoint_id,
                False,
                0,
                None,
                error_msg
            )
            return False, f"Health check failed: {error_msg}"

    async def get_delivery_status(self, webhook_id: str) -> Dict[str, Any]:
        """Get delivery status for a webhook"""
        webhook = await self._get_webhook(webhook_id)
        if not webhook:
            return None

        attempts = await self._get_delivery_attempts(webhook_id)

        return {
            "webhook_id": webhook_id,
            "status": webhook['status'],
            "created_at": webhook['created_at'].isoformat(),
            "delivered_at": webhook['delivered_at'].isoformat() if webhook['delivered_at'] else None,
            "attempts": len(attempts),
            "attempt_details": [
                {
                    "attempt": a['attempt_number'],
                    "timestamp": a['attempted_at'].isoformat(),
                    "status_code": a['status_code'],
                    "success": a['success'],
                    "error": a['error_message']
                } for a in attempts
            ]
        }

    async def get_performance_metrics(self,
                                     endpoint_id: Optional[str] = None,
                                     start_date: Optional[datetime] = None,
                                     end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get performance metrics for webhook delivery"""
        conditions = []
        params = []

        if endpoint_id:
            conditions.append("endpoint_id = %s")
            params.append(endpoint_id)

        if start_date:
            conditions.append("date >= %s")
            params.append(start_date.date())

        if end_date:
            conditions.append("date <= %s")
            params.append(end_date.date())

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT
                COUNT(*) as days,
                SUM(total_deliveries) as total_deliveries,
                SUM(successful_deliveries) as successful_deliveries,
                SUM(failed_deliveries) as failed_deliveries,
                AVG(avg_delivery_time_ms) as avg_delivery_time_ms,
                AVG(avg_attempts_per_delivery) as avg_attempts_per_delivery,
                AVG(sla_met_percentage) as avg_sla_met_percentage
            FROM webhook_performance_metrics
            {where_clause}
        """

        result = await self.db_client.fetch_one(query, tuple(params))

        if result:
            success_rate = (
                (result['successful_deliveries'] / result['total_deliveries'] * 100)
                if result['total_deliveries'] > 0 else 0
            )

            return {
                "period_days": result['days'],
                "total_deliveries": result['total_deliveries'] or 0,
                "successful_deliveries": result['successful_deliveries'] or 0,
                "failed_deliveries": result['failed_deliveries'] or 0,
                "success_rate": success_rate,
                "avg_delivery_time_ms": result['avg_delivery_time_ms'] or 0,
                "avg_attempts_per_delivery": float(result['avg_attempts_per_delivery'] or 0),
                "avg_sla_met_percentage": float(result['avg_sla_met_percentage'] or 0)
            }

        return {
            "period_days": 0,
            "total_deliveries": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "success_rate": 0,
            "avg_delivery_time_ms": 0,
            "avg_attempts_per_delivery": 0,
            "avg_sla_met_percentage": 0
        }

    # Helper methods

    async def _encrypt_payload(self, payload: WebhookPayload) -> str:
        """Encrypt webhook payload"""
        payload_json = json.dumps(self._payload_to_dict(payload))
        encrypted = self.fernet.encrypt(payload_json.encode())
        return encrypted.decode()

    async def _sign_payload(self, payload: WebhookPayload) -> str:
        """Generate HMAC signature for payload"""
        payload_json = json.dumps(self._payload_to_dict(payload), sort_keys=True)
        signature = hmac.new(
            self.encryption_key,
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _payload_to_dict(self, payload: WebhookPayload) -> Dict:
        """Convert payload to dictionary"""
        return {
            "webhook_id": payload.webhook_id,
            "request_id": payload.request_id,
            "process_id": payload.process_id,
            "webhook_type": payload.webhook_type.value,
            "timestamp": payload.timestamp.isoformat(),
            "data": payload.data,
            "metadata": payload.metadata,
            "signature": payload.signature,
            "encrypted": payload.encrypted
        }

    async def _prepare_authentication(self, auth_config: Dict[str, Any]) -> Dict[str, str]:
        """Prepare authentication headers"""
        auth_type = auth_config.get('type')
        headers = {}

        if auth_type == 'bearer':
            token = auth_config.get('token')
            headers['Authorization'] = f"Bearer {token}"
        elif auth_type == 'api_key':
            key_name = auth_config.get('key_name', 'X-API-Key')
            key_value = auth_config.get('key_value')
            headers[key_name] = key_value
        elif auth_type == 'basic':
            username = auth_config.get('username')
            password = auth_config.get('password')
            import base64
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers['Authorization'] = f"Basic {credentials}"

        return headers

    async def _get_endpoint(self, endpoint_id: str) -> Optional[Dict]:
        """Get endpoint configuration"""
        query = """
            SELECT * FROM webhook_endpoints
            WHERE id = %s
        """
        return await self.db_client.fetch_one(query, (endpoint_id,))

    async def _get_webhook(self, webhook_id: str) -> Optional[Dict]:
        """Get webhook details"""
        query = """
            SELECT * FROM webhook_deliveries
            WHERE webhook_id = %s
        """
        return await self.db_client.fetch_one(query, (webhook_id,))

    async def _get_dead_letter_webhook(self, webhook_id: str) -> Optional[Dict]:
        """Get dead letter webhook details"""
        query = """
            SELECT * FROM dead_letter_webhooks
            WHERE webhook_id = %s AND resolved = FALSE
        """
        return await self.db_client.fetch_one(query, (webhook_id,))

    async def _should_retry_dead_letter(self, dead_letter: Dict) -> bool:
        """Determine if dead letter webhook should be retried"""
        # Check if enough time has passed since last attempt
        last_attempt = dead_letter['last_attempt_at']
        hours_since = (datetime.utcnow() - last_attempt).total_seconds() / 3600

        # Retry after 1, 4, 12, 24 hours
        retry_hours = [1, 4, 12, 24]
        attempts = dead_letter['attempts_made']

        if attempts < len(retry_hours) and hours_since >= retry_hours[attempts]:
            return True

        return False

    async def _mark_dead_letter_resolved(self,
                                        webhook_id: str,
                                        resolution_notes: str,
                                        resolved_by: str = "system"):
        """Mark dead letter webhook as resolved"""
        query = """
            UPDATE dead_letter_webhooks
            SET resolved = TRUE,
                resolved_at = %s,
                resolved_by = %s,
                resolution_notes = %s
            WHERE webhook_id = %s
        """

        await self.db_client.execute(
            query,
            (datetime.utcnow(), resolved_by, resolution_notes, webhook_id)
        )

    async def _update_webhook_status(self,
                                    webhook_id: str,
                                    status: DeliveryStatus,
                                    delivered_at: Optional[datetime] = None,
                                    next_retry_at: Optional[datetime] = None):
        """Update webhook delivery status"""
        updates = ["status = %s"]
        params = [status.value]

        if delivered_at:
            updates.append("delivered_at = %s")
            params.append(delivered_at)

        if next_retry_at:
            updates.append("next_retry_at = %s")
            params.append(next_retry_at)

        params.append(webhook_id)

        query = f"""
            UPDATE webhook_deliveries
            SET {', '.join(updates)}
            WHERE webhook_id = %s
        """

        await self.db_client.execute(query, tuple(params))

    async def _record_attempt(self,
                             webhook_id: str,
                             attempt: DeliveryAttempt):
        """Record delivery attempt"""
        query = """
            INSERT INTO webhook_attempts
            (webhook_id, attempt_number, status_code, response_body,
             error_message, duration_ms, success)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (
                webhook_id,
                attempt.attempt_number,
                attempt.status_code,
                attempt.response_body,
                attempt.error_message,
                attempt.duration_ms,
                attempt.success
            )
        )

    async def _get_attempt_count(self, webhook_id: str) -> int:
        """Get number of delivery attempts"""
        query = """
            SELECT COUNT(*) as count
            FROM webhook_attempts
            WHERE webhook_id = %s
        """
        result = await self.db_client.fetch_one(query, (webhook_id,))
        return result['count'] if result else 0

    async def _get_delivery_attempts(self, webhook_id: str) -> List[Dict]:
        """Get all delivery attempts for a webhook"""
        query = """
            SELECT *
            FROM webhook_attempts
            WHERE webhook_id = %s
            ORDER BY attempt_number
        """
        return await self.db_client.fetch_all(query, (webhook_id,))

    async def _update_performance_metrics(self,
                                         endpoint_id: str,
                                         success: bool,
                                         duration_ms: int,
                                         attempts: int):
        """Update performance metrics"""
        today = datetime.utcnow().date()

        query = """
            INSERT INTO webhook_performance_metrics
            (endpoint_id, date, total_deliveries, successful_deliveries,
             failed_deliveries, avg_delivery_time_ms, avg_attempts_per_delivery)
            VALUES (%s, %s, 1, %s, %s, %s, %s)
            ON CONFLICT (endpoint_id, date) DO UPDATE SET
                total_deliveries = webhook_performance_metrics.total_deliveries + 1,
                successful_deliveries = webhook_performance_metrics.successful_deliveries + %s,
                failed_deliveries = webhook_performance_metrics.failed_deliveries + %s,
                avg_delivery_time_ms = (
                    webhook_performance_metrics.avg_delivery_time_ms * webhook_performance_metrics.total_deliveries + %s
                ) / (webhook_performance_metrics.total_deliveries + 1),
                avg_attempts_per_delivery = (
                    webhook_performance_metrics.avg_attempts_per_delivery * webhook_performance_metrics.total_deliveries + %s
                ) / (webhook_performance_metrics.total_deliveries + 1)
        """

        await self.db_client.execute(
            query,
            (
                endpoint_id,
                today,
                1 if success else 0,
                0 if success else 1,
                duration_ms if success else 0,
                attempts,
                1 if success else 0,
                0 if success else 1,
                duration_ms if success else 0,
                attempts
            )
        )

    async def _record_health_check(self,
                                  endpoint_id: str,
                                  is_healthy: bool,
                                  response_time_ms: int,
                                  status_code: Optional[int],
                                  error_message: Optional[str]):
        """Record endpoint health check result"""
        query = """
            INSERT INTO endpoint_health_checks
            (endpoint_id, is_healthy, response_time_ms, status_code, error_message)
            VALUES (%s, %s, %s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (endpoint_id, is_healthy, response_time_ms, status_code, error_message)
        )

    async def _add_audit_trail(self,
                              webhook_id: str,
                              request_id: str,
                              process_id: str,
                              action: str,
                              details: Dict[str, Any],
                              user_id: Optional[str] = None):
        """Add audit trail entry"""
        query = """
            INSERT INTO webhook_audit_trail
            (webhook_id, request_id, process_id, action, details, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        await self.db_client.execute(
            query,
            (
                webhook_id,
                request_id,
                process_id,
                action,
                json.dumps(details),
                user_id
            )
        )

    async def start_workers(self, num_workers: int = 5):
        """Start webhook delivery workers"""
        self.is_running = True

        for i in range(num_workers):
            worker = asyncio.create_task(self._delivery_worker(i))
            self.workers.append(worker)

        # Start dead letter processor
        dead_letter_processor = asyncio.create_task(self.process_dead_letter_queue())
        self.workers.append(dead_letter_processor)

        logger.info(f"Started {num_workers} webhook delivery workers")

    async def stop_workers(self):
        """Stop webhook delivery workers"""
        self.is_running = False

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)

        self.workers = []
        logger.info("Stopped webhook delivery workers")

    async def _delivery_worker(self, worker_id: int):
        """Worker to process webhook delivery queue"""
        logger.info(f"Webhook delivery worker {worker_id} started")

        while self.is_running:
            try:
                # Get webhook from queue with timeout
                webhook_id = await asyncio.wait_for(
                    self.delivery_queue.get(),
                    timeout=1.0
                )

                # Deliver webhook
                await self.deliver_webhook(webhook_id)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)

        logger.info(f"Webhook delivery worker {worker_id} stopped")