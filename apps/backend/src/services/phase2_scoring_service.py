"""
Phase 2 Scoring Service for Parameter-Based Scoring Matrix.

Extracts pharmaceutical parameters from Phase 1 data and calculates scores
using database-driven rubrics with LLM-generated rationales.
"""
import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
import structlog
from datetime import datetime

from ..utils.db_connection import DatabaseConnection
from ..config.llm_config import get_llm_config

logger = structlog.get_logger(__name__)


class Phase2ScoringService:
    """
    Service for Phase 2 parameter-based scoring.

    Handles:
    1. Parameter extraction from Phase 1 data using LLM
    2. Score calculation using database rubrics
    3. Rationale generation using LLM
    4. Markdown and JSON output generation
    """

    def __init__(self):
        self.llm_config = get_llm_config()
        self.parameters = ['Dose', 'Molecular Weight', 'Melting Point', 'Log P']

    async def process_parameter_scoring(
        self,
        request_id: str,
        drug_name: str,
        delivery_method: str,
        phase1_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process parameter-based scoring for a drug.

        Args:
            request_id: Request ID
            drug_name: Drug name
            delivery_method: 'Transdermal' or 'Transmucosal'
            phase1_data: Phase 1 category results

        Returns:
            Dict containing:
                - extracted_parameters: Dict of parameter values
                - scores: Dict of scores per parameter
                - rationales: Dict of rationales per parameter
                - markdown_table: Formatted markdown table
                - json_table: JSON format table
                - weighted_scores: Dict of weighted scores
                - total_score: Final aggregated score
        """
        logger.info(f"[PHASE2_SCORING] Starting for {drug_name}, delivery: {delivery_method}")

        try:
            # Step 1: Extract parameters from Phase 1 data
            extracted_params = await self._extract_parameters(drug_name, phase1_data)
            logger.info(f"[PHASE2_SCORING] Extracted parameters: {extracted_params}")

            # Step 1.5: Dedicated LLM calls for ANY missing parameters
            for param_name in self.parameters:
                if extracted_params.get(param_name) is None:
                    logger.info(f"[PHASE2_SCORING] {param_name} not found in Phase 1 data, making dedicated LLM call...")
                    value = await self._extract_parameter_with_llm(drug_name, param_name)
                    if value is not None:
                        extracted_params[param_name] = value
                        logger.info(f"[PHASE2_SCORING] Extracted {param_name} via dedicated LLM call: {value}")

            # Step 1.6: Search for missing parameters using live search
            missing_params = [p for p, v in extracted_params.items() if v is None]
            if missing_params:
                logger.info(f"[PHASE2_SCORING] Missing parameters detected: {missing_params}")
                logger.info(f"[PHASE2_SCORING] Triggering live search for missing parameters...")

                searched_params = await self._search_missing_parameters(drug_name, missing_params)
                logger.info(f"[PHASE2_SCORING] Live search results: {searched_params}")

                # Update extracted_params with search results
                for param, value in searched_params.items():
                    if value is not None:
                        extracted_params[param] = value
                        logger.info(f"[PHASE2_SCORING] Updated {param} from live search: {value}")

            # Step 2: Calculate scores using database rubrics
            scores_data = await self._calculate_scores(extracted_params, delivery_method)
            logger.info(f"[PHASE2_SCORING] Calculated scores: {scores_data}")

            # Step 3: Generate rationales using LLM
            rationales = await self._generate_rationales(
                drug_name, extracted_params, scores_data, delivery_method
            )
            logger.info(f"[PHASE2_SCORING] Generated rationales")

            # Step 4: Calculate weighted scores
            weighted_data = await self._calculate_weighted_scores(scores_data)

            # Step 5: Generate output tables
            markdown_table = self._generate_markdown_table(
                extracted_params, scores_data, rationales, weighted_data
            )
            json_table = self._generate_json_table(
                extracted_params, scores_data, rationales, weighted_data
            )

            return {
                "extracted_parameters": extracted_params,
                "scores": {p: scores_data[p]['score'] for p in self.parameters},
                "rationales": rationales,
                "markdown_table": markdown_table,
                "json_table": json_table,
                "weighted_scores": {p: weighted_data[p]['weighted_score'] for p in self.parameters},
                "total_score": weighted_data['total_score'],
                "delivery_method": delivery_method
            }

        except Exception as e:
            logger.error(f"[PHASE2_SCORING] Error: {str(e)}")
            import traceback
            logger.error(f"[PHASE2_SCORING] Traceback: {traceback.format_exc()}")
            raise

    async def _extract_parameters(
        self,
        drug_name: str,
        phase1_data: Dict[str, Any]
    ) -> Dict[str, Optional[float]]:
        """
        Extract pharmaceutical parameters from Phase 1 data using LLM.

        Args:
            drug_name: Drug name
            phase1_data: Phase 1 category results

        Returns:
            Dict with keys: Dose, Molecular Weight, Melting Point, Log P
        """
        # Prepare Phase 1 context
        phase1_text = self._prepare_phase1_context(phase1_data)

        # LOG: Output what we're sending
        logger.info(f"[EXTRACTION] Phase 1 context length: {len(phase1_text)} chars")
        logger.info(f"[EXTRACTION] Phase 1 context:\n{phase1_text}")

        prompt = f"""Extract the following pharmaceutical parameters for {drug_name} from the provided data:

1. **Dose** (mg/kg/day): Daily dose - extract exact value as stated, DO NOT perform conversions
2. **Molecular Weight** (Da): Molecular weight in Daltons
3. **Melting Point** (°C): Melting point in Celsius
4. **Log P**: Partition coefficient (log P value)

Phase 1 Data:
{phase1_text}

Instructions:
- Extract exact numerical values only as stated in the source
- If a parameter is not found, return null
- For Dose, extract the value exactly as written (DO NOT divide by 70 or perform any conversions)
- Return ONLY a JSON object with this exact format:

{{
  "Dose": <number or null>,
  "Molecular Weight": <number or null>,
  "Melting Point": <number or null>,
  "Log P": <number or null>
}}

Do not include any explanation, only the JSON object."""

        try:
            # Call LLM for extraction
            from ..core.llm_service import LLMService
            llm_service = LLMService()

            logger.info(f"[EXTRACTION] Sending prompt to LLM (length: {len(prompt)} chars)")

            response = await llm_service.generate(
                prompt=prompt,
                temperature=0.0,  # Deterministic extraction
                max_tokens=500
            )

            logger.info(f"[EXTRACTION] LLM Response: {response}")

            # Parse JSON response
            extracted = json.loads(response.strip())

            # Validate structure
            result = {}
            for param in self.parameters:
                value = extracted.get(param)
                result[param] = float(value) if value is not None else None

            return result

        except Exception as e:
            logger.error(f"[EXTRACTION] Failed: {str(e)}")
            # Return nulls if extraction fails
            return {param: None for param in self.parameters}

    async def _extract_parameter_with_llm(
        self,
        drug_name: str,
        parameter_name: str
    ) -> Optional[float]:
        """
        Generic method to extract ANY pharmaceutical parameter using dedicated LLM call.

        This is a smart, configurable approach that works for all 4 parameters
        without hardcoding separate functions.

        Args:
            drug_name: Drug name
            parameter_name: One of: 'Dose', 'Molecular Weight', 'Melting Point', 'Log P'

        Returns:
            Parameter value or None if not found
        """
        logger.info(f"[PARAM_EXTRACTION] Making dedicated LLM call for {parameter_name} of {drug_name}")

        # Parameter-specific instructions
        param_config = {
            'Dose': {
                'unit': 'mg/kg/day',
                'instruction': '''- Provide the TYPICAL ADULT DOSE exactly as found in the source
- DO NOT perform any conversions or calculations
- If dose is already in mg/kg/day format, use that value directly
- If dose is given as total mg/day, report it as-is (DO NOT divide by 70)
- If dose range is given (e.g., 2.5-5 mg), use the HIGHEST value (maximum therapeutic dose)
- Extract the exact numerical value from the pharmaceutical literature

Examples:
- If dose is stated as "0.14 mg/kg/day" → use 0.14
- If dose is stated as "10 mg twice daily" → use 10
- If dose is stated as "2.5-5 mg twice daily" → use 5 (highest value in range)
- If dose is stated as "5-10 mg/kg/day" → use 10 (highest value in range)''',
                'json_key': 'value'
            },
            'Molecular Weight': {
                'unit': 'Da (Daltons)',
                'instruction': '''- Provide the exact molecular weight in Daltons
- This should be the monoisotopic or average molecular weight
- Use precise values from pharmaceutical databases

Example:
- Apixaban: 459.5 Da''',
                'json_key': 'value'
            },
            'Melting Point': {
                'unit': '°C',
                'instruction': '''- Provide the melting point in degrees Celsius
- If a range is given (e.g., 230-240°C), use the HIGHEST value in the range
- Use data from pharmaceutical literature or drug monographs

Example:
- If range is 230-240°C → use 240°C (highest value)''',
                'json_key': 'value'
            },
            'Log P': {
                'unit': '(unitless)',
                'instruction': '''- Provide the partition coefficient (Log P or LogP value)
- This is the octanol-water partition coefficient
- If a range is given, use the HIGHEST value in the range
- Use experimentally determined values when available

Example:
- If range is 1.1-4.5 → use 4.5 (highest value)''',
                'json_key': 'value'
            }
        }

        config = param_config.get(parameter_name)
        if not config:
            logger.error(f"[PARAM_EXTRACTION] Unknown parameter: {parameter_name}")
            return None

        try:
            from ..core.llm_service import LLMService
            llm_service = LLMService()

            prompt = f"""What is the {parameter_name} of {drug_name} in {config['unit']}?

Instructions:
{config['instruction']}
- Return ONLY a JSON object with the numerical value

Return format:
{{
  "value": <number or null>,
  "reasoning": "brief explanation of source/calculation"
}}

If you cannot find reliable information, return {{"value": null, "reasoning": "not found"}}"""

            response = await llm_service.generate(
                prompt=prompt,
                temperature=0.0,  # Deterministic
                max_tokens=300
            )

            logger.info(f"[PARAM_EXTRACTION] LLM Response for {parameter_name}: {response}")

            # Parse JSON response
            parsed = json.loads(response.strip())
            value = parsed.get(config['json_key'])
            reasoning = parsed.get('reasoning', '')

            if value is not None:
                logger.info(f"[PARAM_EXTRACTION] Extracted {parameter_name}: {value} {config['unit']} (reasoning: {reasoning})")
                return float(value)
            else:
                logger.warning(f"[PARAM_EXTRACTION] Could not extract {parameter_name}: {reasoning}")
                return None

        except Exception as e:
            logger.error(f"[PARAM_EXTRACTION] Failed for {parameter_name}: {str(e)}")
            import traceback
            logger.error(f"[PARAM_EXTRACTION] Traceback: {traceback.format_exc()}")
            return None

    async def _search_missing_parameters(
        self,
        drug_name: str,
        missing_params: List[str]
    ) -> Dict[str, Optional[float]]:
        """
        Search for missing pharmaceutical parameters using live web search.

        Uses Perplexity API to perform real-time web search for each missing
        parameter and extract exact numerical values.

        Args:
            drug_name: Drug name
            missing_params: List of parameter names that are missing

        Returns:
            Dict with parameter names as keys and extracted values (or None)
        """
        logger.info(f"[LIVE_SEARCH] Searching for {len(missing_params)} missing parameters: {missing_params}")

        results = {}

        try:
            # Initialize Perplexity provider
            from ..integrations.providers.perplexity import PerplexityProvider
            from ..config.llm_config import get_llm_config

            llm_config = get_llm_config()
            perplexity_config = llm_config.get_provider_config('perplexity')

            if not perplexity_config or not perplexity_config.api_key:
                logger.warning("[LIVE_SEARCH] Perplexity API key not configured, skipping live search")
                return {param: None for param in missing_params}

            perplexity = PerplexityProvider(api_key=perplexity_config.api_key)

            # Search for each missing parameter
            for param in missing_params:
                try:
                    logger.info(f"[LIVE_SEARCH] Searching for {param} of {drug_name}")

                    # Build search query
                    query = self._build_search_query(drug_name, param)
                    logger.info(f"[LIVE_SEARCH] Query: {query}")

                    # Perform live search
                    search_response = await perplexity.search(query, temperature=0.1)

                    if search_response and search_response.results:
                        # Combine all search result content
                        combined_content = "\n\n".join([
                            result.content for result in search_response.results
                        ])

                        # Extract value from search result
                        value = await self._extract_value_from_search(
                            combined_content,
                            param
                        )

                        results[param] = value
                        logger.info(f"[LIVE_SEARCH] Found {param}: {value}")
                    else:
                        results[param] = None
                        logger.warning(f"[LIVE_SEARCH] No results for {param}")

                except Exception as e:
                    logger.error(f"[LIVE_SEARCH] Failed to search {param}: {str(e)}")
                    results[param] = None

            return results

        except Exception as e:
            import traceback
            logger.error(f"[LIVE_SEARCH] Failed: {str(e)}")
            logger.error(f"[LIVE_SEARCH] Traceback: {traceback.format_exc()}")
            return {param: None for param in missing_params}

    def _build_search_query(self, drug_name: str, param: str) -> str:
        """Build optimized search query for a specific parameter."""
        query_templates = {
            "Dose": f"What is the standard dose or dosage of {drug_name} in mg/kg/day?",
            "Molecular Weight": f"What is the molecular weight of {drug_name} in Daltons?",
            "Melting Point": f"What is the melting point of {drug_name} in Celsius?",
            "Log P": f"What is the Log P or partition coefficient value of {drug_name}?"
        }
        return query_templates.get(param, f"{drug_name} {param}")

    async def _extract_value_from_search(
        self,
        search_content: str,
        param: str
    ) -> Optional[float]:
        """
        Extract numerical value from search result using LLM.

        Args:
            search_content: Search result text
            param: Parameter name

        Returns:
            Extracted numerical value or None
        """
        try:
            from ..core.llm_service import LLMService
            llm_service = LLMService()

            prompt = f"""Extract the exact numerical value for "{param}" from the following text:

{search_content}

Instructions:
- Extract ONLY the numerical value (e.g., 375.44, 150, 3.5)
- If a range is given (e.g., 3.3-5.5), use the HIGHEST value (5.5)
- If no value is found, return null
- Return ONLY a JSON object: {{"value": <number or null>}}

Do not include any explanation, only the JSON object."""

            response = await llm_service.generate(
                prompt=prompt,
                temperature=0.0,
                max_tokens=100
            )

            # Parse response
            parsed = json.loads(response.strip())
            value = parsed.get('value')

            return float(value) if value is not None else None

        except Exception as e:
            logger.error(f"[LIVE_SEARCH] Failed to extract value for {param}: {str(e)}")
            return None

    def _prepare_phase1_context(self, phase1_data: Dict[str, Any]) -> str:
        """
        Prepare Phase 1 data as context for LLM.

        NOTE: Currently using summaries because merged_data_results table
        has no structured_data stored. This is a Phase 1 pipeline bug that
        needs to be fixed separately.
        """
        context_parts = []

        # Prioritize categories most likely to have parameter data
        priority_categories = ['Physicochemical Profile', 'Pharmacokinetics', 'Dosage Forms', 'Current Formulations']

        # Add priority categories first (using summaries due to Phase 1 bug)
        for cat_name in priority_categories:
            if cat_name in phase1_data:
                category_data = phase1_data[cat_name]
                summary = category_data.get('summary', '')

                if summary:
                    part = f"## {cat_name}\n{summary}\n"
                    context_parts.append(part)

        # Add other categories (truncated summaries)
        for category_name, category_data in phase1_data.items():
            if category_name not in priority_categories:
                summary = category_data.get('summary', '')
                if summary:
                    part = f"## {category_name}\n{summary[:500]}\n"
                    context_parts.append(part)

        # Limit total context to avoid token limits
        full_context = "\n".join(context_parts)
        return full_context[:15000]  # Limit to 15K chars

    async def _calculate_scores(
        self,
        extracted_params: Dict[str, Optional[float]],
        delivery_method: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate scores using database scoring rubrics.

        Args:
            extracted_params: Extracted parameter values
            delivery_method: 'Transdermal' or 'Transmucosal'

        Returns:
            Dict with parameter -> {score, range_text, is_exclusion}
        """
        scores_data = {}

        async with DatabaseConnection() as conn:
            # Get parameter IDs
            param_map = await conn.fetch("""
                SELECT id, name FROM scoring_parameters
            """)
            param_id_map = {row['name']: row['id'] for row in param_map}

            for param_name in self.parameters:
                value = extracted_params.get(param_name)

                if value is None:
                    scores_data[param_name] = {
                        'score': None,
                        'range_text': 'Not Available',
                        'is_exclusion': False,
                        'param_value': None
                    }
                    continue

                param_id = param_id_map.get(param_name)
                if not param_id:
                    logger.warning(f"Parameter ID not found for {param_name}")
                    scores_data[param_name] = {
                        'score': None,
                        'range_text': 'Unknown Parameter',
                        'is_exclusion': False,
                        'param_value': value
                    }
                    continue

                # Find matching score range
                matching_range = await conn.fetchrow("""
                    SELECT score, range_text, is_exclusion
                    FROM scoring_ranges
                    WHERE parameter_id = $1
                      AND delivery_method = $2
                      AND (
                        (min_value IS NULL AND $3 <= max_value) OR
                        (max_value IS NULL AND $3 >= min_value) OR
                        ($3 >= min_value AND $3 <= max_value)
                      )
                    ORDER BY is_exclusion ASC, score DESC
                    LIMIT 1
                """, param_id, delivery_method, value)

                if matching_range:
                    scores_data[param_name] = {
                        'score': matching_range['score'],
                        'range_text': matching_range['range_text'],
                        'is_exclusion': matching_range['is_exclusion'],
                        'param_value': value
                    }
                else:
                    # No matching range found
                    scores_data[param_name] = {
                        'score': 0,
                        'range_text': 'Out of Range',
                        'is_exclusion': True,
                        'param_value': value
                    }

        return scores_data

    async def _generate_rationales(
        self,
        drug_name: str,
        extracted_params: Dict[str, Optional[float]],
        scores_data: Dict[str, Dict[str, Any]],
        delivery_method: str
    ) -> Dict[str, str]:
        """
        Generate 1-sentence rationales for each score using LLM.

        Args:
            drug_name: Drug name
            extracted_params: Extracted parameter values
            scores_data: Score data for each parameter
            delivery_method: Delivery method

        Returns:
            Dict with parameter -> rationale
        """
        rationales = {}

        from ..core.llm_service import LLMService
        llm_service = LLMService()

        for param_name in self.parameters:
            value = extracted_params.get(param_name)
            score_info = scores_data.get(param_name, {})
            score = score_info.get('score')
            range_text = score_info.get('range_text')

            if value is None or score is None:
                rationales[param_name] = f"Parameter value not available for {param_name}."
                continue

            prompt = f"""Generate a concise 1-sentence rationale explaining why {drug_name} received a score of {score} for {param_name}.

Parameter: {param_name}
Value: {value}
Score: {score}
Range: {range_text}
Delivery Method: {delivery_method}

Requirements:
- Exactly ONE sentence
- Explain the clinical/pharmaceutical significance
- Reference the parameter value and range
- Be specific and technical

Example format: "The {param_name} of {value} falls within the {range_text} range, indicating [pharmaceutical significance]."

Generate the rationale:"""

            try:
                response = await llm_service.generate(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=100
                )
                rationales[param_name] = response.strip()
            except Exception as e:
                logger.error(f"[RATIONALE] Failed for {param_name}: {str(e)}")
                rationales[param_name] = f"Score {score} assigned based on {param_name} value of {value} in range {range_text}."

        return rationales

    async def _calculate_weighted_scores(
        self,
        scores_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate weighted scores using category weightages.

        Args:
            scores_data: Score data for each parameter

        Returns:
            Dict with parameter -> weighted_score, plus total_score
        """
        async with DatabaseConnection() as conn:
            # Get weightages
            weightages = await conn.fetch("""
                SELECT sp.name, sc.weightage
                FROM scoring_parameters sp
                JOIN scoring_categories sc ON sp.category_id = sc.id
            """)
            weightage_map = {row['name']: float(row['weightage']) / 100.0 for row in weightages}

        weighted_data = {}
        total_score = 0.0

        for param_name in self.parameters:
            score = scores_data.get(param_name, {}).get('score')
            weightage = weightage_map.get(param_name, 0.0)

            if score is not None:
                weighted_score = score * weightage
            else:
                weighted_score = 0.0

            weighted_data[param_name] = {
                'score': score,
                'weightage': weightage,
                'weighted_score': weighted_score
            }

            total_score += weighted_score

        weighted_data['total_score'] = total_score

        return weighted_data

    def _generate_markdown_table(
        self,
        extracted_params: Dict[str, Optional[float]],
        scores_data: Dict[str, Dict[str, Any]],
        rationales: Dict[str, str],
        weighted_data: Dict[str, Any]
    ) -> str:
        """Generate markdown table output."""

        lines = []
        lines.append("## Parameter-Based Scoring Matrix")
        lines.append("")
        lines.append("| Parameter | Value | Score | Range | Weightage | Weighted Score | Rationale |")
        lines.append("|-----------|-------|-------|-------|-----------|----------------|-----------|")

        for param_name in self.parameters:
            value = extracted_params.get(param_name)
            score_info = scores_data.get(param_name, {})
            score = score_info.get('score')
            range_text = score_info.get('range_text', '')

            weighted_info = weighted_data.get(param_name, {})
            weightage = weighted_info.get('weightage', 0.0)
            weighted_score = weighted_info.get('weighted_score', 0.0)

            rationale = rationales.get(param_name, '')

            value_str = f"{value}" if value is not None else "N/A"
            score_str = f"{score}" if score is not None else "N/A"
            weightage_str = f"{weightage * 100:.0f}%"
            weighted_str = f"{weighted_score:.2f}"

            lines.append(f"| {param_name} | {value_str} | {score_str} | {range_text} | {weightage_str} | {weighted_str} | {rationale} |")

        lines.append("")
        lines.append(f"**Total Weighted Score:** {weighted_data.get('total_score', 0.0):.2f}")

        return "\n".join(lines)

    def _generate_json_table(
        self,
        extracted_params: Dict[str, Optional[float]],
        scores_data: Dict[str, Dict[str, Any]],
        rationales: Dict[str, str],
        weighted_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate JSON format table output."""

        parameters_list = []

        for param_name in self.parameters:
            value = extracted_params.get(param_name)
            score_info = scores_data.get(param_name, {})
            weighted_info = weighted_data.get(param_name, {})

            parameters_list.append({
                "parameter": param_name,
                "value": value,
                "score": score_info.get('score'),
                "range": score_info.get('range_text'),
                "is_exclusion": score_info.get('is_exclusion', False),
                "weightage": weighted_info.get('weightage'),
                "weighted_score": weighted_info.get('weighted_score'),
                "rationale": rationales.get(param_name)
            })

        return {
            "parameters": parameters_list,
            "total_weighted_score": weighted_data.get('total_score', 0.0)
        }
