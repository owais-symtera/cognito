"""
Story 4.2: Prompt Template Management System
Advanced prompt template management with pharmaceutical domain optimization
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib
from pydantic import BaseModel, Field, validator
import logging
from dataclasses import dataclass, field
import difflib
from abc import ABC, abstractmethod
import statistics

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Template approval workflow states"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


class TemplateType(Enum):
    """Types of prompt templates"""
    CATEGORY = "category"           # Category-specific prompts
    EXTRACTION = "extraction"        # Data extraction prompts
    VALIDATION = "validation"        # Data validation prompts
    SYNTHESIS = "synthesis"          # Information synthesis prompts
    DECISION = "decision"            # Decision-making prompts
    SUMMARY = "summary"              # Summary generation prompts


@dataclass
class TemplateVersion:
    """Represents a version of a prompt template"""
    version_number: str
    template_content: str
    created_by: str
    created_at: datetime
    modified_by: Optional[str] = None
    modified_at: Optional[datetime] = None
    change_description: str = ""
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    test_results: Dict[str, Any] = field(default_factory=dict)
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)


class PromptTemplate(BaseModel):
    """Main prompt template model with versioning"""
    template_id: str
    name: str
    description: str
    category: str
    template_type: TemplateType
    current_version: str
    versions: Dict[str, TemplateVersion] = Field(default_factory=dict)
    parent_template_id: Optional[str] = None  # For inheritance
    customizations: Dict[str, Any] = Field(default_factory=dict)
    validation_rules: List[str] = Field(default_factory=list)
    required_parameters: List[str] = Field(default_factory=list)
    optional_parameters: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)
    active_ab_tests: List[str] = Field(default_factory=list)
    is_active: bool = True

    @validator('current_version')
    def version_exists(cls, v, values):
        """Ensure current version exists in versions dict"""
        if 'versions' in values and v not in values['versions']:
            raise ValueError(f"Current version {v} not found in versions")
        return v


class ABTestConfig(BaseModel):
    """Configuration for A/B testing templates"""
    test_id: str
    template_a_id: str
    template_a_version: str
    template_b_id: str
    template_b_version: str
    category: str
    start_date: datetime
    end_date: Optional[datetime] = None
    sample_size: int = 100
    success_metrics: List[str]
    current_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    is_active: bool = True
    winner: Optional[str] = None
    confidence_level: float = 0.95
    minimum_difference: float = 0.05  # 5% minimum difference to declare winner


class TemplatePerformanceMetrics(BaseModel):
    """Performance metrics for a template"""
    template_id: str
    version: str
    total_uses: int = 0
    successful_uses: int = 0
    failed_uses: int = 0
    average_quality_score: float = 0.0
    average_processing_time: float = 0.0
    data_completeness_rate: float = 0.0
    parameter_satisfaction_rate: float = 0.0
    user_satisfaction_score: Optional[float] = None
    error_rate: float = 0.0
    last_used: Optional[datetime] = None
    pharmaceutical_accuracy_metrics: Dict[str, float] = Field(default_factory=dict)


class TemplateValidator(ABC):
    """Abstract base class for template validators"""

    @abstractmethod
    def validate(self, template_content: str, parameters: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate template content and parameters"""
        pass


class PharmaceuticalTemplateValidator(TemplateValidator):
    """Pharmaceutical-specific template validator"""

    def __init__(self):
        self.required_sections = [
            'objective',
            'scope',
            'data_requirements',
            'regulatory_context'
        ]
        self.forbidden_terms = [
            'guarantee',
            'cure',
            'safe',
            'no risk'
        ]
        self.required_disclaimers = [
            'medical_disclaimer',
            'data_currency',
            'source_reliability'
        ]

    def validate(self, template_content: str, parameters: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate pharmaceutical template content"""
        issues = []

        # Check for required sections
        for section in self.required_sections:
            if section not in template_content.lower():
                issues.append(f"Missing required section: {section}")

        # Check for forbidden terms
        for term in self.forbidden_terms:
            if term in template_content.lower():
                issues.append(f"Contains forbidden term: {term}")

        # Check parameter placeholders
        placeholders = self._extract_placeholders(template_content)
        for placeholder in placeholders:
            if placeholder not in parameters:
                issues.append(f"Missing parameter definition: {placeholder}")

        # Check for required disclaimers
        for disclaimer in self.required_disclaimers:
            if f"{{disclaimer_{disclaimer}}}" not in template_content:
                issues.append(f"Missing required disclaimer: {disclaimer}")

        # Validate parameter formats
        for param, value in parameters.items():
            if 'ndc' in param.lower() and not self._validate_ndc_format(str(value)):
                issues.append(f"Invalid NDC format for parameter: {param}")
            elif 'date' in param.lower() and not self._validate_date_format(str(value)):
                issues.append(f"Invalid date format for parameter: {param}")

        is_valid = len(issues) == 0
        return is_valid, issues

    def _extract_placeholders(self, template_content: str) -> List[str]:
        """Extract parameter placeholders from template"""
        import re
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, template_content)
        return [m for m in matches if not m.startswith('disclaimer_')]

    def _validate_ndc_format(self, value: str) -> bool:
        """Validate NDC number format"""
        import re
        pattern = r'^\d{4,5}-\d{3,4}-\d{1,2}$'
        return bool(re.match(pattern, value))

    def _validate_date_format(self, value: str) -> bool:
        """Validate date format"""
        try:
            datetime.fromisoformat(value)
            return True
        except:
            return False


class PromptTemplateManager:
    """Main prompt template management system"""

    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self.ab_tests: Dict[str, ABTestConfig] = {}
        self.performance_metrics: Dict[str, TemplatePerformanceMetrics] = {}
        self.validator = PharmaceuticalTemplateValidator()
        self.approval_queue: List[Tuple[str, str]] = []  # (template_id, version)
        self.template_cache: Dict[str, str] = {}  # Cache for compiled templates

    def create_template(self, template: PromptTemplate) -> bool:
        """Create a new prompt template"""
        try:
            # Validate initial version
            if template.versions:
                initial_version = template.versions.get(template.current_version)
                if initial_version:
                    is_valid, issues = self.validator.validate(
                        initial_version.template_content,
                        {p: "" for p in template.required_parameters}
                    )
                    if not is_valid:
                        logger.error(f"Template validation failed: {issues}")
                        return False

            # Store template
            self.templates[template.template_id] = template

            # Initialize performance metrics
            self.performance_metrics[template.template_id] = TemplatePerformanceMetrics(
                template_id=template.template_id,
                version=template.current_version
            )

            # Add to audit trail
            self._add_audit_log(template.template_id, "created", {
                "created_by": template.versions[template.current_version].created_by
                if template.versions else "system"
            })

            logger.info(f"Created template: {template.template_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            return False

    def update_template(self, template_id: str, new_content: str,
                       change_description: str, modified_by: str) -> Optional[str]:
        """Update template with new version"""
        if template_id not in self.templates:
            return None

        template = self.templates[template_id]

        # Generate new version number
        current_version = template.current_version
        version_parts = current_version.split('.')
        if len(version_parts) == 3:
            version_parts[2] = str(int(version_parts[2]) + 1)
        else:
            version_parts = ['1', '0', '0']
        new_version = '.'.join(version_parts)

        # Validate new content
        is_valid, issues = self.validator.validate(
            new_content,
            {p: "" for p in template.required_parameters}
        )
        if not is_valid:
            logger.error(f"Template validation failed: {issues}")
            return None

        # Create new version
        new_version_obj = TemplateVersion(
            version_number=new_version,
            template_content=new_content,
            created_by=modified_by,
            created_at=datetime.now(),
            modified_by=modified_by,
            modified_at=datetime.now(),
            change_description=change_description,
            approval_status=ApprovalStatus.DRAFT
        )

        # Store new version
        template.versions[new_version] = new_version_obj
        template.current_version = new_version

        # Clear cache
        cache_key = f"{template_id}_{new_version}"
        if cache_key in self.template_cache:
            del self.template_cache[cache_key]

        # Add to audit trail
        self._add_audit_log(template_id, "updated", {
            "version": new_version,
            "modified_by": modified_by,
            "change_description": change_description
        })

        logger.info(f"Updated template {template_id} to version {new_version}")
        return new_version

    def get_template(self, template_id: str, version: Optional[str] = None) -> Optional[str]:
        """Get template content, optionally for specific version"""
        if template_id not in self.templates:
            return None

        template = self.templates[template_id]
        version = version or template.current_version

        # Check cache
        cache_key = f"{template_id}_{version}"
        if cache_key in self.template_cache:
            return self.template_cache[cache_key]

        # Get version content
        if version not in template.versions:
            return None

        version_obj = template.versions[version]
        content = version_obj.template_content

        # Apply inheritance if applicable
        if template.parent_template_id:
            parent_content = self.get_template(template.parent_template_id)
            if parent_content:
                content = self._apply_inheritance(parent_content, content)

        # Apply customizations
        if template.customizations:
            content = self._apply_customizations(content, template.customizations)

        # Cache compiled template
        self.template_cache[cache_key] = content

        return content

    def _apply_inheritance(self, parent_content: str, child_content: str) -> str:
        """Apply template inheritance"""
        # Simple implementation - merge sections
        # In production, would use more sophisticated merging
        merged = parent_content

        # Replace overridden sections
        import re
        sections = re.findall(r'<!-- SECTION: (\w+) -->(.*?)<!-- END SECTION -->',
                            child_content, re.DOTALL)
        for section_name, section_content in sections:
            pattern = f'<!-- SECTION: {section_name} -->.*?<!-- END SECTION -->'
            merged = re.sub(pattern, f'<!-- SECTION: {section_name} -->{section_content}<!-- END SECTION -->',
                          merged, flags=re.DOTALL)

        return merged

    def _apply_customizations(self, content: str, customizations: Dict[str, Any]) -> str:
        """Apply template customizations"""
        for key, value in customizations.items():
            placeholder = f"{{{key}}}"
            if placeholder in content:
                content = content.replace(placeholder, str(value))
        return content

    def submit_for_approval(self, template_id: str, version: str) -> bool:
        """Submit template version for approval"""
        if template_id not in self.templates:
            return False

        template = self.templates[template_id]
        if version not in template.versions:
            return False

        version_obj = template.versions[version]
        version_obj.approval_status = ApprovalStatus.PENDING_REVIEW
        self.approval_queue.append((template_id, version))

        self._add_audit_log(template_id, "submitted_for_approval", {
            "version": version,
            "submitted_by": version_obj.modified_by or version_obj.created_by
        })

        logger.info(f"Template {template_id} v{version} submitted for approval")
        return True

    def approve_template(self, template_id: str, version: str, approved_by: str,
                        comments: Optional[str] = None) -> bool:
        """Approve template version"""
        if template_id not in self.templates:
            return False

        template = self.templates[template_id]
        if version not in template.versions:
            return False

        version_obj = template.versions[version]
        version_obj.approval_status = ApprovalStatus.APPROVED
        version_obj.approved_by = approved_by
        version_obj.approved_at = datetime.now()

        # Remove from approval queue
        self.approval_queue = [(tid, v) for tid, v in self.approval_queue
                              if not (tid == template_id and v == version)]

        self._add_audit_log(template_id, "approved", {
            "version": version,
            "approved_by": approved_by,
            "comments": comments
        })

        logger.info(f"Template {template_id} v{version} approved by {approved_by}")
        return True

    def reject_template(self, template_id: str, version: str, rejected_by: str,
                       reason: str) -> bool:
        """Reject template version"""
        if template_id not in self.templates:
            return False

        template = self.templates[template_id]
        if version not in template.versions:
            return False

        version_obj = template.versions[version]
        version_obj.approval_status = ApprovalStatus.REJECTED

        # Remove from approval queue
        self.approval_queue = [(tid, v) for tid, v in self.approval_queue
                              if not (tid == template_id and v == version)]

        self._add_audit_log(template_id, "rejected", {
            "version": version,
            "rejected_by": rejected_by,
            "reason": reason
        })

        logger.info(f"Template {template_id} v{version} rejected by {rejected_by}")
        return True

    def create_ab_test(self, test_config: ABTestConfig) -> bool:
        """Create A/B test for templates"""
        try:
            # Validate templates exist
            if (test_config.template_a_id not in self.templates or
                test_config.template_b_id not in self.templates):
                return False

            # Store test configuration
            self.ab_tests[test_config.test_id] = test_config

            # Mark templates as in A/B test
            self.templates[test_config.template_a_id].active_ab_tests.append(test_config.test_id)
            self.templates[test_config.template_b_id].active_ab_tests.append(test_config.test_id)

            logger.info(f"Created A/B test: {test_config.test_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create A/B test: {e}")
            return False

    def record_ab_test_result(self, test_id: str, template_used: str,
                             success: bool, metrics: Dict[str, float]) -> None:
        """Record result from A/B test"""
        if test_id not in self.ab_tests:
            return

        test = self.ab_tests[test_id]
        if not test.is_active:
            return

        # Determine which template was used
        if template_used == test.template_a_id:
            variant = 'A'
        elif template_used == test.template_b_id:
            variant = 'B'
        else:
            return

        # Update results
        if variant not in test.current_results:
            test.current_results[variant] = {
                'total_uses': 0,
                'successful_uses': 0,
                'metrics': defaultdict(list)
            }

        test.current_results[variant]['total_uses'] += 1
        if success:
            test.current_results[variant]['successful_uses'] += 1

        for metric, value in metrics.items():
            test.current_results[variant]['metrics'][metric].append(value)

        # Check if test should conclude
        self._evaluate_ab_test(test_id)

    def _evaluate_ab_test(self, test_id: str) -> None:
        """Evaluate if A/B test has reached conclusion"""
        test = self.ab_tests[test_id]

        if not test.is_active:
            return

        # Check if we have enough samples
        total_samples = sum(
            test.current_results.get(v, {}).get('total_uses', 0)
            for v in ['A', 'B']
        )

        if total_samples < test.sample_size:
            return

        # Calculate success rates
        success_rate_a = (
            test.current_results['A']['successful_uses'] /
            test.current_results['A']['total_uses']
            if test.current_results.get('A', {}).get('total_uses', 0) > 0 else 0
        )
        success_rate_b = (
            test.current_results['B']['successful_uses'] /
            test.current_results['B']['total_uses']
            if test.current_results.get('B', {}).get('total_uses', 0) > 0 else 0
        )

        # Simple statistical significance test (would use proper statistics in production)
        difference = abs(success_rate_a - success_rate_b)

        if difference >= test.minimum_difference:
            # Declare winner
            test.winner = test.template_a_id if success_rate_a > success_rate_b else test.template_b_id
            test.is_active = False
            test.end_date = datetime.now()

            logger.info(f"A/B test {test_id} concluded. Winner: {test.winner}")

            # Update template performance metrics
            self._update_performance_from_ab_test(test)

    def _update_performance_from_ab_test(self, test: ABTestConfig) -> None:
        """Update template performance metrics from A/B test results"""
        for template_id, variant in [(test.template_a_id, 'A'), (test.template_b_id, 'B')]:
            if template_id in self.performance_metrics:
                metrics = self.performance_metrics[template_id]
                results = test.current_results.get(variant, {})

                metrics.total_uses += results.get('total_uses', 0)
                metrics.successful_uses += results.get('successful_uses', 0)
                metrics.failed_uses += results.get('total_uses', 0) - results.get('successful_uses', 0)

                # Update average metrics
                for metric_name, values in results.get('metrics', {}).items():
                    if values and metric_name in test.success_metrics:
                        avg_value = statistics.mean(values)
                        if metric_name == 'quality_score':
                            metrics.average_quality_score = avg_value
                        elif metric_name == 'processing_time':
                            metrics.average_processing_time = avg_value
                        elif metric_name == 'completeness':
                            metrics.data_completeness_rate = avg_value

    def track_performance(self, template_id: str, version: str,
                         success: bool, quality_score: float,
                         processing_time: float, parameters_satisfied: float,
                         pharmaceutical_metrics: Optional[Dict[str, float]] = None) -> None:
        """Track template performance metrics"""
        key = f"{template_id}_{version}"
        if key not in self.performance_metrics:
            self.performance_metrics[key] = TemplatePerformanceMetrics(
                template_id=template_id,
                version=version
            )

        metrics = self.performance_metrics[key]

        # Update counters
        metrics.total_uses += 1
        if success:
            metrics.successful_uses += 1
        else:
            metrics.failed_uses += 1

        # Update averages
        n = metrics.total_uses
        metrics.average_quality_score = (
            (metrics.average_quality_score * (n - 1) + quality_score) / n
        )
        metrics.average_processing_time = (
            (metrics.average_processing_time * (n - 1) + processing_time) / n
        )
        metrics.parameter_satisfaction_rate = (
            (metrics.parameter_satisfaction_rate * (n - 1) + parameters_satisfied) / n
        )

        # Update error rate
        metrics.error_rate = metrics.failed_uses / metrics.total_uses

        # Update pharmaceutical metrics
        if pharmaceutical_metrics:
            for metric, value in pharmaceutical_metrics.items():
                if metric not in metrics.pharmaceutical_accuracy_metrics:
                    metrics.pharmaceutical_accuracy_metrics[metric] = 0
                metrics.pharmaceutical_accuracy_metrics[metric] = (
                    (metrics.pharmaceutical_accuracy_metrics[metric] * (n - 1) + value) / n
                )

        metrics.last_used = datetime.now()

        # Update version performance in template
        if template_id in self.templates:
            template = self.templates[template_id]
            if version in template.versions:
                template.versions[version].performance_metrics = {
                    'quality_score': metrics.average_quality_score,
                    'success_rate': metrics.successful_uses / metrics.total_uses,
                    'processing_time': metrics.average_processing_time
                }

    def get_performance_report(self, template_id: str,
                              version: Optional[str] = None) -> Dict[str, Any]:
        """Get performance report for template"""
        if version:
            key = f"{template_id}_{version}"
            if key in self.performance_metrics:
                return self.performance_metrics[key].dict()
            return {}

        # Get performance for all versions
        template = self.templates.get(template_id)
        if not template:
            return {}

        report = {
            'template_id': template_id,
            'name': template.name,
            'versions': {}
        }

        for ver in template.versions:
            key = f"{template_id}_{ver}"
            if key in self.performance_metrics:
                report['versions'][ver] = self.performance_metrics[key].dict()

        return report

    def compare_versions(self, template_id: str, version_a: str,
                        version_b: str) -> Dict[str, Any]:
        """Compare two versions of a template"""
        if template_id not in self.templates:
            return {}

        template = self.templates[template_id]
        if version_a not in template.versions or version_b not in template.versions:
            return {}

        version_a_obj = template.versions[version_a]
        version_b_obj = template.versions[version_b]

        # Text difference
        diff = list(difflib.unified_diff(
            version_a_obj.template_content.splitlines(),
            version_b_obj.template_content.splitlines(),
            fromfile=f"v{version_a}",
            tofile=f"v{version_b}",
            lineterm=""
        ))

        # Performance comparison
        perf_a = self.performance_metrics.get(f"{template_id}_{version_a}")
        perf_b = self.performance_metrics.get(f"{template_id}_{version_b}")

        comparison = {
            'template_id': template_id,
            'version_a': version_a,
            'version_b': version_b,
            'text_diff': diff,
            'performance_comparison': {
                'version_a': perf_a.dict() if perf_a else None,
                'version_b': perf_b.dict() if perf_b else None
            },
            'metadata_comparison': {
                'version_a': {
                    'created_at': version_a_obj.created_at.isoformat(),
                    'created_by': version_a_obj.created_by,
                    'approval_status': version_a_obj.approval_status.value
                },
                'version_b': {
                    'created_at': version_b_obj.created_at.isoformat(),
                    'created_by': version_b_obj.created_by,
                    'approval_status': version_b_obj.approval_status.value
                }
            }
        }

        return comparison

    def _add_audit_log(self, template_id: str, action: str, details: Dict[str, Any]) -> None:
        """Add entry to template audit trail"""
        if template_id in self.templates:
            self.templates[template_id].audit_trail.append({
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'details': details
            })

    def export_templates(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Export templates for backup or transfer"""
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'templates': {}
        }

        for template_id, template in self.templates.items():
            if category and template.category != category:
                continue

            export_data['templates'][template_id] = {
                'template': template.dict(),
                'performance': self.get_performance_report(template_id)
            }

        return export_data

    def import_templates(self, import_data: Dict[str, Any]) -> int:
        """Import templates from exported data"""
        imported_count = 0

        for template_id, data in import_data.get('templates', {}).items():
            try:
                template = PromptTemplate(**data['template'])
                if self.create_template(template):
                    imported_count += 1
            except Exception as e:
                logger.error(f"Failed to import template {template_id}: {e}")

        return imported_count