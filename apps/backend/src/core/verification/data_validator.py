"""
Story 3.3: Data Validation & Quality Assurance
Comprehensive pharmaceutical data validation with regulatory compliance documentation
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import IntEnum
import re
import json
from pydantic import BaseModel, Field
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ValidationLevel(IntEnum):
    """Validation severity levels"""
    CRITICAL = 100    # Must fix - regulatory requirement
    HIGH = 75         # Should fix - data quality impact
    MEDIUM = 50       # Consider fixing - best practice
    LOW = 25          # Optional - enhancement
    INFO = 10         # Informational only


class ValidationResult(BaseModel):
    """Individual validation result"""
    field_name: str
    category: str
    level: ValidationLevel
    passed: bool
    message: str
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    source: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    compliance_flag: Optional[str] = None
    audit_info: Dict[str, Any] = Field(default_factory=dict)


class PharmaceuticalValidationRules:
    """Pharmaceutical-specific validation patterns"""

    PATENT_NUMBER = r'^[A-Z]{2}[0-9]{6,10}$'
    NDC_NUMBER = r'^[0-9]{4,5}-[0-9]{3,4}-[0-9]{1,2}$'
    CLINICAL_TRIAL_ID = r'^NCT[0-9]{8}$'
    FDA_APPLICATION = r'^(NDA|ANDA|BLA)[0-9]{6}$'
    CAS_NUMBER = r'^[0-9]{2,7}-[0-9]{2}-[0-9]$'
    UNII_CODE = r'^[A-Z0-9]{10}$'
    RXCUI = r'^[0-9]{1,7}$'
    INN_NAME = r'^[a-z]+$'  # International Nonproprietary Name

    DOSAGE_PATTERN = r'^\d+(\.\d+)?\s?(mg|g|mcg|ml|L|IU|units?)(/\w+)?$'
    CONCENTRATION = r'^\d+(\.\d+)?\s?\w+/\d+(\.\d+)?\s?\w+$'

    # Date formats
    APPROVAL_DATE = r'^\d{4}-\d{2}-\d{2}$'  # ISO format
    EXPIRY_FORMAT = r'^(0[1-9]|1[0-2])/\d{4}$'  # MM/YYYY


@dataclass
class ValidationConfig:
    """Configuration for validation rules per category"""
    category: str
    required_fields: Set[str] = field(default_factory=set)
    optional_fields: Set[str] = field(default_factory=set)
    validation_rules: Dict[str, str] = field(default_factory=dict)
    cross_references: Dict[str, List[str]] = field(default_factory=dict)
    compliance_requirements: Dict[str, str] = field(default_factory=dict)
    anomaly_thresholds: Dict[str, float] = field(default_factory=dict)


class DataValidator:
    """Main data validation and quality assurance engine"""

    def __init__(self):
        self.validation_configs: Dict[str, ValidationConfig] = self._initialize_configs()
        self.validation_history: List[ValidationResult] = []
        self.quality_metrics: Dict[str, float] = {}

    def _initialize_configs(self) -> Dict[str, ValidationConfig]:
        """Initialize validation configurations for each pharmaceutical category"""
        configs = {}

        # Drug Information validation
        configs['drug_info'] = ValidationConfig(
            category='drug_info',
            required_fields={'drug_name', 'active_ingredient', 'manufacturer', 'approval_status'},
            optional_fields={'indication', 'contraindications', 'side_effects'},
            validation_rules={
                'ndc_number': PharmaceuticalValidationRules.NDC_NUMBER,
                'approval_date': PharmaceuticalValidationRules.APPROVAL_DATE,
                'dosage': PharmaceuticalValidationRules.DOSAGE_PATTERN
            },
            compliance_requirements={
                'fda_compliance': 'Must have valid FDA application number',
                'labeling': 'Must include required label elements'
            },
            anomaly_thresholds={
                'price_variance': 0.30,  # 30% price variance threshold
                'dosage_outlier': 3.0    # 3 standard deviations
            }
        )

        # Clinical Trials validation
        configs['clinical_trials'] = ValidationConfig(
            category='clinical_trials',
            required_fields={'trial_id', 'phase', 'status', 'sponsor', 'start_date'},
            optional_fields={'end_date', 'enrollment', 'primary_outcome'},
            validation_rules={
                'trial_id': PharmaceuticalValidationRules.CLINICAL_TRIAL_ID,
                'start_date': PharmaceuticalValidationRules.APPROVAL_DATE,
                'end_date': PharmaceuticalValidationRules.APPROVAL_DATE
            },
            compliance_requirements={
                'registration': 'Must be registered on ClinicalTrials.gov',
                'protocol': 'Must have approved protocol'
            },
            anomaly_thresholds={
                'enrollment_rate': 0.50,  # 50% variance in enrollment
                'duration_outlier': 2.5   # 2.5 standard deviations
            }
        )

        # Patent Information validation
        configs['patents'] = ValidationConfig(
            category='patents',
            required_fields={'patent_number', 'filing_date', 'expiry_date', 'assignee'},
            optional_fields={'priority_date', 'claims', 'classification'},
            validation_rules={
                'patent_number': PharmaceuticalValidationRules.PATENT_NUMBER,
                'filing_date': PharmaceuticalValidationRules.APPROVAL_DATE,
                'expiry_date': PharmaceuticalValidationRules.APPROVAL_DATE
            },
            compliance_requirements={
                'validity': 'Patent must be valid and enforceable',
                'ownership': 'Clear chain of title required'
            }
        )

        # Market Analysis validation
        configs['market_analysis'] = ValidationConfig(
            category='market_analysis',
            required_fields={'market_size', 'growth_rate', 'key_players', 'date'},
            optional_fields={'forecast', 'segments', 'geographic_distribution'},
            validation_rules={
                'date': PharmaceuticalValidationRules.APPROVAL_DATE
            },
            anomaly_thresholds={
                'growth_rate_outlier': 0.40,  # 40% variance
                'market_size_outlier': 2.0     # 2 standard deviations
            }
        )

        # Regulatory validation
        configs['regulatory'] = ValidationConfig(
            category='regulatory',
            required_fields={'application_number', 'submission_date', 'status', 'regulatory_body'},
            optional_fields={'review_timeline', 'approval_conditions'},
            validation_rules={
                'application_number': PharmaceuticalValidationRules.FDA_APPLICATION,
                'submission_date': PharmaceuticalValidationRules.APPROVAL_DATE
            },
            compliance_requirements={
                'documentation': 'Complete regulatory dossier required',
                'gmp': 'Good Manufacturing Practice compliance',
                'glp': 'Good Laboratory Practice compliance'
            }
        )

        return configs

    async def validate_completeness(self, data: Dict[str, Any], category: str) -> List[ValidationResult]:
        """Validate data completeness for required fields"""
        results = []
        config = self.validation_configs.get(category)

        if not config:
            results.append(ValidationResult(
                field_name='category',
                category=category,
                level=ValidationLevel.CRITICAL,
                passed=False,
                message=f'Unknown category: {category}',
                audit_info={'validation_type': 'completeness', 'timestamp': datetime.now().isoformat()}
            ))
            return results

        # Check required fields
        for field in config.required_fields:
            if field not in data or data[field] is None or data[field] == '':
                results.append(ValidationResult(
                    field_name=field,
                    category=category,
                    level=ValidationLevel.CRITICAL,
                    passed=False,
                    message=f'Required field missing: {field}',
                    expected_value='non-empty value',
                    actual_value=data.get(field),
                    compliance_flag='REQUIRED_FIELD',
                    audit_info={
                        'validation_type': 'completeness',
                        'field_requirement': 'required',
                        'timestamp': datetime.now().isoformat()
                    }
                ))
            else:
                results.append(ValidationResult(
                    field_name=field,
                    category=category,
                    level=ValidationLevel.INFO,
                    passed=True,
                    message=f'Required field present: {field}',
                    actual_value=data[field],
                    audit_info={
                        'validation_type': 'completeness',
                        'field_requirement': 'required',
                        'timestamp': datetime.now().isoformat()
                    }
                ))

        # Check optional fields for quality
        for field in config.optional_fields:
            if field in data and data[field]:
                results.append(ValidationResult(
                    field_name=field,
                    category=category,
                    level=ValidationLevel.INFO,
                    passed=True,
                    message=f'Optional field present: {field}',
                    actual_value=data[field],
                    audit_info={
                        'validation_type': 'completeness',
                        'field_requirement': 'optional',
                        'timestamp': datetime.now().isoformat()
                    }
                ))

        return results

    async def validate_format(self, data: Dict[str, Any], category: str) -> List[ValidationResult]:
        """Validate data format against pharmaceutical standards"""
        results = []
        config = self.validation_configs.get(category)

        if not config:
            return results

        for field_name, pattern in config.validation_rules.items():
            if field_name in data and data[field_name]:
                value = str(data[field_name])
                if re.match(pattern, value):
                    results.append(ValidationResult(
                        field_name=field_name,
                        category=category,
                        level=ValidationLevel.INFO,
                        passed=True,
                        message=f'Format validation passed for {field_name}',
                        actual_value=value,
                        audit_info={
                            'validation_type': 'format',
                            'pattern': pattern,
                            'timestamp': datetime.now().isoformat()
                        }
                    ))
                else:
                    results.append(ValidationResult(
                        field_name=field_name,
                        category=category,
                        level=ValidationLevel.HIGH,
                        passed=False,
                        message=f'Invalid format for {field_name}',
                        expected_value=f'Pattern: {pattern}',
                        actual_value=value,
                        compliance_flag='FORMAT_VIOLATION',
                        audit_info={
                            'validation_type': 'format',
                            'pattern': pattern,
                            'timestamp': datetime.now().isoformat()
                        }
                    ))

        return results

    async def validate_cross_references(self, data: Dict[str, Any],
                                       related_data: List[Dict[str, Any]],
                                       category: str) -> List[ValidationResult]:
        """Validate cross-references between related data"""
        results = []
        config = self.validation_configs.get(category)

        if not config or not config.cross_references:
            return results

        for field, reference_fields in config.cross_references.items():
            if field in data:
                field_value = data[field]

                for related in related_data:
                    for ref_field in reference_fields:
                        if ref_field in related and related[ref_field] == field_value:
                            results.append(ValidationResult(
                                field_name=field,
                                category=category,
                                level=ValidationLevel.INFO,
                                passed=True,
                                message=f'Cross-reference validated: {field} -> {ref_field}',
                                actual_value=field_value,
                                source=related.get('source', 'unknown'),
                                audit_info={
                                    'validation_type': 'cross_reference',
                                    'reference_field': ref_field,
                                    'timestamp': datetime.now().isoformat()
                                }
                            ))
                            break
                    else:
                        continue
                    break
                else:
                    results.append(ValidationResult(
                        field_name=field,
                        category=category,
                        level=ValidationLevel.MEDIUM,
                        passed=False,
                        message=f'Cross-reference not found for {field}',
                        expected_value='Matching reference in related data',
                        actual_value=field_value,
                        audit_info={
                            'validation_type': 'cross_reference',
                            'searched_fields': reference_fields,
                            'timestamp': datetime.now().isoformat()
                        }
                    ))

        return results

    async def detect_anomalies(self, data: Dict[str, Any],
                              historical_data: List[Dict[str, Any]],
                              category: str) -> List[ValidationResult]:
        """Detect statistical anomalies in pharmaceutical data"""
        results = []
        config = self.validation_configs.get(category)

        if not config or not config.anomaly_thresholds:
            return results

        for field, threshold in config.anomaly_thresholds.items():
            if field not in data:
                continue

            try:
                current_value = float(data[field]) if not isinstance(data[field], (int, float)) else data[field]
                historical_values = []

                for hist in historical_data:
                    if field in hist:
                        try:
                            hist_val = float(hist[field]) if not isinstance(hist[field], (int, float)) else hist[field]
                            historical_values.append(hist_val)
                        except (ValueError, TypeError):
                            continue

                if len(historical_values) >= 3:  # Need at least 3 data points
                    mean_val = sum(historical_values) / len(historical_values)
                    variance = sum((x - mean_val) ** 2 for x in historical_values) / len(historical_values)
                    std_dev = variance ** 0.5

                    if std_dev > 0:
                        z_score = abs((current_value - mean_val) / std_dev)

                        if z_score > threshold:
                            results.append(ValidationResult(
                                field_name=field,
                                category=category,
                                level=ValidationLevel.MEDIUM,
                                passed=False,
                                message=f'Anomaly detected in {field}: Z-score {z_score:.2f} exceeds threshold {threshold}',
                                expected_value=f'Within {threshold} standard deviations',
                                actual_value=current_value,
                                compliance_flag='STATISTICAL_ANOMALY',
                                audit_info={
                                    'validation_type': 'anomaly_detection',
                                    'z_score': z_score,
                                    'mean': mean_val,
                                    'std_dev': std_dev,
                                    'threshold': threshold,
                                    'historical_count': len(historical_values),
                                    'timestamp': datetime.now().isoformat()
                                }
                            ))
                        else:
                            results.append(ValidationResult(
                                field_name=field,
                                category=category,
                                level=ValidationLevel.INFO,
                                passed=True,
                                message=f'No anomaly in {field}: Z-score {z_score:.2f}',
                                actual_value=current_value,
                                audit_info={
                                    'validation_type': 'anomaly_detection',
                                    'z_score': z_score,
                                    'timestamp': datetime.now().isoformat()
                                }
                            ))

            except (ValueError, TypeError) as e:
                logger.warning(f"Could not perform anomaly detection for {field}: {e}")

        return results

    async def validate_compliance(self, data: Dict[str, Any], category: str) -> List[ValidationResult]:
        """Validate regulatory compliance requirements"""
        results = []
        config = self.validation_configs.get(category)

        if not config or not config.compliance_requirements:
            return results

        for requirement, description in config.compliance_requirements.items():
            # This would connect to actual compliance checking systems
            # For now, we'll check for presence of compliance indicators
            compliance_field = f'{requirement}_compliant'

            if compliance_field in data:
                if data[compliance_field]:
                    results.append(ValidationResult(
                        field_name=requirement,
                        category=category,
                        level=ValidationLevel.INFO,
                        passed=True,
                        message=f'Compliance verified: {description}',
                        compliance_flag=requirement.upper(),
                        audit_info={
                            'validation_type': 'compliance',
                            'requirement': requirement,
                            'description': description,
                            'timestamp': datetime.now().isoformat()
                        }
                    ))
                else:
                    results.append(ValidationResult(
                        field_name=requirement,
                        category=category,
                        level=ValidationLevel.CRITICAL,
                        passed=False,
                        message=f'Compliance violation: {description}',
                        compliance_flag=f'{requirement.upper()}_VIOLATION',
                        audit_info={
                            'validation_type': 'compliance',
                            'requirement': requirement,
                            'description': description,
                            'timestamp': datetime.now().isoformat()
                        }
                    ))

        return results

    async def validate_data(self, data: Dict[str, Any],
                           category: str,
                           related_data: Optional[List[Dict[str, Any]]] = None,
                           historical_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Comprehensive data validation with quality assurance

        Args:
            data: Data to validate
            category: Pharmaceutical category
            related_data: Related data for cross-reference validation
            historical_data: Historical data for anomaly detection

        Returns:
            Validation report with quality metrics
        """
        all_results = []

        # Run all validation checks
        all_results.extend(await self.validate_completeness(data, category))
        all_results.extend(await self.validate_format(data, category))

        if related_data:
            all_results.extend(await self.validate_cross_references(data, related_data, category))

        if historical_data:
            all_results.extend(await self.detect_anomalies(data, historical_data, category))

        all_results.extend(await self.validate_compliance(data, category))

        # Store validation history
        self.validation_history.extend(all_results)

        # Calculate quality metrics
        total_validations = len(all_results)
        passed_validations = sum(1 for r in all_results if r.passed)
        critical_failures = sum(1 for r in all_results if not r.passed and r.level == ValidationLevel.CRITICAL)
        high_failures = sum(1 for r in all_results if not r.passed and r.level == ValidationLevel.HIGH)

        quality_score = (passed_validations / total_validations * 100) if total_validations > 0 else 0

        # Adjust quality score based on severity
        if critical_failures > 0:
            quality_score *= 0.5  # 50% penalty for critical failures
        if high_failures > 0:
            quality_score *= 0.8  # 20% penalty for high failures

        # Group results by field
        field_results = {}
        for result in all_results:
            if result.field_name not in field_results:
                field_results[result.field_name] = []
            field_results[result.field_name].append(result)

        # Generate compliance summary
        compliance_issues = [r for r in all_results if r.compliance_flag and not r.passed]

        validation_report = {
            'category': category,
            'timestamp': datetime.now().isoformat(),
            'data_validated': data,
            'validation_results': all_results,
            'field_results': field_results,
            'quality_metrics': {
                'quality_score': quality_score,
                'total_validations': total_validations,
                'passed_validations': passed_validations,
                'failed_validations': total_validations - passed_validations,
                'critical_failures': critical_failures,
                'high_failures': high_failures,
                'completeness_rate': sum(1 for r in all_results if r.audit_info.get('validation_type') == 'completeness' and r.passed) / max(len(self.validation_configs.get(category, ValidationConfig()).required_fields), 1) * 100
            },
            'compliance_summary': {
                'compliant': len(compliance_issues) == 0,
                'issues': compliance_issues,
                'regulatory_flags': list(set(r.compliance_flag for r in compliance_issues if r.compliance_flag))
            },
            'recommendations': self._generate_recommendations(all_results, category),
            'audit_trail': {
                'validation_id': f'VAL-{category}-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'validator_version': '1.0.0',
                'configuration': {
                    'category': category,
                    'rules_applied': len(self.validation_configs.get(category, ValidationConfig()).validation_rules),
                    'compliance_checks': len(self.validation_configs.get(category, ValidationConfig()).compliance_requirements)
                }
            }
        }

        # Update quality metrics cache
        self.quality_metrics[category] = quality_score

        logger.info(f"Validation completed for {category}: Score {quality_score:.2f}%, "
                   f"Critical failures: {critical_failures}, High failures: {high_failures}")

        return validation_report

    def _generate_recommendations(self, results: List[ValidationResult], category: str) -> List[str]:
        """Generate improvement recommendations based on validation results"""
        recommendations = []

        # Check for missing required fields
        missing_required = [r for r in results if not r.passed and r.level == ValidationLevel.CRITICAL and 'Required field missing' in r.message]
        if missing_required:
            fields = [r.field_name for r in missing_required]
            recommendations.append(f"Complete missing required fields: {', '.join(fields)}")

        # Check for format violations
        format_violations = [r for r in results if not r.passed and r.compliance_flag == 'FORMAT_VIOLATION']
        if format_violations:
            fields = [r.field_name for r in format_violations]
            recommendations.append(f"Fix format violations in fields: {', '.join(fields)}")

        # Check for compliance issues
        compliance_violations = [r for r in results if r.compliance_flag and 'VIOLATION' in r.compliance_flag]
        if compliance_violations:
            violations = set(r.compliance_flag for r in compliance_violations)
            recommendations.append(f"Address compliance violations: {', '.join(violations)}")

        # Check for anomalies
        anomalies = [r for r in results if r.compliance_flag == 'STATISTICAL_ANOMALY']
        if anomalies:
            fields = [r.field_name for r in anomalies]
            recommendations.append(f"Review anomalous values in: {', '.join(fields)}")

        # Check for missing cross-references
        missing_refs = [r for r in results if not r.passed and 'Cross-reference not found' in r.message]
        if missing_refs:
            recommendations.append("Establish cross-references with related data sources")

        # General quality improvement
        passed_rate = sum(1 for r in results if r.passed) / len(results) * 100 if results else 0
        if passed_rate < 80:
            recommendations.append(f"Overall data quality is {passed_rate:.1f}% - consider comprehensive data review")

        return recommendations

    def configure_validation_rules(self, category: str, config: ValidationConfig) -> None:
        """Update validation configuration for a category"""
        self.validation_configs[category] = config
        logger.info(f"Updated validation configuration for {category}")

    def get_quality_trends(self, category: Optional[str] = None,
                          time_window: Optional[int] = 30) -> Dict[str, Any]:
        """Get quality trends over time"""
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=time_window)
        relevant_history = [
            r for r in self.validation_history
            if r.timestamp >= cutoff_date and (not category or r.category == category)
        ]

        if not relevant_history:
            return {'message': 'No validation history available'}

        # Group by date
        daily_scores = {}
        for result in relevant_history:
            date_key = result.timestamp.date().isoformat()
            if date_key not in daily_scores:
                daily_scores[date_key] = {'passed': 0, 'total': 0}
            daily_scores[date_key]['total'] += 1
            if result.passed:
                daily_scores[date_key]['passed'] += 1

        # Calculate daily quality scores
        trends = []
        for date, scores in sorted(daily_scores.items()):
            quality_score = (scores['passed'] / scores['total'] * 100) if scores['total'] > 0 else 0
            trends.append({
                'date': date,
                'quality_score': quality_score,
                'validations': scores['total'],
                'passed': scores['passed']
            })

        return {
            'category': category or 'all',
            'time_window_days': time_window,
            'trends': trends,
            'current_score': self.quality_metrics.get(category, 0) if category else sum(self.quality_metrics.values()) / len(self.quality_metrics) if self.quality_metrics else 0,
            'improvement_rate': (trends[-1]['quality_score'] - trends[0]['quality_score']) / len(trends) if len(trends) > 1 else 0
        }