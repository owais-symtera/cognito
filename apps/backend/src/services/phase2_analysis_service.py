"""
Phase 2 Analysis Service for LLM-based Decision Intelligence Categories.

Generates strategic analysis outputs for:
- Executive Summary & Go/No-Go Decision
- Weighted Scoring Assessment
- Go/No-Go Verdict
- Risk Assessment
- Strategic Recommendations
- Investment Analysis
"""
import json
import time
from typing import Dict, List, Any, Optional
import structlog
from datetime import datetime

from ..core.llm_service import LLMService
from .data_storage_service import DataStorageService

logger = structlog.get_logger(__name__)


class Phase2AnalysisService:
    """
    Service for Phase 2 LLM-based analysis categories.

    Processes Phase 1 results to generate strategic decision intelligence
    outputs without mentioning internal processing details.
    """

    def __init__(self):
        self.llm_service = LLMService()

    async def process_analysis_category(
        self,
        category_name: str,
        drug_name: str,
        request_id: str,
        phase1_data: Dict[str, Any],
        scoring_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a Phase 2 analysis category using LLM.

        Args:
            category_name: Phase 2 category name
            drug_name: Drug name
            request_id: Request ID
            phase1_data: Phase 1 category results
            scoring_results: Parameter-Based Scoring Matrix results (if available)

        Returns:
            Dict containing:
                - summary: Generated analysis text (markdown)
                - structured_data: Extracted structured information
                - confidence_score: Analysis confidence
                - metadata: Processing metadata
        """
        logger.info(f"[PHASE2_ANALYSIS] Processing {category_name} for {drug_name}")

        try:
            # Route to category-specific processor
            # Match exact database category names
            if category_name == "Executive Summary & Recommendations":
                return await self._generate_executive_summary(
                    drug_name, request_id, phase1_data, scoring_results
                )
            elif category_name == "Weighted Scoring Assessment":
                return await self._generate_weighted_assessment(
                    drug_name, request_id, phase1_data, scoring_results
                )
            elif category_name == "Go/No-Go Recommendation":
                return await self._generate_go_nogo_verdict(
                    drug_name, request_id, phase1_data, scoring_results
                )
            elif category_name == "Risk Assessment Analysis":
                return await self._generate_risk_assessment(
                    drug_name, request_id, phase1_data, scoring_results
                )
            elif category_name == "Strategic Opportunities Analysis":
                return await self._generate_strategic_recommendations(
                    drug_name, request_id, phase1_data, scoring_results
                )
            elif category_name == "Competitive Positioning Strategy":
                return await self._generate_investment_analysis(
                    drug_name, request_id, phase1_data, scoring_results
                )
            else:
                logger.warning(f"[PHASE2_ANALYSIS] Unknown category: {category_name}")
                return {
                    "summary": f"Analysis for {category_name} is not yet implemented.",
                    "structured_data": {},
                    "confidence_score": 0.0,
                    "metadata": {"error": "Unknown category"}
                }

        except Exception as e:
            logger.error(f"[PHASE2_ANALYSIS] Error processing {category_name}: {str(e)}")
            import traceback
            logger.error(f"[PHASE2_ANALYSIS] Traceback: {traceback.format_exc()}")
            raise

    async def _generate_executive_summary(
        self,
        drug_name: str,
        request_id: str,
        phase1_data: Dict[str, Any],
        scoring_results: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate Executive Summary & Go/No-Go Decision."""
        logger.info(f"[EXECUTIVE_SUMMARY] Generating for {drug_name}")

        # Prepare context from Phase 1 data
        context = self._prepare_phase1_context(phase1_data)

        # Add scoring results if available
        scoring_context = ""
        if scoring_results:
            scoring_context = f"""
## Scoring Analysis Results

**Total Weighted Score:** {scoring_results.get('total_score', 'N/A')}

**Parameter Scores:**
{self._format_scoring_results(scoring_results)}
"""

        prompt = f"""You are a pharmaceutical strategy consultant. Generate an Executive Summary & Go/No-Go Decision for {drug_name}.

## Available Data

{context}

{scoring_context}

## Instructions

Generate a comprehensive executive summary that includes:

1. **Opening Paragraph**: 3-4 sentence overview covering:
   - Current market value and projected growth
   - GO/NO-GO recommendation with key justification
   - Optimal delivery route and strategic focus
   - Investment priority level

2. **Decision Table** (markdown format):
| Decision | Justification | Key Criteria | Risk Level |
|----------|---------------|--------------|------------|
| GO or NO-GO | Brief justification (1 sentence) | Top 3 criteria | Low/Medium/High |

3. **Key Summary Points** (bulleted list):
   - Decision (GO/NO-GO)
   - Market size (current → projected)
   - Growth rate (CAGR)
   - Patent timing
   - Formulation focus
   - Geographic strategy
   - Investment level
   - Risk assessment

## Critical Requirements

- DO NOT mention "Phase 1", "Phase 2", "API providers", "ChatGPT", "Perplexity", "OpenAI", "Gemini", or any data sources
- Write as an authoritative pharmaceutical analyst
- Use ONLY data from the provided context
- If specific data is missing, state "Data not available" or "Information not publicly available"
- Be concise and executive-focused
- Use markdown formatting

Generate the executive summary:"""

        start_time = time.time()
        summary = await self.llm_service.generate(
            prompt=prompt,
            temperature=0.3,  # Low temperature for consistent analysis
            max_tokens=2000
        )
        response_time_ms = int((time.time() - start_time) * 1000)

        # Log API usage
        await self._log_api_usage(
            request_id, "executive_summary", len(prompt), len(summary), response_time_ms
        )

        return {
            "summary": summary.strip(),
            "structured_data": {
                "category_type": "executive_summary",
                "has_decision_table": True,
                "has_key_points": True
            },
            "confidence_score": 0.85,
            "metadata": {
                "generation_time_ms": response_time_ms,
                "analysis_type": "strategic_decision"
            }
        }

    async def _generate_weighted_assessment(
        self,
        drug_name: str,
        request_id: str,
        phase1_data: Dict[str, Any],
        scoring_results: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate Weighted Scoring Assessment."""
        logger.info(f"[WEIGHTED_ASSESSMENT] Generating for {drug_name}")

        if not scoring_results:
            return {
                "summary": "Weighted Scoring Assessment requires Parameter-Based Scoring Matrix results.",
                "structured_data": {},
                "confidence_score": 0.0,
                "metadata": {"error": "Missing scoring results"}
            }

        # Extract scoring data
        extracted_params = scoring_results.get('extracted_parameters', {})
        scores = scoring_results.get('scores', {})
        weighted_scores = scoring_results.get('weighted_scores', {})
        total_score = scoring_results.get('total_score', 0.0)
        delivery_method = scoring_results.get('delivery_method', 'Transdermal')

        prompt = f"""You are a pharmaceutical formulation scientist. Generate a Weighted Scoring Assessment for {drug_name}'s {delivery_method} delivery route.

## Scoring Results

**Parameters:**
- Dose: {extracted_params.get('Dose', 'N/A')} (Score: {scores.get('Dose', 'N/A')})
- Molecular Weight: {extracted_params.get('Molecular Weight', 'N/A')} Da (Score: {scores.get('Molecular Weight', 'N/A')})
- Melting Point: {extracted_params.get('Melting Point', 'N/A')}°C (Score: {scores.get('Melting Point', 'N/A')})
- Log P: {extracted_params.get('Log P', 'N/A')} (Score: {scores.get('Log P', 'N/A')})

**Weighted Scores:**
{json.dumps(weighted_scores, indent=2)}

**Total Score:** {total_score}

## Instructions

Generate a weighted scoring assessment that includes:

1. **Assessment Title**: "Weighted Scoring Assessment"

2. **Calculation Section**:
   - Show the weighted scoring formula
   - Break down each parameter calculation (score × weight)
   - Show total calculation

3. **Delivery Route Feasibility Table** (markdown):
| Route | Total Score | Max Possible | Percentage | Decision Category | Verdict | Development Priority |
|-------|-------------|--------------|------------|-------------------|---------|---------------------|
| {delivery_method} | {total_score} | 9 | XX.XX% | Moderate/High/Low | Go/No-Go | High/Medium/Low |

4. **Final Weighted Scores Summary**:
   - Transdermal (TD): X.X (XX.XX%)
   - Transmucosal (TM): X.X (XX.XX%)

## Critical Requirements

- DO NOT mention "Phase 1", "Phase 2", "API providers", or data sources
- Use ONLY the scoring data provided
- Calculate percentages as (total_score / 9) × 100
- Determine verdict: >70% = Go, 50-70% = Moderate, <50% = No-Go
- Use markdown formatting

Generate the weighted scoring assessment:"""

        start_time = time.time()
        summary = await self.llm_service.generate(
            prompt=prompt,
            temperature=0.2,  # Very low temperature for calculations
            max_tokens=1500
        )
        response_time_ms = int((time.time() - start_time) * 1000)

        await self._log_api_usage(
            request_id, "weighted_assessment", len(prompt), len(summary), response_time_ms
        )

        return {
            "summary": summary.strip(),
            "structured_data": {
                "category_type": "weighted_assessment",
                "total_score": total_score,
                "delivery_method": delivery_method,
                "percentage": (total_score / 9) * 100
            },
            "confidence_score": 0.90,
            "metadata": {
                "generation_time_ms": response_time_ms,
                "analysis_type": "scoring_calculation"
            }
        }

    async def _generate_go_nogo_verdict(
        self,
        drug_name: str,
        request_id: str,
        phase1_data: Dict[str, Any],
        scoring_results: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate Go/No-Go Verdict."""
        logger.info(f"[GO_NOGO_VERDICT] Generating for {drug_name}")

        context = self._prepare_phase1_context(phase1_data)
        scoring_context = self._format_scoring_results(scoring_results) if scoring_results else "Scoring data not available"

        prompt = f"""You are a pharmaceutical development strategist. Generate a Go/No-Go Verdict for {drug_name}'s alternative delivery route development.

## Available Data

{context}

## Scoring Summary

{scoring_context}

## Instructions

Generate a strategic Go/No-Go verdict that includes:

1. **Strategic Decision Matrix Section**:

### Go/No-Go Verdicts

| Route | Verdict | Justification | Development Priority |
|-------|---------|---------------|---------------------|
| Transdermal (TD) | Go/No-Go | 1-sentence justification based on scoring | High/Medium/Low |
| Transmucosal (TM) | Go/No-Go | 1-sentence justification based on scoring | High/Medium/Low |

2. **Recommended Route**: State which route is recommended and why (1-2 sentences)

3. **Decision Confidence**: State confidence level (High/Medium/Low) and key assumptions

## Decision Criteria

- Score >70%: GO with High priority
- Score 50-70%: CONDITIONAL GO with Medium priority
- Score <50%: NO-GO with Low priority

## Critical Requirements

- DO NOT mention "Phase 1", "Phase 2", or data sources
- Base decisions ONLY on provided data
- Be decisive and clear
- Use markdown formatting

Generate the Go/No-Go verdict:"""

        start_time = time.time()
        summary = await self.llm_service.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=1200
        )
        response_time_ms = int((time.time() - start_time) * 1000)

        await self._log_api_usage(
            request_id, "go_nogo_verdict", len(prompt), len(summary), response_time_ms
        )

        return {
            "summary": summary.strip(),
            "structured_data": {
                "category_type": "go_nogo_verdict",
                "has_decision_table": True
            },
            "confidence_score": 0.85,
            "metadata": {
                "generation_time_ms": response_time_ms,
                "analysis_type": "strategic_decision"
            }
        }

    async def _generate_risk_assessment(
        self,
        drug_name: str,
        request_id: str,
        phase1_data: Dict[str, Any],
        scoring_results: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate Risk Assessment."""
        logger.info(f"[RISK_ASSESSMENT] Generating for {drug_name}")

        context = self._prepare_phase1_context(phase1_data)

        prompt = f"""You are a pharmaceutical risk analyst. Generate a comprehensive Risk Assessment for {drug_name}'s development program.

## Available Data

{context}

## Instructions

Generate a risk assessment that includes:

1. **Risk Assessment Section Title**

2. **High-Risk Factors Table** (markdown):

| Risk Category | Description | Impact Level | Mitigation Strategy |
|---------------|-------------|--------------|---------------------|
| Technical Risks | 1-2 sentence description | High/Medium/Low | 1 sentence mitigation |
| Commercial Risks | 1-2 sentence description | High/Medium/Low | 1 sentence mitigation |
| Regulatory Risks | 1-2 sentence description | High/Medium/Low | 1 sentence mitigation |

3. **Mitigation Opportunities**:
   - List 3-5 key mitigation strategies (bulleted)

4. **Success Probability**:
   - Overall success probability (High/Medium/Low)
   - Key success factors (2-3 bullets)
   - Critical assumptions

## Critical Requirements

- DO NOT mention "Phase 1", "Phase 2", or data sources
- Base risks on pharmaceutical development norms if specific data is missing
- Be realistic and evidence-based
- Use markdown formatting

Generate the risk assessment:"""

        start_time = time.time()
        summary = await self.llm_service.generate(
            prompt=prompt,
            temperature=0.4,
            max_tokens=1800
        )
        response_time_ms = int((time.time() - start_time) * 1000)

        await self._log_api_usage(
            request_id, "risk_assessment", len(prompt), len(summary), response_time_ms
        )

        return {
            "summary": summary.strip(),
            "structured_data": {
                "category_type": "risk_assessment",
                "has_risk_table": True
            },
            "confidence_score": 0.80,
            "metadata": {
                "generation_time_ms": response_time_ms,
                "analysis_type": "risk_analysis"
            }
        }

    async def _generate_strategic_recommendations(
        self,
        drug_name: str,
        request_id: str,
        phase1_data: Dict[str, Any],
        scoring_results: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate Strategic Recommendations."""
        logger.info(f"[STRATEGIC_RECOMMENDATIONS] Generating for {drug_name}")

        context = self._prepare_phase1_context(phase1_data)

        prompt = f"""You are a pharmaceutical development strategist. Generate Strategic Recommendations for {drug_name}'s development program.

## Available Data

{context}

## Instructions

Generate strategic recommendations that include:

1. **Executive Recommendations Section**

2. **Primary Recommendation**:
   - **Recommended Route**: State the primary development route
   - **Decision Rationale**: 2-3 sentence justification

3. **Strategic Actions**:

**Immediate Actions Required (0-6 months):**
1. Action item 1
2. Action item 2
3. Action item 3

**Medium-term Objectives (6-18 months):**
1. Objective 1
2. Objective 2
3. Objective 3

**Long-term Goals (18+ months):**
1. Goal 1
2. Goal 2
3. Goal 3

4. **Investment Priorities**:
   - Priority area 1 (High/Medium/Low priority)
   - Priority area 2 (High/Medium/Low priority)
   - Priority area 3 (High/Medium/Low priority)

5. **Decision Confidence Level**:
   - Overall confidence (High/Medium/Low)
   - Key assumptions (2-3 bullets)
   - Data gaps (2-3 bullets if any)

## Critical Requirements

- DO NOT mention "Phase 1", "Phase 2", or data sources
- Be specific and actionable
- Prioritize recommendations by impact
- Use markdown formatting

Generate the strategic recommendations:"""

        start_time = time.time()
        summary = await self.llm_service.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=2000
        )
        response_time_ms = int((time.time() - start_time) * 1000)

        await self._log_api_usage(
            request_id, "strategic_recommendations", len(prompt), len(summary), response_time_ms
        )

        return {
            "summary": summary.strip(),
            "structured_data": {
                "category_type": "strategic_recommendations",
                "has_action_plan": True
            },
            "confidence_score": 0.80,
            "metadata": {
                "generation_time_ms": response_time_ms,
                "analysis_type": "strategic_planning"
            }
        }

    async def _generate_investment_analysis(
        self,
        drug_name: str,
        request_id: str,
        phase1_data: Dict[str, Any],
        scoring_results: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate Investment Analysis."""
        logger.info(f"[INVESTMENT_ANALYSIS] Generating for {drug_name}")

        context = self._prepare_phase1_context(phase1_data)

        prompt = f"""You are a pharmaceutical investment analyst. Generate an Investment Analysis for {drug_name}'s development program.

## Available Data

{context}

## Instructions

Generate an investment analysis that includes:

1. **Commercial Viability Assessment Section**

2. **Market Opportunity**:
   - Current market formulation (brief description)
   - Alternative delivery value proposition (2-3 sentences)
   - Competitive differentiation potential (2-3 sentences)

3. **Development Investment Requirements**:
   - **Estimated Investment Level**: High/Medium/Low (with brief justification)
   - **Key Investment Areas** (bulleted list of 3-5 items)
   - **Development Timeline**: Estimated years to market

4. **Time-to-Market Considerations**:
   - **Regulatory Pathway**: Expected pathway (505(b)(1), 505(b)(2), etc.)
   - **Development Timeline**: Estimated duration by phase
   - **Market Entry Strategy**: 1-2 sentences

5. **Return on Investment (ROI) Outlook**:
   - **Market Potential**: High/Medium/Low (with justification)
   - **Competitive Advantage**: Key differentiators (2-3 bullets)
   - **Risk-Adjusted ROI**: High/Medium/Low

## Critical Requirements

- DO NOT mention "Phase 1", "Phase 2", or data sources
- Base estimates on industry norms if specific data unavailable
- Be realistic about investment requirements
- Use markdown formatting

Generate the investment analysis:"""

        start_time = time.time()
        summary = await self.llm_service.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=2000
        )
        response_time_ms = int((time.time() - start_time) * 1000)

        await self._log_api_usage(
            request_id, "investment_analysis", len(prompt), len(summary), response_time_ms
        )

        return {
            "summary": summary.strip(),
            "structured_data": {
                "category_type": "investment_analysis",
                "has_roi_analysis": True
            },
            "confidence_score": 0.75,
            "metadata": {
                "generation_time_ms": response_time_ms,
                "analysis_type": "commercial_analysis"
            }
        }

    def _prepare_phase1_context(self, phase1_data: Dict[str, Any]) -> str:
        """
        Prepare Phase 1 data as context for LLM.

        Prioritizes key categories and formats data for analysis.
        """
        context_parts = []

        # Priority categories for strategic analysis
        priority_categories = [
            'Market Overview',
            'Competitive Landscape',
            'Regulatory & Patent Status',
            'Commercial Opportunities',
            'Physicochemical Profile',
            'Pharmacokinetics'
        ]

        # Add priority categories first
        for cat_name in priority_categories:
            if cat_name in phase1_data:
                category_data = phase1_data[cat_name]
                summary = category_data.get('summary', '')

                if summary:
                    # Truncate very long summaries
                    truncated_summary = summary[:2000] if len(summary) > 2000 else summary
                    context_parts.append(f"### {cat_name}\n\n{truncated_summary}\n")

        # Add other categories (with more aggressive truncation)
        for category_name, category_data in phase1_data.items():
            if category_name not in priority_categories:
                summary = category_data.get('summary', '')
                if summary:
                    truncated_summary = summary[:1000] if len(summary) > 1000 else summary
                    context_parts.append(f"### {category_name}\n\n{truncated_summary}\n")

        # Limit total context to avoid token limits
        full_context = "\n".join(context_parts)
        return full_context[:20000]  # Limit to 20K chars

    def _format_scoring_results(self, scoring_results: Optional[Dict[str, Any]]) -> str:
        """Format scoring results for prompt context."""
        if not scoring_results:
            return "Scoring results not available."

        extracted_params = scoring_results.get('extracted_parameters', {})
        scores = scoring_results.get('scores', {})
        weighted_scores = scoring_results.get('weighted_scores', {})
        total_score = scoring_results.get('total_score', 0.0)

        formatted = f"""
**Total Weighted Score:** {total_score:.2f}

**Parameters:**
- Dose: {extracted_params.get('Dose', 'N/A')} (Score: {scores.get('Dose', 'N/A')}, Weighted: {weighted_scores.get('Dose', 'N/A')})
- Molecular Weight: {extracted_params.get('Molecular Weight', 'N/A')} Da (Score: {scores.get('Molecular Weight', 'N/A')}, Weighted: {weighted_scores.get('Molecular Weight', 'N/A')})
- Melting Point: {extracted_params.get('Melting Point', 'N/A')}°C (Score: {scores.get('Melting Point', 'N/A')}, Weighted: {weighted_scores.get('Melting Point', 'N/A')})
- Log P: {extracted_params.get('Log P', 'N/A')} (Score: {scores.get('Log P', 'N/A')}, Weighted: {weighted_scores.get('Log P', 'N/A')})
"""
        return formatted.strip()

    async def _log_api_usage(
        self,
        request_id: str,
        category_type: str,
        prompt_length: int,
        response_length: int,
        response_time_ms: int
    ):
        """Log API usage for Phase 2 analysis."""
        try:
            await DataStorageService.store_api_usage_log(
                request_id=request_id,
                category_result_id=None,
                api_provider="llm_service",
                endpoint=f"phase2_{category_type}",
                response_status=200,
                response_time_ms=response_time_ms,
                token_count=prompt_length // 4 + response_length // 4,  # Rough estimate
                total_cost=0.0,
                category_name=f"Phase 2 - {category_type}",
                prompt_text=f"Generate {category_type}",
                response_data={"operation": category_type},
                request_payload={"category_type": category_type}
            )
        except Exception as e:
            logger.warning(f"Failed to log API usage: {str(e)}")
