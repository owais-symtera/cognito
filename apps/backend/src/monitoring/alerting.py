"""
Alert system for pharmaceutical platform monitoring.

Manages alerts, notifications, and incident escalation for
pharmaceutical operational compliance.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import structlog
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = structlog.get_logger(__name__)


class AlertSeverity(str, Enum):
    """
    Alert severity levels.

    Since:
        Version 1.0.0
    """
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """
    Types of system alerts.

    Since:
        Version 1.0.0
    """
    DATABASE_CONNECTION_FAILURE = "database_connection_failure"
    REDIS_CONNECTION_FAILURE = "redis_connection_failure"
    API_PROVIDER_OUTAGE = "api_provider_outage"
    QUEUE_OVERFLOW = "queue_overflow"
    HIGH_RESPONSE_TIME = "high_response_time"
    HIGH_MEMORY_USAGE = "high_memory_usage"
    HIGH_ERROR_RATE = "high_error_rate"
    PROCESSING_FAILURE = "processing_failure"


class AlertChannel(str, Enum):
    """
    Alert notification channels.

    Since:
        Version 1.0.0
    """
    EMAIL = "email"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"


class AlertManager:
    """
    Manages system alerts and notifications.

    Since:
        Version 1.0.0
    """

    def __init__(self):
        """
        Initialize alert manager.

        Since:
            Version 1.0.0
        """
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        self.alert_history: List[Dict[str, Any]] = []
        self.alert_thresholds = self._load_alert_thresholds()

    def _load_alert_thresholds(self) -> Dict[str, Dict[str, Any]]:
        """
        Load alert threshold configurations.

        Returns:
            Alert threshold configurations

        Since:
            Version 1.0.0
        """
        return {
            AlertType.DATABASE_CONNECTION_FAILURE: {
                "severity": AlertSeverity.CRITICAL,
                "threshold_seconds": 0,
                "channels": [AlertChannel.EMAIL, AlertChannel.PAGERDUTY]
            },
            AlertType.REDIS_CONNECTION_FAILURE: {
                "severity": AlertSeverity.WARNING,
                "threshold_seconds": 300,
                "channels": [AlertChannel.SLACK]
            },
            AlertType.API_PROVIDER_OUTAGE: {
                "severity": AlertSeverity.WARNING,
                "threshold_seconds": 600,
                "channels": [AlertChannel.SLACK, AlertChannel.EMAIL]
            },
            AlertType.QUEUE_OVERFLOW: {
                "severity": AlertSeverity.WARNING,
                "threshold_seconds": 300,
                "threshold_value": 100,
                "channels": [AlertChannel.SLACK]
            },
            AlertType.HIGH_RESPONSE_TIME: {
                "severity": AlertSeverity.WARNING,
                "threshold_seconds": 300,
                "threshold_value": 5000,
                "channels": [AlertChannel.SLACK]
            },
            AlertType.HIGH_MEMORY_USAGE: {
                "severity": AlertSeverity.WARNING,
                "threshold_seconds": 600,
                "threshold_value": 85,
                "channels": [AlertChannel.SLACK, AlertChannel.EMAIL]
            },
            AlertType.HIGH_ERROR_RATE: {
                "severity": AlertSeverity.ERROR,
                "threshold_seconds": 300,
                "threshold_value": 5,
                "channels": [AlertChannel.SLACK, AlertChannel.EMAIL]
            }
        }

    async def trigger_alert(
        self,
        alert_type: AlertType,
        message: str,
        component: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Trigger a system alert.

        Args:
            alert_type: Type of alert
            message: Alert message
            component: Affected component
            metadata: Additional alert metadata

        Returns:
            Alert ID

        Since:
            Version 1.0.0
        """
        alert_id = f"{alert_type.value}_{datetime.utcnow().timestamp()}"
        threshold_config = self.alert_thresholds.get(alert_type, {})

        alert = {
            "alert_id": alert_id,
            "alert_type": alert_type.value,
            "severity": threshold_config.get("severity", AlertSeverity.INFO).value,
            "message": message,
            "component": component,
            "triggered_at": datetime.utcnow(),
            "metadata": metadata or {},
            "acknowledged": False
        }

        # Check if alert already exists
        existing_alert_id = self._find_existing_alert(alert_type, component)
        if existing_alert_id:
            # Update existing alert
            self.active_alerts[existing_alert_id]["last_triggered"] = datetime.utcnow()
            self.active_alerts[existing_alert_id]["occurrence_count"] += 1
            return existing_alert_id

        # Store new alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert.copy())

        # Send notifications
        channels = threshold_config.get("channels", [])
        await self._send_notifications(alert, channels)

        logger.warning(
            "Alert triggered",
            alert_id=alert_id,
            alert_type=alert_type.value,
            severity=alert["severity"],
            component=component
        )

        return alert_id

    async def resolve_alert(self, alert_id: str, resolution_message: str):
        """
        Resolve an active alert.

        Args:
            alert_id: Alert identifier
            resolution_message: Resolution description

        Since:
            Version 1.0.0
        """
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert["resolved_at"] = datetime.utcnow()
            alert["resolution_message"] = resolution_message

            # Move to history
            self.alert_history.append(alert)
            del self.active_alerts[alert_id]

            logger.info(
                "Alert resolved",
                alert_id=alert_id,
                resolution_message=resolution_message
            )

    def _find_existing_alert(
        self,
        alert_type: AlertType,
        component: str
    ) -> Optional[str]:
        """
        Find existing alert of same type and component.

        Args:
            alert_type: Alert type
            component: Component name

        Returns:
            Alert ID if found

        Since:
            Version 1.0.0
        """
        for alert_id, alert in self.active_alerts.items():
            if (alert["alert_type"] == alert_type.value and
                alert["component"] == component):
                return alert_id
        return None

    async def _send_notifications(
        self,
        alert: Dict[str, Any],
        channels: List[AlertChannel]
    ):
        """
        Send alert notifications to specified channels.

        Args:
            alert: Alert details
            channels: Notification channels

        Since:
            Version 1.0.0
        """
        tasks = []
        for channel in channels:
            if channel == AlertChannel.EMAIL:
                tasks.append(self._send_email_notification(alert))
            elif channel == AlertChannel.SLACK:
                tasks.append(self._send_slack_notification(alert))
            elif channel == AlertChannel.PAGERDUTY:
                tasks.append(self._send_pagerduty_notification(alert))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_email_notification(self, alert: Dict[str, Any]):
        """
        Send email notification for alert.

        Args:
            alert: Alert details

        Since:
            Version 1.0.0
        """
        try:
            # TODO: Implement actual email sending
            logger.info(
                "Email notification would be sent",
                alert_id=alert["alert_id"],
                severity=alert["severity"]
            )
        except Exception as e:
            logger.error(
                "Failed to send email notification",
                alert_id=alert["alert_id"],
                error=str(e)
            )

    async def _send_slack_notification(self, alert: Dict[str, Any]):
        """
        Send Slack notification for alert.

        Args:
            alert: Alert details

        Since:
            Version 1.0.0
        """
        try:
            # TODO: Implement actual Slack webhook
            webhook_url = ""  # Get from config

            if not webhook_url:
                return

            payload = {
                "text": f"🚨 *{alert['severity'].upper()} Alert*",
                "attachments": [{
                    "color": self._get_severity_color(alert["severity"]),
                    "fields": [
                        {"title": "Type", "value": alert["alert_type"], "short": True},
                        {"title": "Component", "value": alert["component"], "short": True},
                        {"title": "Message", "value": alert["message"], "short": False},
                        {"title": "Time", "value": alert["triggered_at"].isoformat(), "short": True}
                    ]
                }]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status != 200:
                        logger.error("Slack notification failed", status=response.status)

        except Exception as e:
            logger.error(
                "Failed to send Slack notification",
                alert_id=alert["alert_id"],
                error=str(e)
            )

    async def _send_pagerduty_notification(self, alert: Dict[str, Any]):
        """
        Send PagerDuty notification for alert.

        Args:
            alert: Alert details

        Since:
            Version 1.0.0
        """
        try:
            # TODO: Implement actual PagerDuty integration
            logger.info(
                "PagerDuty notification would be sent",
                alert_id=alert["alert_id"],
                severity=alert["severity"]
            )
        except Exception as e:
            logger.error(
                "Failed to send PagerDuty notification",
                alert_id=alert["alert_id"],
                error=str(e)
            )

    def _get_severity_color(self, severity: str) -> str:
        """
        Get color for alert severity.

        Args:
            severity: Alert severity

        Returns:
            Hex color code

        Since:
            Version 1.0.0
        """
        colors = {
            "info": "#36a64f",
            "warning": "#ff9800",
            "error": "#ff5252",
            "critical": "#d32f2f"
        }
        return colors.get(severity, "#808080")

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """
        Get list of active alerts.

        Returns:
            List of active alerts

        Since:
            Version 1.0.0
        """
        return list(self.active_alerts.values())

    def get_alert_history(
        self,
        hours: int = 24,
        alert_type: Optional[AlertType] = None
    ) -> List[Dict[str, Any]]:
        """
        Get alert history.

        Args:
            hours: Hours of history to retrieve
            alert_type: Filter by alert type

        Returns:
            List of historical alerts

        Since:
            Version 1.0.0
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        filtered = [
            alert for alert in self.alert_history
            if alert["triggered_at"] > cutoff
        ]

        if alert_type:
            filtered = [
                alert for alert in filtered
                if alert["alert_type"] == alert_type.value
            ]

        return filtered


# Global alert manager instance
alert_manager = AlertManager()