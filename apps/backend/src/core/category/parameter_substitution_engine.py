"""
Story 4.3: Dynamic Parameter Substitution Engine
Advanced parameter substitution supporting complex pharmaceutical parameters with audit compliance
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, date
from enum import Enum
import re
import json
import hashlib
from pydantic import BaseModel, Field, validator
import logging
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ParameterType(Enum):
    """Types of parameters supported"""
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    ENUM = "enum"
    ARRAY = "array"
    OBJECT = "object"
    COMPOUND_NAME = "compound_name"
    NDC_NUMBER = "ndc_number"
    PATENT_NUMBER = "patent_number"
    CLINICAL_TRIAL_ID = "clinical_trial_id"
    GEOGRAPHIC_REGION = "geographic_region"
    REGULATORY_IDENTIFIER = "regulatory_identifier"


@dataclass
class ParameterDefinition:
    """Definition of a parameter"""
    name: str
    parameter_type: ParameterType
    description: str
    required: bool = True
    default_value: Optional[Any] = None
    validation_rules: List[str] = field(default_factory=list)
    allowed_values: Optional[List[Any]] = None
    format_pattern: Optional[str] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pharmaceutical_context: Optional[str] = None
    audit_required: bool = False


class ParameterValue(BaseModel):
    """Value of a parameter with metadata"""
    parameter_name: str
    value: Any
    source: Optional[str] = None
    validated: bool = False
    validation_errors: List[str] = Field(default_factory=list)
    substituted_at: Optional[datetime] = None
    audit_info: Dict[str, Any] = Field(default_factory=dict)


class SubstitutionContext(BaseModel):
    """Context for parameter substitution"""
    category: str
    template_id: str
    request_id: str
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    pharmaceutical_domain: Optional[str] = None
    regulatory_requirements: List[str] = Field(default_factory=list)
    performance_tracking: bool = True


class SubstitutionResult(BaseModel):
    """Result of parameter substitution"""
    success: bool
    substituted_template: Optional[str] = None
    parameters_used: List[ParameterValue] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    audit_trail: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)


class ParameterValidator(ABC):
    """Abstract base class for parameter validators"""

    @abstractmethod
    def validate(self, value: Any, definition: ParameterDefinition) -> Tuple[bool, List[str]]:
        """Validate parameter value against definition"""
        pass


class PharmaceuticalParameterValidator(ParameterValidator):
    """Validator for pharmaceutical-specific parameters"""

    def validate(self, value: Any, definition: ParameterDefinition) -> Tuple[bool, List[str]]:
        """Validate pharmaceutical parameter"""
        errors = []

        # Type-specific validation
        if definition.parameter_type == ParameterType.COMPOUND_NAME:
            errors.extend(self._validate_compound_name(value))
        elif definition.parameter_type == ParameterType.NDC_NUMBER:
            errors.extend(self._validate_ndc(value))
        elif definition.parameter_type == ParameterType.PATENT_NUMBER:
            errors.extend(self._validate_patent(value))
        elif definition.parameter_type == ParameterType.CLINICAL_TRIAL_ID:
            errors.extend(self._validate_clinical_trial(value))
        elif definition.parameter_type == ParameterType.REGULATORY_IDENTIFIER:
            errors.extend(self._validate_regulatory_id(value))
        else:
            errors.extend(self._validate_generic(value, definition))

        is_valid = len(errors) == 0
        return is_valid, errors

    def _validate_compound_name(self, value: str) -> List[str]:
        """Validate pharmaceutical compound name"""
        errors = []
        if not isinstance(value, str):
            errors.append("Compound name must be a string")
            return errors

        # Check for invalid characters
        if not re.match(r'^[a-zA-Z0-9\-\s\(\)]+$', value):
            errors.append("Compound name contains invalid characters")

        # Check length
        if len(value) < 2 or len(value) > 200:
            errors.append("Compound name must be between 2 and 200 characters")

        return errors

    def _validate_ndc(self, value: str) -> List[str]:
        """Validate NDC number format"""
        errors = []
        if not isinstance(value, str):
            errors.append("NDC number must be a string")
            return errors

        # NDC format: XXXXX-XXXX-XX or XXXXX-XXX-XX
        pattern = r'^\d{4,5}-\d{3,4}-\d{1,2}$'
        if not re.match(pattern, value):
            errors.append("Invalid NDC format. Expected: XXXXX-XXXX-XX")

        return errors

    def _validate_patent(self, value: str) -> List[str]:
        """Validate patent number format"""
        errors = []
        if not isinstance(value, str):
            errors.append("Patent number must be a string")
            return errors

        # US Patent format: US########
        # EU Patent format: EP#######
        pattern = r'^(US|EP|WO|CN|JP)[0-9]{6,10}[A-Z]?[0-9]?$'
        if not re.match(pattern, value):
            errors.append("Invalid patent number format")

        return errors

    def _validate_clinical_trial(self, value: str) -> List[str]:
        """Validate clinical trial ID"""
        errors = []
        if not isinstance(value, str):
            errors.append("Clinical trial ID must be a string")
            return errors

        # NCT format
        if not re.match(r'^NCT[0-9]{8}$', value):
            errors.append("Invalid clinical trial ID. Expected format: NCT########")

        return errors

    def _validate_regulatory_id(self, value: str) -> List[str]:
        """Validate regulatory identifier"""
        errors = []
        if not isinstance(value, str):
            errors.append("Regulatory identifier must be a string")
            return errors

        # Various regulatory formats
        patterns = [
            r'^(NDA|ANDA|BLA)[0-9]{6}$',  # FDA
            r'^EU/[0-9]/[0-9]{2}/[0-9]{3}/[0-9]{3}$',  # EMA
            r'^[A-Z]{2}[0-9]{4,8}$'  # Generic
        ]

        if not any(re.match(p, value) for p in patterns):
            errors.append("Invalid regulatory identifier format")

        return errors

    def _validate_generic(self, value: Any, definition: ParameterDefinition) -> List[str]:
        """Generic parameter validation"""
        errors = []

        # Type validation
        if definition.parameter_type == ParameterType.STRING:
            if not isinstance(value, str):
                errors.append(f"{definition.name} must be a string")
            elif definition.min_length and len(value) < definition.min_length:
                errors.append(f"{definition.name} must be at least {definition.min_length} characters")
            elif definition.max_length and len(value) > definition.max_length:
                errors.append(f"{definition.name} must be at most {definition.max_length} characters")

        elif definition.parameter_type == ParameterType.NUMBER:
            if not isinstance(value, (int, float)):
                errors.append(f"{definition.name} must be a number")
            elif definition.min_value is not None and value < definition.min_value:
                errors.append(f"{definition.name} must be at least {definition.min_value}")
            elif definition.max_value is not None and value > definition.max_value:
                errors.append(f"{definition.name} must be at most {definition.max_value}")

        elif definition.parameter_type == ParameterType.DATE:
            try:
                if isinstance(value, str):
                    datetime.fromisoformat(value)
                elif not isinstance(value, (datetime, date)):
                    errors.append(f"{definition.name} must be a valid date")
            except ValueError:
                errors.append(f"{definition.name} must be in ISO format")

        elif definition.parameter_type == ParameterType.BOOLEAN:
            if not isinstance(value, bool):
                errors.append(f"{definition.name} must be a boolean")

        elif definition.parameter_type == ParameterType.ENUM:
            if definition.allowed_values and value not in definition.allowed_values:
                errors.append(f"{definition.name} must be one of: {definition.allowed_values}")

        elif definition.parameter_type == ParameterType.ARRAY:
            if not isinstance(value, list):
                errors.append(f"{definition.name} must be an array")

        elif definition.parameter_type == ParameterType.OBJECT:
            if not isinstance(value, dict):
                errors.append(f"{definition.name} must be an object")

        # Format pattern validation
        if definition.format_pattern and isinstance(value, str):
            if not re.match(definition.format_pattern, value):
                errors.append(f"{definition.name} does not match required format")

        # Custom validation rules
        for rule in definition.validation_rules:
            # Execute custom validation (simplified)
            if not self._execute_custom_rule(value, rule):
                errors.append(f"{definition.name} failed validation rule: {rule}")

        return errors

    def _execute_custom_rule(self, value: Any, rule: str) -> bool:
        """Execute custom validation rule"""
        # Simplified implementation - would use safe evaluation in production
        try:
            # Example rules: "len(value) > 5", "value.startswith('FDA')"
            # In production, use a safe expression evaluator
            return True
        except:
            return False


class ParameterSubstitutionEngine:
    """Main parameter substitution engine"""

    def __init__(self):
        self.parameter_definitions: Dict[str, Dict[str, ParameterDefinition]] = {}
        self.parameter_sets: Dict[str, Dict[str, Any]] = {}
        self.validator = PharmaceuticalParameterValidator()
        self.default_parameters = self._initialize_default_parameters()
        self.substitution_cache: Dict[str, str] = {}
        self.audit_trail: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, List[float]] = {
            'validation_time': [],
            'substitution_time': [],
            'total_time': []
        }

    def _initialize_default_parameters(self) -> Dict[str, Any]:
        """Initialize default parameter values"""
        return {
            'current_date': datetime.now().date().isoformat(),
            'analysis_version': '1.0.0',
            'regulatory_framework': 'FDA',
            'geographic_scope': 'United States',
            'language': 'en-US',
            'currency': 'USD',
            'measurement_system': 'metric',
            'confidence_threshold': 0.95,
            'data_freshness_days': 30
        }

    def register_parameter(self, category: str, definition: ParameterDefinition) -> bool:
        """Register a parameter definition for a category"""
        try:
            if category not in self.parameter_definitions:
                self.parameter_definitions[category] = {}

            self.parameter_definitions[category][definition.name] = definition

            logger.info(f"Registered parameter {definition.name} for category {category}")
            return True

        except Exception as e:
            logger.error(f"Failed to register parameter: {e}")
            return False

    def create_parameter_set(self, set_id: str, parameters: Dict[str, Any],
                           category: Optional[str] = None) -> bool:
        """Create a reusable parameter set"""
        try:
            # Validate parameters if category specified
            if category and category in self.parameter_definitions:
                for param_name, param_value in parameters.items():
                    if param_name in self.parameter_definitions[category]:
                        definition = self.parameter_definitions[category][param_name]
                        is_valid, errors = self.validator.validate(param_value, definition)
                        if not is_valid:
                            logger.error(f"Invalid parameter {param_name}: {errors}")
                            return False

            self.parameter_sets[set_id] = parameters
            logger.info(f"Created parameter set: {set_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create parameter set: {e}")
            return False

    def substitute_parameters(self, template: str, parameters: Dict[str, Any],
                            context: SubstitutionContext) -> SubstitutionResult:
        """Perform parameter substitution on template"""
        start_time = datetime.now()
        result = SubstitutionResult(success=False)

        try:
            # Check cache
            cache_key = self._generate_cache_key(template, parameters, context)
            if cache_key in self.substitution_cache:
                cached_template = self.substitution_cache[cache_key]
                result.success = True
                result.substituted_template = cached_template
                result.warnings.append("Using cached substitution")
                return result

            # Merge with defaults
            all_parameters = {**self.default_parameters, **parameters}

            # Add context parameters
            all_parameters['category'] = context.category
            all_parameters['request_id'] = context.request_id
            all_parameters['timestamp'] = context.timestamp.isoformat()

            # Validate parameters
            validation_start = datetime.now()
            validated_params = []

            for param_name, param_value in all_parameters.items():
                param_val = ParameterValue(
                    parameter_name=param_name,
                    value=param_value,
                    source='user' if param_name in parameters else 'default'
                )

                # Find definition
                definition = None
                if context.category in self.parameter_definitions:
                    definition = self.parameter_definitions[context.category].get(param_name)

                if definition:
                    is_valid, errors = self.validator.validate(param_value, definition)
                    param_val.validated = is_valid
                    param_val.validation_errors = errors
                    if not is_valid and definition.required:
                        result.validation_errors.extend(errors)
                else:
                    param_val.validated = True  # No definition means no validation

                validated_params.append(param_val)

            validation_time = (datetime.now() - validation_start).total_seconds()

            # Check for validation errors on required parameters
            if result.validation_errors:
                result.success = False
                return result

            # Perform substitution
            substitution_start = datetime.now()
            substituted_template = self._perform_substitution(template, all_parameters, context)
            substitution_time = (datetime.now() - substitution_start).total_seconds()

            # Check for unsubstituted placeholders
            remaining_placeholders = self._find_placeholders(substituted_template)
            if remaining_placeholders:
                for placeholder in remaining_placeholders:
                    if placeholder not in all_parameters:
                        result.warnings.append(f"Unsubstituted placeholder: {{{placeholder}}}")

            # Cache result
            self.substitution_cache[cache_key] = substituted_template

            # Build result
            result.success = True
            result.substituted_template = substituted_template
            result.parameters_used = validated_params

            # Add audit information
            if context.pharmaceutical_domain or any(p.audit_required for p in validated_params):
                result.audit_trail = self._create_audit_record(
                    context, all_parameters, substituted_template
                )

            # Performance metrics
            total_time = (datetime.now() - start_time).total_seconds()
            result.performance_metrics = {
                'validation_time': validation_time,
                'substitution_time': substitution_time,
                'total_time': total_time,
                'parameters_count': len(all_parameters),
                'cache_hit': False
            }

            # Track performance
            self.performance_metrics['validation_time'].append(validation_time)
            self.performance_metrics['substitution_time'].append(substitution_time)
            self.performance_metrics['total_time'].append(total_time)

            logger.info(f"Parameter substitution completed for {context.request_id}")
            return result

        except Exception as e:
            logger.error(f"Parameter substitution failed: {e}")
            result.success = False
            result.validation_errors.append(f"Substitution error: {str(e)}")
            return result

    def _perform_substitution(self, template: str, parameters: Dict[str, Any],
                            context: SubstitutionContext) -> str:
        """Perform actual parameter substitution"""
        substituted = template

        # Sort parameters by length (longer first) to avoid partial substitutions
        sorted_params = sorted(parameters.items(), key=lambda x: len(x[0]), reverse=True)

        for param_name, param_value in sorted_params:
            # Handle different placeholder formats
            placeholders = [
                f"{{{param_name}}}",  # {param}
                f"{{{{ {param_name} }}}}",  # {{ param }}
                f"${param_name}",  # $param
                f"${{{param_name}}}"  # ${param}
            ]

            for placeholder in placeholders:
                if placeholder in substituted:
                    # Format value based on type
                    formatted_value = self._format_value(param_value, param_name, context)
                    substituted = substituted.replace(placeholder, formatted_value)

        # Handle conditional sections
        substituted = self._process_conditionals(substituted, parameters)

        # Handle loops/iterations
        substituted = self._process_loops(substituted, parameters)

        return substituted

    def _format_value(self, value: Any, param_name: str, context: SubstitutionContext) -> str:
        """Format parameter value for substitution"""
        if value is None:
            return ""

        # Special formatting for pharmaceutical parameters
        if 'ndc' in param_name.lower():
            return self._format_ndc(str(value))
        elif 'date' in param_name.lower():
            return self._format_date(value)
        elif 'price' in param_name.lower() or 'cost' in param_name.lower():
            return self._format_currency(value, context.pharmaceutical_domain)
        elif isinstance(value, list):
            return ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            return json.dumps(value)
        elif isinstance(value, bool):
            return "Yes" if value else "No"
        else:
            return str(value)

    def _format_ndc(self, ndc: str) -> str:
        """Format NDC number for display"""
        # Ensure proper formatting: XXXXX-XXXX-XX
        parts = ndc.replace("-", "")
        if len(parts) == 11:
            return f"{parts[:5]}-{parts[5:9]}-{parts[9:]}"
        return ndc

    def _format_date(self, date_value: Any) -> str:
        """Format date for display"""
        if isinstance(date_value, str):
            try:
                date_obj = datetime.fromisoformat(date_value)
                return date_obj.strftime("%B %d, %Y")
            except:
                return date_value
        elif isinstance(date_value, (datetime, date)):
            return date_value.strftime("%B %d, %Y")
        return str(date_value)

    def _format_currency(self, value: Any, domain: Optional[str]) -> str:
        """Format currency value"""
        try:
            amount = float(value)
            # Determine currency symbol based on domain
            if domain == "EU":
                return f"€{amount:,.2f}"
            elif domain == "UK":
                return f"£{amount:,.2f}"
            elif domain == "JP":
                return f"¥{amount:,.0f}"
            else:
                return f"${amount:,.2f}"
        except:
            return str(value)

    def _process_conditionals(self, template: str, parameters: Dict[str, Any]) -> str:
        """Process conditional sections in template"""
        # Simple conditional processing: {if:param_name}...{/if}
        pattern = r'\{if:(\w+)\}(.*?)\{/if\}'

        def replace_conditional(match):
            param_name = match.group(1)
            content = match.group(2)

            if param_name in parameters and parameters[param_name]:
                return content
            return ""

        return re.sub(pattern, replace_conditional, template, flags=re.DOTALL)

    def _process_loops(self, template: str, parameters: Dict[str, Any]) -> str:
        """Process loop sections in template"""
        # Simple loop processing: {foreach:param_name}...{/foreach}
        pattern = r'\{foreach:(\w+)\}(.*?)\{/foreach\}'

        def replace_loop(match):
            param_name = match.group(1)
            content = match.group(2)

            if param_name in parameters and isinstance(parameters[param_name], list):
                results = []
                for item in parameters[param_name]:
                    item_content = content
                    if isinstance(item, dict):
                        for key, value in item.items():
                            item_content = item_content.replace(f"{{item.{key}}}", str(value))
                    else:
                        item_content = item_content.replace("{item}", str(item))
                    results.append(item_content)
                return "".join(results)
            return ""

        return re.sub(pattern, replace_loop, template, flags=re.DOTALL)

    def _find_placeholders(self, template: str) -> List[str]:
        """Find all placeholders in template"""
        placeholders = set()

        # Find {param} style
        pattern1 = r'\{([^}]+)\}'
        placeholders.update(re.findall(pattern1, template))

        # Find $param style
        pattern2 = r'\$(\w+)'
        placeholders.update(re.findall(pattern2, template))

        # Filter out conditionals and loops
        placeholders = {p for p in placeholders
                       if not p.startswith('if:') and not p.startswith('foreach:')
                       and not p.startswith('/') and '.' not in p}

        return list(placeholders)

    def _generate_cache_key(self, template: str, parameters: Dict[str, Any],
                           context: SubstitutionContext) -> str:
        """Generate cache key for substitution"""
        # Create hash of template and parameters
        content = f"{template}_{json.dumps(parameters, sort_keys=True)}_{context.category}"
        return hashlib.md5(content.encode()).hexdigest()

    def _create_audit_record(self, context: SubstitutionContext,
                            parameters: Dict[str, Any],
                            result: str) -> Dict[str, Any]:
        """Create audit record for substitution"""
        audit_record = {
            'timestamp': datetime.now().isoformat(),
            'context': {
                'category': context.category,
                'template_id': context.template_id,
                'request_id': context.request_id,
                'user_id': context.user_id,
                'pharmaceutical_domain': context.pharmaceutical_domain,
                'regulatory_requirements': context.regulatory_requirements
            },
            'parameters_used': {
                k: v for k, v in parameters.items()
                if k not in self.default_parameters
            },
            'result_hash': hashlib.md5(result.encode()).hexdigest(),
            'compliance_check': self._check_regulatory_compliance(parameters, context)
        }

        self.audit_trail.append(audit_record)
        return audit_record

    def _check_regulatory_compliance(self, parameters: Dict[str, Any],
                                    context: SubstitutionContext) -> Dict[str, bool]:
        """Check if substitution meets regulatory requirements"""
        compliance = {}

        for requirement in context.regulatory_requirements:
            if requirement == "FDA":
                compliance["FDA"] = all([
                    'ndc_number' not in parameters or self._validate_ndc_format(parameters.get('ndc_number')),
                    'clinical_trial_id' not in parameters or parameters.get('clinical_trial_id', '').startswith('NCT')
                ])
            elif requirement == "EMA":
                compliance["EMA"] = all([
                    'regulatory_identifier' in parameters,
                    'marketing_authorization' in parameters
                ])
            elif requirement == "GMP":
                compliance["GMP"] = all([
                    'manufacturing_site' in parameters,
                    'batch_number' in parameters
                ])

        return compliance

    def _validate_ndc_format(self, ndc: Any) -> bool:
        """Quick NDC format validation"""
        if not ndc:
            return True
        return bool(re.match(r'^\d{4,5}-\d{3,4}-\d{1,2}$', str(ndc)))

    def optimize_performance(self) -> Dict[str, Any]:
        """Optimize substitution performance based on metrics"""
        if not self.performance_metrics['total_time']:
            return {'message': 'No performance data available'}

        import statistics

        optimization_report = {
            'average_times': {
                'validation': statistics.mean(self.performance_metrics['validation_time']),
                'substitution': statistics.mean(self.performance_metrics['substitution_time']),
                'total': statistics.mean(self.performance_metrics['total_time'])
            },
            'cache_size': len(self.substitution_cache),
            'recommendations': []
        }

        # Generate recommendations
        if optimization_report['average_times']['validation'] > 0.1:
            optimization_report['recommendations'].append(
                "Consider caching validation results for frequently used parameters"
            )

        if optimization_report['average_times']['substitution'] > 0.2:
            optimization_report['recommendations'].append(
                "Consider optimizing template complexity or using simpler placeholders"
            )

        if len(self.substitution_cache) > 1000:
            optimization_report['recommendations'].append(
                "Consider implementing cache eviction policy"
            )

        # Clear old performance metrics if too large
        max_metrics = 1000
        for key in self.performance_metrics:
            if len(self.performance_metrics[key]) > max_metrics:
                self.performance_metrics[key] = self.performance_metrics[key][-max_metrics:]

        return optimization_report

    def export_parameter_definitions(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Export parameter definitions for documentation"""
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'categories': {}
        }

        for cat, definitions in self.parameter_definitions.items():
            if category and cat != category:
                continue

            export_data['categories'][cat] = {
                param_name: {
                    'name': param_def.name,
                    'type': param_def.parameter_type.value,
                    'description': param_def.description,
                    'required': param_def.required,
                    'default_value': param_def.default_value,
                    'validation_rules': param_def.validation_rules,
                    'pharmaceutical_context': param_def.pharmaceutical_context
                }
                for param_name, param_def in definitions.items()
            }

        return export_data