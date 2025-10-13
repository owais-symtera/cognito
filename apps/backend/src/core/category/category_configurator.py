"""
Story 4.1: Advanced Category Configuration & Dependencies
Enhanced category management with dependency tracking and pharmaceutical workflow optimization
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from enum import IntEnum, Enum
import json
import networkx as nx
from pydantic import BaseModel, Field
import logging
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


class AnalysisProfile(Enum):
    """Pharmaceutical analysis focus profiles"""
    REGULATORY_FOCUS = "regulatory_focus"
    MARKET_FOCUS = "market_focus"
    TECHNICAL_FOCUS = "technical_focus"
    COMPLIANCE_FOCUS = "compliance_focus"
    COMMERCIAL_FOCUS = "commercial_focus"
    CLINICAL_FOCUS = "clinical_focus"


class CategoryPriority(IntEnum):
    """Category processing priority levels"""
    CRITICAL = 100    # Must process first
    HIGH = 75         # Process early
    MEDIUM = 50       # Standard priority
    LOW = 25          # Process when available
    OPTIONAL = 10     # Process if requested


@dataclass
class CategoryDependency:
    """Represents a dependency between categories"""
    source_category: str
    target_category: str
    dependency_type: str  # 'requires', 'enhances', 'conflicts'
    strength: float = 1.0  # 0-1 strength of dependency
    description: str = ""
    validation_rule: Optional[str] = None


@dataclass
class CategoryConfiguration:
    """Advanced category configuration"""
    category_id: str
    name: str
    description: str
    priority: CategoryPriority = CategoryPriority.MEDIUM
    enabled: bool = True
    dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    enhances: List[str] = field(default_factory=list)
    cost_factor: float = 1.0  # Relative cost multiplier
    processing_time_estimate: int = 60  # Estimated seconds
    required_sources: List[str] = field(default_factory=list)
    output_fields: List[str] = field(default_factory=list)
    validation_rules: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    audit_info: Dict[str, Any] = field(default_factory=dict)


class WorkflowOptimization(BaseModel):
    """Workflow optimization recommendations"""
    recommended_categories: List[str]
    optional_categories: List[str]
    processing_order: List[str]
    estimated_cost: float
    estimated_time: int  # seconds
    optimization_score: float
    rationale: str
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)


class CategoryUsageAnalytics(BaseModel):
    """Analytics for category usage"""
    category_id: str
    usage_count: int
    success_rate: float
    average_processing_time: float
    average_quality_score: float
    common_combinations: List[List[str]]
    failure_reasons: Dict[str, int]
    cost_efficiency: float
    last_used: datetime
    trend: str  # 'increasing', 'stable', 'decreasing'


class CategoryConfigurator:
    """Advanced category configuration and dependency management system"""

    def __init__(self):
        self.configurations: Dict[str, CategoryConfiguration] = {}
        self.dependency_graph = nx.DiGraph()
        self.analysis_profiles = self._initialize_analysis_profiles()
        self.usage_analytics: Dict[str, CategoryUsageAnalytics] = {}
        self.optimization_cache: Dict[str, WorkflowOptimization] = {}

    def _initialize_analysis_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Initialize pharmaceutical analysis profiles"""
        return {
            AnalysisProfile.REGULATORY_FOCUS.value: {
                'required_categories': [
                    'regulatory_status',
                    'patent_status',
                    'clinical_trials',
                    'approval_timelines'
                ],
                'optional_categories': [
                    'manufacturing_compliance',
                    'labeling_requirements'
                ],
                'priority_weights': {
                    'regulatory_status': 1.0,
                    'patent_status': 0.9,
                    'clinical_trials': 0.8
                },
                'cost_optimization': 'balanced',
                'description': 'Focus on regulatory compliance and approval status'
            },
            AnalysisProfile.MARKET_FOCUS.value: {
                'required_categories': [
                    'market_overview',
                    'competitive_landscape',
                    'market_size',
                    'growth_projections'
                ],
                'optional_categories': [
                    'pricing_analysis',
                    'distribution_channels',
                    'customer_segmentation'
                ],
                'priority_weights': {
                    'market_overview': 1.0,
                    'competitive_landscape': 0.95,
                    'market_size': 0.9
                },
                'cost_optimization': 'performance',
                'description': 'Focus on market opportunity and competitive analysis'
            },
            AnalysisProfile.TECHNICAL_FOCUS.value: {
                'required_categories': [
                    'physicochemical_profile',
                    'pharmacokinetics',
                    'formulations',
                    'mechanism_of_action'
                ],
                'optional_categories': [
                    'drug_interactions',
                    'bioavailability',
                    'stability_data'
                ],
                'priority_weights': {
                    'mechanism_of_action': 1.0,
                    'pharmacokinetics': 0.9,
                    'formulations': 0.85
                },
                'cost_optimization': 'balanced',
                'description': 'Focus on technical and scientific aspects'
            },
            AnalysisProfile.COMPLIANCE_FOCUS.value: {
                'required_categories': [
                    'gmp_compliance',
                    'quality_control',
                    'audit_findings',
                    'deviation_history'
                ],
                'optional_categories': [
                    'supplier_qualification',
                    'change_control',
                    'validation_status'
                ],
                'priority_weights': {
                    'gmp_compliance': 1.0,
                    'quality_control': 0.95,
                    'audit_findings': 0.9
                },
                'cost_optimization': 'thoroughness',
                'description': 'Focus on quality and compliance requirements'
            },
            AnalysisProfile.COMMERCIAL_FOCUS.value: {
                'required_categories': [
                    'commercial_opportunities',
                    'partnership_potential',
                    'revenue_projections',
                    'roi_analysis'
                ],
                'optional_categories': [
                    'licensing_opportunities',
                    'market_access',
                    'reimbursement_landscape'
                ],
                'priority_weights': {
                    'commercial_opportunities': 1.0,
                    'revenue_projections': 0.9,
                    'roi_analysis': 0.85
                },
                'cost_optimization': 'performance',
                'description': 'Focus on commercial viability and opportunities'
            },
            AnalysisProfile.CLINICAL_FOCUS.value: {
                'required_categories': [
                    'clinical_efficacy',
                    'safety_profile',
                    'patient_populations',
                    'clinical_endpoints'
                ],
                'optional_categories': [
                    'adverse_events',
                    'comparative_effectiveness',
                    'real_world_evidence'
                ],
                'priority_weights': {
                    'clinical_efficacy': 1.0,
                    'safety_profile': 0.95,
                    'patient_populations': 0.85
                },
                'cost_optimization': 'thoroughness',
                'description': 'Focus on clinical outcomes and patient impact'
            }
        }

    def add_category_configuration(self, config: CategoryConfiguration) -> bool:
        """Add or update a category configuration"""
        try:
            # Store configuration
            self.configurations[config.category_id] = config

            # Update dependency graph
            self.dependency_graph.add_node(
                config.category_id,
                data=config,
                priority=config.priority
            )

            # Add edges for dependencies
            for dep in config.dependencies:
                self.dependency_graph.add_edge(
                    dep,
                    config.category_id,
                    type='requires',
                    weight=1.0
                )

            # Add edges for enhancements
            for enh in config.enhances:
                self.dependency_graph.add_edge(
                    config.category_id,
                    enh,
                    type='enhances',
                    weight=0.5
                )

            # Add conflict relationships (stored as node attributes)
            if config.conflicts:
                nx.set_node_attributes(
                    self.dependency_graph,
                    {config.category_id: {'conflicts': config.conflicts}}
                )

            logger.info(f"Added category configuration: {config.category_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add category configuration: {e}")
            return False

    def validate_category_activation(self, category_id: str,
                                   active_categories: Set[str]) -> Tuple[bool, List[str]]:
        """
        Validate if a category can be activated given current active categories

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        if category_id not in self.configurations:
            issues.append(f"Category {category_id} not found in configurations")
            return False, issues

        config = self.configurations[category_id]

        # Check if category is enabled
        if not config.enabled:
            issues.append(f"Category {category_id} is disabled")

        # Check dependencies
        for dep in config.dependencies:
            if dep not in active_categories:
                issues.append(f"Missing required dependency: {dep}")

        # Check conflicts
        for conflict in config.conflicts:
            if conflict in active_categories:
                issues.append(f"Conflict with active category: {conflict}")

        # Check required sources availability
        # This would integrate with Epic 2 source management
        if config.required_sources:
            # Placeholder for source availability check
            pass

        is_valid = len(issues) == 0
        return is_valid, issues

    def get_category_dependencies(self, category_id: str,
                                 recursive: bool = True) -> Dict[str, List[str]]:
        """Get all dependencies for a category"""
        dependencies = {
            'requires': [],
            'enhances': [],
            'enhanced_by': [],
            'conflicts': []
        }

        if category_id not in self.dependency_graph:
            return dependencies

        if recursive:
            # Get all ancestors (required dependencies)
            try:
                ancestors = nx.ancestors(self.dependency_graph, category_id)
                dependencies['requires'] = list(ancestors)
            except nx.NetworkXError:
                pass

            # Get all descendants (categories that depend on this)
            try:
                descendants = nx.descendants(self.dependency_graph, category_id)
                dependencies['required_by'] = list(descendants)
            except nx.NetworkXError:
                pass
        else:
            # Get direct dependencies only
            for pred in self.dependency_graph.predecessors(category_id):
                edge_data = self.dependency_graph.edges[pred, category_id]
                if edge_data.get('type') == 'requires':
                    dependencies['requires'].append(pred)

            for succ in self.dependency_graph.successors(category_id):
                edge_data = self.dependency_graph.edges[category_id, succ]
                if edge_data.get('type') == 'enhances':
                    dependencies['enhances'].append(succ)

        # Get conflicts from node attributes
        node_data = self.dependency_graph.nodes.get(category_id, {})
        dependencies['conflicts'] = node_data.get('conflicts', [])

        return dependencies

    def optimize_workflow(self, analysis_profile: str,
                         constraints: Optional[Dict[str, Any]] = None) -> WorkflowOptimization:
        """
        Optimize category workflow for a specific analysis profile

        Args:
            analysis_profile: The analysis profile to optimize for
            constraints: Optional constraints (max_cost, max_time, required_categories)

        Returns:
            WorkflowOptimization with recommendations
        """
        # Check cache first
        cache_key = f"{analysis_profile}_{json.dumps(constraints or {}, sort_keys=True)}"
        if cache_key in self.optimization_cache:
            return self.optimization_cache[cache_key]

        profile = self.analysis_profiles.get(analysis_profile)
        if not profile:
            return WorkflowOptimization(
                recommended_categories=[],
                optional_categories=[],
                processing_order=[],
                estimated_cost=0,
                estimated_time=0,
                optimization_score=0,
                rationale="Invalid analysis profile"
            )

        constraints = constraints or {}
        max_cost = constraints.get('max_cost', float('inf'))
        max_time = constraints.get('max_time', float('inf'))
        required_categories = set(constraints.get('required_categories', []))

        # Start with profile requirements
        recommended = set(profile['required_categories'])
        optional = set(profile['optional_categories'])

        # Add user-required categories
        recommended.update(required_categories)

        # Resolve dependencies
        all_categories = recommended.copy()
        for cat in recommended:
            deps = self.get_category_dependencies(cat, recursive=True)
            all_categories.update(deps['requires'])

        # Remove conflicting categories
        final_categories = all_categories.copy()
        for cat in all_categories:
            config = self.configurations.get(cat)
            if config:
                for conflict in config.conflicts:
                    final_categories.discard(conflict)

        # Calculate cost and time
        total_cost = 0
        total_time = 0
        for cat in final_categories:
            config = self.configurations.get(cat)
            if config:
                total_cost += config.cost_factor
                total_time += config.processing_time_estimate

        # Apply cost optimization strategy
        optimization_strategy = profile.get('cost_optimization', 'balanced')

        if optimization_strategy == 'performance' and total_cost > max_cost:
            # Remove optional categories to reduce cost
            for cat in optional.copy():
                if cat in final_categories:
                    config = self.configurations.get(cat)
                    if config and total_cost - config.cost_factor >= max_cost * 0.9:
                        final_categories.remove(cat)
                        optional.remove(cat)
                        total_cost -= config.cost_factor
                        total_time -= config.processing_time_estimate

        # Determine processing order using topological sort
        try:
            subgraph = self.dependency_graph.subgraph(final_categories)
            processing_order = list(nx.topological_sort(subgraph))
        except nx.NetworkXError:
            # If there's a cycle, use priority-based ordering
            processing_order = sorted(
                final_categories,
                key=lambda x: self.configurations.get(x, CategoryConfiguration(x, "", "")).priority,
                reverse=True
            )

        # Calculate optimization score
        optimization_score = self._calculate_optimization_score(
            final_categories,
            profile,
            total_cost,
            total_time,
            constraints
        )

        # Generate rationale
        rationale = self._generate_optimization_rationale(
            analysis_profile,
            final_categories,
            total_cost,
            total_time,
            optimization_score
        )

        # Generate alternatives
        alternatives = self._generate_workflow_alternatives(
            profile,
            final_categories,
            constraints
        )

        optimization = WorkflowOptimization(
            recommended_categories=list(recommended & final_categories),
            optional_categories=list(optional & final_categories),
            processing_order=processing_order,
            estimated_cost=total_cost,
            estimated_time=total_time,
            optimization_score=optimization_score,
            rationale=rationale,
            alternatives=alternatives
        )

        # Cache the result
        self.optimization_cache[cache_key] = optimization

        return optimization

    def _calculate_optimization_score(self, categories: Set[str],
                                     profile: Dict[str, Any],
                                     cost: float,
                                     time: int,
                                     constraints: Dict[str, Any]) -> float:
        """Calculate optimization score for a workflow"""
        score = 100.0

        # Coverage score - how well we cover the profile requirements
        required = set(profile['required_categories'])
        coverage = len(required & categories) / len(required) if required else 1.0
        score *= coverage

        # Cost efficiency
        max_cost = constraints.get('max_cost')
        if max_cost:
            cost_efficiency = min(1.0, max_cost / cost) if cost > 0 else 1.0
            score *= cost_efficiency

        # Time efficiency
        max_time = constraints.get('max_time')
        if max_time:
            time_efficiency = min(1.0, max_time / time) if time > 0 else 1.0
            score *= time_efficiency

        # Dependency satisfaction
        dependency_issues = 0
        for cat in categories:
            deps = self.get_category_dependencies(cat, recursive=False)
            for dep in deps['requires']:
                if dep not in categories:
                    dependency_issues += 1

        dependency_score = max(0.5, 1.0 - (dependency_issues * 0.1))
        score *= dependency_score

        return min(100.0, score)

    def _generate_optimization_rationale(self, profile: str,
                                        categories: Set[str],
                                        cost: float,
                                        time: int,
                                        score: float) -> str:
        """Generate human-readable rationale for optimization"""
        rationale_parts = []

        profile_desc = self.analysis_profiles[profile].get('description', profile)
        rationale_parts.append(f"Optimized for {profile_desc}")

        rationale_parts.append(f"Selected {len(categories)} categories")
        rationale_parts.append(f"Estimated cost: {cost:.2f} units")
        rationale_parts.append(f"Estimated time: {time} seconds")
        rationale_parts.append(f"Optimization score: {score:.1f}/100")

        if score < 70:
            rationale_parts.append("Consider reviewing constraints or selecting fewer categories")
        elif score < 85:
            rationale_parts.append("Good balance between coverage and efficiency")
        else:
            rationale_parts.append("Excellent optimization achieved")

        return ". ".join(rationale_parts)

    def _generate_workflow_alternatives(self, profile: Dict[str, Any],
                                       selected_categories: Set[str],
                                       constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alternative workflow configurations"""
        alternatives = []

        # Minimal configuration - required only
        minimal_cats = set(profile['required_categories'])
        minimal_cost = sum(
            self.configurations.get(cat, CategoryConfiguration(cat, "", "")).cost_factor
            for cat in minimal_cats
        )
        minimal_time = sum(
            self.configurations.get(cat, CategoryConfiguration(cat, "", "")).processing_time_estimate
            for cat in minimal_cats
        )

        alternatives.append({
            'name': 'Minimal',
            'description': 'Required categories only',
            'categories': list(minimal_cats),
            'cost': minimal_cost,
            'time': minimal_time
        })

        # Maximal configuration - all categories
        maximal_cats = set(profile['required_categories']) | set(profile['optional_categories'])
        maximal_cost = sum(
            self.configurations.get(cat, CategoryConfiguration(cat, "", "")).cost_factor
            for cat in maximal_cats
        )
        maximal_time = sum(
            self.configurations.get(cat, CategoryConfiguration(cat, "", "")).processing_time_estimate
            for cat in maximal_cats
        )

        alternatives.append({
            'name': 'Comprehensive',
            'description': 'All recommended categories',
            'categories': list(maximal_cats),
            'cost': maximal_cost,
            'time': maximal_time
        })

        return alternatives

    def track_usage(self, category_id: str,
                   success: bool,
                   processing_time: float,
                   quality_score: float,
                   used_with: List[str],
                   failure_reason: Optional[str] = None) -> None:
        """Track category usage for analytics"""
        if category_id not in self.usage_analytics:
            self.usage_analytics[category_id] = CategoryUsageAnalytics(
                category_id=category_id,
                usage_count=0,
                success_rate=0,
                average_processing_time=0,
                average_quality_score=0,
                common_combinations=[],
                failure_reasons={},
                cost_efficiency=0,
                last_used=datetime.now(),
                trend='stable'
            )

        analytics = self.usage_analytics[category_id]

        # Update counters
        analytics.usage_count += 1
        analytics.last_used = datetime.now()

        # Update success rate
        if success:
            analytics.success_rate = (
                (analytics.success_rate * (analytics.usage_count - 1) + 1) /
                analytics.usage_count
            )
        else:
            analytics.success_rate = (
                (analytics.success_rate * (analytics.usage_count - 1)) /
                analytics.usage_count
            )
            if failure_reason:
                analytics.failure_reasons[failure_reason] = analytics.failure_reasons.get(failure_reason, 0) + 1

        # Update averages
        analytics.average_processing_time = (
            (analytics.average_processing_time * (analytics.usage_count - 1) + processing_time) /
            analytics.usage_count
        )
        analytics.average_quality_score = (
            (analytics.average_quality_score * (analytics.usage_count - 1) + quality_score) /
            analytics.usage_count
        )

        # Track common combinations
        if used_with and len(used_with) > 1:
            combination = sorted(used_with)
            # Keep only top 10 combinations
            if combination not in analytics.common_combinations:
                analytics.common_combinations.append(combination)
                analytics.common_combinations = analytics.common_combinations[-10:]

        # Calculate cost efficiency
        config = self.configurations.get(category_id)
        if config and config.cost_factor > 0:
            analytics.cost_efficiency = quality_score / config.cost_factor

        # Determine trend (simple implementation)
        # In production, would use time-series analysis
        if analytics.usage_count > 10:
            if analytics.success_rate > 0.8 and analytics.average_quality_score > 0.7:
                analytics.trend = 'increasing'
            elif analytics.success_rate < 0.5 or analytics.average_quality_score < 0.5:
                analytics.trend = 'decreasing'
            else:
                analytics.trend = 'stable'

    def get_usage_recommendations(self, category_id: str) -> List[str]:
        """Get usage recommendations based on analytics"""
        recommendations = []

        analytics = self.usage_analytics.get(category_id)
        if not analytics:
            recommendations.append("No usage data available for recommendations")
            return recommendations

        # Success rate recommendations
        if analytics.success_rate < 0.7:
            top_failure = max(analytics.failure_reasons.items(), key=lambda x: x[1])[0] if analytics.failure_reasons else "unknown"
            recommendations.append(f"Low success rate ({analytics.success_rate:.1%}). Most common failure: {top_failure}")

        # Performance recommendations
        config = self.configurations.get(category_id)
        if config and analytics.average_processing_time > config.processing_time_estimate * 1.5:
            recommendations.append(f"Processing time ({analytics.average_processing_time:.1f}s) exceeds estimate. Consider optimization.")

        # Quality recommendations
        if analytics.average_quality_score < 0.6:
            recommendations.append(f"Low quality scores ({analytics.average_quality_score:.2f}). Review data sources or validation rules.")

        # Combination recommendations
        if analytics.common_combinations:
            best_combo = analytics.common_combinations[0]
            recommendations.append(f"Commonly used with: {', '.join(best_combo[:3])}")

        # Cost efficiency recommendations
        if analytics.cost_efficiency < 0.5:
            recommendations.append("Low cost efficiency. Consider if this category provides sufficient value.")

        # Trend recommendations
        if analytics.trend == 'decreasing':
            recommendations.append("Usage trend is declining. Investigate potential issues.")
        elif analytics.trend == 'increasing':
            recommendations.append("Usage trend is positive. Consider expanding related categories.")

        if not recommendations:
            recommendations.append("Category performing well. No specific recommendations.")

        return recommendations

    def export_configuration(self, category_id: Optional[str] = None) -> Dict[str, Any]:
        """Export category configuration(s) for backup or transfer"""
        if category_id:
            config = self.configurations.get(category_id)
            if not config:
                return {}
            return {
                'category_id': config.category_id,
                'name': config.name,
                'description': config.description,
                'priority': config.priority,
                'enabled': config.enabled,
                'dependencies': config.dependencies,
                'conflicts': config.conflicts,
                'enhances': config.enhances,
                'cost_factor': config.cost_factor,
                'processing_time_estimate': config.processing_time_estimate,
                'required_sources': config.required_sources,
                'output_fields': config.output_fields,
                'validation_rules': config.validation_rules,
                'metadata': config.metadata
            }
        else:
            # Export all configurations
            return {
                cat_id: self.export_configuration(cat_id)
                for cat_id in self.configurations
            }

    def import_configuration(self, config_data: Dict[str, Any]) -> bool:
        """Import category configuration from exported data"""
        try:
            config = CategoryConfiguration(
                category_id=config_data['category_id'],
                name=config_data['name'],
                description=config_data['description'],
                priority=config_data.get('priority', CategoryPriority.MEDIUM),
                enabled=config_data.get('enabled', True),
                dependencies=config_data.get('dependencies', []),
                conflicts=config_data.get('conflicts', []),
                enhances=config_data.get('enhances', []),
                cost_factor=config_data.get('cost_factor', 1.0),
                processing_time_estimate=config_data.get('processing_time_estimate', 60),
                required_sources=config_data.get('required_sources', []),
                output_fields=config_data.get('output_fields', []),
                validation_rules=config_data.get('validation_rules', {}),
                metadata=config_data.get('metadata', {})
            )
            return self.add_category_configuration(config)
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            return False

    def validate_dependency_graph(self) -> Tuple[bool, List[str]]:
        """Validate the entire dependency graph for issues"""
        issues = []

        # Check for cycles
        if not nx.is_directed_acyclic_graph(self.dependency_graph):
            cycles = list(nx.simple_cycles(self.dependency_graph))
            for cycle in cycles:
                issues.append(f"Circular dependency detected: {' -> '.join(cycle)}")

        # Check for orphaned nodes
        for node in self.dependency_graph.nodes():
            if (self.dependency_graph.in_degree(node) == 0 and
                self.dependency_graph.out_degree(node) == 0):
                issues.append(f"Orphaned category (no dependencies): {node}")

        # Check for missing configurations
        for node in self.dependency_graph.nodes():
            if node not in self.configurations:
                issues.append(f"Category in graph but missing configuration: {node}")

        # Check for invalid references
        for config in self.configurations.values():
            for dep in config.dependencies:
                if dep not in self.configurations:
                    issues.append(f"Category {config.category_id} depends on unknown category: {dep}")
            for conflict in config.conflicts:
                if conflict not in self.configurations:
                    issues.append(f"Category {config.category_id} conflicts with unknown category: {conflict}")

        is_valid = len(issues) == 0
        return is_valid, issues