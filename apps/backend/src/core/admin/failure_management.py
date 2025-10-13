"""
Epic 7, Story 7.3: Failure Management & Recovery Tools
Comprehensive failure management with pharmaceutical regulatory audit compliance
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import hashlib
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from ...database.session import get_session
from ...database.models import (
    ProcessingRequest, ProcessStage, ProcessLog, FailureRecord,
    RecoveryAttempt, SystemHealth, AuditLog, Alert,
    ErrorClassification, RootCauseAnalysis, ComplianceLog
)
from ...utils.notifications import NotificationService
from ...utils.encryption import EncryptionService

logger = logging.getLogger(__name__)

class ErrorCategory(Enum):
    """Pharmaceutical-specific error classifications"""
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    DATA_INTEGRITY = "data_integrity"
    CHEMICAL_VALIDATION = "chemical_validation"
    PATENT_CONFLICT = "patent_conflict"
    MARKET_DATA_ISSUE = "market_data_issue"
    API_FAILURE = "api_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CONFIGURATION_ERROR = "configuration_error"
    INTEGRATION_FAILURE = "integration_failure"
    PROCESSING_TIMEOUT = "processing_timeout"

class RecoveryStrategy(Enum):
    """Recovery strategies for different failure types"""
    AUTOMATIC_RETRY = "automatic_retry"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    MANUAL_INTERVENTION = "manual_intervention"
    PARTIAL_REPROCESS = "partial_reprocess"
    FULL_REPROCESS = "full_reprocess"
    SKIP_AND_CONTINUE = "skip_and_continue"
    ESCALATE_TO_ADMIN = "escalate_to_admin"
    ROLLBACK = "rollback"

class ComplianceSeverity(Enum):
    """FDA/regulatory compliance severity levels"""
    CRITICAL_GMP = "critical_gmp"  # Good Manufacturing Practice
    MAJOR_DEVIATION = "major_deviation"
    MINOR_OBSERVATION = "minor_observation"
    DOCUMENTATION_GAP = "documentation_gap"
    AUDIT_FINDING = "audit_finding"

@dataclass
class FailureAnalysis:
    """Comprehensive failure analysis"""
    error_id: str
    category: ErrorCategory
    severity: str
    root_cause: str
    impact_assessment: Dict[str, Any]
    affected_systems: List[str]
    recovery_strategy: RecoveryStrategy
    compliance_impact: Optional[ComplianceSeverity]
    estimated_recovery_time: int  # minutes
    manual_steps_required: List[str]

@dataclass
class RecoveryPlan:
    """Structured recovery plan"""
    failure_id: str
    strategy: RecoveryStrategy
    steps: List[Dict[str, Any]]
    estimated_duration: int  # minutes
    resources_required: List[str]
    compliance_requirements: List[str]
    success_criteria: List[str]
    rollback_procedure: Optional[Dict[str, Any]]

@dataclass
class ComplianceAudit:
    """Pharmaceutical compliance audit record"""
    event_id: str
    event_type: str
    severity: ComplianceSeverity
    regulation_reference: str  # e.g., "21 CFR 211.68"
    description: str
    corrective_action: str
    preventive_action: str
    verification_required: bool
    auditor_approval: Optional[str]

class FailureManagementService:
    """Comprehensive failure management and recovery service"""

    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.notification_service = NotificationService()
        self.encryption_service = EncryptionService()
        self.recovery_executors = {}
        self.failure_patterns = defaultdict(list)
        self.max_retry_attempts = 5
        self.base_retry_delay = 60  # seconds

    async def initialize(self):
        """Initialize failure management service"""
        try:
            self.redis_client = await Redis.from_url(
                "redis://localhost:6379",
                encoding="utf-8",
                decode_responses=True
            )
            await self._load_failure_patterns()
            logger.info("Failure management service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize failure management: {e}")

    async def handle_failure(
        self,
        request_id: str,
        error: Exception,
        stage: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle processing failure with compliance tracking"""
        async with get_session() as session:
            try:
                # Analyze failure
                analysis = await self._analyze_failure(error, stage, context, session)

                # Record failure with audit trail
                failure_id = await self._record_failure(
                    request_id, analysis, session
                )

                # Determine recovery strategy
                recovery_plan = await self._create_recovery_plan(
                    failure_id, analysis, session
                )

                # Check compliance implications
                if analysis.compliance_impact:
                    await self._handle_compliance_failure(
                        failure_id, analysis, session
                    )

                # Execute recovery if automatic
                if recovery_plan.strategy in [
                    RecoveryStrategy.AUTOMATIC_RETRY,
                    RecoveryStrategy.EXPONENTIAL_BACKOFF
                ]:
                    recovery_result = await self._execute_automatic_recovery(
                        recovery_plan, session
                    )
                else:
                    # Queue for manual intervention
                    await self._queue_manual_recovery(recovery_plan, session)
                    recovery_result = {"status": "queued_for_manual_review"}

                # Update failure patterns for trend analysis
                self.failure_patterns[analysis.category].append({
                    "timestamp": datetime.utcnow(),
                    "stage": stage,
                    "root_cause": analysis.root_cause
                })

                return {
                    "failure_id": failure_id,
                    "analysis": asdict(analysis),
                    "recovery_plan": asdict(recovery_plan),
                    "recovery_result": recovery_result
                }

            except Exception as e:
                logger.error(f"Failure handling error: {e}")
                raise

    async def _analyze_failure(
        self,
        error: Exception,
        stage: str,
        context: Dict[str, Any],
        session: AsyncSession
    ) -> FailureAnalysis:
        """Perform comprehensive failure analysis"""
        # Classify error
        category = await self._classify_error(error, context)

        # Determine severity
        severity = await self._determine_severity(category, stage)

        # Root cause analysis
        root_cause = await self._identify_root_cause(error, stage, context, session)

        # Impact assessment
        impact = await self._assess_impact(category, stage, context, session)

        # Identify affected systems
        affected_systems = await self._identify_affected_systems(stage, context)

        # Determine recovery strategy
        strategy = await self._determine_recovery_strategy(
            category, severity, context
        )

        # Check compliance impact
        compliance_impact = None
        if category in [
            ErrorCategory.REGULATORY_COMPLIANCE,
            ErrorCategory.DATA_INTEGRITY,
            ErrorCategory.CHEMICAL_VALIDATION
        ]:
            compliance_impact = await self._assess_compliance_impact(
                category, severity
            )

        # Estimate recovery time
        recovery_time = await self._estimate_recovery_time(strategy, impact)

        # Determine manual steps
        manual_steps = await self._determine_manual_steps(strategy, category)

        return FailureAnalysis(
            error_id=hashlib.sha256(f"{error}{datetime.utcnow()}".encode()).hexdigest()[:16],
            category=category,
            severity=severity,
            root_cause=root_cause,
            impact_assessment=impact,
            affected_systems=affected_systems,
            recovery_strategy=strategy,
            compliance_impact=compliance_impact,
            estimated_recovery_time=recovery_time,
            manual_steps_required=manual_steps
        )

    async def _classify_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> ErrorCategory:
        """Classify error into pharmaceutical-specific categories"""
        error_str = str(error).lower()

        if "compliance" in error_str or "regulation" in error_str:
            return ErrorCategory.REGULATORY_COMPLIANCE
        elif "integrity" in error_str or "validation" in error_str:
            return ErrorCategory.DATA_INTEGRITY
        elif "chemical" in error_str or "compound" in error_str:
            return ErrorCategory.CHEMICAL_VALIDATION
        elif "patent" in error_str:
            return ErrorCategory.PATENT_CONFLICT
        elif "market" in error_str or "pricing" in error_str:
            return ErrorCategory.MARKET_DATA_ISSUE
        elif "api" in error_str or "endpoint" in error_str:
            return ErrorCategory.API_FAILURE
        elif "memory" in error_str or "resource" in error_str:
            return ErrorCategory.RESOURCE_EXHAUSTION
        elif "config" in error_str or "setting" in error_str:
            return ErrorCategory.CONFIGURATION_ERROR
        elif "timeout" in error_str:
            return ErrorCategory.PROCESSING_TIMEOUT
        else:
            return ErrorCategory.INTEGRATION_FAILURE

    async def _determine_severity(
        self,
        category: ErrorCategory,
        stage: str
    ) -> str:
        """Determine failure severity"""
        critical_categories = [
            ErrorCategory.REGULATORY_COMPLIANCE,
            ErrorCategory.DATA_INTEGRITY
        ]

        critical_stages = [
            "chemical_validation",
            "regulatory_check",
            "decision_generation"
        ]

        if category in critical_categories or stage in critical_stages:
            return "critical"
        elif category in [ErrorCategory.CHEMICAL_VALIDATION, ErrorCategory.PATENT_CONFLICT]:
            return "high"
        elif category in [ErrorCategory.API_FAILURE, ErrorCategory.RESOURCE_EXHAUSTION]:
            return "medium"
        else:
            return "low"

    async def _identify_root_cause(
        self,
        error: Exception,
        stage: str,
        context: Dict[str, Any],
        session: AsyncSession
    ) -> str:
        """Perform root cause analysis"""
        # Check recent similar failures
        similar_failures = await session.execute(
            select(FailureRecord)
            .where(and_(
                FailureRecord.stage == stage,
                FailureRecord.created_at >= datetime.utcnow() - timedelta(hours=24)
            ))
            .limit(10)
        )

        patterns = []
        for failure in similar_failures.scalars():
            if failure.root_cause:
                patterns.append(failure.root_cause)

        # Analyze patterns
        if patterns:
            most_common = max(set(patterns), key=patterns.count)
            if patterns.count(most_common) > 3:
                return f"Recurring issue: {most_common}"

        # Default root cause based on error type
        if isinstance(error, TimeoutError):
            return "Processing timeout - possible resource constraint"
        elif isinstance(error, ValueError):
            return "Data validation failure - invalid input format"
        elif isinstance(error, ConnectionError):
            return "Network connectivity issue - external service unavailable"
        else:
            return f"Unclassified error: {type(error).__name__}"

    async def _assess_impact(
        self,
        category: ErrorCategory,
        stage: str,
        context: Dict[str, Any],
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Assess failure impact on pharmaceutical processing"""
        impact = {
            "data_loss": False,
            "compliance_breach": False,
            "processing_delay": 0,  # minutes
            "affected_requests": 0,
            "financial_impact": 0,
            "regulatory_risk": "none"
        }

        # Check for data loss
        if category in [ErrorCategory.DATA_INTEGRITY, ErrorCategory.CHEMICAL_VALIDATION]:
            impact["data_loss"] = True

        # Check compliance breach
        if category == ErrorCategory.REGULATORY_COMPLIANCE:
            impact["compliance_breach"] = True
            impact["regulatory_risk"] = "high"

        # Estimate processing delay
        if stage in ["chemical_extraction", "patent_analysis"]:
            impact["processing_delay"] = 30  # Critical stages take longer
        else:
            impact["processing_delay"] = 10

        # Count affected requests
        affected = await session.scalar(
            select(func.count(ProcessingRequest.id))
            .where(and_(
                ProcessingRequest.status == "processing",
                ProcessingRequest.last_stage == stage
            ))
        )
        impact["affected_requests"] = affected or 0

        return impact

    async def _determine_recovery_strategy(
        self,
        category: ErrorCategory,
        severity: str,
        context: Dict[str, Any]
    ) -> RecoveryStrategy:
        """Determine appropriate recovery strategy"""
        if severity == "critical":
            return RecoveryStrategy.MANUAL_INTERVENTION

        strategy_map = {
            ErrorCategory.API_FAILURE: RecoveryStrategy.EXPONENTIAL_BACKOFF,
            ErrorCategory.PROCESSING_TIMEOUT: RecoveryStrategy.AUTOMATIC_RETRY,
            ErrorCategory.RESOURCE_EXHAUSTION: RecoveryStrategy.EXPONENTIAL_BACKOFF,
            ErrorCategory.CONFIGURATION_ERROR: RecoveryStrategy.MANUAL_INTERVENTION,
            ErrorCategory.DATA_INTEGRITY: RecoveryStrategy.FULL_REPROCESS,
            ErrorCategory.CHEMICAL_VALIDATION: RecoveryStrategy.PARTIAL_REPROCESS,
            ErrorCategory.REGULATORY_COMPLIANCE: RecoveryStrategy.ESCALATE_TO_ADMIN
        }

        return strategy_map.get(category, RecoveryStrategy.MANUAL_INTERVENTION)

    async def _record_failure(
        self,
        request_id: str,
        analysis: FailureAnalysis,
        session: AsyncSession
    ) -> str:
        """Record failure with complete audit trail"""
        failure = FailureRecord(
            id=analysis.error_id,
            request_id=request_id,
            category=analysis.category.value,
            severity=analysis.severity,
            root_cause=analysis.root_cause,
            impact_assessment=analysis.impact_assessment,
            affected_systems=analysis.affected_systems,
            recovery_strategy=analysis.recovery_strategy.value,
            compliance_impact=analysis.compliance_impact.value if analysis.compliance_impact else None,
            created_at=datetime.utcnow(),
            created_by="system"
        )

        session.add(failure)

        # Create audit log for pharmaceutical compliance
        audit = AuditLog(
            action="FAILURE_RECORDED",
            source="failure_management",
            request_id=request_id,
            details={
                "failure_id": failure.id,
                "category": analysis.category.value,
                "severity": analysis.severity,
                "compliance_impact": analysis.compliance_impact.value if analysis.compliance_impact else None
            },
            created_at=datetime.utcnow()
        )
        session.add(audit)

        await session.commit()
        return failure.id

    async def _create_recovery_plan(
        self,
        failure_id: str,
        analysis: FailureAnalysis,
        session: AsyncSession
    ) -> RecoveryPlan:
        """Create detailed recovery plan"""
        steps = []
        resources = []
        compliance_reqs = []

        if analysis.recovery_strategy == RecoveryStrategy.AUTOMATIC_RETRY:
            steps = [
                {"step": 1, "action": "validate_system_resources", "automated": True},
                {"step": 2, "action": "reset_processing_state", "automated": True},
                {"step": 3, "action": "retry_failed_operation", "automated": True},
                {"step": 4, "action": "verify_success", "automated": True}
            ]
            resources = ["processing_queue", "worker_pool"]

        elif analysis.recovery_strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
            steps = [
                {"step": 1, "action": "calculate_backoff_delay", "automated": True},
                {"step": 2, "action": "queue_retry_with_delay", "automated": True},
                {"step": 3, "action": "monitor_retry_attempts", "automated": True}
            ]
            resources = ["retry_scheduler", "monitoring_service"]

        elif analysis.recovery_strategy == RecoveryStrategy.MANUAL_INTERVENTION:
            steps = [
                {"step": 1, "action": "notify_operations_team", "automated": True},
                {"step": 2, "action": "await_manual_review", "automated": False},
                {"step": 3, "action": "apply_manual_fix", "automated": False},
                {"step": 4, "action": "validate_fix", "automated": False},
                {"step": 5, "action": "resume_processing", "automated": False}
            ]
            resources = ["operations_team", "subject_matter_expert"]
            compliance_reqs = ["document_manual_intervention", "obtain_approval"]

        elif analysis.recovery_strategy == RecoveryStrategy.FULL_REPROCESS:
            steps = [
                {"step": 1, "action": "rollback_partial_changes", "automated": True},
                {"step": 2, "action": "reset_to_initial_state", "automated": True},
                {"step": 3, "action": "requeue_for_processing", "automated": True}
            ]
            resources = ["rollback_service", "processing_queue"]

        # Add compliance requirements for pharmaceutical operations
        if analysis.compliance_impact:
            compliance_reqs.extend([
                "create_deviation_report",
                "document_corrective_action",
                "obtain_qa_approval",
                "update_batch_record"
            ])

        # Define success criteria
        success_criteria = [
            "processing_completed_successfully",
            "data_integrity_verified",
            "audit_trail_complete"
        ]

        if analysis.compliance_impact:
            success_criteria.append("compliance_requirements_met")

        return RecoveryPlan(
            failure_id=failure_id,
            strategy=analysis.recovery_strategy,
            steps=steps,
            estimated_duration=analysis.estimated_recovery_time,
            resources_required=resources,
            compliance_requirements=compliance_reqs,
            success_criteria=success_criteria,
            rollback_procedure={
                "enabled": True,
                "trigger": "recovery_failure",
                "actions": ["restore_previous_state", "notify_admin"]
            } if analysis.recovery_strategy != RecoveryStrategy.SKIP_AND_CONTINUE else None
        )

    async def execute_recovery(
        self,
        recovery_id: str,
        executor: str,
        override_strategy: Optional[RecoveryStrategy] = None
    ) -> Dict[str, Any]:
        """Execute recovery plan with audit trail"""
        async with get_session() as session:
            # Get recovery attempt
            result = await session.execute(
                select(RecoveryAttempt)
                .where(RecoveryAttempt.id == recovery_id)
            )
            attempt = result.scalar_one_or_none()

            if not attempt:
                raise ValueError(f"Recovery attempt {recovery_id} not found")

            # Override strategy if requested
            if override_strategy:
                attempt.strategy = override_strategy.value

            # Execute based on strategy
            attempt.started_at = datetime.utcnow()
            attempt.executed_by = executor

            try:
                if attempt.strategy == RecoveryStrategy.AUTOMATIC_RETRY.value:
                    result = await self._execute_retry(attempt, session)
                elif attempt.strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF.value:
                    result = await self._execute_backoff_retry(attempt, session)
                elif attempt.strategy == RecoveryStrategy.PARTIAL_REPROCESS.value:
                    result = await self._execute_partial_reprocess(attempt, session)
                elif attempt.strategy == RecoveryStrategy.FULL_REPROCESS.value:
                    result = await self._execute_full_reprocess(attempt, session)
                else:
                    result = {"status": "manual_intervention_required"}

                attempt.completed_at = datetime.utcnow()
                attempt.success = result.get("status") == "success"
                attempt.result = result

                # Log audit trail
                await self._log_recovery_audit(
                    attempt, executor, result, session
                )

                await session.commit()
                return result

            except Exception as e:
                attempt.error_message = str(e)
                attempt.success = False
                await session.commit()
                raise

    async def _execute_retry(
        self,
        attempt: RecoveryAttempt,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Execute simple retry recovery"""
        # Get original request
        result = await session.execute(
            select(ProcessingRequest)
            .where(ProcessingRequest.id == attempt.request_id)
        )
        request = result.scalar_one()

        # Reset status
        request.status = "queued"
        request.retry_count += 1
        request.error_message = None

        # Queue for reprocessing
        if self.redis_client:
            await self.redis_client.rpush(
                f"retry_queue:{request.last_stage}",
                json.dumps({
                    "request_id": request.id,
                    "attempt": request.retry_count
                })
            )

        return {
            "status": "success",
            "action": "requeued_for_processing",
            "retry_count": request.retry_count
        }

    async def _execute_backoff_retry(
        self,
        attempt: RecoveryAttempt,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Execute exponential backoff retry"""
        retry_count = attempt.retry_count or 0
        delay = self.base_retry_delay * (2 ** retry_count)
        max_delay = 3600  # 1 hour maximum

        delay = min(delay, max_delay)

        # Schedule retry
        if self.redis_client:
            await self.redis_client.zadd(
                "scheduled_retries",
                {attempt.request_id: time.time() + delay}
            )

        return {
            "status": "scheduled",
            "delay_seconds": delay,
            "retry_count": retry_count + 1,
            "scheduled_time": (datetime.utcnow() + timedelta(seconds=delay)).isoformat()
        }

    async def _execute_partial_reprocess(
        self,
        attempt: RecoveryAttempt,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Execute partial reprocessing from failed stage"""
        # Identify failed stage
        result = await session.execute(
            select(ProcessStage)
            .where(and_(
                ProcessStage.request_id == attempt.request_id,
                ProcessStage.status == "failed"
            ))
            .order_by(desc(ProcessStage.started_at))
            .limit(1)
        )
        failed_stage = result.scalar_one_or_none()

        if not failed_stage:
            return {"status": "error", "message": "No failed stage found"}

        # Reset stage and subsequent stages
        await session.execute(
            update(ProcessStage)
            .where(and_(
                ProcessStage.request_id == attempt.request_id,
                ProcessStage.sequence >= failed_stage.sequence
            ))
            .values(
                status="pending",
                error_message=None,
                completed_at=None
            )
        )

        # Requeue from failed stage
        if self.redis_client:
            await self.redis_client.rpush(
                f"stage_queue:{failed_stage.stage_name}",
                attempt.request_id
            )

        return {
            "status": "success",
            "action": "partial_reprocess",
            "restarted_from": failed_stage.stage_name
        }

    async def _execute_full_reprocess(
        self,
        attempt: RecoveryAttempt,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Execute full reprocessing from beginning"""
        # Reset all stages
        await session.execute(
            update(ProcessStage)
            .where(ProcessStage.request_id == attempt.request_id)
            .values(
                status="pending",
                started_at=None,
                completed_at=None,
                error_message=None,
                duration_seconds=None
            )
        )

        # Reset request
        await session.execute(
            update(ProcessingRequest)
            .where(ProcessingRequest.id == attempt.request_id)
            .values(
                status="queued",
                last_stage="initialization",
                error_message=None,
                processing_time_seconds=None
            )
        )

        # Queue for full reprocessing
        if self.redis_client:
            await self.redis_client.rpush(
                "processing_queue:high_priority",
                attempt.request_id
            )

        return {
            "status": "success",
            "action": "full_reprocess",
            "message": "Request queued for complete reprocessing"
        }

    async def get_failure_trends(
        self,
        timeframe_hours: int = 24
    ) -> Dict[str, Any]:
        """Analyze failure trends for systemic issues"""
        async with get_session() as session:
            cutoff = datetime.utcnow() - timedelta(hours=timeframe_hours)

            # Get failure counts by category
            category_counts = await session.execute(
                select(
                    FailureRecord.category,
                    func.count(FailureRecord.id).label('count')
                )
                .where(FailureRecord.created_at >= cutoff)
                .group_by(FailureRecord.category)
            )

            # Get failure counts by stage
            stage_counts = await session.execute(
                select(
                    ProcessStage.stage_name,
                    func.count(ProcessStage.id).label('count')
                )
                .where(and_(
                    ProcessStage.status == "failed",
                    ProcessStage.started_at >= cutoff
                ))
                .group_by(ProcessStage.stage_name)
            )

            # Identify trending issues
            trends = []
            for category, patterns in self.failure_patterns.items():
                recent = [p for p in patterns if p['timestamp'] >= cutoff]
                if len(recent) > 5:  # Threshold for trend
                    trends.append({
                        "category": category.value,
                        "count": len(recent),
                        "common_cause": max(set(p['root_cause'] for p in recent),
                                           key=lambda x: sum(1 for p in recent if p['root_cause'] == x))
                    })

            return {
                "timeframe_hours": timeframe_hours,
                "by_category": {row.category: row.count for row in category_counts},
                "by_stage": {row.stage_name: row.count for row in stage_counts},
                "trending_issues": trends,
                "recommendations": await self._generate_recommendations(trends)
            }

    async def _generate_recommendations(
        self,
        trends: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on failure trends"""
        recommendations = []

        for trend in trends:
            if trend['category'] == ErrorCategory.RESOURCE_EXHAUSTION.value:
                recommendations.append("Consider scaling up processing resources")
            elif trend['category'] == ErrorCategory.API_FAILURE.value:
                recommendations.append("Review external API reliability and implement circuit breakers")
            elif trend['category'] == ErrorCategory.DATA_INTEGRITY.value:
                recommendations.append("Enhance data validation at ingestion stage")
            elif trend['category'] == ErrorCategory.CONFIGURATION_ERROR.value:
                recommendations.append("Review and validate configuration settings")

        return recommendations

    async def generate_failure_report(
        self,
        start_date: datetime,
        end_date: datetime,
        include_compliance: bool = True
    ) -> Dict[str, Any]:
        """Generate comprehensive failure report with compliance documentation"""
        async with get_session() as session:
            # Get all failures in timeframe
            failures = await session.execute(
                select(FailureRecord)
                .where(and_(
                    FailureRecord.created_at >= start_date,
                    FailureRecord.created_at <= end_date
                ))
            )

            # Analyze by category
            category_analysis = defaultdict(lambda: {
                "count": 0,
                "avg_recovery_time": 0,
                "success_rate": 0
            })

            for failure in failures.scalars():
                cat = category_analysis[failure.category]
                cat["count"] += 1

            # Get recovery statistics
            recovery_stats = await session.execute(
                select(
                    RecoveryAttempt.strategy,
                    func.count(RecoveryAttempt.id).label('attempts'),
                    func.sum(func.cast(RecoveryAttempt.success, type_=int)).label('successes')
                )
                .where(and_(
                    RecoveryAttempt.started_at >= start_date,
                    RecoveryAttempt.started_at <= end_date
                ))
                .group_by(RecoveryAttempt.strategy)
            )

            # Compliance section
            compliance_section = {}
            if include_compliance:
                compliance_events = await session.execute(
                    select(ComplianceLog)
                    .where(and_(
                        ComplianceLog.event_type == "failure_related",
                        ComplianceLog.created_at >= start_date,
                        ComplianceLog.created_at <= end_date
                    ))
                )

                compliance_section = {
                    "total_compliance_events": len(list(compliance_events.scalars())),
                    "critical_deviations": 0,
                    "corrective_actions": [],
                    "preventive_actions": []
                }

            return {
                "report_period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "summary": {
                    "total_failures": sum(c["count"] for c in category_analysis.values()),
                    "categories": dict(category_analysis)
                },
                "recovery_performance": [
                    {
                        "strategy": row.strategy,
                        "attempts": row.attempts,
                        "success_rate": (row.successes / row.attempts * 100) if row.attempts > 0 else 0
                    }
                    for row in recovery_stats
                ],
                "compliance": compliance_section if include_compliance else None,
                "generated_at": datetime.utcnow().isoformat(),
                "generated_by": "failure_management_service"
            }

    async def _handle_compliance_failure(
        self,
        failure_id: str,
        analysis: FailureAnalysis,
        session: AsyncSession
    ):
        """Handle failures with compliance implications"""
        # Create compliance event
        compliance_log = ComplianceLog(
            event_type="failure_related",
            severity=analysis.compliance_impact.value,
            regulation_reference=self._get_regulation_reference(analysis.category),
            description=f"Failure {failure_id}: {analysis.root_cause}",
            corrective_action="Automated recovery initiated",
            preventive_action="System monitoring enhanced",
            created_at=datetime.utcnow(),
            created_by="system"
        )
        session.add(compliance_log)

        # Create alert for QA team
        alert = Alert(
            severity="high",
            category="COMPLIANCE",
            message=f"Compliance-impacting failure detected: {analysis.category.value}",
            source="failure_management",
            metadata={
                "failure_id": failure_id,
                "compliance_severity": analysis.compliance_impact.value,
                "regulation": compliance_log.regulation_reference
            },
            created_at=datetime.utcnow()
        )
        session.add(alert)

        # Notify compliance team
        await self.notification_service.notify_compliance_team(
            event_type="failure",
            severity=analysis.compliance_impact.value,
            details={
                "failure_id": failure_id,
                "category": analysis.category.value,
                "impact": analysis.impact_assessment
            }
        )

    def _get_regulation_reference(self, category: ErrorCategory) -> str:
        """Get FDA regulation reference for error category"""
        regulation_map = {
            ErrorCategory.REGULATORY_COMPLIANCE: "21 CFR Part 11",
            ErrorCategory.DATA_INTEGRITY: "21 CFR 211.68",
            ErrorCategory.CHEMICAL_VALIDATION: "21 CFR 211.165",
            ErrorCategory.PATENT_CONFLICT: "35 U.S.C. 271",
            ErrorCategory.MARKET_DATA_ISSUE: "21 CFR 314.81"
        }
        return regulation_map.get(category, "21 CFR 211.22")

    async def _identify_affected_systems(
        self,
        stage: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """Identify systems affected by failure"""
        stage_dependencies = {
            "document_ingestion": ["storage_service", "ocr_service"],
            "chemical_extraction": ["chemistry_service", "validation_service"],
            "patent_analysis": ["patent_database", "legal_service"],
            "market_intelligence": ["market_data_api", "pricing_service"],
            "decision_generation": ["llm_service", "rule_engine"],
            "report_generation": ["template_service", "pdf_generator"]
        }
        return stage_dependencies.get(stage, ["unknown"])

    async def _assess_compliance_impact(
        self,
        category: ErrorCategory,
        severity: str
    ) -> ComplianceSeverity:
        """Assess pharmaceutical compliance impact"""
        if category == ErrorCategory.REGULATORY_COMPLIANCE:
            if severity == "critical":
                return ComplianceSeverity.CRITICAL_GMP
            else:
                return ComplianceSeverity.MAJOR_DEVIATION

        elif category == ErrorCategory.DATA_INTEGRITY:
            if severity in ["critical", "high"]:
                return ComplianceSeverity.MAJOR_DEVIATION
            else:
                return ComplianceSeverity.MINOR_OBSERVATION

        elif category == ErrorCategory.CHEMICAL_VALIDATION:
            return ComplianceSeverity.AUDIT_FINDING

        else:
            return ComplianceSeverity.DOCUMENTATION_GAP

    async def _estimate_recovery_time(
        self,
        strategy: RecoveryStrategy,
        impact: Dict[str, Any]
    ) -> int:
        """Estimate recovery time in minutes"""
        base_times = {
            RecoveryStrategy.AUTOMATIC_RETRY: 5,
            RecoveryStrategy.EXPONENTIAL_BACKOFF: 15,
            RecoveryStrategy.MANUAL_INTERVENTION: 60,
            RecoveryStrategy.PARTIAL_REPROCESS: 20,
            RecoveryStrategy.FULL_REPROCESS: 45,
            RecoveryStrategy.SKIP_AND_CONTINUE: 1,
            RecoveryStrategy.ESCALATE_TO_ADMIN: 120,
            RecoveryStrategy.ROLLBACK: 30
        }

        base = base_times.get(strategy, 30)

        # Adjust based on impact
        if impact.get("compliance_breach"):
            base *= 2
        if impact.get("affected_requests", 0) > 10:
            base *= 1.5

        return int(base)

    async def _determine_manual_steps(
        self,
        strategy: RecoveryStrategy,
        category: ErrorCategory
    ) -> List[str]:
        """Determine required manual intervention steps"""
        steps = []

        if strategy == RecoveryStrategy.MANUAL_INTERVENTION:
            steps = [
                "Review error details and logs",
                "Identify root cause",
                "Apply manual fix or configuration change",
                "Validate fix in test environment",
                "Deploy fix to production",
                "Verify recovery success"
            ]

        if category == ErrorCategory.REGULATORY_COMPLIANCE:
            steps.extend([
                "Document deviation in quality system",
                "Obtain QA approval for recovery",
                "Update batch records if applicable"
            ])

        return steps

    async def _execute_automatic_recovery(
        self,
        plan: RecoveryPlan,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Execute automatic recovery based on plan"""
        attempt = RecoveryAttempt(
            failure_id=plan.failure_id,
            strategy=plan.strategy.value,
            started_at=datetime.utcnow(),
            executed_by="system_automatic"
        )
        session.add(attempt)

        try:
            if plan.strategy == RecoveryStrategy.AUTOMATIC_RETRY:
                result = await self._execute_retry(attempt, session)
            elif plan.strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
                result = await self._execute_backoff_retry(attempt, session)
            else:
                result = {"status": "unsupported_automatic_strategy"}

            attempt.completed_at = datetime.utcnow()
            attempt.success = result.get("status") == "success"
            attempt.result = result

            await session.commit()
            return result

        except Exception as e:
            attempt.error_message = str(e)
            attempt.success = False
            await session.commit()
            return {"status": "failed", "error": str(e)}

    async def _queue_manual_recovery(
        self,
        plan: RecoveryPlan,
        session: AsyncSession
    ):
        """Queue recovery for manual intervention"""
        # Create recovery attempt record
        attempt = RecoveryAttempt(
            failure_id=plan.failure_id,
            strategy=plan.strategy.value,
            queued_at=datetime.utcnow(),
            status="awaiting_manual_intervention"
        )
        session.add(attempt)

        # Create alert for operations team
        alert = Alert(
            severity="high",
            category="RECOVERY",
            message=f"Manual intervention required for failure {plan.failure_id}",
            source="failure_management",
            metadata={
                "recovery_plan": asdict(plan),
                "priority": "high"
            },
            created_at=datetime.utcnow()
        )
        session.add(alert)

        await session.commit()

    async def _log_recovery_audit(
        self,
        attempt: RecoveryAttempt,
        executor: str,
        result: Dict[str, Any],
        session: AsyncSession
    ):
        """Log recovery attempt for audit trail"""
        audit = AuditLog(
            action="RECOVERY_EXECUTED",
            source=executor,
            request_id=attempt.request_id,
            details={
                "attempt_id": attempt.id,
                "strategy": attempt.strategy,
                "success": attempt.success,
                "result": result,
                "duration_seconds": (
                    attempt.completed_at - attempt.started_at
                ).total_seconds() if attempt.completed_at else None
            },
            created_at=datetime.utcnow()
        )
        session.add(audit)

    async def _load_failure_patterns(self):
        """Load historical failure patterns for analysis"""
        async with get_session() as session:
            # Load recent failure patterns
            recent = datetime.utcnow() - timedelta(days=7)
            failures = await session.execute(
                select(FailureRecord)
                .where(FailureRecord.created_at >= recent)
            )

            for failure in failures.scalars():
                self.failure_patterns[ErrorCategory(failure.category)].append({
                    "timestamp": failure.created_at,
                    "stage": failure.stage,
                    "root_cause": failure.root_cause
                })

    async def predict_failures(self) -> List[Dict[str, Any]]:
        """Predict potential failures based on patterns"""
        predictions = []

        for category, patterns in self.failure_patterns.items():
            if len(patterns) > 10:
                # Simple frequency-based prediction
                recent_hour = [p for p in patterns
                             if p['timestamp'] >= datetime.utcnow() - timedelta(hours=1)]

                if len(recent_hour) > 3:
                    predictions.append({
                        "category": category.value,
                        "likelihood": "high",
                        "expected_in_minutes": 30,
                        "recommended_action": "Scale resources or review configuration"
                    })

        return predictions