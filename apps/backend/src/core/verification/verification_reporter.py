"""
Story 3.5: Verification Reporting & Quality Metrics
Comprehensive verification reporting with pharmaceutical compliance metrics
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from enum import IntEnum
import json
import hashlib
from pydantic import BaseModel, Field
import logging
from dataclasses import dataclass, field
import statistics
from collections import defaultdict

logger = logging.getLogger(__name__)


class ReportType(IntEnum):
    """Types of verification reports"""
    SUMMARY = 1           # High-level executive summary
    DETAILED = 2          # Detailed technical report
    COMPLIANCE = 3        # Regulatory compliance report
    QUALITY = 4           # Quality metrics report
    SOURCE = 5            # Source contribution report
    TREND = 6             # Historical trend analysis
    ALERT = 7             # Quality threshold alerts
    AUDIT = 8             # Complete audit trail


class QualityThreshold(IntEnum):
    """Quality threshold levels for alerts"""
    EXCELLENT = 90        # 90%+ quality score
    GOOD = 75            # 75-89% quality score
    ACCEPTABLE = 60      # 60-74% quality score
    POOR = 40            # 40-59% quality score
    CRITICAL = 0         # Below 40% quality score


@dataclass
class CategoryMetrics:
    """Quality metrics for a pharmaceutical category"""
    category: str
    quality_score: float
    completeness: float
    accuracy: float
    consistency: float
    timeliness: float
    source_coverage: int
    validation_passes: int
    validation_failures: int
    conflict_count: int
    merge_count: int
    last_updated: datetime = field(default_factory=datetime.now)


class VerificationReport(BaseModel):
    """Complete verification report"""
    report_id: str
    report_type: ReportType
    category: str
    process_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    quality_score: float
    summary: Dict[str, Any]
    details: Dict[str, Any]
    metrics: Dict[str, float]
    recommendations: List[str]
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    compliance_status: Dict[str, Any] = Field(default_factory=dict)
    audit_trail: Dict[str, Any] = Field(default_factory=dict)


class SourceContribution(BaseModel):
    """Analysis of source contributions"""
    source_name: str
    contribution_count: int
    quality_score: float
    reliability_score: float
    coverage_areas: List[str]
    conflict_rate: float
    last_update: datetime
    value_score: float  # Composite value score


class QualityTrend(BaseModel):
    """Quality trend over time"""
    period: str  # daily, weekly, monthly
    start_date: datetime
    end_date: datetime
    category: str
    quality_scores: List[float]
    improvement_rate: float
    volatility: float
    forecast: Optional[float] = None


class VerificationReporter:
    """Main verification reporting and quality metrics engine"""

    def __init__(self):
        self.report_history: List[VerificationReport] = []
        self.category_metrics: Dict[str, CategoryMetrics] = {}
        self.source_contributions: Dict[str, SourceContribution] = {}
        self.quality_trends: Dict[str, List[QualityTrend]] = defaultdict(list)
        self.alert_thresholds = self._initialize_alert_thresholds()
        self.compliance_requirements = self._initialize_compliance_requirements()

    def _initialize_alert_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Initialize quality threshold alerts per category"""
        thresholds = {
            'drug_info': {
                'quality_score': 75.0,
                'completeness': 80.0,
                'accuracy': 85.0,
                'source_coverage': 3
            },
            'clinical_trials': {
                'quality_score': 80.0,
                'completeness': 85.0,
                'accuracy': 90.0,
                'source_coverage': 2
            },
            'patents': {
                'quality_score': 70.0,
                'completeness': 75.0,
                'accuracy': 80.0,
                'source_coverage': 2
            },
            'market_analysis': {
                'quality_score': 65.0,
                'completeness': 70.0,
                'accuracy': 75.0,
                'source_coverage': 3
            },
            'regulatory': {
                'quality_score': 85.0,
                'completeness': 90.0,
                'accuracy': 95.0,
                'source_coverage': 2
            }
        }
        return thresholds

    def _initialize_compliance_requirements(self) -> Dict[str, List[str]]:
        """Initialize regulatory compliance requirements"""
        requirements = {
            'FDA': ['21_CFR_Part_11', 'GMP', 'GLP', 'GCP', 'FDAAA'],
            'EMA': ['EU_GMP', 'EU_GCP', 'EU_GDPR', 'Eudralex_Vol4'],
            'PMDA': ['J_GMP', 'J_GCP', 'J_GLP', 'PMD_Act'],
            'NMPA': ['China_GMP', 'China_GCP', 'China_GLP'],
            'CDSCO': ['Schedule_Y', 'India_GMP', 'India_GCP', 'India_GLP']
        }
        return requirements

    async def generate_verification_summary(self,
                                          verification_data: Dict[str, Any],
                                          category: str,
                                          process_id: Optional[str] = None) -> VerificationReport:
        """
        Generate comprehensive verification summary report

        Args:
            verification_data: Complete verification data including all stages
            category: Pharmaceutical category
            process_id: Optional process tracking ID

        Returns:
            Verification summary report
        """
        # Extract key metrics from verification data
        source_auth = verification_data.get('source_authentication', {})
        conflict_resolution = verification_data.get('conflict_resolution', {})
        data_validation = verification_data.get('data_validation', {})
        data_merge = verification_data.get('data_merge', {})

        # Calculate overall quality score
        quality_components = {
            'source_quality': source_auth.get('hierarchy_score', 0) / 10 * 100,  # Normalize to 100
            'conflict_resolution': (1 - conflict_resolution.get('conflict_rate', 0)) * 100,
            'validation_score': data_validation.get('quality_metrics', {}).get('quality_score', 0),
            'merge_confidence': data_merge.get('confidence_scores', {}).get('overall', 0) * 100
        }

        overall_quality_score = statistics.mean(quality_components.values()) if quality_components else 0

        # Generate summary
        summary = {
            'total_sources': source_auth.get('total_sources', 0),
            'authenticated_sources': source_auth.get('authenticated_count', 0),
            'conflicts_detected': conflict_resolution.get('conflicts_detected', 0),
            'conflicts_resolved': conflict_resolution.get('conflicts_resolved', 0),
            'validation_passes': data_validation.get('quality_metrics', {}).get('passed_validations', 0),
            'validation_failures': data_validation.get('quality_metrics', {}).get('failed_validations', 0),
            'fields_merged': len(data_merge.get('merged_data', {})),
            'overall_quality_score': overall_quality_score
        }

        # Generate details
        details = {
            'source_breakdown': self._analyze_source_breakdown(source_auth),
            'conflict_analysis': self._analyze_conflicts(conflict_resolution),
            'validation_details': self._analyze_validation(data_validation),
            'merge_summary': self._analyze_merge(data_merge),
            'data_completeness': self._calculate_completeness(verification_data)
        }

        # Calculate metrics
        metrics = {
            'quality_score': overall_quality_score,
            'completeness': details['data_completeness'],
            'source_diversity': self._calculate_source_diversity(source_auth),
            'conflict_rate': conflict_resolution.get('conflict_rate', 0),
            'validation_rate': self._calculate_validation_rate(data_validation),
            'merge_confidence': data_merge.get('confidence_scores', {}).get('overall', 0)
        }

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, category)

        # Check for alerts
        alerts = self._check_quality_thresholds(metrics, category)

        # Compliance status
        compliance_status = self._assess_compliance(verification_data, category)

        # Create report
        report = VerificationReport(
            report_id=self._generate_report_id(category, process_id),
            report_type=ReportType.SUMMARY,
            category=category,
            process_id=process_id,
            quality_score=overall_quality_score,
            summary=summary,
            details=details,
            metrics=metrics,
            recommendations=recommendations,
            alerts=alerts,
            compliance_status=compliance_status,
            audit_trail={
                'generation_timestamp': datetime.now().isoformat(),
                'data_sources': verification_data.get('sources', []),
                'processing_stages': ['authentication', 'conflict_resolution', 'validation', 'merge'],
                'quality_components': quality_components
            }
        )

        # Store report
        self.report_history.append(report)

        # Update category metrics
        self._update_category_metrics(category, metrics, summary)

        logger.info(f"Generated verification summary for {category}: Quality score {overall_quality_score:.2f}%")

        return report

    def _analyze_source_breakdown(self, source_auth: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze source authentication breakdown"""
        sources = source_auth.get('authenticated_sources', [])
        breakdown = defaultdict(list)

        for source in sources:
            level = source.get('authentication_level', 'UNKNOWN')
            breakdown[level].append(source.get('source_name', 'unknown'))

        return {
            'by_authentication_level': dict(breakdown),
            'total_sources': len(sources),
            'average_weight': statistics.mean([s.get('weight', 0) for s in sources]) if sources else 0,
            'primary_sources': [s for s in sources if s.get('weight', 0) >= 8]
        }

    def _analyze_conflicts(self, conflict_resolution: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze conflict resolution details"""
        conflicts = conflict_resolution.get('conflicts', [])
        resolutions = conflict_resolution.get('resolutions', [])

        conflict_types = defaultdict(int)
        resolution_methods = defaultdict(int)

        for conflict in conflicts:
            conflict_types[conflict.get('conflict_type', 'unknown')] += 1

        for resolution in resolutions:
            resolution_methods[resolution.get('resolution_method', 'unknown')] += 1

        return {
            'conflict_types': dict(conflict_types),
            'resolution_methods': dict(resolution_methods),
            'auto_resolved': sum(1 for r in resolutions if r.get('auto_resolved', False)),
            'manual_review_needed': sum(1 for r in resolutions if r.get('requires_review', False))
        }

    def _analyze_validation(self, data_validation: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze validation details"""
        validation_results = data_validation.get('validation_results', [])

        validation_by_type = defaultdict(lambda: {'passed': 0, 'failed': 0})
        compliance_issues = []

        for result in validation_results:
            val_type = result.get('audit_info', {}).get('validation_type', 'unknown')
            if result.get('passed'):
                validation_by_type[val_type]['passed'] += 1
            else:
                validation_by_type[val_type]['failed'] += 1

            if result.get('compliance_flag') and not result.get('passed'):
                compliance_issues.append(result.get('compliance_flag'))

        return {
            'validation_breakdown': dict(validation_by_type),
            'compliance_issues': list(set(compliance_issues)),
            'critical_failures': data_validation.get('quality_metrics', {}).get('critical_failures', 0),
            'recommendations': data_validation.get('recommendations', [])
        }

    def _analyze_merge(self, data_merge: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data merge details"""
        merge_records = data_merge.get('audit_trail', {}).get('merge_records', [])

        merge_strategies = defaultdict(int)
        enrichment_count = 0

        for record in merge_records:
            strategy = record.get('merge_strategy', 'unknown')
            merge_strategies[strategy] += 1
            if strategy == 'ENRICHMENT':
                enrichment_count += 1

        return {
            'merge_strategies_used': dict(merge_strategies),
            'fields_merged': data_merge.get('audit_trail', {}).get('fields_merged', 0),
            'enrichment_operations': enrichment_count,
            'confidence_distribution': self._calculate_confidence_distribution(
                data_merge.get('confidence_scores', {})
            )
        }

    def _calculate_completeness(self, verification_data: Dict[str, Any]) -> float:
        """Calculate overall data completeness"""
        validation = verification_data.get('data_validation', {})
        metrics = validation.get('quality_metrics', {})
        return metrics.get('completeness_rate', 0)

    def _calculate_source_diversity(self, source_auth: Dict[str, Any]) -> float:
        """Calculate source diversity score"""
        sources = source_auth.get('authenticated_sources', [])
        if not sources:
            return 0

        unique_types = len(set(s.get('source_type', 'unknown') for s in sources))
        unique_levels = len(set(s.get('authentication_level', 'unknown') for s in sources))

        # Diversity score based on variety of source types and authentication levels
        diversity = (unique_types + unique_levels) / (len(sources) * 2) * 100
        return min(100, diversity * 2)  # Scale up and cap at 100

    def _calculate_validation_rate(self, data_validation: Dict[str, Any]) -> float:
        """Calculate validation success rate"""
        metrics = data_validation.get('quality_metrics', {})
        total = metrics.get('total_validations', 0)
        passed = metrics.get('passed_validations', 0)
        return (passed / total * 100) if total > 0 else 0

    def _calculate_confidence_distribution(self, confidence_scores: Dict[str, float]) -> Dict[str, int]:
        """Calculate distribution of confidence scores"""
        distribution = {
            'high': 0,      # > 0.8
            'medium': 0,    # 0.6 - 0.8
            'low': 0        # < 0.6
        }

        for field, score in confidence_scores.items():
            if field == 'overall':
                continue
            if score > 0.8:
                distribution['high'] += 1
            elif score >= 0.6:
                distribution['medium'] += 1
            else:
                distribution['low'] += 1

        return distribution

    def _generate_recommendations(self, metrics: Dict[str, float], category: str) -> List[str]:
        """Generate improvement recommendations based on metrics"""
        recommendations = []
        thresholds = self.alert_thresholds.get(category, {})

        # Check quality score
        if metrics['quality_score'] < thresholds.get('quality_score', 75):
            recommendations.append(
                f"Quality score ({metrics['quality_score']:.1f}%) below threshold. "
                f"Consider adding more authoritative sources."
            )

        # Check completeness
        if metrics['completeness'] < thresholds.get('completeness', 80):
            recommendations.append(
                f"Data completeness ({metrics['completeness']:.1f}%) needs improvement. "
                f"Enrich data with additional sources."
            )

        # Check source diversity
        if metrics['source_diversity'] < 50:
            recommendations.append(
                "Low source diversity. Add varied source types for better coverage."
            )

        # Check conflict rate
        if metrics['conflict_rate'] > 0.2:
            recommendations.append(
                f"High conflict rate ({metrics['conflict_rate']:.1%}). "
                f"Review conflict resolution rules."
            )

        # Check validation rate
        if metrics['validation_rate'] < 80:
            recommendations.append(
                f"Validation rate ({metrics['validation_rate']:.1f}%) can be improved. "
                f"Review validation rules and data quality."
            )

        # Check merge confidence
        if metrics['merge_confidence'] < 0.7:
            recommendations.append(
                "Low merge confidence. Consider manual review of merged data."
            )

        if not recommendations:
            recommendations.append("Data quality meets all thresholds. Continue monitoring.")

        return recommendations

    def _check_quality_thresholds(self, metrics: Dict[str, float], category: str) -> List[Dict[str, Any]]:
        """Check for quality threshold violations and generate alerts"""
        alerts = []
        thresholds = self.alert_thresholds.get(category, {})

        for metric_name, metric_value in metrics.items():
            if metric_name in thresholds:
                threshold = thresholds[metric_name]
                if isinstance(metric_value, (int, float)) and metric_value < threshold:
                    severity = self._determine_alert_severity(metric_value, threshold)
                    alerts.append({
                        'metric': metric_name,
                        'value': metric_value,
                        'threshold': threshold,
                        'severity': severity,
                        'message': f"{metric_name} ({metric_value:.1f}) below threshold ({threshold})",
                        'timestamp': datetime.now().isoformat()
                    })

        return alerts

    def _determine_alert_severity(self, value: float, threshold: float) -> str:
        """Determine alert severity based on how far below threshold"""
        percentage = (value / threshold * 100) if threshold > 0 else 0

        if percentage >= 90:
            return 'LOW'
        elif percentage >= 75:
            return 'MEDIUM'
        elif percentage >= 50:
            return 'HIGH'
        else:
            return 'CRITICAL'

    def _assess_compliance(self, verification_data: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Assess regulatory compliance status"""
        compliance_status = {
            'compliant': True,
            'requirements_met': [],
            'requirements_missing': [],
            'regulatory_bodies': []
        }

        # Check validation compliance
        validation = verification_data.get('data_validation', {})
        compliance_summary = validation.get('compliance_summary', {})

        if not compliance_summary.get('compliant', True):
            compliance_status['compliant'] = False
            compliance_status['requirements_missing'].extend(
                compliance_summary.get('regulatory_flags', [])
            )

        # Check merge compliance
        merge = verification_data.get('data_merge', {})
        qa_validation = merge.get('quality_assurance', {})

        if not qa_validation.get('passed', True):
            compliance_status['compliant'] = False
            compliance_status['requirements_missing'].extend(
                qa_validation.get('issues', [])
            )

        # Check geographic compliance
        geographic = merge.get('geographic_consolidation', {})
        regulatory_compliance = geographic.get('regulatory_compliance', {})

        for body, compliance in regulatory_compliance.items():
            compliance_status['regulatory_bodies'].append(body)
            if compliance.get('data_available'):
                compliance_status['requirements_met'].extend(
                    compliance.get('requirements', [])
                )

        return compliance_status

    def _generate_report_id(self, category: str, process_id: Optional[str]) -> str:
        """Generate unique report ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        if process_id:
            return f"VR-{category}-{process_id}-{timestamp}"
        else:
            return f"VR-{category}-{timestamp}"

    def _update_category_metrics(self, category: str, metrics: Dict[str, float], summary: Dict[str, Any]) -> None:
        """Update stored metrics for a category"""
        category_metric = CategoryMetrics(
            category=category,
            quality_score=metrics.get('quality_score', 0),
            completeness=metrics.get('completeness', 0),
            accuracy=metrics.get('validation_rate', 0),
            consistency=1 - metrics.get('conflict_rate', 0),
            timeliness=self._calculate_timeliness(summary),
            source_coverage=summary.get('total_sources', 0),
            validation_passes=summary.get('validation_passes', 0),
            validation_failures=summary.get('validation_failures', 0),
            conflict_count=summary.get('conflicts_detected', 0),
            merge_count=summary.get('fields_merged', 0)
        )

        self.category_metrics[category] = category_metric

    def _calculate_timeliness(self, summary: Dict[str, Any]) -> float:
        """Calculate timeliness score (placeholder for actual implementation)"""
        # This would check data freshness in real implementation
        return 85.0

    async def generate_source_contribution_analysis(self,
                                                   verification_history: List[Dict[str, Any]],
                                                   category: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze source contributions and value

        Args:
            verification_history: Historical verification data
            category: Optional specific category

        Returns:
            Source contribution analysis
        """
        source_stats = defaultdict(lambda: {
            'contribution_count': 0,
            'quality_scores': [],
            'conflict_participation': 0,
            'successful_merges': 0,
            'coverage_areas': set()
        })

        # Analyze verification history
        for verification in verification_history:
            if category and verification.get('category') != category:
                continue

            # Track source authentication
            source_auth = verification.get('source_authentication', {})
            for source in source_auth.get('authenticated_sources', []):
                source_name = source.get('source_name', 'unknown')
                source_stats[source_name]['contribution_count'] += 1
                source_stats[source_name]['quality_scores'].append(
                    source.get('weight', 0) / 10 * 100
                )
                source_stats[source_name]['coverage_areas'].add(
                    verification.get('category', 'unknown')
                )

            # Track conflict participation
            conflicts = verification.get('conflict_resolution', {}).get('conflicts', [])
            for conflict in conflicts:
                for source in conflict.get('sources', []):
                    source_stats[source]['conflict_participation'] += 1

            # Track successful merges
            merge_records = verification.get('data_merge', {}).get('audit_trail', {}).get('merge_records', [])
            for record in merge_records:
                for source in record.get('sources_used', []):
                    source_stats[source]['successful_merges'] += 1

        # Calculate source contributions
        contributions = []
        for source_name, stats in source_stats.items():
            quality_score = statistics.mean(stats['quality_scores']) if stats['quality_scores'] else 0
            reliability_score = stats['successful_merges'] / max(stats['contribution_count'], 1) * 100
            conflict_rate = stats['conflict_participation'] / max(stats['contribution_count'], 1)

            # Calculate composite value score
            value_score = (
                quality_score * 0.4 +
                reliability_score * 0.3 +
                (1 - conflict_rate) * 100 * 0.2 +
                len(stats['coverage_areas']) * 10 * 0.1
            )

            contribution = SourceContribution(
                source_name=source_name,
                contribution_count=stats['contribution_count'],
                quality_score=quality_score,
                reliability_score=reliability_score,
                coverage_areas=list(stats['coverage_areas']),
                conflict_rate=conflict_rate,
                last_update=datetime.now(),
                value_score=value_score
            )

            contributions.append(contribution)
            self.source_contributions[source_name] = contribution

        # Sort by value score
        contributions.sort(key=lambda x: x.value_score, reverse=True)

        return {
            'category': category or 'all',
            'analysis_timestamp': datetime.now().isoformat(),
            'total_sources': len(contributions),
            'top_contributors': [c.model_dump() for c in contributions[:10]],
            'source_rankings': {
                'by_quality': sorted(contributions, key=lambda x: x.quality_score, reverse=True)[:5],
                'by_reliability': sorted(contributions, key=lambda x: x.reliability_score, reverse=True)[:5],
                'by_coverage': sorted(contributions, key=lambda x: len(x.coverage_areas), reverse=True)[:5]
            },
            'recommendations': self._generate_source_recommendations(contributions)
        }

    def _generate_source_recommendations(self, contributions: List[SourceContribution]) -> List[str]:
        """Generate recommendations for source optimization"""
        recommendations = []

        # Check for low-value sources
        low_value = [c for c in contributions if c.value_score < 40]
        if low_value:
            recommendations.append(
                f"Consider removing {len(low_value)} low-value sources with scores below 40"
            )

        # Check for high-conflict sources
        high_conflict = [c for c in contributions if c.conflict_rate > 0.3]
        if high_conflict:
            sources = ', '.join([c.source_name for c in high_conflict[:3]])
            recommendations.append(
                f"Review high-conflict sources: {sources}"
            )

        # Check for limited coverage
        single_area = [c for c in contributions if len(c.coverage_areas) == 1 and c.contribution_count > 10]
        if single_area:
            recommendations.append(
                f"{len(single_area)} sources limited to single category. Consider expanding coverage."
            )

        # Identify best performers
        if contributions:
            top_performer = contributions[0]
            recommendations.append(
                f"Top performer: {top_performer.source_name} (value score: {top_performer.value_score:.1f})"
            )

        return recommendations

    async def generate_quality_trends(self,
                                    category: str,
                                    time_period: int = 30,
                                    period_type: str = 'daily') -> Dict[str, Any]:
        """
        Generate quality trend analysis

        Args:
            category: Pharmaceutical category
            time_period: Number of days to analyze
            period_type: 'daily', 'weekly', or 'monthly'

        Returns:
            Quality trend analysis
        """
        cutoff_date = datetime.now() - timedelta(days=time_period)

        # Get historical metrics
        relevant_reports = [
            r for r in self.report_history
            if r.category == category and r.timestamp >= cutoff_date
        ]

        if not relevant_reports:
            return {'message': f'No trend data available for {category}'}

        # Group by period
        period_data = defaultdict(list)
        for report in relevant_reports:
            if period_type == 'daily':
                period_key = report.timestamp.date()
            elif period_type == 'weekly':
                period_key = report.timestamp.isocalendar()[1]  # Week number
            else:  # monthly
                period_key = report.timestamp.month

            period_data[period_key].append(report.quality_score)

        # Calculate trends
        periods = sorted(period_data.keys())
        quality_scores = [statistics.mean(period_data[p]) for p in periods]

        # Calculate statistics
        improvement_rate = 0
        if len(quality_scores) > 1:
            improvement_rate = (quality_scores[-1] - quality_scores[0]) / len(quality_scores)

        volatility = statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0

        # Simple forecast (linear extrapolation)
        forecast = None
        if len(quality_scores) >= 3:
            recent_trend = (quality_scores[-1] - quality_scores[-3]) / 2
            forecast = quality_scores[-1] + recent_trend

        trend = QualityTrend(
            period=period_type,
            start_date=relevant_reports[0].timestamp,
            end_date=relevant_reports[-1].timestamp,
            category=category,
            quality_scores=quality_scores,
            improvement_rate=improvement_rate,
            volatility=volatility,
            forecast=forecast
        )

        self.quality_trends[category].append(trend)

        return {
            'category': category,
            'period_type': period_type,
            'time_period_days': time_period,
            'data_points': len(quality_scores),
            'current_score': quality_scores[-1] if quality_scores else 0,
            'average_score': statistics.mean(quality_scores) if quality_scores else 0,
            'min_score': min(quality_scores) if quality_scores else 0,
            'max_score': max(quality_scores) if quality_scores else 0,
            'improvement_rate': improvement_rate,
            'volatility': volatility,
            'forecast': forecast,
            'trend_direction': 'improving' if improvement_rate > 0 else 'declining' if improvement_rate < 0 else 'stable',
            'recommendations': self._generate_trend_recommendations(improvement_rate, volatility, quality_scores)
        }

    def _generate_trend_recommendations(self, improvement_rate: float,
                                       volatility: float,
                                       scores: List[float]) -> List[str]:
        """Generate recommendations based on trends"""
        recommendations = []

        if improvement_rate < -0.5:
            recommendations.append("Quality declining. Investigate recent changes in data sources.")
        elif improvement_rate > 1:
            recommendations.append("Strong improvement trend. Maintain current practices.")

        if volatility > 15:
            recommendations.append("High volatility in quality scores. Standardize data collection processes.")

        if scores and scores[-1] < 60:
            recommendations.append("Current quality below acceptable threshold. Immediate action required.")

        if not recommendations:
            recommendations.append("Quality metrics stable. Continue monitoring.")

        return recommendations

    async def create_real_time_status(self,
                                    process_id: str,
                                    current_stage: str,
                                    progress_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create real-time verification status update

        Args:
            process_id: Process tracking ID
            current_stage: Current verification stage
            progress_data: Current progress information

        Returns:
            Real-time status update
        """
        status = {
            'process_id': process_id,
            'timestamp': datetime.now().isoformat(),
            'current_stage': current_stage,
            'progress': progress_data.get('progress', 0),
            'status': progress_data.get('status', 'processing'),
            'stages_completed': progress_data.get('stages_completed', []),
            'current_metrics': {},
            'estimated_completion': None,
            'alerts': []
        }

        # Add current metrics if available
        if 'metrics' in progress_data:
            status['current_metrics'] = {
                'sources_processed': progress_data['metrics'].get('sources_processed', 0),
                'conflicts_found': progress_data['metrics'].get('conflicts_found', 0),
                'validations_performed': progress_data['metrics'].get('validations_performed', 0),
                'current_quality_score': progress_data['metrics'].get('quality_score', 0)
            }

        # Estimate completion
        if progress_data.get('progress', 0) > 0:
            elapsed_time = progress_data.get('elapsed_seconds', 0)
            if elapsed_time > 0 and progress_data['progress'] < 100:
                remaining_time = (elapsed_time / progress_data['progress']) * (100 - progress_data['progress'])
                status['estimated_completion'] = (
                    datetime.now() + timedelta(seconds=remaining_time)
                ).isoformat()

        # Check for alerts during processing
        if 'quality_score' in progress_data.get('metrics', {}):
            score = progress_data['metrics']['quality_score']
            if score < 60:
                status['alerts'].append({
                    'type': 'QUALITY_WARNING',
                    'message': f'Quality score {score} below threshold during processing',
                    'severity': 'HIGH'
                })

        logger.info(f"Real-time status for {process_id}: {current_stage} ({progress_data.get('progress', 0)}%)")

        return status

    async def generate_compliance_report(self,
                                        verification_data: Dict[str, Any],
                                        category: str,
                                        regulatory_body: str) -> VerificationReport:
        """
        Generate comprehensive compliance report for regulatory audit

        Args:
            verification_data: Complete verification data
            category: Pharmaceutical category
            regulatory_body: Regulatory body (FDA, EMA, etc.)

        Returns:
            Compliance-focused verification report
        """
        requirements = self.compliance_requirements.get(regulatory_body, [])

        # Assess compliance for each requirement
        compliance_assessment = {}
        for requirement in requirements:
            compliance_assessment[requirement] = self._assess_requirement_compliance(
                verification_data, requirement
            )

        # Calculate compliance score
        compliant_count = sum(1 for v in compliance_assessment.values() if v['compliant'])
        compliance_score = (compliant_count / len(requirements) * 100) if requirements else 0

        # Generate compliance summary
        summary = {
            'regulatory_body': regulatory_body,
            'requirements_assessed': len(requirements),
            'requirements_met': compliant_count,
            'compliance_score': compliance_score,
            'category': category,
            'assessment_date': datetime.now().isoformat()
        }

        # Generate detailed compliance information
        details = {
            'requirement_assessments': compliance_assessment,
            'data_integrity': self._assess_data_integrity(verification_data),
            'audit_trail_completeness': self._assess_audit_trail(verification_data),
            'source_documentation': self._assess_source_documentation(verification_data),
            'validation_evidence': self._assess_validation_evidence(verification_data)
        }

        # Generate recommendations
        recommendations = []
        for requirement, assessment in compliance_assessment.items():
            if not assessment['compliant']:
                recommendations.append(
                    f"Address {requirement}: {assessment.get('gap', 'Review required')}"
                )

        # Create compliance report
        report = VerificationReport(
            report_id=self._generate_report_id(f'COMPLIANCE-{regulatory_body}', None),
            report_type=ReportType.COMPLIANCE,
            category=category,
            quality_score=compliance_score,
            summary=summary,
            details=details,
            metrics={'compliance_score': compliance_score},
            recommendations=recommendations,
            compliance_status={
                'regulatory_body': regulatory_body,
                'compliant': compliance_score >= 80,  # 80% threshold for compliance
                'score': compliance_score,
                'gaps': [r for r, a in compliance_assessment.items() if not a['compliant']]
            },
            audit_trail={
                'report_type': 'REGULATORY_COMPLIANCE',
                'regulatory_body': regulatory_body,
                'generation_timestamp': datetime.now().isoformat(),
                'requirements_framework': requirements
            }
        )

        self.report_history.append(report)

        logger.info(f"Generated compliance report for {regulatory_body}: Score {compliance_score:.1f}%")

        return report

    def _assess_requirement_compliance(self, verification_data: Dict[str, Any],
                                      requirement: str) -> Dict[str, Any]:
        """Assess compliance for specific requirement"""
        # This would be expanded with specific requirement checks
        assessment = {
            'requirement': requirement,
            'compliant': True,  # Default, would be determined by specific checks
            'evidence': [],
            'gap': None
        }

        # Example compliance checks
        if '21_CFR_Part_11' in requirement:
            # Check for electronic signatures and audit trails
            if 'audit_trail' in verification_data:
                assessment['evidence'].append('Audit trail present')
            else:
                assessment['compliant'] = False
                assessment['gap'] = 'Missing audit trail for 21 CFR Part 11'

        elif 'GMP' in requirement or 'GCP' in requirement or 'GLP' in requirement:
            # Check for quality controls
            quality_score = verification_data.get('quality_score', 0)
            if quality_score >= 75:
                assessment['evidence'].append(f'Quality score {quality_score} meets GxP standards')
            else:
                assessment['compliant'] = False
                assessment['gap'] = f'Quality score {quality_score} below GxP requirement'

        return assessment

    def _assess_data_integrity(self, verification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess data integrity for compliance"""
        return {
            'complete': bool(verification_data.get('data_validation')),
            'accurate': verification_data.get('data_validation', {}).get('quality_metrics', {}).get('accuracy', 0) > 80,
            'consistent': verification_data.get('conflict_resolution', {}).get('conflict_rate', 1) < 0.2,
            'timely': True,  # Would check data freshness
            'traceable': bool(verification_data.get('audit_trail'))
        }

    def _assess_audit_trail(self, verification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess audit trail completeness"""
        audit_components = {
            'source_tracking': bool(verification_data.get('source_authentication')),
            'conflict_documentation': bool(verification_data.get('conflict_resolution', {}).get('audit_trail')),
            'validation_records': bool(verification_data.get('data_validation', {}).get('audit_trail')),
            'merge_documentation': bool(verification_data.get('data_merge', {}).get('audit_trail'))
        }

        completeness = sum(audit_components.values()) / len(audit_components) * 100

        return {
            'completeness_score': completeness,
            'components': audit_components,
            'compliant': completeness >= 90
        }

    def _assess_source_documentation(self, verification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess source documentation for compliance"""
        sources = verification_data.get('source_authentication', {}).get('authenticated_sources', [])

        return {
            'total_sources': len(sources),
            'authenticated_sources': sum(1 for s in sources if s.get('authenticated')),
            'documented_sources': sum(1 for s in sources if s.get('documentation')),
            'primary_sources': sum(1 for s in sources if s.get('weight', 0) >= 8)
        }

    def _assess_validation_evidence(self, verification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess validation evidence for compliance"""
        validation = verification_data.get('data_validation', {})

        return {
            'validations_performed': validation.get('quality_metrics', {}).get('total_validations', 0),
            'validations_passed': validation.get('quality_metrics', {}).get('passed_validations', 0),
            'validation_rate': validation.get('quality_metrics', {}).get('validation_rate', 0),
            'compliance_checks': len(validation.get('compliance_summary', {}).get('regulatory_flags', []))
        }

    def get_report_history(self, category: Optional[str] = None,
                          report_type: Optional[ReportType] = None,
                          time_window: Optional[int] = 30) -> List[Dict[str, Any]]:
        """Get report generation history"""
        cutoff_date = datetime.now() - timedelta(days=time_window)

        relevant_reports = [
            r.model_dump() for r in self.report_history
            if r.timestamp >= cutoff_date and
            (not category or r.category == category) and
            (not report_type or r.report_type == report_type)
        ]

        return relevant_reports

    def get_category_metrics(self, category: str) -> Optional[Dict[str, Any]]:
        """Get current metrics for a category"""
        if category in self.category_metrics:
            return self.category_metrics[category].__dict__
        return None

    def get_alert_status(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get current alert status"""
        active_alerts = []

        for cat, metrics in self.category_metrics.items():
            if category and cat != category:
                continue

            thresholds = self.alert_thresholds.get(cat, {})

            if metrics.quality_score < thresholds.get('quality_score', 75):
                active_alerts.append({
                    'category': cat,
                    'alert_type': 'QUALITY_SCORE',
                    'current_value': metrics.quality_score,
                    'threshold': thresholds['quality_score'],
                    'severity': self._determine_alert_severity(
                        metrics.quality_score,
                        thresholds['quality_score']
                    )
                })

        return {
            'timestamp': datetime.now().isoformat(),
            'active_alerts': active_alerts,
            'alert_count': len(active_alerts),
            'categories_affected': list(set(a['category'] for a in active_alerts))
        }