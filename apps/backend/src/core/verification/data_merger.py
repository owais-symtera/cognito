"""
Story 3.4: Validated Data Merging & Consolidation
Intelligent merging of validated data with comprehensive pharmaceutical audit compliance
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

logger = logging.getLogger(__name__)


class MergeStrategy(IntEnum):
    """Strategies for merging conflicting data"""
    HIGHEST_CONFIDENCE = 1    # Use data with highest confidence score
    MOST_RECENT = 2          # Use most recent data
    CONSENSUS = 3            # Use consensus from multiple sources
    WEIGHTED_AVERAGE = 4     # For numeric data - weighted average
    UNION = 5                # Combine all unique values
    INTERSECTION = 6         # Only common values
    SOURCE_PRIORITY = 7      # Based on source authentication level


class DataType(IntEnum):
    """Types of pharmaceutical data for merging logic"""
    NUMERIC = 1       # Dosages, prices, quantities
    CATEGORICAL = 2   # Drug classes, categories
    TEXT = 3          # Descriptions, notes
    DATE = 4          # Approval dates, expiry dates
    IDENTIFIER = 5    # Patent numbers, NDC codes
    BOOLEAN = 6       # Yes/no fields
    LIST = 7          # Side effects, indications
    STRUCTURED = 8    # Complex nested data


@dataclass
class MergeConfiguration:
    """Configuration for data merging per field"""
    field_name: str
    data_type: DataType
    merge_strategy: MergeStrategy
    required: bool = True
    temporal_weight: float = 0.2  # Weight for recency
    confidence_weight: float = 0.5  # Weight for confidence score
    source_weight: float = 0.3  # Weight for source authority


class MergeRecord(BaseModel):
    """Record of a merge operation for audit trail"""
    field_name: str
    original_values: List[Dict[str, Any]]
    merged_value: Any
    merge_strategy: str
    confidence_score: float
    sources_used: List[str]
    timestamp: datetime = Field(default_factory=datetime.now)
    audit_info: Dict[str, Any] = Field(default_factory=dict)


class GeographicData(BaseModel):
    """Geographic pharmaceutical market data"""
    region: str
    country: Optional[str] = None
    regulatory_body: str
    market_size: Optional[float] = None
    currency: Optional[str] = None
    compliance_requirements: List[str] = Field(default_factory=list)


class TemporalData(BaseModel):
    """Time-series pharmaceutical data"""
    timestamp: datetime
    value: Any
    data_type: str
    confidence: float
    source: str
    validity_period: Optional[timedelta] = None


class DataMerger:
    """Main engine for merging and consolidating pharmaceutical data"""

    def __init__(self):
        self.merge_configs = self._initialize_merge_configs()
        self.merge_history: List[MergeRecord] = []
        self.geographic_handlers = self._initialize_geographic_handlers()

    def _initialize_merge_configs(self) -> Dict[str, List[MergeConfiguration]]:
        """Initialize merge configurations for different pharmaceutical categories"""
        configs = {}

        # Drug Information merging
        configs['drug_info'] = [
            MergeConfiguration('drug_name', DataType.IDENTIFIER, MergeStrategy.HIGHEST_CONFIDENCE),
            MergeConfiguration('active_ingredient', DataType.TEXT, MergeStrategy.CONSENSUS),
            MergeConfiguration('dosage', DataType.NUMERIC, MergeStrategy.WEIGHTED_AVERAGE),
            MergeConfiguration('price', DataType.NUMERIC, MergeStrategy.MOST_RECENT),
            MergeConfiguration('side_effects', DataType.LIST, MergeStrategy.UNION),
            MergeConfiguration('indications', DataType.LIST, MergeStrategy.UNION),
            MergeConfiguration('manufacturer', DataType.CATEGORICAL, MergeStrategy.SOURCE_PRIORITY),
            MergeConfiguration('approval_date', DataType.DATE, MergeStrategy.HIGHEST_CONFIDENCE)
        ]

        # Clinical Trials merging
        configs['clinical_trials'] = [
            MergeConfiguration('trial_id', DataType.IDENTIFIER, MergeStrategy.HIGHEST_CONFIDENCE),
            MergeConfiguration('enrollment', DataType.NUMERIC, MergeStrategy.MOST_RECENT),
            MergeConfiguration('phase', DataType.CATEGORICAL, MergeStrategy.CONSENSUS),
            MergeConfiguration('status', DataType.CATEGORICAL, MergeStrategy.MOST_RECENT),
            MergeConfiguration('primary_outcome', DataType.TEXT, MergeStrategy.HIGHEST_CONFIDENCE),
            MergeConfiguration('adverse_events', DataType.LIST, MergeStrategy.UNION),
            MergeConfiguration('sites', DataType.LIST, MergeStrategy.UNION)
        ]

        # Patent Information merging
        configs['patents'] = [
            MergeConfiguration('patent_number', DataType.IDENTIFIER, MergeStrategy.HIGHEST_CONFIDENCE),
            MergeConfiguration('expiry_date', DataType.DATE, MergeStrategy.CONSENSUS),
            MergeConfiguration('claims', DataType.LIST, MergeStrategy.UNION),
            MergeConfiguration('assignee', DataType.TEXT, MergeStrategy.SOURCE_PRIORITY),
            MergeConfiguration('priority_date', DataType.DATE, MergeStrategy.HIGHEST_CONFIDENCE)
        ]

        # Market Analysis merging
        configs['market_analysis'] = [
            MergeConfiguration('market_size', DataType.NUMERIC, MergeStrategy.WEIGHTED_AVERAGE),
            MergeConfiguration('growth_rate', DataType.NUMERIC, MergeStrategy.WEIGHTED_AVERAGE),
            MergeConfiguration('market_share', DataType.NUMERIC, MergeStrategy.CONSENSUS),
            MergeConfiguration('competitors', DataType.LIST, MergeStrategy.UNION),
            MergeConfiguration('forecast', DataType.STRUCTURED, MergeStrategy.HIGHEST_CONFIDENCE)
        ]

        # Regulatory merging
        configs['regulatory'] = [
            MergeConfiguration('application_number', DataType.IDENTIFIER, MergeStrategy.HIGHEST_CONFIDENCE),
            MergeConfiguration('approval_status', DataType.CATEGORICAL, MergeStrategy.MOST_RECENT),
            MergeConfiguration('submission_date', DataType.DATE, MergeStrategy.CONSENSUS),
            MergeConfiguration('conditions', DataType.LIST, MergeStrategy.UNION),
            MergeConfiguration('review_timeline', DataType.NUMERIC, MergeStrategy.WEIGHTED_AVERAGE)
        ]

        return configs

    def _initialize_geographic_handlers(self) -> Dict[str, GeographicData]:
        """Initialize geographic data handlers for global markets"""
        handlers = {
            'US': GeographicData(
                region='North America',
                country='United States',
                regulatory_body='FDA',
                compliance_requirements=['NDA', 'ANDA', 'BLA', 'GMP', 'GLP']
            ),
            'EU': GeographicData(
                region='Europe',
                regulatory_body='EMA',
                compliance_requirements=['MAA', 'GMP', 'GCP', 'GDPR']
            ),
            'JP': GeographicData(
                region='Asia Pacific',
                country='Japan',
                regulatory_body='PMDA',
                compliance_requirements=['JNDA', 'GMP', 'GCP']
            ),
            'CN': GeographicData(
                region='Asia Pacific',
                country='China',
                regulatory_body='NMPA',
                compliance_requirements=['IND', 'NDA', 'GMP']
            ),
            'IN': GeographicData(
                region='Asia Pacific',
                country='India',
                regulatory_body='CDSCO',
                compliance_requirements=['IND', 'NDA', 'GMP', 'Schedule Y']
            )
        }
        return handlers

    async def merge_complementary_data(self, data_sources: List[Dict[str, Any]],
                                      category: str) -> Tuple[Dict[str, Any], List[MergeRecord]]:
        """
        Merge complementary data from multiple sources

        Args:
            data_sources: List of validated data from different sources
            category: Pharmaceutical category

        Returns:
            Merged data and audit records
        """
        if not data_sources:
            return {}, []

        merge_config = self.merge_configs.get(category, [])
        merged_data = {}
        merge_records = []

        # Group data by field
        field_values = {}
        for source_data in data_sources:
            source_name = source_data.get('source', 'unknown')
            confidence = source_data.get('confidence_score', 0.5)
            timestamp = source_data.get('timestamp', datetime.now())

            for field, value in source_data.items():
                if field in ['source', 'confidence_score', 'timestamp']:
                    continue

                if field not in field_values:
                    field_values[field] = []

                field_values[field].append({
                    'value': value,
                    'source': source_name,
                    'confidence': confidence,
                    'timestamp': timestamp
                })

        # Apply merge strategy for each field
        for config in merge_config:
            field = config.field_name
            if field not in field_values:
                if config.required:
                    logger.warning(f"Required field {field} not found in any source")
                continue

            values = field_values[field]
            merged_value, merge_confidence = await self._apply_merge_strategy(
                values, config
            )

            merged_data[field] = merged_value

            # Create audit record
            merge_record = MergeRecord(
                field_name=field,
                original_values=values,
                merged_value=merged_value,
                merge_strategy=config.merge_strategy.name,
                confidence_score=merge_confidence,
                sources_used=[v['source'] for v in values],
                audit_info={
                    'category': category,
                    'data_type': config.data_type.name,
                    'value_count': len(values)
                }
            )
            merge_records.append(merge_record)
            self.merge_history.append(merge_record)

        # Handle remaining fields not in config (preserve them)
        for field, values in field_values.items():
            if field not in merged_data:
                # Use highest confidence value for unconfigured fields
                best_value = max(values, key=lambda x: x['confidence'])
                merged_data[field] = best_value['value']

        return merged_data, merge_records

    async def _apply_merge_strategy(self, values: List[Dict[str, Any]],
                                   config: MergeConfiguration) -> Tuple[Any, float]:
        """Apply specific merge strategy to field values"""

        if config.merge_strategy == MergeStrategy.HIGHEST_CONFIDENCE:
            best = max(values, key=lambda x: x['confidence'])
            return best['value'], best['confidence']

        elif config.merge_strategy == MergeStrategy.MOST_RECENT:
            most_recent = max(values, key=lambda x: x['timestamp'])
            return most_recent['value'], most_recent['confidence']

        elif config.merge_strategy == MergeStrategy.CONSENSUS:
            # Find most common value
            value_counts = {}
            total_confidence = 0
            for item in values:
                val_str = str(item['value'])
                if val_str not in value_counts:
                    value_counts[val_str] = {'count': 0, 'confidence': 0, 'value': item['value']}
                value_counts[val_str]['count'] += 1
                value_counts[val_str]['confidence'] += item['confidence']
                total_confidence += item['confidence']

            # Get value with highest weighted count
            best = max(value_counts.values(),
                      key=lambda x: x['count'] * (x['confidence'] / max(x['count'], 1)))
            avg_confidence = best['confidence'] / best['count']
            return best['value'], avg_confidence

        elif config.merge_strategy == MergeStrategy.WEIGHTED_AVERAGE:
            if config.data_type != DataType.NUMERIC:
                # Fall back to highest confidence for non-numeric
                best = max(values, key=lambda x: x['confidence'])
                return best['value'], best['confidence']

            # Calculate weighted average
            total_weight = 0
            weighted_sum = 0
            for item in values:
                try:
                    numeric_val = float(item['value'])
                    # Calculate combined weight
                    recency_weight = self._calculate_recency_weight(item['timestamp'])
                    combined_weight = (
                        config.confidence_weight * item['confidence'] +
                        config.temporal_weight * recency_weight
                    )
                    weighted_sum += numeric_val * combined_weight
                    total_weight += combined_weight
                except (ValueError, TypeError):
                    continue

            if total_weight > 0:
                avg_value = weighted_sum / total_weight
                avg_confidence = sum(v['confidence'] for v in values) / len(values)
                return avg_value, avg_confidence
            else:
                best = max(values, key=lambda x: x['confidence'])
                return best['value'], best['confidence']

        elif config.merge_strategy == MergeStrategy.UNION:
            # Combine all unique values (for lists)
            all_values = []
            total_confidence = 0
            for item in values:
                if isinstance(item['value'], list):
                    all_values.extend(item['value'])
                else:
                    all_values.append(item['value'])
                total_confidence += item['confidence']

            unique_values = list(set(str(v) for v in all_values))
            avg_confidence = total_confidence / len(values) if values else 0
            return unique_values, avg_confidence

        elif config.merge_strategy == MergeStrategy.INTERSECTION:
            # Only common values (for lists)
            if not values:
                return [], 0

            common_values = None
            total_confidence = 0
            for item in values:
                item_set = set(item['value']) if isinstance(item['value'], list) else {item['value']}
                if common_values is None:
                    common_values = item_set
                else:
                    common_values = common_values.intersection(item_set)
                total_confidence += item['confidence']

            avg_confidence = total_confidence / len(values)
            return list(common_values) if common_values else [], avg_confidence

        elif config.merge_strategy == MergeStrategy.SOURCE_PRIORITY:
            # Use source authentication levels (from source_authenticator)
            # Import here to avoid circular dependency
            from .source_authenticator import SourceWeights

            def get_source_priority(source: str) -> int:
                source_lower = source.lower()
                if any(api in source_lower for api in ['openai', 'anthropic', 'perplexity', 'grok', 'gemini', 'tavily']):
                    return SourceWeights.PAID_APIS
                elif '.gov' in source_lower or any(reg in source_lower for reg in ['fda', 'ema', 'pmda']):
                    return SourceWeights.GOVERNMENT
                elif any(journal in source_lower for journal in ['pubmed', 'nejm', 'lancet', 'jama']):
                    return SourceWeights.PEER_REVIEWED
                elif any(industry in source_lower for industry in ['pharma', 'association', 'society']):
                    return SourceWeights.INDUSTRY
                elif any(company in source_lower for company in ['pfizer', 'merck', 'novartis', 'roche']):
                    return SourceWeights.COMPANY
                elif any(news in source_lower for news in ['reuters', 'bloomberg', 'news']):
                    return SourceWeights.NEWS
                else:
                    return SourceWeights.UNKNOWN

            best = max(values, key=lambda x: (get_source_priority(x['source']), x['confidence']))
            return best['value'], best['confidence']

        else:
            # Default to highest confidence
            best = max(values, key=lambda x: x['confidence'])
            return best['value'], best['confidence']

    def _calculate_recency_weight(self, timestamp: datetime) -> float:
        """Calculate weight based on data recency"""
        now = datetime.now()
        age_days = (now - timestamp).days

        if age_days <= 1:
            return 1.0
        elif age_days <= 7:
            return 0.9
        elif age_days <= 30:
            return 0.7
        elif age_days <= 90:
            return 0.5
        elif age_days <= 365:
            return 0.3
        else:
            return 0.1

    async def enrich_incomplete_records(self, primary_data: Dict[str, Any],
                                       supplementary_sources: List[Dict[str, Any]],
                                       category: str) -> Tuple[Dict[str, Any], List[MergeRecord]]:
        """
        Enrich incomplete records with data from supplementary sources

        Args:
            primary_data: Primary data record (potentially incomplete)
            supplementary_sources: Additional data sources for enrichment
            category: Pharmaceutical category

        Returns:
            Enriched data and audit records
        """
        enriched_data = primary_data.copy()
        merge_records = []

        # Identify missing or low-quality fields
        merge_config = self.merge_configs.get(category, [])
        required_fields = {config.field_name for config in merge_config if config.required}
        missing_fields = required_fields - set(primary_data.keys())

        # Also check for None or empty values
        incomplete_fields = missing_fields.copy()
        for field in primary_data:
            if primary_data[field] is None or primary_data[field] == '':
                incomplete_fields.add(field)

        logger.info(f"Enriching {len(incomplete_fields)} incomplete fields")

        # Enrich from supplementary sources
        for field in incomplete_fields:
            field_values = []

            for source in supplementary_sources:
                if field in source and source[field] is not None and source[field] != '':
                    field_values.append({
                        'value': source[field],
                        'source': source.get('source', 'unknown'),
                        'confidence': source.get('confidence_score', 0.5),
                        'timestamp': source.get('timestamp', datetime.now())
                    })

            if field_values:
                # Find the config for this field
                field_config = next((c for c in merge_config if c.field_name == field), None)
                if field_config:
                    merged_value, confidence = await self._apply_merge_strategy(field_values, field_config)
                else:
                    # Use highest confidence if no config
                    best = max(field_values, key=lambda x: x['confidence'])
                    merged_value = best['value']
                    confidence = best['confidence']

                enriched_data[field] = merged_value

                # Create audit record
                merge_record = MergeRecord(
                    field_name=field,
                    original_values=[{'primary': primary_data.get(field)}] + field_values,
                    merged_value=merged_value,
                    merge_strategy='ENRICHMENT',
                    confidence_score=confidence,
                    sources_used=[v['source'] for v in field_values],
                    audit_info={
                        'enrichment_type': 'missing_field' if field in missing_fields else 'empty_field',
                        'category': category
                    }
                )
                merge_records.append(merge_record)
                self.merge_history.append(merge_record)

        return enriched_data, merge_records

    async def handle_temporal_data(self, time_series_data: List[TemporalData],
                                  category: str) -> Dict[str, Any]:
        """
        Handle time-series pharmaceutical data with compliance tracking

        Args:
            time_series_data: List of temporal data points
            category: Pharmaceutical category

        Returns:
            Processed temporal data with trends and compliance info
        """
        if not time_series_data:
            return {}

        # Sort by timestamp
        sorted_data = sorted(time_series_data, key=lambda x: x.timestamp)

        # Group by data type
        grouped_data = {}
        for td in sorted_data:
            if td.data_type not in grouped_data:
                grouped_data[td.data_type] = []
            grouped_data[td.data_type].append(td)

        temporal_analysis = {}

        for data_type, series in grouped_data.items():
            # Extract values for analysis
            values = []
            timestamps = []
            for point in series:
                try:
                    if isinstance(point.value, (int, float)):
                        values.append(float(point.value))
                        timestamps.append(point.timestamp)
                except (ValueError, TypeError):
                    continue

            if len(values) >= 2:
                # Calculate trends
                trend = self._calculate_trend(timestamps, values)
                volatility = statistics.stdev(values) if len(values) > 1 else 0
                current_value = series[-1].value
                previous_value = series[-2].value if len(series) > 1 else None

                temporal_analysis[data_type] = {
                    'current_value': current_value,
                    'previous_value': previous_value,
                    'trend': trend,
                    'volatility': volatility,
                    'data_points': len(series),
                    'time_range': {
                        'start': series[0].timestamp.isoformat(),
                        'end': series[-1].timestamp.isoformat()
                    },
                    'sources': list(set(point.source for point in series)),
                    'average_confidence': sum(point.confidence for point in series) / len(series),
                    'audit_trail': {
                        'processing_timestamp': datetime.now().isoformat(),
                        'category': category,
                        'compliance_tracking': True
                    }
                }

                # Check for significant changes (compliance alert)
                if previous_value and isinstance(current_value, (int, float)) and isinstance(previous_value, (int, float)):
                    change_percent = abs((current_value - previous_value) / previous_value * 100)
                    if change_percent > 20:  # 20% change threshold
                        temporal_analysis[data_type]['compliance_alert'] = {
                            'type': 'SIGNIFICANT_CHANGE',
                            'change_percent': change_percent,
                            'requires_review': True
                        }
            else:
                # Single data point or non-numeric data
                temporal_analysis[data_type] = {
                    'current_value': series[-1].value if series else None,
                    'data_points': len(series),
                    'sources': list(set(point.source for point in series)),
                    'audit_trail': {
                        'processing_timestamp': datetime.now().isoformat(),
                        'category': category
                    }
                }

        return temporal_analysis

    def _calculate_trend(self, timestamps: List[datetime], values: List[float]) -> str:
        """Calculate trend from time series data"""
        if len(values) < 2:
            return 'insufficient_data'

        # Convert timestamps to numeric (days from first point)
        first_time = timestamps[0]
        x_values = [(t - first_time).days for t in timestamps]

        # Simple linear regression
        n = len(values)
        if n == 0:
            return 'no_data'

        x_mean = sum(x_values) / n
        y_mean = sum(values) / n

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        if denominator == 0:
            return 'stable'

        slope = numerator / denominator

        # Determine trend based on slope
        if slope > 0.01:
            return 'increasing'
        elif slope < -0.01:
            return 'decreasing'
        else:
            return 'stable'

    async def consolidate_geographic_data(self, regional_data: Dict[str, Dict[str, Any]],
                                         category: str) -> Dict[str, Any]:
        """
        Consolidate data from different geographic regions

        Args:
            regional_data: Data organized by region/country code
            category: Pharmaceutical category

        Returns:
            Consolidated global data with regional breakdowns
        """
        consolidated = {
            'global_summary': {},
            'regional_data': {},
            'regulatory_compliance': {},
            'market_coverage': []
        }

        all_values = {}

        for region_code, data in regional_data.items():
            if region_code in self.geographic_handlers:
                geo_info = self.geographic_handlers[region_code]

                # Store regional data
                consolidated['regional_data'][region_code] = {
                    'data': data,
                    'region': geo_info.region,
                    'country': geo_info.country,
                    'regulatory_body': geo_info.regulatory_body,
                    'compliance_requirements': geo_info.compliance_requirements
                }

                # Track compliance
                consolidated['regulatory_compliance'][geo_info.regulatory_body] = {
                    'region': region_code,
                    'requirements': geo_info.compliance_requirements,
                    'data_available': True
                }

                # Collect values for global summary
                for key, value in data.items():
                    if key not in all_values:
                        all_values[key] = []
                    all_values[key].append({
                        'value': value,
                        'region': region_code,
                        'confidence': data.get('confidence_score', 0.7)
                    })

        # Generate global summary
        merge_config = self.merge_configs.get(category, [])
        for field in all_values:
            field_config = next((c for c in merge_config if c.field_name == field), None)
            if field_config:
                # Apply appropriate merge strategy for global consolidation
                if field_config.data_type == DataType.NUMERIC:
                    # Use weighted average for numeric fields
                    try:
                        values = [float(v['value']) for v in all_values[field] if isinstance(v['value'], (int, float))]
                        if values:
                            consolidated['global_summary'][field] = {
                                'average': statistics.mean(values),
                                'median': statistics.median(values),
                                'min': min(values),
                                'max': max(values),
                                'regions_reporting': len(values)
                            }
                    except (ValueError, TypeError):
                        pass
                elif field_config.data_type == DataType.LIST:
                    # Combine lists from all regions
                    combined = []
                    for item in all_values[field]:
                        if isinstance(item['value'], list):
                            combined.extend(item['value'])
                        else:
                            combined.append(item['value'])
                    consolidated['global_summary'][field] = list(set(str(v) for v in combined))
                else:
                    # For other types, use most common or highest confidence
                    best = max(all_values[field], key=lambda x: x['confidence'])
                    consolidated['global_summary'][field] = best['value']

        # Market coverage analysis
        consolidated['market_coverage'] = list(regional_data.keys())
        consolidated['coverage_percentage'] = len(regional_data) / len(self.geographic_handlers) * 100

        # Audit trail
        consolidated['audit_trail'] = {
            'consolidation_timestamp': datetime.now().isoformat(),
            'category': category,
            'regions_processed': len(regional_data),
            'total_regions': len(self.geographic_handlers),
            'merge_id': hashlib.md5(
                json.dumps(sorted(regional_data.keys())).encode()
            ).hexdigest()
        }

        return consolidated

    async def calculate_confidence_scores(self, merged_data: Dict[str, Any],
                                         merge_records: List[MergeRecord]) -> Dict[str, float]:
        """
        Calculate confidence scores for merged data

        Args:
            merged_data: The merged data
            merge_records: Records of merge operations

        Returns:
            Confidence scores per field
        """
        confidence_scores = {}

        for record in merge_records:
            field = record.field_name
            base_confidence = record.confidence_score

            # Adjust confidence based on number of sources
            source_factor = min(1.0, len(record.sources_used) * 0.2)  # More sources = higher confidence

            # Adjust based on merge strategy
            strategy_factors = {
                'HIGHEST_CONFIDENCE': 1.0,
                'SOURCE_PRIORITY': 0.95,
                'CONSENSUS': 0.9,
                'WEIGHTED_AVERAGE': 0.85,
                'MOST_RECENT': 0.8,
                'UNION': 0.75,
                'INTERSECTION': 0.7,
                'ENRICHMENT': 0.6
            }
            strategy_factor = strategy_factors.get(record.merge_strategy, 0.5)

            # Calculate final confidence
            final_confidence = base_confidence * (0.6 + source_factor * 0.4) * strategy_factor
            confidence_scores[field] = min(1.0, final_confidence)

        # Calculate overall confidence
        if confidence_scores:
            confidence_scores['overall'] = statistics.mean(confidence_scores.values())
        else:
            confidence_scores['overall'] = 0.0

        return confidence_scores

    async def merge_pharmaceutical_data(self, validated_sources: List[Dict[str, Any]],
                                       category: str,
                                       temporal_data: Optional[List[TemporalData]] = None,
                                       regional_data: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Complete pharmaceutical data merging with full audit trail

        Args:
            validated_sources: List of validated data sources
            category: Pharmaceutical category
            temporal_data: Optional time-series data
            regional_data: Optional geographic data

        Returns:
            Complete merged dataset with audit trail
        """
        logger.info(f"Merging {len(validated_sources)} sources for category {category}")

        # Merge complementary data
        merged_data, merge_records = await self.merge_complementary_data(validated_sources, category)

        # Enrich incomplete records if we have supplementary data
        if len(validated_sources) > 1:
            primary = validated_sources[0]
            supplementary = validated_sources[1:]
            enriched_data, enrich_records = await self.enrich_incomplete_records(
                primary, supplementary, category
            )
            # Update merged data with enriched values
            merged_data.update(enriched_data)
            merge_records.extend(enrich_records)

        # Handle temporal data if provided
        temporal_analysis = {}
        if temporal_data:
            temporal_analysis = await self.handle_temporal_data(temporal_data, category)

        # Consolidate geographic data if provided
        geographic_consolidation = {}
        if regional_data:
            geographic_consolidation = await self.consolidate_geographic_data(regional_data, category)

        # Calculate confidence scores
        confidence_scores = await self.calculate_confidence_scores(merged_data, merge_records)

        # Quality assurance checks
        qa_validation = self._perform_qa_validation(merged_data, category)

        # Generate complete audit trail
        audit_trail = {
            'merge_id': hashlib.md5(
                json.dumps(merged_data, sort_keys=True, default=str).encode()
            ).hexdigest(),
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'sources_merged': len(validated_sources),
            'fields_merged': len(merged_data),
            'merge_operations': len(merge_records),
            'enrichment_operations': sum(1 for r in merge_records if r.merge_strategy == 'ENRICHMENT'),
            'confidence_scores': confidence_scores,
            'qa_validation': qa_validation,
            'merge_records': [r.model_dump() for r in merge_records]
        }

        # Compile final merged result
        final_result = {
            'merged_data': merged_data,
            'temporal_analysis': temporal_analysis,
            'geographic_consolidation': geographic_consolidation,
            'confidence_scores': confidence_scores,
            'quality_assurance': qa_validation,
            'audit_trail': audit_trail,
            'merge_timestamp': datetime.now().isoformat(),
            'data_sources': [{'source': s.get('source', 'unknown'),
                            'timestamp': s.get('timestamp', datetime.now()).isoformat() if isinstance(s.get('timestamp'), datetime) else s.get('timestamp', '')}
                           for s in validated_sources]
        }

        logger.info(f"Merge completed: {len(merged_data)} fields, overall confidence {confidence_scores.get('overall', 0):.2%}")

        return final_result

    def _perform_qa_validation(self, merged_data: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Perform quality assurance validation on merged data"""
        qa_results = {
            'passed': True,
            'checks_performed': [],
            'issues': []
        }

        # Check for required fields
        merge_config = self.merge_configs.get(category, [])
        required_fields = [c.field_name for c in merge_config if c.required]

        for field in required_fields:
            if field not in merged_data or merged_data[field] is None:
                qa_results['passed'] = False
                qa_results['issues'].append(f"Missing required field: {field}")

        qa_results['checks_performed'].append('required_fields')

        # Check for data consistency
        if category == 'drug_info' and 'approval_date' in merged_data and 'expiry_date' in merged_data:
            try:
                approval = datetime.fromisoformat(str(merged_data['approval_date']))
                expiry = datetime.fromisoformat(str(merged_data['expiry_date']))
                if expiry < approval:
                    qa_results['passed'] = False
                    qa_results['issues'].append("Expiry date before approval date")
            except (ValueError, TypeError):
                pass

        qa_results['checks_performed'].append('data_consistency')

        # Check for suspicious patterns
        numeric_fields = [c.field_name for c in merge_config if c.data_type == DataType.NUMERIC]
        for field in numeric_fields:
            if field in merged_data:
                try:
                    value = float(merged_data[field])
                    if value < 0:
                        qa_results['issues'].append(f"Negative value in {field}: {value}")
                        qa_results['passed'] = False
                except (ValueError, TypeError):
                    pass

        qa_results['checks_performed'].append('value_validation')

        return qa_results

    def get_merge_history(self, category: Optional[str] = None,
                         time_window: Optional[int] = 30) -> List[Dict[str, Any]]:
        """Get merge operation history"""
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=time_window)
        relevant_history = [
            r.model_dump() for r in self.merge_history
            if r.timestamp >= cutoff_date and
            (not category or r.audit_info.get('category') == category)
        ]

        return relevant_history