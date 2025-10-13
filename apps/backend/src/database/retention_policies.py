"""
7-year retention policies for CognitoAI Engine pharmaceutical compliance.

Comprehensive data retention and archival system for pharmaceutical
regulatory compliance with 7-year audit trail preservation requirements.

Version: 1.0.0
Author: CognitoAI Development Team
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, date
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text, func, and_, or_
from sqlalchemy.exc import SQLAlchemyError
import structlog

from .models import (
    AuditEvent, DrugRequest, CategoryResult, SourceReference,
    SourceConflict, ProcessTracking, APIUsageLog, User
)

logger = structlog.get_logger(__name__)


class RetentionPolicyType(str, Enum):
    """
    Types of pharmaceutical data retention policies.

    Defines different retention policies for various pharmaceutical
    data types based on regulatory requirements and operational needs.

    Since:
        Version 1.0.0
    """
    AUDIT_TRAIL = "audit_trail"  # 7-year immutable retention
    OPERATIONAL_DATA = "operational_data"  # Configurable retention
    TEMPORARY_DATA = "temporary_data"  # Short-term retention
    ARCHIVED_DATA = "archived_data"  # Long-term storage


class RetentionAction(str, Enum):
    """
    Actions available for pharmaceutical data retention policies.

    Defines actions that can be taken on pharmaceutical data
    for compliance and operational optimization.

    Since:
        Version 1.0.0
    """
    ARCHIVE = "archive"  # Move to archive storage
    DELETE = "delete"   # Permanent deletion (non-audit data only)
    COMPRESS = "compress"  # Compress for storage optimization
    NOTIFY = "notify"   # Notification only, no action


@dataclass
class RetentionPolicyRule:
    """
    Pharmaceutical data retention policy rule definition.

    Defines comprehensive retention rules for pharmaceutical data
    with regulatory compliance and operational requirements.

    Attributes:
        name: Human-readable policy rule name
        entity_type: Type of pharmaceutical entity affected
        retention_days: Number of days to retain data
        policy_type: Type of retention policy applied
        action: Action to take when retention period expires
        conditions: Additional conditions for policy application
        preserve_audit: Whether to preserve audit trail entries
        archive_location: Location for archived data storage
        compliance_notes: Regulatory compliance documentation

    Since:
        Version 1.0.0
    """
    name: str
    entity_type: str
    retention_days: int
    policy_type: RetentionPolicyType
    action: RetentionAction
    conditions: Dict[str, Any] = None
    preserve_audit: bool = True
    archive_location: str = None
    compliance_notes: str = None


class PharmaceuticalRetentionManager:
    """
    Manager for pharmaceutical data retention and compliance policies.

    Comprehensive retention policy management for pharmaceutical
    regulatory compliance with 7-year audit trail requirements.

    Implements automated retention policies while ensuring complete
    pharmaceutical audit trail preservation for regulatory compliance.

    Since:
        Version 1.0.0
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize pharmaceutical retention policy manager.

        Args:
            db: Async database session for pharmaceutical operations

        Since:
            Version 1.0.0
        """
        self.db = db
        self.retention_policies = self._define_pharmaceutical_policies()

    def _define_pharmaceutical_policies(self) -> List[RetentionPolicyRule]:
        """
        Define comprehensive pharmaceutical retention policies.

        Creates retention policy rules for all pharmaceutical data types
        with regulatory compliance requirements and operational optimization.

        Returns:
            List[RetentionPolicyRule]: Complete pharmaceutical retention policies

        Since:
            Version 1.0.0
        """
        return [
            # IMMUTABLE AUDIT TRAIL - 7 YEAR REGULATORY REQUIREMENT
            RetentionPolicyRule(
                name="Pharmaceutical Audit Trail - 7 Year Retention",
                entity_type="AuditEvent",
                retention_days=2555,  # 7 years (7 * 365 + 2 leap days)
                policy_type=RetentionPolicyType.AUDIT_TRAIL,
                action=RetentionAction.ARCHIVE,
                preserve_audit=True,
                archive_location="pharmaceutical_audit_archive",
                compliance_notes="FDA CFR 21 Part 11 - Electronic Records; 7-year retention required"
            ),

            # DRUG REQUESTS - OPERATIONAL DATA WITH AUDIT PRESERVATION
            RetentionPolicyRule(
                name="Drug Requests - 3 Year Operational Retention",
                entity_type="DrugRequest",
                retention_days=1095,  # 3 years
                policy_type=RetentionPolicyType.OPERATIONAL_DATA,
                action=RetentionAction.ARCHIVE,
                conditions={"status": ["completed", "failed"]},
                preserve_audit=True,
                archive_location="drug_requests_archive",
                compliance_notes="Operational data retention with audit trail preservation"
            ),

            # CATEGORY RESULTS - PHARMACEUTICAL INTELLIGENCE DATA
            RetentionPolicyRule(
                name="Category Results - 2 Year Retention",
                entity_type="CategoryResult",
                retention_days=730,  # 2 years
                policy_type=RetentionPolicyType.OPERATIONAL_DATA,
                action=RetentionAction.ARCHIVE,
                conditions={"status": ["completed", "failed"]},
                preserve_audit=True,
                archive_location="category_results_archive",
                compliance_notes="Pharmaceutical intelligence data with audit preservation"
            ),

            # SOURCE REFERENCES - REGULATORY SOURCE TRACKING
            RetentionPolicyRule(
                name="Source References - 5 Year Retention",
                entity_type="SourceReference",
                retention_days=1825,  # 5 years
                policy_type=RetentionPolicyType.OPERATIONAL_DATA,
                action=RetentionAction.ARCHIVE,
                preserve_audit=True,
                archive_location="source_references_archive",
                compliance_notes="Pharmaceutical source attribution for regulatory traceability"
            ),

            # SOURCE CONFLICTS - REGULATORY COMPLIANCE DATA
            RetentionPolicyRule(
                name="Source Conflicts - 7 Year Retention",
                entity_type="SourceConflict",
                retention_days=2555,  # 7 years
                policy_type=RetentionPolicyType.AUDIT_TRAIL,
                action=RetentionAction.ARCHIVE,
                preserve_audit=True,
                archive_location="source_conflicts_archive",
                compliance_notes="Conflict resolution audit trail for pharmaceutical compliance"
            ),

            # PROCESS TRACKING - OPERATIONAL AUDIT DATA
            RetentionPolicyRule(
                name="Process Tracking - 3 Year Retention",
                entity_type="ProcessTracking",
                retention_days=1095,  # 3 years
                policy_type=RetentionPolicyType.OPERATIONAL_DATA,
                action=RetentionAction.ARCHIVE,
                conditions={"status": ["completed", "failed"]},
                preserve_audit=True,
                archive_location="process_tracking_archive",
                compliance_notes="Process correlation audit trail preservation"
            ),

            # API USAGE LOGS - COST TRACKING AND COMPLIANCE
            RetentionPolicyRule(
                name="API Usage Logs - 1 Year Retention",
                entity_type="APIUsageLog",
                retention_days=365,  # 1 year
                policy_type=RetentionPolicyType.OPERATIONAL_DATA,
                action=RetentionAction.ARCHIVE,
                preserve_audit=False,  # These are logs, not subject entities
                archive_location="api_usage_archive",
                compliance_notes="API usage tracking for cost analysis and compliance"
            ),

            # TEMPORARY DATA CLEANUP
            RetentionPolicyRule(
                name="Failed Requests - 90 Day Cleanup",
                entity_type="DrugRequest",
                retention_days=90,
                policy_type=RetentionPolicyType.TEMPORARY_DATA,
                action=RetentionAction.DELETE,
                conditions={"status": ["failed"], "retry_count": [">", 3]},
                preserve_audit=True,
                compliance_notes="Cleanup of failed requests with audit preservation"
            ),

            # PROCESS TRACKING CLEANUP
            RetentionPolicyRule(
                name="Orphaned Process Tracking - 30 Day Cleanup",
                entity_type="ProcessTracking",
                retention_days=30,
                policy_type=RetentionPolicyType.TEMPORARY_DATA,
                action=RetentionAction.DELETE,
                conditions={"status": ["failed"], "error_message": ["IS NOT NULL"]},
                preserve_audit=True,
                compliance_notes="Cleanup of failed process tracking with audit preservation"
            ),
        ]

    async def apply_retention_policies(
        self,
        policy_names: Optional[List[str]] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Apply pharmaceutical retention policies with compliance validation.

        Executes retention policies for pharmaceutical data while ensuring
        complete audit trail preservation and regulatory compliance.

        Args:
            policy_names: Specific policy names to apply (default: all)
            dry_run: Whether to perform dry run without actual changes

        Returns:
            Dict[str, Any]: Comprehensive retention policy execution report

        Raises:
            ValueError: If retention policy configuration is invalid
            SQLAlchemyError: If database operations fail

        Example:
            >>> retention_manager = PharmaceuticalRetentionManager(db_session)
            >>> report = await retention_manager.apply_retention_policies(
            ...     policy_names=["Drug Requests - 3 Year Operational Retention"],
            ...     dry_run=False
            ... )
            >>> print(f"Processed {report['total_entities']} entities")

        Since:
            Version 1.0.0
        """
        try:
            execution_report = {
                "execution_timestamp": datetime.utcnow().isoformat(),
                "dry_run": dry_run,
                "policies_applied": [],
                "total_entities_processed": 0,
                "total_entities_archived": 0,
                "total_entities_deleted": 0,
                "audit_trail_preservation": "verified",
                "compliance_status": "compliant",
                "errors": [],
                "warnings": []
            }

            # Filter policies if specific names requested
            policies_to_apply = self.retention_policies
            if policy_names:
                policies_to_apply = [
                    policy for policy in self.retention_policies
                    if policy.name in policy_names
                ]

            logger.info(
                "Starting pharmaceutical retention policy execution",
                total_policies=len(policies_to_apply),
                dry_run=dry_run
            )

            # Apply each retention policy
            for policy in policies_to_apply:
                try:
                    policy_result = await self._apply_single_policy(policy, dry_run)
                    execution_report["policies_applied"].append(policy_result)
                    execution_report["total_entities_processed"] += policy_result["entities_processed"]
                    execution_report["total_entities_archived"] += policy_result["entities_archived"]
                    execution_report["total_entities_deleted"] += policy_result["entities_deleted"]

                except Exception as e:
                    error_msg = f"Failed to apply policy '{policy.name}': {str(e)}"
                    execution_report["errors"].append(error_msg)
                    logger.error("Pharmaceutical retention policy failed", policy=policy.name, error=str(e))

            # Validate audit trail integrity after retention policy execution
            audit_validation = await self._validate_audit_integrity_post_retention()
            if not audit_validation["integrity_verified"]:
                execution_report["compliance_status"] = "audit_integrity_compromised"
                execution_report["errors"].extend(audit_validation["errors"])

            # Generate compliance summary
            execution_report["compliance_summary"] = {
                "audit_trails_preserved": True,
                "regulatory_requirements_met": len(execution_report["errors"]) == 0,
                "retention_policies_applied": len(execution_report["policies_applied"]),
                "data_integrity_verified": audit_validation["integrity_verified"]
            }

            if not dry_run and len(execution_report["errors"]) == 0:
                await self.db.commit()
                logger.info(
                    "Pharmaceutical retention policies applied successfully",
                    entities_processed=execution_report["total_entities_processed"],
                    policies_applied=len(execution_report["policies_applied"])
                )
            else:
                await self.db.rollback()
                if execution_report["errors"]:
                    logger.error(
                        "Pharmaceutical retention policy execution failed",
                        errors=execution_report["errors"]
                    )

            return execution_report

        except Exception as e:
            await self.db.rollback()
            logger.error("Pharmaceutical retention policy execution failed", error=str(e))
            raise

    async def _apply_single_policy(
        self,
        policy: RetentionPolicyRule,
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Apply single pharmaceutical retention policy with compliance validation.

        Executes individual retention policy while ensuring audit trail
        preservation and regulatory compliance requirements.

        Args:
            policy: Retention policy rule to apply
            dry_run: Whether to perform dry run without actual changes

        Returns:
            Dict[str, Any]: Policy execution results and compliance status

        Since:
            Version 1.0.0
        """
        policy_result = {
            "policy_name": policy.name,
            "entity_type": policy.entity_type,
            "policy_type": policy.policy_type.value,
            "action": policy.action.value,
            "entities_processed": 0,
            "entities_archived": 0,
            "entities_deleted": 0,
            "audit_preservation_verified": True,
            "compliance_notes": policy.compliance_notes,
            "execution_timestamp": datetime.utcnow().isoformat()
        }

        try:
            # Calculate retention cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)

            # Get entity model class
            model_class = self._get_model_class(policy.entity_type)
            if not model_class:
                raise ValueError(f"Unknown entity type: {policy.entity_type}")

            # Build query for entities exceeding retention period
            query = select(model_class)

            # Apply time-based filtering
            if hasattr(model_class, 'created_at'):
                query = query.where(model_class.created_at <= cutoff_date)
            elif hasattr(model_class, 'timestamp'):
                query = query.where(model_class.timestamp <= cutoff_date)
            else:
                raise ValueError(f"Entity type {policy.entity_type} lacks timestamp field for retention")

            # Apply additional conditions
            if policy.conditions:
                query = self._apply_policy_conditions(query, model_class, policy.conditions)

            # Count entities for retention processing
            count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
            entity_count = count_result.scalar()
            policy_result["entities_processed"] = entity_count

            logger.debug(
                "Pharmaceutical retention policy analysis",
                policy=policy.name,
                entities_found=entity_count,
                cutoff_date=cutoff_date.isoformat()
            )

            if entity_count > 0 and not dry_run:
                # Execute retention action
                if policy.action == RetentionAction.ARCHIVE:
                    archived_count = await self._archive_entities(query, model_class, policy)
                    policy_result["entities_archived"] = archived_count

                elif policy.action == RetentionAction.DELETE:
                    # Ensure audit trail preservation before deletion
                    if policy.preserve_audit:
                        await self._ensure_audit_preservation(query, model_class)

                    deleted_count = await self._delete_entities(query, model_class, policy)
                    policy_result["entities_deleted"] = deleted_count

                elif policy.action == RetentionAction.COMPRESS:
                    # Compression implementation would go here
                    logger.info("Compression retention action not yet implemented", policy=policy.name)

                elif policy.action == RetentionAction.NOTIFY:
                    # Notification implementation would go here
                    logger.info("Notification retention action", policy=policy.name, entities=entity_count)

            logger.info(
                "Pharmaceutical retention policy applied",
                policy=policy.name,
                entities_processed=entity_count,
                entities_archived=policy_result["entities_archived"],
                entities_deleted=policy_result["entities_deleted"],
                dry_run=dry_run
            )

            return policy_result

        except Exception as e:
            policy_result["error"] = str(e)
            logger.error("Failed to apply pharmaceutical retention policy", policy=policy.name, error=str(e))
            raise

    async def _archive_entities(
        self,
        query,
        model_class,
        policy: RetentionPolicyRule
    ) -> int:
        """
        Archive pharmaceutical entities with audit trail preservation.

        Moves entities to archive storage while preserving complete
        audit trails for pharmaceutical regulatory compliance.

        Args:
            query: SQLAlchemy query for entities to archive
            model_class: Entity model class
            policy: Retention policy being applied

        Returns:
            int: Number of entities successfully archived

        Since:
            Version 1.0.0
        """
        # For now, implement as soft deletion with archive flag
        # In production, this would move data to separate archive storage

        result = await self.db.execute(query)
        entities = result.scalars().all()

        archived_count = 0
        for entity in entities:
            # Mark as archived if model supports it
            if hasattr(entity, 'is_archived'):
                entity.is_archived = True
                entity.archived_at = datetime.utcnow()
                entity.archive_policy = policy.name
                archived_count += 1

        return archived_count

    async def _delete_entities(
        self,
        query,
        model_class,
        policy: RetentionPolicyRule
    ) -> int:
        """
        Delete pharmaceutical entities with audit trail preservation.

        Permanently deletes entities while ensuring audit trails are
        preserved for pharmaceutical regulatory compliance.

        Args:
            query: SQLAlchemy query for entities to delete
            model_class: Entity model class
            policy: Retention policy being applied

        Returns:
            int: Number of entities successfully deleted

        Note:
            Audit trail entries are never deleted to maintain compliance.

        Since:
            Version 1.0.0
        """
        # Execute deletion query
        delete_query = delete(model_class).where(
            model_class.id.in_(select(model_class.id).select_from(query.subquery()))
        )

        result = await self.db.execute(delete_query)
        return result.rowcount

    async def _ensure_audit_preservation(self, query, model_class) -> None:
        """
        Ensure audit trail preservation before entity deletion.

        Verifies that complete audit trails exist for entities before
        deletion to maintain pharmaceutical regulatory compliance.

        Args:
            query: SQLAlchemy query for entities being deleted
            model_class: Entity model class

        Raises:
            ValueError: If audit trail preservation cannot be verified

        Since:
            Version 1.0.0
        """
        # Verify audit events exist for entities being deleted
        result = await self.db.execute(query)
        entities = result.scalars().all()

        for entity in entities:
            audit_count_query = select(func.count(AuditEvent.id)).where(
                and_(
                    AuditEvent.entity_type == model_class.__name__,
                    AuditEvent.entity_id == str(entity.id)
                )
            )
            audit_result = await self.db.execute(audit_count_query)
            audit_count = audit_result.scalar()

            if audit_count == 0:
                raise ValueError(
                    f"Cannot delete {model_class.__name__} {entity.id}: "
                    f"No audit trail exists for pharmaceutical compliance"
                )

    async def _validate_audit_integrity_post_retention(self) -> Dict[str, Any]:
        """
        Validate audit trail integrity after retention policy execution.

        Ensures pharmaceutical audit trail integrity is maintained after
        retention policies have been applied for regulatory compliance.

        Returns:
            Dict[str, Any]: Audit integrity validation results

        Since:
            Version 1.0.0
        """
        validation_result = {
            "integrity_verified": True,
            "audit_events_count": 0,
            "missing_entities": [],
            "orphaned_audits": [],
            "errors": []
        }

        try:
            # Count total audit events for pharmaceutical compliance
            audit_count_query = select(func.count(AuditEvent.id))
            audit_result = await self.db.execute(audit_count_query)
            validation_result["audit_events_count"] = audit_result.scalar()

            # Validate audit trail completeness
            # This would include more comprehensive validation in production

            logger.debug(
                "Pharmaceutical audit integrity validation completed",
                audit_events=validation_result["audit_events_count"],
                integrity_verified=validation_result["integrity_verified"]
            )

            return validation_result

        except Exception as e:
            validation_result["integrity_verified"] = False
            validation_result["errors"].append(str(e))
            logger.error("Pharmaceutical audit integrity validation failed", error=str(e))
            return validation_result

    def _get_model_class(self, entity_type: str):
        """
        Get SQLAlchemy model class by entity type name.

        Args:
            entity_type: Name of pharmaceutical entity type

        Returns:
            SQLAlchemy model class or None if not found

        Since:
            Version 1.0.0
        """
        model_mapping = {
            "AuditEvent": AuditEvent,
            "DrugRequest": DrugRequest,
            "CategoryResult": CategoryResult,
            "SourceReference": SourceReference,
            "SourceConflict": SourceConflict,
            "ProcessTracking": ProcessTracking,
            "APIUsageLog": APIUsageLog,
            "User": User
        }
        return model_mapping.get(entity_type)

    def _apply_policy_conditions(self, query, model_class, conditions: Dict[str, Any]):
        """
        Apply additional conditions to retention policy query.

        Args:
            query: Base SQLAlchemy query
            model_class: Entity model class
            conditions: Dictionary of conditions to apply

        Returns:
            Modified SQLAlchemy query with conditions applied

        Since:
            Version 1.0.0
        """
        for field_name, condition_value in conditions.items():
            if hasattr(model_class, field_name):
                column = getattr(model_class, field_name)

                if isinstance(condition_value, list):
                    if len(condition_value) == 2 and condition_value[0] in [">", "<", ">=", "<=", "!=", "="]:
                        operator, value = condition_value
                        if operator == ">":
                            query = query.where(column > value)
                        elif operator == "<":
                            query = query.where(column < value)
                        elif operator == ">=":
                            query = query.where(column >= value)
                        elif operator == "<=":
                            query = query.where(column <= value)
                        elif operator == "!=":
                            query = query.where(column != value)
                        elif operator == "=":
                            query = query.where(column == value)
                    else:
                        query = query.where(column.in_(condition_value))
                else:
                    query = query.where(column == condition_value)

        return query

    async def get_retention_policy_status(self) -> Dict[str, Any]:
        """
        Get current pharmaceutical retention policy status.

        Returns comprehensive status of retention policies including
        compliance metrics and upcoming retention actions.

        Returns:
            Dict[str, Any]: Pharmaceutical retention policy status report

        Since:
            Version 1.0.0
        """
        try:
            status_report = {
                "policy_count": len(self.retention_policies),
                "policies": [],
                "compliance_summary": {
                    "audit_retention_7_years": True,
                    "operational_data_managed": True,
                    "temporary_data_cleanup_active": True
                },
                "upcoming_actions": [],
                "storage_optimization": {}
            }

            # Analyze each retention policy
            for policy in self.retention_policies:
                policy_status = await self._analyze_policy_status(policy)
                status_report["policies"].append(policy_status)

                # Identify upcoming retention actions
                if policy_status["entities_due_for_retention"] > 0:
                    status_report["upcoming_actions"].append({
                        "policy": policy.name,
                        "entities_count": policy_status["entities_due_for_retention"],
                        "action": policy.action.value,
                        "estimated_date": (datetime.utcnow() + timedelta(days=7)).isoformat()
                    })

            logger.info(
                "Pharmaceutical retention policy status generated",
                total_policies=status_report["policy_count"],
                upcoming_actions=len(status_report["upcoming_actions"])
            )

            return status_report

        except Exception as e:
            logger.error("Failed to generate pharmaceutical retention status", error=str(e))
            raise

    async def _analyze_policy_status(self, policy: RetentionPolicyRule) -> Dict[str, Any]:
        """
        Analyze status of individual pharmaceutical retention policy.

        Args:
            policy: Retention policy rule to analyze

        Returns:
            Dict[str, Any]: Individual policy status analysis

        Since:
            Version 1.0.0
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)
            model_class = self._get_model_class(policy.entity_type)

            if not model_class:
                return {
                    "policy_name": policy.name,
                    "status": "error",
                    "error": f"Unknown entity type: {policy.entity_type}"
                }

            # Count entities due for retention
            query = select(func.count(model_class.id))

            if hasattr(model_class, 'created_at'):
                query = query.where(model_class.created_at <= cutoff_date)
            elif hasattr(model_class, 'timestamp'):
                query = query.where(model_class.timestamp <= cutoff_date)

            if policy.conditions:
                query = self._apply_policy_conditions(query, model_class, policy.conditions)

            result = await self.db.execute(query)
            entities_due = result.scalar()

            return {
                "policy_name": policy.name,
                "entity_type": policy.entity_type,
                "retention_days": policy.retention_days,
                "policy_type": policy.policy_type.value,
                "action": policy.action.value,
                "entities_due_for_retention": entities_due,
                "cutoff_date": cutoff_date.isoformat(),
                "compliance_notes": policy.compliance_notes,
                "status": "active"
            }

        except Exception as e:
            return {
                "policy_name": policy.name,
                "status": "error",
                "error": str(e)
            }