"""
Structured logging configuration for pharmaceutical compliance.

Configures logging with pharmaceutical compliance formatting,
correlation IDs, and audit trail support.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import logging
import sys
from typing import Any, Dict, Optional
import structlog
from structlog.processors import JSONRenderer, TimeStamper
from structlog.stdlib import BoundLogger, LoggerFactory


class PharmaceuticalLogger:
    """
    Pharmaceutical compliance logging with structured format.

    Since:
        Version 1.0.0
    """

    def __init__(self, logger: BoundLogger):
        """
        Initialize pharmaceutical logger.

        Args:
            logger: Structlog bound logger

        Since:
            Version 1.0.0
        """
        self.logger = logger

    def log_processing_start(
        self,
        request_id: str,
        drug_name: str,
        user_id: Optional[str] = None
    ):
        """
        Log pharmaceutical processing start event.

        Args:
            request_id: Unique request identifier
            drug_name: Drug being processed
            user_id: User initiating the processing

        Since:
            Version 1.0.0
        """
        self.logger.info(
            "pharmaceutical_processing_started",
            request_id=request_id,
            drug_name=drug_name,
            user_id=user_id,
            event_type="processing_start",
            compliance_level="regulatory"
        )

    def log_processing_complete(
        self,
        request_id: str,
        drug_name: str,
        duration_ms: float,
        success: bool
    ):
        """
        Log pharmaceutical processing completion.

        Args:
            request_id: Unique request identifier
            drug_name: Drug that was processed
            duration_ms: Processing duration in milliseconds
            success: Whether processing succeeded

        Since:
            Version 1.0.0
        """
        self.logger.info(
            "pharmaceutical_processing_completed",
            request_id=request_id,
            drug_name=drug_name,
            duration_ms=duration_ms,
            success=success,
            event_type="processing_complete",
            compliance_level="regulatory"
        )

    def log_system_health_check(
        self,
        component: str,
        status: str,
        response_time_ms: Optional[float] = None
    ):
        """
        Log system health check event.

        Args:
            component: Component being checked
            status: Health status
            response_time_ms: Response time if applicable

        Since:
            Version 1.0.0
        """
        self.logger.info(
            "system_health_check",
            component=component,
            status=status,
            response_time_ms=response_time_ms,
            event_type="health_monitoring",
            compliance_level="operational"
        )

    def log_api_call(
        self,
        provider: str,
        endpoint: str,
        success: bool,
        response_time_ms: float,
        error: Optional[str] = None
    ):
        """
        Log external API call for audit trail.

        Args:
            provider: API provider name
            endpoint: API endpoint called
            success: Whether call succeeded
            response_time_ms: Response time
            error: Error message if failed

        Since:
            Version 1.0.0
        """
        self.logger.info(
            "external_api_call",
            provider=provider,
            endpoint=endpoint,
            success=success,
            response_time_ms=response_time_ms,
            error=error,
            event_type="api_call",
            compliance_level="audit"
        )

    def log_security_event(
        self,
        event: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log security-related event.

        Args:
            event: Security event type
            user_id: User involved
            ip_address: IP address
            details: Additional event details

        Since:
            Version 1.0.0
        """
        self.logger.warning(
            "security_event",
            security_event=event,
            user_id=user_id,
            ip_address=ip_address,
            details=details,
            event_type="security",
            compliance_level="regulatory"
        )

    def log_data_access(
        self,
        resource: str,
        action: str,
        user_id: str,
        success: bool,
        drug_names: Optional[list] = None
    ):
        """
        Log pharmaceutical data access for compliance.

        Args:
            resource: Resource accessed
            action: Action performed
            user_id: User performing action
            success: Whether access succeeded
            drug_names: Drugs involved if applicable

        Since:
            Version 1.0.0
        """
        self.logger.info(
            "pharmaceutical_data_access",
            resource=resource,
            action=action,
            user_id=user_id,
            success=success,
            drug_names=drug_names,
            event_type="data_access",
            compliance_level="regulatory"
        )


def add_correlation_id(logger, method_name, event_dict):
    """
    Add correlation ID to all log entries.

    Args:
        logger: Logger instance
        method_name: Log method name
        event_dict: Event dictionary

    Returns:
        Modified event dictionary

    Since:
        Version 1.0.0
    """
    import contextvars
    correlation_id = contextvars.ContextVar('correlation_id', default=None)
    if correlation_id.get():
        event_dict['correlation_id'] = correlation_id.get()
    return event_dict


def configure_logging(log_level: str = "INFO", log_format: str = "json"):
    """
    Configure structured logging for pharmaceutical compliance.

    Args:
        log_level: Logging level
        log_format: Output format (json or console)

    Since:
        Version 1.0.0
    """
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        TimeStamper(fmt="iso"),
        add_correlation_id,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if log_format == "json":
        processors.append(JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure Python logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )


def get_logger(name: str) -> PharmaceuticalLogger:
    """
    Get pharmaceutical compliance logger.

    Args:
        name: Logger name

    Returns:
        Configured pharmaceutical logger

    Since:
        Version 1.0.0
    """
    logger = structlog.get_logger(name)
    return PharmaceuticalLogger(logger)