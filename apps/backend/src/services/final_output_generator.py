"""
Final Output Generator Service

Generates the complete final output JSON matching the apixaban-complete-response.json format.
Assembles data from:
- merged_data_results (Phase 1 categories)
- phase2_results (suitability matrix)
- LLM generation (executive summary, recommendations)

Author: CognitoAI Development Team
Version: 1.0.0
"""

import asyncpg
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from ..utils.db_connection import get_db_connection, DatabaseConnection
from ..core.llm_service import LLMService

logger = logging.getLogger(__name__)


class FinalOutputGenerator:
    """
    Generates the complete final output JSON matching the required format.

    This service assembles all Phase 1 and Phase 2 results into a single
    comprehensive JSON document ready for webhook delivery or API retrieval.
    """

    def __init__(self):
        self.llm_service = LLMService()

        # Category name mapping: DB name -> JSON key
        self.category_mapping = {
            "Market Overview": "market_overview",
            "Competitive Landscape": "competitive_landscape",
            "Regulatory & Patent Status": "regulatory_and_patent_status",
            "Commercial Opportunities": "commercial_opportunities_and_risks",
            "Current Formulations": "current_formulations",
            "Investigational Formulations": "investigational_formulations",
            "Physicochemical Profile": "physicochemical_and_suitability_profile",
            "Pharmacokinetics": "pharmacokinetics",
            "Dosage Forms": "dosage_and_delivery_challenges",
            "Clinical Trials & Safety": "clinical_trials"
        }

        # Parameter weights for scoring
        self.parameter_weights = {
            "Dose": 0.40,
            "Molecular Weight": 0.30,
            "Melting Point": 0.20,
            "Log P": 0.10
        }

    async def generate_final_output(self, request_id: str) -> Dict[str, Any]:
        """
        Generate complete final output for a request.

        Args:
            request_id: UUID of the request

        Returns:
            Complete JSON matching apixaban-complete-response.json format

        Raises:
            ValueError: If request not found or incomplete
        """
        logger.info(f"[FINAL_OUTPUT] Starting generation for request_id={request_id}")

        try:
            # 1. Get request details
            request = await self._get_request(request_id)
            if not request:
                raise ValueError(f"Request {request_id} not found")

            logger.info(f"[FINAL_OUTPUT] Request found: {request['drug_name']} - {request['delivery_method']}")

            # 2. Gather all Phase 1 categories from merged_data_results
            phase1_categories = await self._gather_phase1_categories(request_id)
            logger.info(f"[FINAL_OUTPUT] Gathered {len(phase1_categories)} Phase 1 categories")

            # 3. Gather Phase 2 scoring results
            suitability_matrix = await self._build_suitability_matrix(request_id, request['delivery_method'])
            logger.info(f"[FINAL_OUTPUT] Built suitability matrix with TD={suitability_matrix.get('td_total', 0)}, TM={suitability_matrix.get('tm_total', 0)}")

            # 4. Calculate data coverage scorecard
            data_coverage = await self._calculate_data_coverage(phase1_categories)
            logger.info(f"[FINAL_OUTPUT] Calculated data coverage")

            # 5. Generate executive summary using LLM
            executive_summary = await self._generate_executive_summary(
                request=request,
                phase1=phase1_categories,
                suitability=suitability_matrix,
                coverage=data_coverage
            )
            logger.info(f"[FINAL_OUTPUT] Generated executive summary: {executive_summary.get('decision', 'N/A')}")

            # 6. Generate recommendations using LLM
            recommendations = await self._generate_recommendations(
                request=request,
                suitability=suitability_matrix,
                executive=executive_summary,
                phase1=phase1_categories
            )
            logger.info(f"[FINAL_OUTPUT] Generated {len(recommendations.get('data', []))} recommendations")

            # 7. Assemble final JSON
            final_output = {
                "request_id": request_id,
                "webhookType": "drug",
                "unstructured_data": "",
                "structured_data": {
                    "executive_summary_and_decision": executive_summary,

                    # Phase 1 categories (snake_case keys)
                    **{self.category_mapping[cat_name]: cat_data
                       for cat_name, cat_data in phase1_categories.items()
                       if cat_name in self.category_mapping},

                    # Phase 2 scoring (remove internal fields)
                    "suitability_matrix": {k: v for k, v in suitability_matrix.items()
                                          if k not in ['td_total', 'tm_total']},

                    # Meta sections
                    "data_coverage_scorecard": data_coverage,
                    "recommendations": recommendations
                }
            }

            # 8. Store to database
            await self._store_final_output(
                request_id=request_id,
                drug_name=request['drug_name'],
                delivery_method=request['delivery_method'],
                final_output=final_output,
                td_score=suitability_matrix.get('td_total', 0),
                tm_score=suitability_matrix.get('tm_total', 0),
                td_verdict=suitability_matrix.get('td_verdict', 'Unknown'),
                tm_verdict=suitability_matrix.get('tm_verdict', 'Unknown'),
                go_decision=executive_summary.get('decision', 'UNKNOWN'),
                investment_priority=executive_summary.get('investment_priority', 'Medium'),
                risk_level=executive_summary.get('risk_level', 'Medium')
            )

            logger.info(f"[FINAL_OUTPUT] Successfully generated and stored final output for {request_id}")

            return final_output

        except Exception as e:
            logger.error(f"[FINAL_OUTPUT] Failed to generate final output for {request_id}: {str(e)}")
            import traceback
            logger.error(f"[FINAL_OUTPUT] Traceback: {traceback.format_exc()}")
            raise

    async def _get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get request details from database"""
        async with DatabaseConnection() as conn:
            row = await conn.fetchrow("""
                SELECT id, drug_name, status, created_at
                FROM drug_requests
                WHERE id = $1
            """, request_id)

            if row:
                result = dict(row)
                # Add default delivery_method since it's not in drug_requests table
                result['delivery_method'] = 'Transdermal'  # Default
                return result
            return None

    async def _gather_phase1_categories(self, request_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Gather all Phase 1 category data from merged_data_results and category_results.

        Returns dict keyed by category name with structured_data + LLM summary.
        """
        print("\n" + "="*100)
        print("METHOD CALLED: _gather_phase1_categories")
        print(f"Request ID: {request_id}")
        print("="*100 + "\n")

        logger.info(f"[FINAL_OUTPUT] Gathering Phase 1 categories for {request_id}")

        async with DatabaseConnection() as conn:
            # Join merged_data_results with category_results to get LLM summary
            results = await conn.fetch("""
                SELECT
                    mdr.category_name,
                    mdr.merged_content,
                    mdr.structured_data,
                    mdr.merge_confidence_score,
                    mdr.data_quality_score,
                    cr.summary as llm_summary
                FROM merged_data_results mdr
                LEFT JOIN category_results cr ON cr.request_id = mdr.request_id
                    AND cr.category_name = mdr.category_name
                WHERE mdr.request_id = $1
                ORDER BY mdr.created_at
            """, request_id)

            categories = {}
            for row in results:
                category_name = row['category_name']

                # Parse structured_data if it's a string
                structured_data = row['structured_data']
                if isinstance(structured_data, str):
                    try:
                        structured_data = json.loads(structured_data)
                    except (json.JSONDecodeError, TypeError):
                        structured_data = {}
                elif structured_data is None:
                    structured_data = {}

                # Use LLM summary only, do not fall back to merged_content
                # DEBUG: Check what keys are in the row
                print(f"\n{'='*80}")
                print(f"DEBUG - Category: {category_name}")
                print(f"  Row keys: {list(row.keys())}")

                llm_summary_value = row.get('llm_summary')
                merged_content_value = row.get('merged_content')

                print(f"  llm_summary: {'YES' if llm_summary_value else 'NO'} ({len(llm_summary_value) if llm_summary_value else 0} chars)")
                print(f"  merged_content: {'YES' if merged_content_value else 'NO'} ({len(merged_content_value) if merged_content_value else 0} chars)")

                # Use LLM summary instead of merged_content
                if llm_summary_value:
                    summary_text = llm_summary_value
                    print(f"  USING: LLM Summary ({len(summary_text)} chars)")
                else:
                    summary_text = ""  # Empty string if no LLM summary available
                    print(f"  WARNING: No LLM summary available for {category_name}")

                # Double-check we're NOT using merged_content
                if llm_summary_value and llm_summary_value == merged_content_value:
                    print(f"  WARNING: LLM summary matches merged_content!")

                print(f"{'='*80}\n")

                logger.info(f"[FINAL_OUTPUT] Category: {category_name}, LLM Summary: {bool(llm_summary_value)}, Len: {len(summary_text)}")

                # Build category dict with LLM summary + structured fields
                # Put summary AFTER spreading structured_data won't overwrite
                category_dict = {
                    **structured_data,  # Spread the structured data FIRST
                    "summary": summary_text  # Then set summary - this overwrites any 'summary' in structured_data
                }

                categories[category_name] = category_dict
                logger.info(f"[FINAL_OUTPUT] Loaded category: {category_name}")

            return categories

    async def _build_suitability_matrix(self, request_id: str, delivery_method: str) -> Dict[str, Any]:
        """
        Build suitability matrix from phase2_results.

        Matches the format in lines 803-899 of sample JSON.
        """
        logger.info(f"[FINAL_OUTPUT] Building suitability matrix for {request_id}")

        async with DatabaseConnection() as conn:
            # Get Phase 2 parameter scores
            params = await conn.fetch("""
                SELECT
                    parameter_name,
                    extracted_value,
                    score,
                    weighted_score,
                    extraction_method,
                    unit
                FROM phase2_results
                WHERE request_id = $1
                ORDER BY
                    CASE parameter_name
                        WHEN 'Dose' THEN 1
                        WHEN 'Molecular Weight' THEN 2
                        WHEN 'Melting Point' THEN 3
                        WHEN 'Log P' THEN 4
                        ELSE 5
                    END
            """, request_id)

            if not params:
                logger.warning(f"[FINAL_OUTPUT] No Phase 2 results found for {request_id}")
                return self._empty_suitability_matrix()

            # Build parameter scoring
            parameter_scores = []
            td_total = 0.0
            tm_total = 0.0

            for param in params:
                param_name = param['parameter_name']
                value = param['extracted_value']
                score = param['score'] or 0
                weighted_score = param['weighted_score'] or 0
                unit = param['unit'] or ""

                # Format value with unit
                if value is not None:
                    if unit:
                        formatted_value = f"{value} {unit}"
                    else:
                        formatted_value = str(value)
                else:
                    formatted_value = "Not available"

                # Get rationale from scoring range
                rationale = await self._get_score_rationale(
                    conn, param_name, value, score, delivery_method
                )

                parameter_scores.append({
                    "parameter": param_name,
                    f"{request_id[:8]}_value": formatted_value,  # Use short request ID as prefix
                    "td_score": score,
                    "td_rationale": rationale,
                    "tm_score": score,  # Same for both routes in current implementation
                    "tm_rationale": rationale
                })

                # Calculate weighted totals
                td_total += weighted_score
                tm_total += weighted_score

            # Determine verdicts
            td_verdict = self._get_verdict(td_total)
            tm_verdict = self._get_verdict(tm_total)
            td_category = self._get_decision_category(td_total)
            tm_category = self._get_decision_category(tm_total)
            td_priority = self._get_priority(td_total)
            tm_priority = self._get_priority(tm_total)

            return {
                "summary": f"The quantitative analysis shows that both transdermal and transmucosal routes have been evaluated. "
                          f"Transmucosal delivery scores {tm_total:.1f}/9 while transdermal scores {td_total:.1f}/9.",
                "corrected_parameter_based_scoring": parameter_scores,
                "weighted_scoring_assessment": {
                    "td_weighted_score": {
                        **{param['parameter_name'].lower().replace(' ', '_'):
                           f"{param['score']} × {self.parameter_weights.get(param['parameter_name'], 0.25):.2f} = "
                           f"{param['weighted_score']:.1f}"
                           for param in params},
                        "total_td_score": f"{td_total:.1f}"
                    },
                    "tm_weighted_score": {
                        **{param['parameter_name'].lower().replace(' ', '_'):
                           f"{param['score']} × {self.parameter_weights.get(param['parameter_name'], 0.25):.2f} = "
                           f"{param['weighted_score']:.1f}"
                           for param in params},
                        "total_tm_score": f"{tm_total:.1f}"
                    }
                },
                "delivery_route_feasibility_assessment": [
                    {
                        "route": "Transdermal (TD)",
                        "total_score": f"{td_total:.1f}",
                        "max_possible": "9",
                        "percentage": f"{td_total/9*100:.2f}%",
                        "decision_category": td_category,
                        "cognito_verdict": td_verdict,
                        "development_priority": td_priority
                    },
                    {
                        "route": "Transmucosal (TM)",
                        "total_score": f"{tm_total:.1f}",
                        "max_possible": "9",
                        "percentage": f"{tm_total/9*100:.2f}%",
                        "decision_category": tm_category,
                        "cognito_verdict": tm_verdict,
                        "development_priority": tm_priority
                    }
                ],
                "final_weighted_scores": {
                    "transdermal_td": f"{td_total:.1f} ({td_total/9*100:.2f}%)",
                    "transmucosal_tm": f"{tm_total:.1f} ({tm_total/9*100:.2f}%)"
                },
                "strategic_decision_matrix": {
                    "go_no_go_verdicts": {
                        "transdermal_route": f"{td_verdict} - {self._get_verdict_rationale(td_total, parameter_scores)}",
                        "transmucosal_route": f"{tm_verdict} - {self._get_verdict_rationale(tm_total, parameter_scores)}"
                    },
                    "risk_assessment": {
                        "high_risk_factors": {
                            "td": self._get_risk_factors(parameter_scores, "td"),
                            "tm": self._get_risk_factors(parameter_scores, "tm")
                        },
                        "mitigation_opportunities": {
                            "td": "Advanced penetration enhancers and formulation technologies.",
                            "tm": "Permeation enhancers and novel delivery systems."
                        },
                        "success_probability": {
                            "td_route": f"{self._get_success_probability(td_total)} - {self._get_risk_level(td_total)} risk",
                            "tm_route": f"{self._get_success_probability(tm_total)} - {self._get_risk_level(tm_total)} risk"
                        }
                    }
                },
                # Internal fields for storage
                "td_total": td_total,
                "tm_total": tm_total,
                "td_verdict": td_verdict,
                "tm_verdict": tm_verdict
            }

    async def _get_score_rationale(
        self,
        conn: asyncpg.Connection,
        parameter_name: str,
        value: Optional[float],
        score: float,
        delivery_method: str
    ) -> str:
        """Get rationale for score from scoring_ranges table"""
        if value is None:
            return "Parameter not available for scoring"

        row = await conn.fetchrow("""
            SELECT range_text, min_value, max_value
            FROM scoring_ranges
            WHERE parameter_id = (SELECT id FROM scoring_parameters WHERE name = $1)
              AND delivery_method = $2
              AND score = $3
            LIMIT 1
        """, parameter_name, delivery_method, score)

        if row:
            return f"{parameter_name} value of {value} falls within the {row['range_text']} range"
        else:
            return f"{parameter_name} scored {score}/9"

    def _empty_suitability_matrix(self) -> Dict[str, Any]:
        """Return empty suitability matrix structure"""
        return {
            "summary": "Suitability analysis pending - no parameter data available yet.",
            "corrected_parameter_based_scoring": [],
            "weighted_scoring_assessment": {
                "td_weighted_score": {"total_td_score": "0"},
                "tm_weighted_score": {"total_tm_score": "0"}
            },
            "delivery_route_feasibility_assessment": [],
            "final_weighted_scores": {
                "transdermal_td": "0 (0%)",
                "transmucosal_tm": "0 (0%)"
            },
            "td_total": 0,
            "tm_total": 0,
            "td_verdict": "Pending",
            "tm_verdict": "Pending"
        }

    def _get_verdict(self, score: float) -> str:
        """Determine Go/No-Go verdict based on score"""
        if score >= 7.0:
            return "Go"
        elif score >= 5.0:
            return "Conditional-Go"
        else:
            return "No-Go"

    def _get_decision_category(self, score: float) -> str:
        """Determine decision category based on score"""
        if score >= 7.5:
            return "Highly Suitable"
        elif score >= 6.0:
            return "Suitable"
        elif score >= 4.5:
            return "Moderate"
        else:
            return "Limited Suitability"

    def _get_priority(self, score: float) -> str:
        """Determine development priority based on score"""
        if score >= 7.5:
            return "High"
        elif score >= 5.5:
            return "Medium"
        else:
            return "Low"

    def _get_risk_level(self, score: float) -> str:
        """Determine risk level based on score"""
        if score >= 7.0:
            return "Low"
        elif score >= 5.0:
            return "Medium"
        else:
            return "High"

    def _get_success_probability(self, score: float) -> str:
        """Determine success probability based on score"""
        if score >= 7.5:
            return "High"
        elif score >= 6.0:
            return "Medium-High"
        elif score >= 4.5:
            return "Medium"
        else:
            return "Low"

    def _get_verdict_rationale(self, score: float, params: List[Dict]) -> str:
        """Generate rationale for verdict"""
        if score >= 7.0:
            return "Favorable physicochemical properties support development"
        elif score >= 5.0:
            return "Moderate suitability with formulation enhancement required"
        else:
            # Find limiting parameters
            limiting = [p['parameter'] for p in params if p['td_score'] < 5]
            if limiting:
                return f"Limited by {', '.join(limiting[:2])} constraints"
            return "Physicochemical limitations present development challenges"

    def _get_risk_factors(self, params: List[Dict], route: str) -> str:
        """Identify high-risk factors"""
        low_scoring = [p['parameter'] for p in params if p['td_score'] < 5]
        if low_scoring:
            return f"Challenges with {', '.join(low_scoring)} require mitigation strategies"
        return "No significant high-risk factors identified"

    async def _calculate_data_coverage(self, phase1_categories: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Calculate data coverage scorecard.

        Analyzes completeness of data for each category.
        """
        logger.info(f"[FINAL_OUTPUT] Calculating data coverage scorecard")

        # Expected categories and their data sources
        expected_categories = {
            "Market Overview": "IQVIA, Market Analysis Reports",
            "Competitive Landscape": "Market Intelligence, Company Reports",
            "Regulatory & Patent Status": "FDA, EMA, USPTO, EPO",
            "Commercial Opportunities": "Market Analysis Reports",
            "Current Formulations": "FDA, Manufacturer Reports",
            "Investigational Formulations": "Company Reports, ClinicalTrials.gov",
            "Physicochemical Profile": "PubChem, Literature",
            "Pharmacokinetics": "FDA Label, PubMed",
            "Dosage Forms": "FDA Label, Manufacturer Reports",
            "Clinical Trials & Safety": "ClinicalTrials.gov, PubMed"
        }

        coverage_data = []
        total_completion = 0

        for cat_name, data_source in expected_categories.items():
            if cat_name in phase1_categories:
                cat_data = phase1_categories[cat_name]

                # Calculate completion based on data presence
                completion = self._calculate_category_completion(cat_name, cat_data)

                # Convert to JSON key
                json_key = self.category_mapping.get(cat_name, cat_name.lower().replace(' ', '_'))

                coverage_data.append({
                    "category": json_key.replace('_', ' ').title(),
                    "completion_percent": f"{completion}%",
                    "data_source": data_source,
                    "notes": self._get_coverage_notes(cat_name, cat_data, completion)
                })

                total_completion += completion
            else:
                # Category missing
                json_key = self.category_mapping.get(cat_name, cat_name.lower().replace(' ', '_'))
                coverage_data.append({
                    "category": json_key.replace('_', ' ').title(),
                    "completion_percent": "0%",
                    "data_source": data_source,
                    "notes": "Data not available - category not processed"
                })

        avg_completion = total_completion / len(expected_categories) if expected_categories else 0

        return {
            "summary": f"The data coverage is {'comprehensive' if avg_completion >= 85 else 'partial'} across "
                      f"{'most' if avg_completion >= 70 else 'some'} categories, with an average completion of {avg_completion:.0f}%. "
                      f"{'Robust data available for decision-making.' if avg_completion >= 80 else 'Additional data gathering recommended for key categories.'}",
            "data": coverage_data
        }

    def _calculate_category_completion(self, category_name: str, category_data: Dict) -> int:
        """Calculate completion percentage for a category (0-100)"""
        # Basic heuristic: check for summary and structured data presence
        score = 0

        # Has summary text (40 points)
        summary = category_data.get('summary', '')
        if summary and len(summary) > 100:
            score += 40
        elif summary:
            score += 20

        # Has structured data (60 points)
        structured_keys = [k for k in category_data.keys() if k != 'summary']
        if len(structured_keys) >= 3:
            score += 60
        elif len(structured_keys) >= 1:
            score += 30

        return min(score, 100)

    def _get_coverage_notes(self, category_name: str, category_data: Dict, completion: int) -> str:
        """Generate notes about data coverage"""
        if completion >= 90:
            return "Comprehensive data with detailed insights."
        elif completion >= 70:
            return "Good coverage with most key data points available."
        elif completion >= 50:
            return "Partial coverage - additional data could enhance analysis."
        else:
            return "Limited data available - consider additional research."

    async def _generate_executive_summary(
        self,
        request: Dict,
        phase1: Dict,
        suitability: Dict,
        coverage: Dict
    ) -> Dict[str, Any]:
        """
        Generate executive summary using LLM.

        This creates the high-level strategic summary with GO/NO-GO decision.
        """
        logger.info(f"[FINAL_OUTPUT] Generating executive summary via LLM")

        # Extract key metrics
        td_score = suitability.get('td_total', 0)
        tm_score = suitability.get('tm_total', 0)
        td_verdict = suitability.get('td_verdict', 'Unknown')
        tm_verdict = suitability.get('tm_verdict', 'Unknown')

        # Get market data
        market_data = phase1.get('Market Overview', {})
        market_current = market_data.get('current', [{}])[0] if market_data.get('current') else {}
        market_forecast = market_data.get('forecast', [{}])[0] if market_data.get('forecast') else {}

        # Get patent data
        patent_data = phase1.get('Regulatory & Patent Status', {})

        # Build prompt for LLM
        prompt = f"""Generate an executive summary and GO/NO-GO decision for the following drug development opportunity:

**Drug:** {request['drug_name']}
**Delivery Method:** {request['delivery_method']}

**Market Overview:**
- Current Market Size: {market_current.get('market_size_usd', 'N/A')}
- Forecast Market Size: {market_forecast.get('market_size_usd', 'N/A')}
- Growth Rate (CAGR): {market_forecast.get('cagr', 'N/A')}

**Suitability Scores:**
- Transdermal: {td_score:.1f}/9 ({td_verdict})
- Transmucosal: {tm_score:.1f}/9 ({tm_verdict})

**Patent Status:**
Available in phase1 data (analyze for patent cliff timing)

**Data Coverage:**
Average: {coverage.get('summary', 'N/A')}

Generate a concise executive summary (2-3 sentences) and provide:
1. GO/NO-GO/CONDITIONAL decision
2. Investment priority (Low/Medium/High)
3. Risk level (Low/Medium/High)
4. Key strategic points (5-7 bullet points covering market size, growth, patent timing, formulation focus, geographic strategy, risk assessment)

Return ONLY valid JSON in this exact format:
{{
    "summary": "2-3 sentence executive summary...",
    "data": [
        {{
            "decision": "GO or NO-GO or CONDITIONAL",
            "justification": "Brief justification",
            "key_criteria": "Main decision criteria",
            "risk_level": "Low or Medium or High"
        }}
    ],
    "key_summary_points": {{
        "decision": "Clear decision statement",
        "market_size": "Current → Projected",
        "growth_rate": "CAGR description",
        "patent_timing": "Patent expiry analysis",
        "formulation_focus": "Key formulation strategy",
        "geographic_strategy": "Geographic focus",
        "investment_level": "Low or Medium or High priority",
        "risk_assessment": "Risk level with description"
    }},
    "decision": "GO or NO-GO or CONDITIONAL",
    "investment_priority": "Low or Medium or High",
    "risk_level": "Low or Medium or High"
}}"""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.3,  # Lower temperature for more consistent output
                max_tokens=1000
            )

            # Parse JSON response
            summary_data = json.loads(response.strip())

            logger.info(f"[FINAL_OUTPUT] Executive summary generated: {summary_data.get('decision', 'N/A')}")

            return summary_data

        except Exception as e:
            logger.error(f"[FINAL_OUTPUT] Failed to generate executive summary: {str(e)}")
            # Fallback to rule-based summary
            return self._fallback_executive_summary(request, td_score, tm_score, market_current, market_forecast)

    def _fallback_executive_summary(
        self,
        request: Dict,
        td_score: float,
        tm_score: float,
        market_current: Dict,
        market_forecast: Dict
    ) -> Dict[str, Any]:
        """Fallback executive summary when LLM fails"""
        best_score = max(td_score, tm_score)

        if best_score >= 7.0:
            decision = "GO"
            priority = "High"
            risk = "Medium"
        elif best_score >= 5.0:
            decision = "CONDITIONAL"
            priority = "Medium"
            risk = "Medium"
        else:
            decision = "NO-GO"
            priority = "Low"
            risk = "High"

        return {
            "summary": f"{request['drug_name']} shows {self._get_decision_category(best_score).lower()} potential "
                      f"for {request['delivery_method']} delivery with a suitability score of {best_score:.1f}/9. "
                      f"{decision} decision recommended based on technical feasibility and market analysis.",
            "data": [
                {
                    "decision": decision,
                    "justification": f"Suitability score of {best_score:.1f}/9 indicates {self._get_decision_category(best_score).lower()} potential",
                    "key_criteria": "Suitability score, market size, technical feasibility",
                    "risk_level": risk
                }
            ],
            "key_summary_points": {
                "decision": f"{decision} - {self._get_decision_category(best_score)}",
                "market_size": f"{market_current.get('market_size_usd', 'N/A')} → {market_forecast.get('market_size_usd', 'N/A')}",
                "growth_rate": market_forecast.get('cagr', 'N/A'),
                "patent_timing": "See detailed patent analysis",
                "formulation_focus": request['delivery_method'],
                "geographic_strategy": "Global opportunity",
                "investment_level": f"{priority} priority",
                "risk_assessment": f"{risk} risk level"
            },
            "decision": decision,
            "investment_priority": priority,
            "risk_level": risk
        }

    async def _generate_recommendations(
        self,
        request: Dict,
        suitability: Dict,
        executive: Dict,
        phase1: Dict
    ) -> Dict[str, Any]:
        """
        Generate strategic recommendations using LLM.
        """
        logger.info(f"[FINAL_OUTPUT] Generating recommendations via LLM")

        td_score = suitability.get('td_total', 0)
        tm_score = suitability.get('tm_total', 0)
        decision = executive.get('decision', 'UNKNOWN')

        prompt = f"""Generate 3-5 strategic recommendations for the following drug development opportunity:

**Drug:** {request['drug_name']}
**Decision:** {decision}
**Transdermal Score:** {td_score:.1f}/9
**Transmucosal Score:** {tm_score:.1f}/9

Generate actionable recommendations covering:
1. Formulation development priorities
2. Market expansion strategies
3. Risk mitigation approaches
4. Patent/regulatory strategies
5. Investment priorities

Return ONLY valid JSON in this exact format:
{{
    "summary": "1-2 sentence overview of key recommendations",
    "data": [
        {{
            "recommendation": "Clear, actionable recommendation",
            "rationale": "Why this is important with specific metrics/data",
            "timeline": "Timeframe (e.g., '6-12 months', '12-18 months')",
            "owner": "Responsible function (e.g., 'R&D', 'Commercial', 'Clinical Development')"
        }}
    ]
}}"""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.4,
                max_tokens=1200
            )

            recommendations_data = json.loads(response.strip())

            logger.info(f"[FINAL_OUTPUT] Generated {len(recommendations_data.get('data', []))} recommendations")

            return recommendations_data

        except Exception as e:
            logger.error(f"[FINAL_OUTPUT] Failed to generate recommendations: {str(e)}")
            # Fallback to rule-based recommendations
            return self._fallback_recommendations(decision, td_score, tm_score, request['delivery_method'])

    def _fallback_recommendations(
        self,
        decision: str,
        td_score: float,
        tm_score: float,
        delivery_method: str
    ) -> Dict[str, Any]:
        """Fallback recommendations when LLM fails"""
        recs = []

        if decision == "GO":
            recs.append({
                "recommendation": f"Prioritize development of {delivery_method} delivery system",
                "rationale": f"High suitability score ({max(td_score, tm_score):.1f}/9) indicates strong technical feasibility",
                "timeline": "12-18 months",
                "owner": "R&D"
            })
            recs.append({
                "recommendation": "Conduct market validation studies",
                "rationale": "Confirm market demand and pricing assumptions before full-scale development",
                "timeline": "6-9 months",
                "owner": "Commercial"
            })
        elif decision == "CONDITIONAL":
            recs.append({
                "recommendation": "Address formulation challenges through advanced technologies",
                "rationale": f"Moderate score ({max(td_score, tm_score):.1f}/9) requires formulation enhancement",
                "timeline": "12-24 months",
                "owner": "R&D"
            })
        else:  # NO-GO
            recs.append({
                "recommendation": "Explore alternative delivery routes",
                "rationale": f"Current route shows limited feasibility (score: {max(td_score, tm_score):.1f}/9)",
                "timeline": "6-12 months",
                "owner": "R&D"
            })

        recs.append({
            "recommendation": "Monitor competitive landscape and patent expirations",
            "rationale": "Stay informed of market dynamics and generic entry timing",
            "timeline": "Ongoing",
            "owner": "Strategic Planning"
        })

        return {
            "summary": f"Key recommendations focus on {'advancing development' if decision == 'GO' else 'addressing limitations'} "
                      f"and managing commercial risks.",
            "data": recs
        }

    async def _store_final_output(
        self,
        request_id: str,
        drug_name: str,
        delivery_method: str,
        final_output: Dict,
        td_score: float,
        tm_score: float,
        td_verdict: str,
        tm_verdict: str,
        go_decision: str,
        investment_priority: str,
        risk_level: str
    ) -> None:
        """Store final output to database"""
        logger.info(f"[FINAL_OUTPUT] Storing final output to database for {request_id}")

        async with DatabaseConnection() as conn:
            await conn.execute("""
                INSERT INTO request_final_output (
                    request_id,
                    drug_name,
                    delivery_method,
                    final_output,
                    overall_td_score,
                    overall_tm_score,
                    td_verdict,
                    tm_verdict,
                    go_decision,
                    investment_priority,
                    risk_level
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (request_id)
                DO UPDATE SET
                    final_output = EXCLUDED.final_output,
                    overall_td_score = EXCLUDED.overall_td_score,
                    overall_tm_score = EXCLUDED.overall_tm_score,
                    td_verdict = EXCLUDED.td_verdict,
                    tm_verdict = EXCLUDED.tm_verdict,
                    go_decision = EXCLUDED.go_decision,
                    investment_priority = EXCLUDED.investment_priority,
                    risk_level = EXCLUDED.risk_level,
                    updated_at = NOW()
            """, request_id, drug_name, delivery_method, json.dumps(final_output),
                td_score, tm_score, td_verdict, tm_verdict, go_decision,
                investment_priority, risk_level)

        logger.info(f"[FINAL_OUTPUT] Successfully stored final output")

    async def get_final_output(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored final output from database.

        Args:
            request_id: UUID of the request

        Returns:
            Final output JSON or None if not found
        """
        async with DatabaseConnection() as conn:
            row = await conn.fetchrow("""
                SELECT final_output
                FROM request_final_output
                WHERE request_id = $1
            """, request_id)

            if row:
                return row['final_output']
            return None
