# Monitoring and Logging

### Structured Logging Configuration
```python
# apps/backend/src/config/logging.py
import logging
import structlog
from datetime import datetime

def configure_logging():
    """Configure structured logging for pharmaceutical compliance"""

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=False,
    )

class PharmaceuticalLogger:
    """
    Specialized logger for pharmaceutical data processing with regulatory compliance
    """

    def __init__(self):
        self.logger = structlog.get_logger()

    def log_processing_start(self, request_id: str, drug_name: str):
        """Log start of pharmaceutical data processing"""
        self.logger.info(
            "pharmaceutical_processing_started",
            request_id=request_id,
            drug_name=drug_name,
            event_type="processing_start",
            compliance_level="regulatory"
        )

    def log_category_completion(self, request_id: str, category: str, sources_count: int):
        """Log completion of category processing"""
        self.logger.info(
            "category_processing_completed",
            request_id=request_id,
            category=category,
            sources_count=sources_count,
            event_type="category_completion"
        )

    def log_source_conflict(self, request_id: str, conflict_data: dict):
        """Log source conflicts for regulatory tracking"""
        self.logger.warning(
            "source_conflict_detected",
            request_id=request_id,
            conflict_type=conflict_data["type"],
            severity=conflict_data["severity"],
            event_type="conflict_detection",
            compliance_level="critical"
        )

    def log_api_error(self, provider: str, error: str, request_id: str):
        """Log API integration errors"""
        self.logger.error(
            "api_integration_error",
            provider=provider,
            error=error,
            request_id=request_id,
            event_type="api_error",
            requires_investigation=True
        )
```
