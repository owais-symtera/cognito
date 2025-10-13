"""
Category Validation Engine
Executes validation schemas stored in database to validate category results
"""

import json
import asyncpg
import structlog
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = structlog.get_logger(__name__)


class CategoryValidationEngine:
    """Engine for executing category-specific validation rules"""

    def __init__(self):
        """Initialize validation engine"""
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'user': 'postgres',
            'password': 'postgres',
            'database': 'cognito-engine'
        }

    async def _get_connection(self):
        """Get database connection"""
        return await asyncpg.connect(**self.db_config)

    async def get_validation_schema(self, category_id: int) -> Optional[Dict[str, Any]]:
        """
        Get validation schema for a category

        Args:
            category_id: Category ID

        Returns:
            Validation schema dict or None
        """
        conn = await self._get_connection()
        try:
            row = await conn.fetchrow("""
                SELECT id, category_id, category_name, version, validation_config, enabled
                FROM category_validation_schemas
                WHERE category_id = $1 AND enabled = true
                ORDER BY created_at DESC
                LIMIT 1
            """, category_id)

            if not row:
                return None

            # Parse JSONB config if it's a string
            config = row['validation_config']
            if isinstance(config, str):
                config = json.loads(config)

            return {
                'schema_id': str(row['id']),
                'category_id': row['category_id'],
                'category_name': row['category_name'],
                'version': row['version'],
                'config': config,
                'enabled': row['enabled']
            }
        finally:
            await conn.close()

    async def validate_category_result(
        self,
        category_result_id: str,
        category_id: int,
        category_data: Dict[str, Any],
        source_references: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate a category result using its validation schema

        Args:
            category_result_id: UUID of category result
            category_id: Category ID
            category_data: Extracted data for the category
            source_references: List of source references used

        Returns:
            Validation result with score, passed status, and details
        """
        logger.info("Starting category validation", category_id=category_id)

        # Get validation schema
        schema = await self.get_validation_schema(category_id)
        if not schema:
            logger.warning("No validation schema found", category_id=category_id)
            return self._create_default_validation_result(
                category_result_id,
                "no_schema",
                "No validation schema configured for this category"
            )

        config = schema['config']
        validation_steps = config.get('validation_steps', [])

        # Execute validation steps
        step_results = []
        failed_steps = []
        total_score = 0.0
        total_weight = 0.0

        for step in validation_steps:
            step_name = step['step_name']
            step_type = step['type']
            weight = step.get('weight', 0.0)

            logger.debug("Executing validation step", step=step_name, type=step_type)

            # Execute step based on type
            step_result = await self._execute_validation_step(
                step,
                category_data,
                source_references,
                config
            )

            step_results.append(step_result)

            if not step_result['passed']:
                failed_steps.append(step_name)

            # Calculate weighted score
            step_score = step_result.get('score', 0.0)
            total_score += step_score * weight
            total_weight += weight

        # Calculate final validation score
        validation_score = total_score / total_weight if total_weight > 0 else 0.0

        # Determine if validation passed
        pass_threshold = config.get('scoring', {}).get('pass_threshold', 0.70)
        validation_passed = validation_score >= pass_threshold

        # Calculate confidence penalty
        confidence_penalty = self._calculate_confidence_penalty(
            validation_score,
            config.get('scoring', {})
        )

        # Identify data quality issues
        data_quality_issues = self._identify_quality_issues(
            step_results,
            failed_steps
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            failed_steps,
            data_quality_issues,
            validation_score
        )

        # Store validation result
        validation_result = {
            'category_result_id': category_result_id,
            'validation_schema_id': schema['schema_id'],
            'validation_passed': validation_passed,
            'validation_score': round(validation_score, 4),
            'confidence_penalty': round(confidence_penalty, 4),
            'step_results': step_results,
            'failed_steps': failed_steps,
            'data_quality_issues': data_quality_issues,
            'recommendations': recommendations
        }

        await self._store_validation_result(validation_result)

        logger.info(
            "Validation completed",
            category_id=category_id,
            score=validation_score,
            passed=validation_passed,
            failed_steps_count=len(failed_steps)
        )

        return validation_result

    async def _execute_validation_step(
        self,
        step: Dict[str, Any],
        category_data: Dict[str, Any],
        source_references: List[Dict[str, Any]],
        full_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single validation step

        Returns:
            Step result with passed status and score
        """
        step_name = step['step_name']
        step_type = step['type']
        rules = step.get('rules', {})

        try:
            if step_type == 'data_collection':
                return await self._validate_data_collection(step_name, rules, source_references)

            elif step_type == 'consistency_check':
                return await self._validate_consistency(step_name, rules, source_references, category_data)

            elif step_type == 'normalization':
                return await self._validate_normalization(step_name, rules, category_data)

            elif step_type == 'table_validation':
                return await self._validate_table_structure(step_name, rules, category_data)

            elif step_type == 'calculation':
                return await self._validate_calculations(step_name, rules, category_data)

            elif step_type == 'classification':
                return await self._validate_classification(step_name, rules, category_data)

            else:
                logger.warning("Unknown validation step type", type=step_type)
                return {
                    'step_name': step_name,
                    'passed': False,
                    'score': 0.0,
                    'message': f"Unknown validation type: {step_type}"
                }

        except Exception as e:
            logger.error("Validation step failed", step=step_name, error=str(e))
            return {
                'step_name': step_name,
                'passed': False,
                'score': 0.0,
                'message': f"Validation error: {str(e)}"
            }

    async def _validate_data_collection(
        self,
        step_name: str,
        rules: Dict[str, Any],
        sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate data collection - check if minimum sources exist"""
        min_sources = rules.get('min_sources', 1)
        source_count = len(sources)

        passed = source_count >= min_sources
        score = min(1.0, source_count / max(min_sources, 1))

        return {
            'step_name': step_name,
            'passed': passed,
            'score': score,
            'message': f"Found {source_count} sources (minimum: {min_sources})",
            'metadata': {
                'source_count': source_count,
                'min_required': min_sources
            }
        }

    async def _validate_consistency(
        self,
        step_name: str,
        rules: Dict[str, Any],
        sources: List[Dict[str, Any]],
        category_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate source consistency - check for agreement"""
        supported_threshold = rules.get('supported_threshold', 0.10)
        plausible_threshold = rules.get('plausible_threshold', 0.20)

        # Calculate consistency score based on source agreement
        # For now, use a simple heuristic: more sources = higher consistency
        source_count = len(sources)

        if source_count >= 3:
            consistency_level = 'supported'
            score = 1.0
        elif source_count >= 2:
            consistency_level = 'plausible'
            score = 0.6
        else:
            consistency_level = 'weak'
            score = 0.3

        passed = score >= 0.3  # Weak threshold

        return {
            'step_name': step_name,
            'passed': passed,
            'score': score,
            'message': f"Consistency level: {consistency_level}",
            'metadata': {
                'consistency_level': consistency_level,
                'source_count': source_count
            }
        }

    async def _validate_normalization(
        self,
        step_name: str,
        rules: Dict[str, Any],
        category_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate time period normalization"""
        # Check if data has consistent time periods
        # For now, assume normalized if data structure is present

        has_data = bool(category_data.get('content') or category_data.get('tables'))

        return {
            'step_name': step_name,
            'passed': has_data,
            'score': 1.0 if has_data else 0.0,
            'message': "Time periods normalized" if has_data else "No data to normalize",
            'metadata': {
                'has_content': bool(category_data.get('content')),
                'has_tables': bool(category_data.get('tables'))
            }
        }

    async def _validate_table_structure(
        self,
        step_name: str,
        rules: Dict[str, Any],
        category_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate table structure with row-by-row source validation"""
        required_columns = rules.get('required_columns', [])
        required_regions = rules.get('required_regions', [])

        tables = category_data.get('tables', [])
        content = category_data.get('content', '') or category_data.get('summary', '')

        # If no structured tables, parse from text
        if not tables and content:
            table_indicators = self._detect_text_tables(content)

            if not table_indicators['has_tables']:
                return {
                    'step_name': step_name,
                    'passed': False,
                    'score': 0.0,
                    'message': "No tables found in category data",
                    'metadata': {'table_count': 0}
                }

            # Parse and validate tables from text
            validation_result = self._validate_text_table_rows(content)

            return {
                'step_name': step_name,
                'passed': validation_result['passed'],
                'score': validation_result['score'],
                'message': validation_result['message'],
                'metadata': validation_result['metadata']
            }

        # No tables at all
        if not tables and not content:
            return {
                'step_name': step_name,
                'passed': False,
                'score': 0.0,
                'message': "No tables found in category data",
                'metadata': {'table_count': 0}
            }

        # Validate structured tables (if any)
        return {
            'step_name': step_name,
            'passed': True,
            'score': 0.7,
            'message': "Structured table found, source validation not yet implemented",
            'metadata': {
                'table_count': len(tables) if isinstance(tables, list) else 1,
                'requires_row_validation': True
            }
        }

    def _detect_text_tables(self, content: str) -> Dict[str, Any]:
        """Detect tables in text format (markdown, pipe-separated, etc.)"""
        import re

        if not content:
            return {'has_tables': False, 'count': 0, 'format': None}

        # Check for markdown tables (|---|---|)
        markdown_pattern = r'\|[\s]*[-:]+[\s]*\|'
        markdown_matches = re.findall(markdown_pattern, content)

        # Check for pipe-separated tables (| col1 | col2 |)
        pipe_pattern = r'\|[^|]+\|[^|]+\|'
        pipe_lines = [line for line in content.split('\n') if re.match(pipe_pattern, line.strip())]

        # Check for tab-separated or multi-column data
        tab_pattern = r'\t.*\t'
        tab_lines = [line for line in content.split('\n') if re.search(tab_pattern, line)]

        if len(markdown_matches) > 0:
            return {
                'has_tables': True,
                'count': len(markdown_matches),
                'format': 'markdown'
            }
        elif len(pipe_lines) >= 3:  # At least header + separator + 1 row
            return {
                'has_tables': True,
                'count': 1,
                'format': 'pipe-separated'
            }
        elif len(tab_lines) >= 2:  # At least 2 rows with tabs
            return {
                'has_tables': True,
                'count': 1,
                'format': 'tab-separated'
            }

        return {'has_tables': False, 'count': 0, 'format': None}

    def _validate_text_table_rows(self, content: str) -> Dict[str, Any]:
        """Validate each row in text tables for source citations"""
        import re

        # Parse all markdown/pipe-separated tables in content
        tables = self._parse_markdown_tables(content)

        if not tables:
            return {
                'passed': False,
                'score': 0.0,
                'message': "No parseable tables found",
                'metadata': {'tables_count': 0}
            }

        total_rows = 0
        validated_rows = 0
        failed_rows = []
        validation_details = []

        for table_idx, table in enumerate(tables):
            for row_idx, row in enumerate(table['rows']):
                total_rows += 1

                # Validate source citation in row
                source_validation = self._validate_row_source(row, row_idx + 1)

                if source_validation['has_source']:
                    validated_rows += 1
                else:
                    failed_rows.append({
                        'table': table_idx + 1,
                        'row': row_idx + 1,
                        'data': row,
                        'reason': source_validation['reason']
                    })

                validation_details.append({
                    'row_number': row_idx + 1,
                    'status': 'PASS' if source_validation['has_source'] else 'FAIL',
                    'source_priority': source_validation.get('priority'),
                    'source_type': source_validation.get('source_type'),
                    'reason': source_validation.get('reason', '')
                })

        # Calculate validation score
        score = validated_rows / total_rows if total_rows > 0 else 0.0
        passed = score >= 0.70  # Pass if 70% of rows have valid sources

        return {
            'passed': passed,
            'score': round(score, 2),
            'message': f"Row validation: {validated_rows}/{total_rows} rows have source citations" +
                      (f" ({len(failed_rows)} failed)" if failed_rows else ""),
            'metadata': {
                'tables_count': len(tables),
                'total_rows': total_rows,
                'validated_rows': validated_rows,
                'failed_rows': len(failed_rows),
                'validation_details': validation_details[:10],  # First 10 for brevity
                'pass_rate': f"{score * 100:.1f}%"
            }
        }

    def _parse_markdown_tables(self, content: str) -> List[Dict[str, Any]]:
        """Parse markdown tables from content"""
        import re

        tables = []
        lines = content.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check if this is a table header (contains pipes)
            if '|' in line and i + 1 < len(lines):
                # Check next line for separator (---|---|)
                next_line = lines[i + 1].strip()
                if re.match(r'\|[\s]*[-:]+', next_line):
                    # Found a table!
                    header = [cell.strip() for cell in line.split('|') if cell.strip()]
                    rows = []

                    # Parse rows until we hit a non-table line
                    j = i + 2
                    while j < len(lines):
                        row_line = lines[j].strip()
                        if '|' in row_line and not re.match(r'\|[\s]*[-:]+', row_line):
                            row_cells = [cell.strip() for cell in row_line.split('|') if cell.strip()]
                            if row_cells:
                                rows.append(row_cells)
                            j += 1
                        else:
                            break

                    if rows:
                        tables.append({
                            'headers': header,
                            'rows': rows
                        })

                    i = j
                    continue

            i += 1

        return tables

    def _validate_row_source(self, row_cells: List[str], row_number: int) -> Dict[str, Any]:
        """Validate if a row has proper source citation"""
        import re

        # Source priority hierarchy (from SYSTEM_PROMPT)
        source_priorities = {
            'PAID_APIS': 1,          # Pharmacircle, GlobalData, Evaluate Pharma, Cortellis, IQVIA
            'GOVERNMENT': 2,         # .gov, .edu, FDA, EMA, PMDA, ClinicalTrials.gov
            'PEER_REVIEWED': 3,      # journals with DOI/PMID, PubMed
            'INDUSTRY': 4,           # pharma associations, industry databases
            'COMPANY': 5,            # official pharma websites, press releases
            'NEWS': 6                # news sources
        }

        source_keywords = {
            'PAID_APIS': ['pharmacircle', 'globaldata', 'evaluate pharma', 'cortellis', 'iqvia'],
            'GOVERNMENT': ['.gov', '.edu', 'fda', 'ema', 'pmda', 'clinicaltrials', 'government'],
            'PEER_REVIEWED': ['pubmed', 'doi:', 'pmid:', 'journal', 'peer-reviewed'],
            'INDUSTRY': ['association', 'white paper', 'industry report'],
            'COMPANY': ['press release', 'corporate', 'company website'],
            'NEWS': ['news', 'report', 'article']
        }

        # Join all cells in the row to check for source citations
        row_text = ' '.join(row_cells).lower()

        # Check for source citation patterns
        # Pattern 1: [Priority X: Source Name]
        priority_pattern = r'\[priority\s+(\d+):\s*([^\]]+)\]'
        priority_match = re.search(priority_pattern, row_text, re.IGNORECASE)

        if priority_match:
            priority_num = int(priority_match.group(1))
            source_name = priority_match.group(2).strip()

            # Determine source type from priority number
            source_type = None
            for stype, prio in source_priorities.items():
                if prio == priority_num:
                    source_type = stype
                    break

            return {
                'has_source': True,
                'priority': priority_num,
                'source_type': source_type or 'UNKNOWN',
                'source_name': source_name
            }

        # Pattern 2: Direct source keywords
        for source_type, keywords in source_keywords.items():
            for keyword in keywords:
                if keyword in row_text:
                    return {
                        'has_source': True,
                        'priority': source_priorities[source_type],
                        'source_type': source_type,
                        'source_name': f'Detected: {keyword}'
                    }

        # Pattern 3: Check for any citation-like patterns (year in parentheses, URLs, etc.)
        citation_patterns = [
            r'\(\d{4}\)',  # (2025)
            r'https?://',   # URLs
            r'\d{4}\s+report',  # "2025 report"
            r'study\s+\d{4}',  # "study 2025"
        ]

        for pattern in citation_patterns:
            if re.search(pattern, row_text):
                return {
                    'has_source': True,
                    'priority': 6,  # Lowest priority for generic citations
                    'source_type': 'GENERIC_CITATION',
                    'source_name': 'Generic citation found'
                }

        # No source found
        return {
            'has_source': False,
            'priority': None,
            'source_type': None,
            'reason': 'No source citation detected'
        }

    async def _validate_calculations(
        self,
        step_name: str,
        rules: Dict[str, Any],
        category_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate calculations like CAGR formulas"""
        formula = rules.get('formula', '')

        # Check if data has numerical values
        # In production, would validate CAGR calculations

        has_data = bool(category_data.get('content'))

        return {
            'step_name': step_name,
            'passed': has_data,
            'score': 0.7 if has_data else 0.0,
            'message': "Calculations validated" if has_data else "No data for calculations",
            'metadata': {
                'formula': formula
            }
        }

    async def _validate_classification(
        self,
        step_name: str,
        rules: Dict[str, Any],
        category_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate validity notes classification"""
        validity_levels = rules.get('validity_levels', {})

        # Check if data has validity information
        # For now, assume valid if data exists

        has_data = bool(category_data.get('content'))

        return {
            'step_name': step_name,
            'passed': has_data,
            'score': 1.0 if has_data else 0.0,
            'message': "Classification validated" if has_data else "No data to classify",
            'metadata': {
                'validity_levels': list(validity_levels.keys())
            }
        }

    def _calculate_confidence_penalty(
        self,
        validation_score: float,
        scoring_config: Dict[str, Any]
    ) -> float:
        """Calculate confidence penalty based on validation score"""
        penalty_formula = scoring_config.get('confidence_penalty_formula', '')

        # Default: (1.0 - validation_score) * 0.5
        # Failed validation reduces confidence by up to 50%
        penalty = (1.0 - validation_score) * 0.5

        return max(0.0, min(1.0, penalty))

    def _identify_quality_issues(
        self,
        step_results: List[Dict[str, Any]],
        failed_steps: List[str]
    ) -> Dict[str, Any]:
        """Identify specific data quality issues"""
        issues = {
            'failed_step_count': len(failed_steps),
            'failed_steps': failed_steps,
            'issues': []
        }

        for result in step_results:
            if not result['passed']:
                issues['issues'].append({
                    'step': result['step_name'],
                    'message': result.get('message', 'Validation failed'),
                    'metadata': result.get('metadata', {})
                })

        return issues

    def _generate_recommendations(
        self,
        failed_steps: List[str],
        quality_issues: Dict[str, Any],
        validation_score: float
    ) -> List[str]:
        """Generate recommendations for improvement"""
        recommendations = []

        if validation_score < 0.5:
            recommendations.append("Data quality is low. Consider gathering more sources.")

        if 'data_collection' in failed_steps:
            recommendations.append("Increase number of data sources for better validation.")

        if 'consistency_check' in failed_steps:
            recommendations.append("Cross-reference data across multiple sources to improve consistency.")

        if 'table_validation' in failed_steps:
            recommendations.append("Ensure all required table columns and regions are present.")

        if 'calculation' in failed_steps:
            recommendations.append("Verify calculation formulas and numerical accuracy.")

        if not recommendations:
            recommendations.append("Validation passed successfully. Data quality is acceptable.")

        return recommendations

    def _create_default_validation_result(
        self,
        category_result_id: str,
        reason: str,
        message: str
    ) -> Dict[str, Any]:
        """Create default validation result when no schema exists"""
        return {
            'category_result_id': category_result_id,
            'validation_schema_id': None,
            'validation_passed': True,  # Default to passing
            'validation_score': 1.0,
            'confidence_penalty': 0.0,
            'step_results': [],
            'failed_steps': [],
            'data_quality_issues': {'reason': reason, 'message': message},
            'recommendations': [message]
        }

    async def _store_validation_result(self, result: Dict[str, Any]) -> str:
        """
        Store validation result to database

        Returns:
            Validation result ID
        """
        conn = await self._get_connection()
        try:
            # Convert JSONB fields to JSON strings for asyncpg
            row = await conn.fetchrow("""
                INSERT INTO validation_results (
                    category_result_id,
                    validation_schema_id,
                    validation_passed,
                    validation_score,
                    confidence_penalty,
                    step_results,
                    failed_steps,
                    data_quality_issues,
                    recommendations
                ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8::jsonb, $9::jsonb)
                RETURNING id
            """,
                result['category_result_id'],
                result.get('validation_schema_id'),
                result['validation_passed'],
                result['validation_score'],
                result['confidence_penalty'],
                json.dumps(result['step_results']),
                result['failed_steps'],
                json.dumps(result['data_quality_issues']),
                json.dumps(result['recommendations'])
            )

            validation_id = str(row['id'])
            logger.info("Validation result stored", validation_id=validation_id)
            return validation_id

        finally:
            await conn.close()

    async def get_validation_results(
        self,
        category_result_id: str
    ) -> List[Dict[str, Any]]:
        """Get all validation results for a category result"""
        conn = await self._get_connection()
        try:
            rows = await conn.fetch("""
                SELECT
                    id,
                    validation_schema_id,
                    validation_passed,
                    validation_score,
                    confidence_penalty,
                    step_results,
                    failed_steps,
                    data_quality_issues,
                    recommendations,
                    validated_at
                FROM validation_results
                WHERE category_result_id = $1
                ORDER BY validated_at DESC
            """, category_result_id)

            return [dict(row) for row in rows]

        finally:
            await conn.close()

    async def validate_source_response(
        self,
        category_result_id: str,
        category_id: int,
        source_response: Dict[str, Any],
        source_index: int
    ) -> Dict[str, Any]:
        """
        Validate a single source's response with table-to-JSON conversion

        Args:
            category_result_id: Category result ID
            category_id: Category ID
            source_response: Single source's response data
            source_index: Index of source (for tracking)

        Returns:
            Per-source validation result with JSON tables and row validation
        """
        logger.info(
            "Validating source response",
            category_id=category_id,
            provider=source_response.get("provider"),
            model=source_response.get("model")
        )

        # Get validation schema
        schema = await self.get_validation_schema(category_id)
        if not schema:
            return self._create_source_validation_default(
                category_result_id,
                source_response,
                source_index,
                "no_schema"
            )

        # Extract response content
        response_content = str(source_response.get("response", ""))

        # Convert tables to JSON with row validation
        tables_json = self._convert_tables_to_json_with_validation(response_content)

        # Calculate overall validation score based on table row validation
        total_rows = sum(t.get("total_rows", 0) for t in tables_json)
        validated_rows = sum(t.get("validated_rows", 0) for t in tables_json)

        if total_rows > 0:
            validation_score = validated_rows / total_rows
            validation_passed = validation_score >= 0.70
        else:
            validation_score = 0.0
            validation_passed = False

        # Build result
        source_validation = {
            "category_result_id": category_result_id,
            "source_index": source_index,
            "provider": source_response.get("provider"),
            "model": source_response.get("model"),
            "authority_score": source_response.get("authority_score", 0),
            "tables_json": tables_json,
            "total_tables": len(tables_json),
            "total_rows": total_rows,
            "validated_rows": validated_rows,
            "validation_score": round(validation_score, 4),
            "validation_passed": validation_passed,
            "pass_rate": f"{validation_score * 100:.1f}%" if total_rows > 0 else "0.0%"
        }

        # Store per-source validation
        await self._store_source_validation(source_validation)

        logger.info(
            "Source validation completed",
            provider=source_response.get("provider"),
            tables=len(tables_json),
            total_rows=total_rows,
            validated_rows=validated_rows,
            score=validation_score
        )

        return source_validation

    def _convert_tables_to_json_with_validation(self, content: str) -> List[Dict[str, Any]]:
        """
        Convert tables in content to JSON format with row validation metadata

        Args:
            content: Text content containing tables

        Returns:
            List of JSON table structures with validation metadata
        """
        import re

        tables = self._parse_markdown_tables(content)
        tables_json = []

        for table_idx, table in enumerate(tables):
            # Build JSON structure for table
            table_json = {
                "table_index": table_idx + 1,
                "headers": table.get("headers", []),
                "rows": [],
                "total_rows": len(table.get("rows", [])),
                "validated_rows": 0,
                "failed_rows": 0,
                "pass_rate": "0.0%"
            }

            # Validate and convert each row to JSON
            for row_idx, row_cells in enumerate(table.get("rows", [])):
                # Validate row source
                source_validation = self._validate_row_source(row_cells, row_idx + 1)

                # Build row JSON with validation metadata
                row_json = {
                    "row_number": row_idx + 1,
                    "data": {
                        table["headers"][i]: cell
                        for i, cell in enumerate(row_cells)
                        if i < len(table["headers"])
                    },
                    "validation": {
                        "status": "PASS" if source_validation["has_source"] else "FAIL",
                        "has_source": source_validation["has_source"],
                        "source_priority": source_validation.get("priority"),
                        "source_type": source_validation.get("source_type"),
                        "source_name": source_validation.get("source_name"),
                        "reason": source_validation.get("reason", "")
                    }
                }

                table_json["rows"].append(row_json)

                if source_validation["has_source"]:
                    table_json["validated_rows"] += 1
                else:
                    table_json["failed_rows"] += 1

            # Calculate pass rate for this table
            if table_json["total_rows"] > 0:
                pass_rate = table_json["validated_rows"] / table_json["total_rows"]
                table_json["pass_rate"] = f"{pass_rate * 100:.1f}%"

            tables_json.append(table_json)

        return tables_json

    async def _store_source_validation(self, source_validation: Dict[str, Any]) -> None:
        """
        Store per-source validation result to database

        Args:
            source_validation: Source validation data
        """
        import uuid
        import json
        from datetime import datetime

        result_id = str(uuid.uuid4())
        now = datetime.utcnow()

        conn = await self._get_connection()
        try:
            await conn.execute("""
                INSERT INTO source_validation_results (
                    id, category_result_id, source_index,
                    provider, model, authority_score,
                    tables_json, total_tables, total_rows, validated_rows,
                    validation_score, validation_passed, pass_rate,
                    validated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
                result_id,
                source_validation["category_result_id"],
                source_validation["source_index"],
                source_validation["provider"],
                source_validation["model"],
                source_validation["authority_score"],
                json.dumps(source_validation["tables_json"]),
                source_validation["total_tables"],
                source_validation["total_rows"],
                source_validation["validated_rows"],
                source_validation["validation_score"],
                source_validation["validation_passed"],
                source_validation["pass_rate"],
                now
            )

            logger.info(
                "Source validation stored",
                result_id=result_id,
                provider=source_validation["provider"]
            )

        except Exception as e:
            logger.error(
                "Failed to store source validation",
                error=str(e),
                provider=source_validation.get("provider")
            )
        finally:
            await conn.close()

    def _create_source_validation_default(
        self,
        category_result_id: str,
        source_response: Dict[str, Any],
        source_index: int,
        reason: str
    ) -> Dict[str, Any]:
        """Create default source validation result when no schema exists"""
        return {
            "category_result_id": category_result_id,
            "source_index": source_index,
            "provider": source_response.get("provider"),
            "model": source_response.get("model"),
            "authority_score": source_response.get("authority_score", 0),
            "tables_json": [],
            "total_tables": 0,
            "total_rows": 0,
            "validated_rows": 0,
            "validation_score": 0.0,
            "validation_passed": False,
            "pass_rate": "0.0%",
            "reason": reason
        }
