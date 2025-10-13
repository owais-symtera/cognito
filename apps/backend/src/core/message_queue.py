"""
Message queue integration for pipeline stage transitions.

Implements RabbitMQ integration for reliable stage transitions
with audit logging and dead letter queue handling.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import json
import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import structlog
import aio_pika
from aio_pika import ExchangeType

from ..config.logging import PharmaceuticalLogger

logger = structlog.get_logger(__name__)


class MessageQueueService:
    """
    Service for managing message queue operations.

    Provides reliable message passing between pipeline stages
    with dead letter queue support for pharmaceutical compliance.

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        connection_url: str,
        audit_logger: PharmaceuticalLogger,
        exchange_name: str = "pipeline",
        dead_letter_exchange: str = "pipeline.dlx"
    ):
        """
        Initialize message queue service.

        Args:
            connection_url: RabbitMQ connection URL
            audit_logger: Audit logger
            exchange_name: Main exchange name
            dead_letter_exchange: Dead letter exchange name

        Since:
            Version 1.0.0
        """
        self.connection_url = connection_url
        self.audit_logger = audit_logger
        self.exchange_name = exchange_name
        self.dead_letter_exchange = dead_letter_exchange
        self.connection = None
        self.channel = None
        self.exchange = None
        self.dlx_exchange = None
        self.consumers = {}

    async def connect(self):
        """
        Establish connection to RabbitMQ.

        Since:
            Version 1.0.0
        """
        try:
            # Create connection
            self.connection = await aio_pika.connect_robust(
                self.connection_url,
                client_properties={
                    'application': 'CognitoAI-Pipeline',
                    'version': '1.0.0'
                }
            )

            # Create channel
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)

            # Declare main exchange
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                ExchangeType.TOPIC,
                durable=True
            )

            # Declare dead letter exchange
            self.dlx_exchange = await self.channel.declare_exchange(
                self.dead_letter_exchange,
                ExchangeType.TOPIC,
                durable=True
            )

            # Declare pipeline stage queues
            await self._setup_stage_queues()

            logger.info(
                "Connected to message queue",
                exchange=self.exchange_name
            )

        except Exception as e:
            logger.error(
                "Failed to connect to message queue",
                error=str(e)
            )
            raise

    async def _setup_stage_queues(self):
        """
        Set up queues for pipeline stages.

        Since:
            Version 1.0.0
        """
        stages = [
            'collection',
            'verification',
            'merging',
            'summary'
        ]

        for stage in stages:
            # Main queue for stage
            queue_name = f"pipeline.stage.{stage}"
            dlq_name = f"pipeline.dlq.{stage}"

            # Declare dead letter queue
            dlq = await self.channel.declare_queue(
                dlq_name,
                durable=True
            )
            await dlq.bind(self.dlx_exchange, routing_key=f"dlq.{stage}")

            # Declare main queue with DLX settings
            queue = await self.channel.declare_queue(
                queue_name,
                durable=True,
                arguments={
                    'x-dead-letter-exchange': self.dead_letter_exchange,
                    'x-dead-letter-routing-key': f"dlq.{stage}",
                    'x-message-ttl': 3600000,  # 1 hour TTL
                    'x-max-retries': 3
                }
            )

            # Bind to exchange
            await queue.bind(self.exchange, routing_key=f"stage.{stage}")

            logger.info(f"Set up queue for stage: {stage}")

    async def publish(
        self,
        routing_key: str,
        message: str,
        headers: Optional[Dict[str, Any]] = None
    ):
        """
        Publish message to queue.

        Args:
            routing_key: Routing key for message
            message: Message content (JSON string)
            headers: Optional message headers

        Since:
            Version 1.0.0
        """
        if not self.channel:
            await self.connect()

        try:
            # Parse message for logging
            msg_data = json.loads(message)
            process_id = msg_data.get('process_id', 'unknown')

            # Create message
            amqp_message = aio_pika.Message(
                body=message.encode(),
                content_type='application/json',
                headers=headers or {},
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                timestamp=datetime.utcnow()
            )

            # Publish to exchange
            await self.exchange.publish(
                amqp_message,
                routing_key=routing_key
            )

            # Log message publication
            await self.audit_logger.log_system_event(
                event_type="message_published",
                process_id=process_id,
                component="message_queue",
                details={
                    'routing_key': routing_key,
                    'message_size': len(message)
                }
            )

            logger.debug(
                "Message published",
                routing_key=routing_key,
                process_id=process_id
            )

        except Exception as e:
            logger.error(
                "Failed to publish message",
                routing_key=routing_key,
                error=str(e)
            )
            raise

    async def consume(
        self,
        queue_name: str,
        callback: Callable,
        auto_ack: bool = False
    ):
        """
        Start consuming messages from queue.

        Args:
            queue_name: Queue to consume from
            callback: Async callback function
            auto_ack: Auto-acknowledge messages

        Since:
            Version 1.0.0
        """
        if not self.channel:
            await self.connect()

        try:
            # Get queue
            queue = await self.channel.get_queue(queue_name)

            # Start consuming
            consumer_tag = f"consumer_{queue_name}_{datetime.utcnow().timestamp()}"

            async def message_handler(message: aio_pika.IncomingMessage):
                """Handle incoming message."""
                async with message.process(ignore_processed=True):
                    try:
                        # Parse message
                        msg_data = json.loads(message.body.decode())
                        process_id = msg_data.get('process_id', 'unknown')

                        # Log message receipt
                        logger.debug(
                            "Message received",
                            queue=queue_name,
                            process_id=process_id
                        )

                        # Call handler
                        await callback(msg_data, message.headers)

                        # Acknowledge if not auto-ack
                        if not auto_ack:
                            await message.ack()

                        # Log successful processing
                        await self.audit_logger.log_system_event(
                            event_type="message_processed",
                            process_id=process_id,
                            component="message_queue",
                            details={
                                'queue': queue_name,
                                'success': True
                            }
                        )

                    except Exception as e:
                        logger.error(
                            "Message processing failed",
                            queue=queue_name,
                            error=str(e)
                        )

                        # Reject and requeue or send to DLQ
                        retry_count = message.headers.get('x-retry-count', 0)

                        if retry_count < 3:
                            # Requeue with incremented retry count
                            await message.reject(requeue=True)

                            # Update retry count
                            headers = dict(message.headers)
                            headers['x-retry-count'] = retry_count + 1

                            # Republish with updated headers
                            await self.publish(
                                message.routing_key,
                                message.body.decode(),
                                headers
                            )
                        else:
                            # Send to dead letter queue
                            await message.reject(requeue=False)

                            await self.audit_logger.log_error(
                                "Message sent to DLQ",
                                process_id=process_id,
                                queue=queue_name,
                                error=str(e),
                                drug_names=[]
                            )

            # Register consumer
            await queue.consume(message_handler, consumer_tag=consumer_tag)
            self.consumers[queue_name] = consumer_tag

            logger.info(
                "Started consuming from queue",
                queue=queue_name,
                consumer_tag=consumer_tag
            )

        except Exception as e:
            logger.error(
                "Failed to start consumer",
                queue=queue_name,
                error=str(e)
            )
            raise

    async def stop_consumer(self, queue_name: str):
        """
        Stop consuming from a queue.

        Args:
            queue_name: Queue name

        Since:
            Version 1.0.0
        """
        if queue_name in self.consumers:
            try:
                queue = await self.channel.get_queue(queue_name)
                await queue.cancel(self.consumers[queue_name])
                del self.consumers[queue_name]

                logger.info(
                    "Stopped consuming from queue",
                    queue=queue_name
                )

            except Exception as e:
                logger.error(
                    "Failed to stop consumer",
                    queue=queue_name,
                    error=str(e)
                )

    async def get_queue_info(self, queue_name: str) -> Dict[str, Any]:
        """
        Get information about a queue.

        Args:
            queue_name: Queue name

        Returns:
            Queue information

        Since:
            Version 1.0.0
        """
        if not self.channel:
            await self.connect()

        try:
            queue = await self.channel.get_queue(queue_name)

            # Get queue statistics
            info = await queue.declaration_result

            return {
                'name': queue_name,
                'message_count': info.message_count,
                'consumer_count': info.consumer_count,
                'durable': queue.durable,
                'arguments': queue.arguments
            }

        except Exception as e:
            logger.error(
                "Failed to get queue info",
                queue=queue_name,
                error=str(e)
            )
            return {}

    async def get_dlq_messages(
        self,
        stage: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get messages from dead letter queue.

        Args:
            stage: Pipeline stage
            limit: Maximum messages to retrieve

        Returns:
            List of DLQ messages

        Since:
            Version 1.0.0
        """
        if not self.channel:
            await self.connect()

        dlq_name = f"pipeline.dlq.{stage}"
        messages = []

        try:
            queue = await self.channel.get_queue(dlq_name)

            # Get messages without consuming
            async for message in queue.iterator(max_messages=limit):
                async with message.process(ignore_processed=True):
                    msg_data = json.loads(message.body.decode())
                    messages.append({
                        'data': msg_data,
                        'headers': dict(message.headers),
                        'timestamp': message.timestamp,
                        'routing_key': message.routing_key
                    })

                    # Don't acknowledge - leave in DLQ
                    await message.nack(requeue=True)

            return messages

        except Exception as e:
            logger.error(
                "Failed to get DLQ messages",
                stage=stage,
                error=str(e)
            )
            return []

    async def retry_dlq_message(
        self,
        stage: str,
        process_id: str
    ) -> bool:
        """
        Retry a message from dead letter queue.

        Args:
            stage: Pipeline stage
            process_id: Process ID to retry

        Returns:
            True if message was requeued

        Since:
            Version 1.0.0
        """
        if not self.channel:
            await self.connect()

        dlq_name = f"pipeline.dlq.{stage}"

        try:
            queue = await self.channel.get_queue(dlq_name)

            async for message in queue.iterator():
                async with message.process(ignore_processed=True):
                    msg_data = json.loads(message.body.decode())

                    if msg_data.get('process_id') == process_id:
                        # Republish to main queue
                        await self.publish(
                            f"stage.{stage}",
                            message.body.decode(),
                            {'x-retry-from-dlq': True}
                        )

                        # Remove from DLQ
                        await message.ack()

                        # Log retry
                        await self.audit_logger.log_system_event(
                            event_type="dlq_retry",
                            process_id=process_id,
                            component="message_queue",
                            details={
                                'stage': stage,
                                'success': True
                            }
                        )

                        return True

            return False

        except Exception as e:
            logger.error(
                "Failed to retry DLQ message",
                stage=stage,
                process_id=process_id,
                error=str(e)
            )
            return False

    async def disconnect(self):
        """
        Close connection to message queue.

        Since:
            Version 1.0.0
        """
        try:
            # Stop all consumers
            for queue_name in list(self.consumers.keys()):
                await self.stop_consumer(queue_name)

            # Close connection
            if self.connection:
                await self.connection.close()

            logger.info("Disconnected from message queue")

        except Exception as e:
            logger.error(
                "Error during disconnect",
                error=str(e)
            )