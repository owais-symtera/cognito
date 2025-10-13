"""
Epic 7, Story 7.4: Scoring Configuration Management UI
Database-driven scoring configuration management with approval workflows
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import hashlib
from decimal import Decimal

from sqlalchemy import select, func, and_, or_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.session import get_session
from ...database.models import (
    ScoringConfiguration, ScoringWeight, ScoringRule, ScoringThreshold,
    ScoringApproval, ScoringHistory, AuditLog, Alert,
    ChemicalScoringMatrix, PatentScoringMatrix, MarketScoringMatrix,
    TechnologyScore, ConfigurationChange
)
from ...utils.validation import ValidationService
from ...utils.notifications import NotificationService

logger = logging.getLogger(__name__)

class ScoringComponent(Enum):
    """Scoring system components"""
    CHEMICAL_ANALYSIS = "chemical_analysis"
    PATENT_ASSESSMENT = "patent_assessment"
    MARKET_INTELLIGENCE = "market_intelligence"
    TECHNOLOGY_SCORING = "technology_scoring"
    WEIGHTED_DECISION = "weighted_decision"
    THRESHOLD_RULES = "threshold_rules"

class ConfigurationStatus(Enum):
    """Configuration status"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"

class ApprovalLevel(Enum):
    """Approval levels for configuration changes"""
    MINOR_ADJUSTMENT = "minor_adjustment"  # Single approval
    STANDARD_CHANGE = "standard_change"    # Two approvals
    MAJOR_REVISION = "major_revision"      # Three approvals + QA
    CRITICAL_UPDATE = "critical_update"    # Executive + QA + Compliance

@dataclass
class ScoringConfig:
    """Complete scoring configuration"""
    id: str
    name: str
    version: str
    component: ScoringComponent
    weights: Dict[str, float]
    rules: List[Dict[str, Any]]
    thresholds: Dict[str, float]
    metadata: Dict[str, Any]
    status: ConfigurationStatus
    effective_date: datetime
    created_by: str
    approved_by: Optional[List[str]]

@dataclass
class WeightConfiguration:
    """Weight configuration for scoring components"""
    component: str
    factor: str
    weight: float
    min_value: float
    max_value: float
    normalization: str
    description: str

@dataclass
class RuleConfiguration:
    """Rule configuration for scoring"""
    id: str
    name: str
    condition: str
    action: str
    priority: int
    enabled: bool
    parameters: Dict[str, Any]

@dataclass
class ThresholdConfiguration:
    """Threshold configuration for decisions"""
    metric: str
    pass_threshold: float
    fail_threshold: float
    warning_threshold: Optional[float]
    critical_threshold: Optional[float]
    unit: str

class ScoringConfigurationService:
    """Scoring configuration management service"""

    def __init__(self):
        self.validation_service = ValidationService()
        self.notification_service = NotificationService()
        self.configuration_cache = {}
        self.approval_workflows = {}

    async def initialize(self):
        """Initialize scoring configuration service"""
        await self._load_active_configurations()
        logger.info("Scoring configuration service initialized")

    async def get_configurations(
        self,
        component: Optional[ScoringComponent] = None,
        status: Optional[ConfigurationStatus] = None
    ) -> List[ScoringConfig]:
        """Get scoring configurations"""
        async with get_session() as session:
            query = select(ScoringConfiguration)

            if component:
                query = query.where(ScoringConfiguration.component == component.value)

            if status:
                query = query.where(ScoringConfiguration.status == status.value)

            query = query.order_by(desc(ScoringConfiguration.created_at))

            result = await session.execute(query)
            configurations = []

            for config in result.scalars():
                configurations.append(ScoringConfig(
                    id=config.id,
                    name=config.name,
                    version=config.version,
                    component=ScoringComponent(config.component),
                    weights=config.weights or {},
                    rules=config.rules or [],
                    thresholds=config.thresholds or {},
                    metadata=config.metadata or {},
                    status=ConfigurationStatus(config.status),
                    effective_date=config.effective_date,
                    created_by=config.created_by,
                    approved_by=config.approved_by
                ))

            return configurations

    async def get_active_configuration(
        self,
        component: ScoringComponent
    ) -> Optional[ScoringConfig]:
        """Get active configuration for component"""
        if component.value in self.configuration_cache:
            return self.configuration_cache[component.value]

        async with get_session() as session:
            result = await session.execute(
                select(ScoringConfiguration)
                .where(and_(
                    ScoringConfiguration.component == component.value,
                    ScoringConfiguration.status == ConfigurationStatus.ACTIVE.value
                ))
                .order_by(desc(ScoringConfiguration.effective_date))
                .limit(1)
            )
            config = result.scalar_one_or_none()

            if config:
                scoring_config = ScoringConfig(
                    id=config.id,
                    name=config.name,
                    version=config.version,
                    component=ScoringComponent(config.component),
                    weights=config.weights or {},
                    rules=config.rules or [],
                    thresholds=config.thresholds or {},
                    metadata=config.metadata or {},
                    status=ConfigurationStatus(config.status),
                    effective_date=config.effective_date,
                    created_by=config.created_by,
                    approved_by=config.approved_by
                )
                self.configuration_cache[component.value] = scoring_config
                return scoring_config

            return None

    async def create_configuration(
        self,
        component: ScoringComponent,
        name: str,
        weights: Dict[str, float],
        rules: List[Dict[str, Any]],
        thresholds: Dict[str, float],
        created_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create new scoring configuration"""
        async with get_session() as session:
            # Validate configuration
            validation_result = await self._validate_configuration(
                component, weights, rules, thresholds
            )

            if not validation_result['valid']:
                raise ValueError(f"Invalid configuration: {validation_result['errors']}")

            # Generate version
            version = await self._generate_version(component, session)

            # Create configuration
            config = ScoringConfiguration(
                id=hashlib.sha256(f"{component.value}{version}{datetime.utcnow()}".encode()).hexdigest()[:16],
                name=name,
                version=version,
                component=component.value,
                weights=weights,
                rules=rules,
                thresholds=thresholds,
                metadata=metadata or {},
                status=ConfigurationStatus.DRAFT.value,
                created_by=created_by,
                created_at=datetime.utcnow()
            )

            session.add(config)

            # Create audit log
            await self._log_audit(
                action="SCORING_CONFIG_CREATED",
                details={
                    "config_id": config.id,
                    "component": component.value,
                    "version": version
                },
                user=created_by,
                session=session
            )

            await session.commit()
            return config.id

    async def update_configuration(
        self,
        config_id: str,
        updates: Dict[str, Any],
        updated_by: str
    ) -> Dict[str, Any]:
        """Update scoring configuration"""
        async with get_session() as session:
            result = await session.execute(
                select(ScoringConfiguration)
                .where(ScoringConfiguration.id == config_id)
            )
            config = result.scalar_one_or_none()

            if not config:
                raise ValueError(f"Configuration {config_id} not found")

            if config.status == ConfigurationStatus.ACTIVE.value:
                raise ValueError("Cannot modify active configuration directly")

            # Store original for comparison
            original = {
                "weights": config.weights.copy() if config.weights else {},
                "rules": config.rules.copy() if config.rules else [],
                "thresholds": config.thresholds.copy() if config.thresholds else {}
            }

            # Apply updates
            if "weights" in updates:
                config.weights = updates["weights"]
            if "rules" in updates:
                config.rules = updates["rules"]
            if "thresholds" in updates:
                config.thresholds = updates["thresholds"]
            if "name" in updates:
                config.name = updates["name"]

            config.updated_at = datetime.utcnow()
            config.updated_by = updated_by

            # Determine approval level needed
            approval_level = await self._determine_approval_level(
                original, updates, config.component
            )

            # Create configuration change record
            change = ConfigurationChange(
                config_id=config.id,
                change_type="update",
                original_values=original,
                new_values=updates,
                approval_level=approval_level.value,
                created_by=updated_by,
                created_at=datetime.utcnow()
            )
            session.add(change)

            # Log audit
            await self._log_audit(
                action="SCORING_CONFIG_UPDATED",
                details={
                    "config_id": config.id,
                    "changes": updates,
                    "approval_level": approval_level.value
                },
                user=updated_by,
                session=session
            )

            await session.commit()

            return {
                "config_id": config.id,
                "status": "updated",
                "approval_required": approval_level.value,
                "change_id": change.id
            }

    async def submit_for_approval(
        self,
        config_id: str,
        submitted_by: str,
        justification: str
    ) -> str:
        """Submit configuration for approval"""
        async with get_session() as session:
            result = await session.execute(
                select(ScoringConfiguration)
                .where(ScoringConfiguration.id == config_id)
            )
            config = result.scalar_one_or_none()

            if not config:
                raise ValueError(f"Configuration {config_id} not found")

            if config.status != ConfigurationStatus.DRAFT.value:
                raise ValueError(f"Configuration must be in draft status")

            # Get recent changes
            changes_result = await session.execute(
                select(ConfigurationChange)
                .where(ConfigurationChange.config_id == config_id)
                .order_by(desc(ConfigurationChange.created_at))
                .limit(1)
            )
            change = changes_result.scalar_one_or_none()

            approval_level = ApprovalLevel.STANDARD_CHANGE
            if change:
                approval_level = ApprovalLevel(change.approval_level)

            # Create approval workflow
            approval = ScoringApproval(
                id=hashlib.sha256(f"{config_id}{datetime.utcnow()}".encode()).hexdigest()[:16],
                config_id=config_id,
                approval_level=approval_level.value,
                submitted_by=submitted_by,
                justification=justification,
                status="pending",
                required_approvers=await self._get_required_approvers(approval_level),
                created_at=datetime.utcnow()
            )
            session.add(approval)

            # Update configuration status
            config.status = ConfigurationStatus.PENDING_APPROVAL.value

            # Send notifications
            await self.notification_service.notify_approvers(
                approval_type="scoring_configuration",
                config_id=config_id,
                component=config.component,
                approval_level=approval_level.value
            )

            # Log audit
            await self._log_audit(
                action="SCORING_CONFIG_SUBMITTED",
                details={
                    "config_id": config_id,
                    "approval_id": approval.id,
                    "approval_level": approval_level.value
                },
                user=submitted_by,
                session=session
            )

            await session.commit()
            return approval.id

    async def approve_configuration(
        self,
        approval_id: str,
        approver: str,
        comments: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve configuration change"""
        async with get_session() as session:
            result = await session.execute(
                select(ScoringApproval)
                .where(ScoringApproval.id == approval_id)
            )
            approval = result.scalar_one_or_none()

            if not approval:
                raise ValueError(f"Approval {approval_id} not found")

            if approver not in approval.required_approvers:
                raise ValueError(f"User {approver} is not authorized to approve")

            if approver in approval.approved_by:
                raise ValueError(f"User {approver} has already approved")

            # Add approval
            approval.approved_by = approval.approved_by or []
            approval.approved_by.append(approver)
            approval.approval_comments = approval.approval_comments or {}
            approval.approval_comments[approver] = comments or "Approved"
            approval.updated_at = datetime.utcnow()

            # Check if fully approved
            if set(approval.approved_by) >= set(approval.required_approvers):
                approval.status = "approved"
                approval.approved_at = datetime.utcnow()

                # Activate configuration
                await self._activate_configuration(approval.config_id, session)

            # Log audit
            await self._log_audit(
                action="SCORING_CONFIG_APPROVED",
                details={
                    "approval_id": approval_id,
                    "config_id": approval.config_id,
                    "approver": approver,
                    "fully_approved": approval.status == "approved"
                },
                user=approver,
                session=session
            )

            await session.commit()

            return {
                "approval_id": approval_id,
                "status": approval.status,
                "remaining_approvers": list(set(approval.required_approvers) - set(approval.approved_by)),
                "fully_approved": approval.status == "approved"
            }

    async def reject_configuration(
        self,
        approval_id: str,
        rejector: str,
        reason: str
    ) -> Dict[str, Any]:
        """Reject configuration change"""
        async with get_session() as session:
            result = await session.execute(
                select(ScoringApproval)
                .where(ScoringApproval.id == approval_id)
            )
            approval = result.scalar_one_or_none()

            if not approval:
                raise ValueError(f"Approval {approval_id} not found")

            if rejector not in approval.required_approvers:
                raise ValueError(f"User {rejector} is not authorized to reject")

            approval.status = "rejected"
            approval.rejected_by = rejector
            approval.rejection_reason = reason
            approval.rejected_at = datetime.utcnow()

            # Update configuration status
            config_result = await session.execute(
                select(ScoringConfiguration)
                .where(ScoringConfiguration.id == approval.config_id)
            )
            config = config_result.scalar_one()
            config.status = ConfigurationStatus.DRAFT.value

            # Notify submitter
            await self.notification_service.notify_rejection(
                approval_type="scoring_configuration",
                config_id=approval.config_id,
                rejected_by=rejector,
                reason=reason,
                submitted_by=approval.submitted_by
            )

            # Log audit
            await self._log_audit(
                action="SCORING_CONFIG_REJECTED",
                details={
                    "approval_id": approval_id,
                    "config_id": approval.config_id,
                    "rejector": rejector,
                    "reason": reason
                },
                user=rejector,
                session=session
            )

            await session.commit()

            return {
                "approval_id": approval_id,
                "status": "rejected",
                "rejected_by": rejector,
                "reason": reason
            }

    async def get_weight_configurations(
        self,
        component: ScoringComponent
    ) -> List[WeightConfiguration]:
        """Get weight configurations for component"""
        async with get_session() as session:
            if component == ScoringComponent.CHEMICAL_ANALYSIS:
                weights = [
                    WeightConfiguration(
                        component="chemical",
                        factor="molecular_weight",
                        weight=0.25,
                        min_value=100,
                        max_value=1000,
                        normalization="linear",
                        description="Molecular weight scoring factor"
                    ),
                    WeightConfiguration(
                        component="chemical",
                        factor="logp",
                        weight=0.20,
                        min_value=-2,
                        max_value=7,
                        normalization="sigmoid",
                        description="Lipophilicity scoring factor"
                    ),
                    WeightConfiguration(
                        component="chemical",
                        factor="hbd",
                        weight=0.15,
                        min_value=0,
                        max_value=10,
                        normalization="linear",
                        description="Hydrogen bond donors"
                    ),
                    WeightConfiguration(
                        component="chemical",
                        factor="hba",
                        weight=0.15,
                        min_value=0,
                        max_value=15,
                        normalization="linear",
                        description="Hydrogen bond acceptors"
                    ),
                    WeightConfiguration(
                        component="chemical",
                        factor="tpsa",
                        weight=0.25,
                        min_value=0,
                        max_value=200,
                        normalization="linear",
                        description="Topological polar surface area"
                    )
                ]

            elif component == ScoringComponent.TECHNOLOGY_SCORING:
                # Load from database
                result = await session.execute(
                    select(TechnologyScore)
                    .where(TechnologyScore.active == True)
                )
                tech_score = result.scalar_one_or_none()

                if tech_score:
                    weights = [
                        WeightConfiguration(
                            component="technology",
                            factor="dose",
                            weight=tech_score.dose_weight,
                            min_value=0.001,
                            max_value=1000,
                            normalization="logarithmic",
                            description="Dosage scoring weight"
                        ),
                        WeightConfiguration(
                            component="technology",
                            factor="molecular_weight",
                            weight=tech_score.mw_weight,
                            min_value=100,
                            max_value=1500,
                            normalization="linear",
                            description="Molecular weight technology score"
                        ),
                        WeightConfiguration(
                            component="technology",
                            factor="melting_point",
                            weight=tech_score.mp_weight,
                            min_value=-50,
                            max_value=400,
                            normalization="linear",
                            description="Melting point score"
                        ),
                        WeightConfiguration(
                            component="technology",
                            factor="logp",
                            weight=tech_score.logp_weight,
                            min_value=-3,
                            max_value=8,
                            normalization="sigmoid",
                            description="Partition coefficient score"
                        )
                    ]
                else:
                    weights = []

            else:
                weights = []

            return weights

    async def update_weights(
        self,
        config_id: str,
        weight_updates: List[Dict[str, Any]],
        updated_by: str
    ) -> Dict[str, Any]:
        """Update scoring weights"""
        async with get_session() as session:
            result = await session.execute(
                select(ScoringConfiguration)
                .where(ScoringConfiguration.id == config_id)
            )
            config = result.scalar_one_or_none()

            if not config:
                raise ValueError(f"Configuration {config_id} not found")

            # Validate weights sum to 1.0
            total_weight = sum(w.get('weight', 0) for w in weight_updates)
            if abs(total_weight - 1.0) > 0.001:
                raise ValueError(f"Weights must sum to 1.0, got {total_weight}")

            # Update weights
            new_weights = {}
            for update in weight_updates:
                new_weights[update['factor']] = update['weight']

            config.weights = new_weights
            config.updated_at = datetime.utcnow()
            config.updated_by = updated_by

            # Create history entry
            history = ScoringHistory(
                config_id=config.id,
                change_type="weight_update",
                old_values=config.weights,
                new_values=new_weights,
                changed_by=updated_by,
                changed_at=datetime.utcnow()
            )
            session.add(history)

            await session.commit()

            return {
                "config_id": config_id,
                "status": "weights_updated",
                "new_weights": new_weights
            }

    async def get_rules(
        self,
        component: ScoringComponent
    ) -> List[RuleConfiguration]:
        """Get rules for component"""
        async with get_session() as session:
            result = await session.execute(
                select(ScoringRule)
                .where(ScoringRule.component == component.value)
                .order_by(ScoringRule.priority)
            )

            rules = []
            for rule in result.scalars():
                rules.append(RuleConfiguration(
                    id=rule.id,
                    name=rule.name,
                    condition=rule.condition,
                    action=rule.action,
                    priority=rule.priority,
                    enabled=rule.enabled,
                    parameters=rule.parameters or {}
                ))

            return rules

    async def update_rule(
        self,
        rule_id: str,
        updates: Dict[str, Any],
        updated_by: str
    ) -> Dict[str, Any]:
        """Update scoring rule"""
        async with get_session() as session:
            result = await session.execute(
                select(ScoringRule)
                .where(ScoringRule.id == rule_id)
            )
            rule = result.scalar_one_or_none()

            if not rule:
                raise ValueError(f"Rule {rule_id} not found")

            # Apply updates
            if "condition" in updates:
                rule.condition = updates["condition"]
            if "action" in updates:
                rule.action = updates["action"]
            if "priority" in updates:
                rule.priority = updates["priority"]
            if "enabled" in updates:
                rule.enabled = updates["enabled"]
            if "parameters" in updates:
                rule.parameters = updates["parameters"]

            rule.updated_at = datetime.utcnow()
            rule.updated_by = updated_by

            # Log audit
            await self._log_audit(
                action="SCORING_RULE_UPDATED",
                details={
                    "rule_id": rule_id,
                    "updates": updates
                },
                user=updated_by,
                session=session
            )

            await session.commit()

            return {
                "rule_id": rule_id,
                "status": "updated",
                "updates_applied": updates
            }

    async def get_thresholds(
        self,
        component: ScoringComponent
    ) -> List[ThresholdConfiguration]:
        """Get threshold configurations"""
        async with get_session() as session:
            result = await session.execute(
                select(ScoringThreshold)
                .where(ScoringThreshold.component == component.value)
            )

            thresholds = []
            for threshold in result.scalars():
                thresholds.append(ThresholdConfiguration(
                    metric=threshold.metric,
                    pass_threshold=threshold.pass_threshold,
                    fail_threshold=threshold.fail_threshold,
                    warning_threshold=threshold.warning_threshold,
                    critical_threshold=threshold.critical_threshold,
                    unit=threshold.unit
                ))

            return thresholds

    async def update_thresholds(
        self,
        config_id: str,
        threshold_updates: List[Dict[str, Any]],
        updated_by: str
    ) -> Dict[str, Any]:
        """Update scoring thresholds"""
        async with get_session() as session:
            result = await session.execute(
                select(ScoringConfiguration)
                .where(ScoringConfiguration.id == config_id)
            )
            config = result.scalar_one_or_none()

            if not config:
                raise ValueError(f"Configuration {config_id} not found")

            # Validate thresholds
            for update in threshold_updates:
                if update.get('pass_threshold', 0) <= update.get('fail_threshold', 0):
                    raise ValueError("Pass threshold must be higher than fail threshold")

            # Update thresholds
            new_thresholds = {}
            for update in threshold_updates:
                new_thresholds[update['metric']] = {
                    'pass': update['pass_threshold'],
                    'fail': update['fail_threshold'],
                    'warning': update.get('warning_threshold'),
                    'critical': update.get('critical_threshold')
                }

            config.thresholds = new_thresholds
            config.updated_at = datetime.utcnow()
            config.updated_by = updated_by

            # Create history entry
            history = ScoringHistory(
                config_id=config.id,
                change_type="threshold_update",
                old_values=config.thresholds,
                new_values=new_thresholds,
                changed_by=updated_by,
                changed_at=datetime.utcnow()
            )
            session.add(history)

            await session.commit()

            return {
                "config_id": config_id,
                "status": "thresholds_updated",
                "new_thresholds": new_thresholds
            }

    async def test_configuration(
        self,
        config_id: str,
        test_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test configuration with sample data"""
        async with get_session() as session:
            result = await session.execute(
                select(ScoringConfiguration)
                .where(ScoringConfiguration.id == config_id)
            )
            config = result.scalar_one_or_none()

            if not config:
                raise ValueError(f"Configuration {config_id} not found")

            # Apply scoring logic
            scores = {}
            weighted_score = 0

            for factor, value in test_data.items():
                if factor in config.weights:
                    weight = config.weights[factor]
                    # Normalize value (simplified)
                    normalized = min(max(value / 100, 0), 1)
                    score = normalized * weight
                    scores[factor] = score
                    weighted_score += score

            # Apply thresholds
            decision = "pending"
            for metric, thresholds in config.thresholds.items():
                if metric == "overall":
                    if weighted_score >= thresholds['pass']:
                        decision = "pass"
                    elif weighted_score <= thresholds['fail']:
                        decision = "fail"
                    else:
                        decision = "review"

            return {
                "config_id": config_id,
                "test_data": test_data,
                "scores": scores,
                "weighted_score": weighted_score,
                "decision": decision,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def get_configuration_history(
        self,
        config_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get configuration change history"""
        async with get_session() as session:
            result = await session.execute(
                select(ScoringHistory)
                .where(ScoringHistory.config_id == config_id)
                .order_by(desc(ScoringHistory.changed_at))
                .limit(limit)
            )

            history = []
            for entry in result.scalars():
                history.append({
                    "id": entry.id,
                    "change_type": entry.change_type,
                    "old_values": entry.old_values,
                    "new_values": entry.new_values,
                    "changed_by": entry.changed_by,
                    "changed_at": entry.changed_at.isoformat(),
                    "comments": entry.comments
                })

            return history

    async def rollback_configuration(
        self,
        config_id: str,
        history_id: str,
        rolled_back_by: str
    ) -> Dict[str, Any]:
        """Rollback configuration to previous state"""
        async with get_session() as session:
            # Get history entry
            history_result = await session.execute(
                select(ScoringHistory)
                .where(ScoringHistory.id == history_id)
            )
            history = history_result.scalar_one_or_none()

            if not history:
                raise ValueError(f"History entry {history_id} not found")

            # Get configuration
            config_result = await session.execute(
                select(ScoringConfiguration)
                .where(ScoringConfiguration.id == config_id)
            )
            config = config_result.scalar_one()

            # Store current state
            current_state = {
                "weights": config.weights,
                "rules": config.rules,
                "thresholds": config.thresholds
            }

            # Apply rollback
            if history.change_type == "weight_update":
                config.weights = history.old_values
            elif history.change_type == "rule_update":
                config.rules = history.old_values
            elif history.change_type == "threshold_update":
                config.thresholds = history.old_values

            config.updated_at = datetime.utcnow()
            config.updated_by = rolled_back_by

            # Create new history entry for rollback
            rollback_history = ScoringHistory(
                config_id=config.id,
                change_type="rollback",
                old_values=current_state,
                new_values=history.old_values,
                changed_by=rolled_back_by,
                changed_at=datetime.utcnow(),
                comments=f"Rolled back to history entry {history_id}"
            )
            session.add(rollback_history)

            # Log audit
            await self._log_audit(
                action="SCORING_CONFIG_ROLLBACK",
                details={
                    "config_id": config_id,
                    "history_id": history_id,
                    "rollback_type": history.change_type
                },
                user=rolled_back_by,
                session=session
            )

            await session.commit()

            return {
                "config_id": config_id,
                "status": "rolled_back",
                "history_id": history_id,
                "rollback_history_id": rollback_history.id
            }

    async def export_configuration(
        self,
        config_id: str
    ) -> Dict[str, Any]:
        """Export configuration for backup or transfer"""
        async with get_session() as session:
            result = await session.execute(
                select(ScoringConfiguration)
                .where(ScoringConfiguration.id == config_id)
            )
            config = result.scalar_one_or_none()

            if not config:
                raise ValueError(f"Configuration {config_id} not found")

            # Get all related data
            weights_result = await session.execute(
                select(ScoringWeight)
                .where(ScoringWeight.config_id == config_id)
            )

            rules_result = await session.execute(
                select(ScoringRule)
                .where(ScoringRule.component == config.component)
            )

            thresholds_result = await session.execute(
                select(ScoringThreshold)
                .where(ScoringThreshold.component == config.component)
            )

            return {
                "configuration": {
                    "id": config.id,
                    "name": config.name,
                    "version": config.version,
                    "component": config.component,
                    "status": config.status,
                    "created_at": config.created_at.isoformat(),
                    "created_by": config.created_by
                },
                "weights": config.weights,
                "rules": [asdict(RuleConfiguration(
                    id=r.id,
                    name=r.name,
                    condition=r.condition,
                    action=r.action,
                    priority=r.priority,
                    enabled=r.enabled,
                    parameters=r.parameters
                )) for r in rules_result.scalars()],
                "thresholds": config.thresholds,
                "metadata": config.metadata,
                "export_timestamp": datetime.utcnow().isoformat()
            }

    async def import_configuration(
        self,
        import_data: Dict[str, Any],
        imported_by: str
    ) -> str:
        """Import configuration from export"""
        config_data = import_data['configuration']

        # Create new configuration from import
        config_id = await self.create_configuration(
            component=ScoringComponent(config_data['component']),
            name=f"{config_data['name']} (Imported)",
            weights=import_data['weights'],
            rules=import_data['rules'],
            thresholds=import_data['thresholds'],
            created_by=imported_by,
            metadata={
                **import_data.get('metadata', {}),
                "imported_from": config_data['id'],
                "imported_at": datetime.utcnow().isoformat()
            }
        )

        return config_id

    async def _validate_configuration(
        self,
        component: ScoringComponent,
        weights: Dict[str, float],
        rules: List[Dict[str, Any]],
        thresholds: Dict[str, float]
    ) -> Dict[str, Any]:
        """Validate configuration completeness and correctness"""
        errors = []

        # Validate weights sum to 1.0
        if weights:
            total = sum(weights.values())
            if abs(total - 1.0) > 0.001:
                errors.append(f"Weights must sum to 1.0, got {total}")

        # Validate each weight is between 0 and 1
        for factor, weight in weights.items():
            if weight < 0 or weight > 1:
                errors.append(f"Weight for {factor} must be between 0 and 1")

        # Validate thresholds
        for metric, values in thresholds.items():
            if 'pass' in values and 'fail' in values:
                if values['pass'] <= values['fail']:
                    errors.append(f"Pass threshold for {metric} must be higher than fail")

        # Validate rules have required fields
        for rule in rules:
            if not rule.get('condition'):
                errors.append("Rule missing condition")
            if not rule.get('action'):
                errors.append("Rule missing action")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    async def _generate_version(
        self,
        component: ScoringComponent,
        session: AsyncSession
    ) -> str:
        """Generate next version number"""
        result = await session.execute(
            select(func.max(ScoringConfiguration.version))
            .where(ScoringConfiguration.component == component.value)
        )
        latest = result.scalar()

        if latest:
            # Increment version
            parts = latest.split('.')
            parts[-1] = str(int(parts[-1]) + 1)
            return '.'.join(parts)
        else:
            return "1.0.0"

    async def _determine_approval_level(
        self,
        original: Dict[str, Any],
        updates: Dict[str, Any],
        component: str
    ) -> ApprovalLevel:
        """Determine required approval level for changes"""
        # Check magnitude of changes
        major_change = False
        critical_change = False

        if 'weights' in updates:
            # Check if weights changed by more than 20%
            for factor, new_weight in updates['weights'].items():
                old_weight = original['weights'].get(factor, 0)
                if abs(new_weight - old_weight) > 0.2:
                    major_change = True

        if 'thresholds' in updates:
            # Threshold changes are always major
            major_change = True

        # Critical components require higher approval
        if component in ['regulatory_compliance', 'chemical_validation']:
            critical_change = True

        if critical_change:
            return ApprovalLevel.CRITICAL_UPDATE
        elif major_change:
            return ApprovalLevel.MAJOR_REVISION
        else:
            return ApprovalLevel.STANDARD_CHANGE

    async def _get_required_approvers(
        self,
        level: ApprovalLevel
    ) -> List[str]:
        """Get list of required approvers for level"""
        approvers = []

        if level == ApprovalLevel.MINOR_ADJUSTMENT:
            approvers = ["team_lead"]
        elif level == ApprovalLevel.STANDARD_CHANGE:
            approvers = ["team_lead", "manager"]
        elif level == ApprovalLevel.MAJOR_REVISION:
            approvers = ["team_lead", "manager", "director", "qa_lead"]
        elif level == ApprovalLevel.CRITICAL_UPDATE:
            approvers = ["director", "vp_engineering", "qa_lead", "compliance_officer"]

        return approvers

    async def _activate_configuration(
        self,
        config_id: str,
        session: AsyncSession
    ):
        """Activate approved configuration"""
        # Deactivate current active configuration
        result = await session.execute(
            select(ScoringConfiguration)
            .where(ScoringConfiguration.id == config_id)
        )
        config = result.scalar_one()

        # Deactivate existing active config
        await session.execute(
            update(ScoringConfiguration)
            .where(and_(
                ScoringConfiguration.component == config.component,
                ScoringConfiguration.status == ConfigurationStatus.ACTIVE.value
            ))
            .values(status=ConfigurationStatus.DEPRECATED.value)
        )

        # Activate new configuration
        config.status = ConfigurationStatus.ACTIVE.value
        config.effective_date = datetime.utcnow()

        # Clear cache
        if config.component in self.configuration_cache:
            del self.configuration_cache[config.component]

    async def _load_active_configurations(self):
        """Load all active configurations into cache"""
        async with get_session() as session:
            result = await session.execute(
                select(ScoringConfiguration)
                .where(ScoringConfiguration.status == ConfigurationStatus.ACTIVE.value)
            )

            for config in result.scalars():
                scoring_config = ScoringConfig(
                    id=config.id,
                    name=config.name,
                    version=config.version,
                    component=ScoringComponent(config.component),
                    weights=config.weights or {},
                    rules=config.rules or [],
                    thresholds=config.thresholds or {},
                    metadata=config.metadata or {},
                    status=ConfigurationStatus(config.status),
                    effective_date=config.effective_date,
                    created_by=config.created_by,
                    approved_by=config.approved_by
                )
                self.configuration_cache[config.component] = scoring_config

    async def _log_audit(
        self,
        action: str,
        details: Dict[str, Any],
        user: str,
        session: AsyncSession
    ):
        """Log audit trail for configuration changes"""
        audit = AuditLog(
            action=action,
            source=user,
            details=details,
            created_at=datetime.utcnow()
        )
        session.add(audit)