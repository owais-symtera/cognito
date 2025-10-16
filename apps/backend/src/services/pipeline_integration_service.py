"""
Simplified Pipeline Integration Service
Integrates verification, merging, and LLM processing stages into the processing pipeline.

This is a simplified wrapper around the complex Epic 3/5 components to enable
quick integration and testing of the 4-stage pipeline.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import statistics
import time
from .pipeline_config_service import PipelineConfigService
from .pipeline_stage_logger import PipelineStageLogger
from .category_validation_engine import CategoryValidationEngine
from .llm_merger_service import LLMMergerService
from .merged_data_storage import MergedDataStorage
from .summary_config_service import SummaryConfigService
from .llm_summary_generator import LLMSummaryGenerator
import asyncpg
import logging

logger = logging.getLogger(__name__)


class PipelineIntegrationService:
    """Simplified integration of pipeline stages"""

    def __init__(self):
        self.config_service = PipelineConfigService()
        self.validation_engine = CategoryValidationEngine()
        self.llm_merger = LLMMergerService()
        self.merged_storage = MergedDataStorage()
        self.summary_config = SummaryConfigService()
        self.summary_generator = LLMSummaryGenerator(self.summary_config)

    async def process_with_pipeline(self,
                                    category_name: str,
                                    drug_name: str,
                                    api_responses: List[Dict[str, Any]],
                                    request_id: str,
                                    category_result_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process API responses through enabled pipeline stages

        Args:
            category_name: Name of the pharmaceutical category
            drug_name: Name of the drug being analyzed
            api_responses: List of API responses with provider metadata
            request_id: Request ID for tracking
            category_result_id: Category result ID for tracking

        Returns:
            Processed results with pipeline metadata
        """
        # Check if this is a Phase 2 category
        if await self.is_phase2_category(category_name):
            logger.info(f"Routing to Phase 2 processor for category: {category_name}")
            return await self.process_phase2_category(
                category_name=category_name,
                drug_name=drug_name,
                request_id=request_id,
                category_result_id=category_result_id
            )

        # Phase 1 pipeline processing
        pipeline_result = {
            "drug_name": drug_name,
            "category": category_name,
            "request_id": request_id,
            "stages_executed": [],
            "stages_skipped": [],
            "final_summary": "",
            "confidence_score": 0.0,
            "quality_score": 0.0,
            "metadata": {}
        }

        # Stage 1: Data Collection (already done, just record it)
        if self.config_service.is_stage_enabled("data_collection"):
            pipeline_result["stages_executed"].append("data_collection")
            pipeline_result["metadata"]["collection"] = {
                "total_responses": len(api_responses),
                "timestamp": datetime.now().isoformat()
            }

        # Stage 2: Verification
        verified_data = api_responses
        stage_start = time.time()
        if self.config_service.is_stage_enabled("verification"):
            verified_data = await self._verification_stage(
                api_responses,
                category_name,
                drug_name,
                category_result_id=category_result_id
            )
            pipeline_result["stages_executed"].append("verification")
            pipeline_result["metadata"]["verification"] = verified_data.get("metadata", {})

            # Log verification stage execution
            await PipelineStageLogger.log_stage_execution(
                request_id=request_id,
                category_result_id=category_result_id,
                stage_name="verification",
                stage_order=2,
                executed=True,
                skipped=False,
                input_data={"response_count": len(api_responses)},
                output_data=verified_data.get("metadata", {}),
                stage_metadata=verified_data.get("metadata", {}),
                execution_time_ms=int((time.time() - stage_start) * 1000)
            )
        else:
            pipeline_result["stages_skipped"].append("verification")

            # Log verification stage skipped
            await PipelineStageLogger.log_stage_execution(
                request_id=request_id,
                category_result_id=category_result_id,
                stage_name="verification",
                stage_order=2,
                executed=False,
                skipped=True,
                input_data={"response_count": len(api_responses)},
                execution_time_ms=0
            )

        # Stage 3: Merging
        merged_data = verified_data
        stage_start = time.time()
        if self.config_service.is_stage_enabled("merging"):
            merged_data = await self._merging_stage(
                verified_data,
                category_name,
                drug_name,
                request_id=request_id,
                category_result_id=category_result_id
            )
            pipeline_result["stages_executed"].append("merging")
            pipeline_result["metadata"]["merging"] = merged_data.get("metadata", {})

            # Log merging stage execution
            await PipelineStageLogger.log_stage_execution(
                request_id=request_id,
                category_result_id=category_result_id,
                stage_name="merging",
                stage_order=3,
                executed=True,
                skipped=False,
                input_data={
                    "verified_responses": len(verified_data.get("responses", [])) if isinstance(verified_data, dict) else 0
                },
                output_data={
                    "structured_data": merged_data.get("structured_data", {}),
                    **merged_data.get("metadata", {})
                },
                stage_metadata={
                    "structured_data": merged_data.get("structured_data", {}),
                    **merged_data.get("metadata", {})
                },
                execution_time_ms=int((time.time() - stage_start) * 1000)
            )
        else:
            pipeline_result["stages_skipped"].append("merging")

            # Log merging stage skipped
            await PipelineStageLogger.log_stage_execution(
                request_id=request_id,
                category_result_id=category_result_id,
                stage_name="merging",
                stage_order=3,
                executed=False,
                skipped=True,
                execution_time_ms=0
            )

        # Stage 4: LLM Summary
        stage_start = time.time()
        if self.config_service.is_stage_enabled("llm_summary"):
            summary_data = await self._llm_summary_stage(
                merged_data, category_name, drug_name, request_id
            )
            pipeline_result["stages_executed"].append("llm_summary")
            pipeline_result["final_summary"] = summary_data["summary"]
            pipeline_result["confidence_score"] = summary_data["confidence_score"]
            pipeline_result["metadata"]["llm_summary"] = summary_data.get("metadata", {})

            # Log LLM summary stage execution
            await PipelineStageLogger.log_stage_execution(
                request_id=request_id,
                category_result_id=category_result_id,
                stage_name="llm_summary",
                stage_order=4,
                executed=True,
                skipped=False,
                input_data={
                    "merged_responses": len(merged_data.get("responses", [])) if isinstance(merged_data, dict) else 0
                },
                output_data={
                    "summary": summary_data.get("summary", ""),  # Include actual summary text
                    **summary_data.get("metadata", {})
                },
                stage_metadata=summary_data.get("metadata", {}),
                execution_time_ms=int((time.time() - stage_start) * 1000)
            )
        else:
            pipeline_result["stages_skipped"].append("llm_summary")

            # Log LLM summary stage skipped
            await PipelineStageLogger.log_stage_execution(
                request_id=request_id,
                category_result_id=category_result_id,
                stage_name="llm_summary",
                stage_order=4,
                executed=False,
                skipped=True,
                execution_time_ms=0
            )
            # Fallback to merged data summary
            if isinstance(merged_data, dict) and "summary" in merged_data:
                pipeline_result["final_summary"] = merged_data["summary"]
            else:
                # Create basic summary from responses
                pipeline_result["final_summary"] = self._create_basic_summary(api_responses, category_name, drug_name)

        # Calculate overall quality score
        pipeline_result["quality_score"] = self._calculate_quality_score(pipeline_result)

        return pipeline_result

    async def _verification_stage(self,
                                 api_responses: List[Dict[str, Any]],
                                 category_name: str,
                                 drug_name: str,
                                 category_result_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Stage 2: Verification - Apply hierarchical source weighting + category-specific validation

        Hybrid model: Basic synchronous verification + optional deep category validation
        """
        # Source weights (from Story 3.1)
        source_weights = {
            "chatgpt": 10,  # Paid API
            "openai": 10,   # Paid API
            "perplexity": 10,  # Paid API
            "grok": 10,  # Paid API
            "gemini": 10,  # Paid API
            "tavily": 10,  # Paid API
            "government": 8,
            "peer_reviewed": 6,
            "industry": 4,
            "company": 2,
            "news": 1,
            "unknown": 0
        }

        verified_responses = []
        total_weight = 0
        weighted_content_length = 0

        for response in api_responses:
            provider = response.get("provider", "unknown").lower()
            content = response.get("response", "")

            # Assign weight
            weight = source_weights.get(provider, source_weights["unknown"])

            # Calculate credibility score based on content length and structure
            credibility_score = min(1.0, len(str(content)) / 1000)  # Simple heuristic

            verified_response = {
                "provider": response.get("provider"),
                "model": response.get("model"),
                "response": content,
                "temperature": response.get("temperature"),
                "weight": weight,
                "credibility_score": credibility_score,
                "verification_status": "verified" if weight > 0 else "unverified",
                "authority_score": weight * 10,  # Normalize to 0-100
                "verification_timestamp": datetime.now().isoformat()
            }

            verified_responses.append(verified_response)
            total_weight += weight
            weighted_content_length += len(str(content)) * weight

        # Calculate average authority score
        avg_authority = (total_weight / len(verified_responses) * 10) if verified_responses else 0

        result = {
            "responses": verified_responses,
            "summary": f"Verified {len(verified_responses)} sources for {category_name} - {drug_name}",
            "metadata": {
                "total_sources": len(verified_responses),
                "avg_authority_score": avg_authority,
                "total_weight": total_weight,
                "verified_count": len([r for r in verified_responses if r["verification_status"] == "verified"]),
                "unverified_count": len([r for r in verified_responses if r["verification_status"] == "unverified"])
            }
        }

        # CATEGORY-SPECIFIC VALIDATION (Hybrid model)
        if category_result_id:
            print(f"[VALIDATION DEBUG] category_result_id provided: {category_result_id}")
            try:
                # Map category name to ID
                category_id = self._get_category_id(category_name)
                print(f"[VALIDATION DEBUG] category_name: {category_name}, category_id: {category_id}")

                if category_id:
                    # PER-SOURCE VALIDATION - Validate each source individually
                    print(f"[PER-SOURCE VALIDATION] Validating {len(verified_responses)} sources individually...")
                    source_validations = []

                    for source_idx, verified_response in enumerate(verified_responses):
                        try:
                            source_validation = await self.validation_engine.validate_source_response(
                                category_result_id=category_result_id,
                                category_id=category_id,
                                source_response=verified_response,
                                source_index=source_idx
                            )
                            source_validations.append(source_validation)
                            print(f"[PER-SOURCE VALIDATION] Source {source_idx + 1} ({verified_response.get('provider')}): " +
                                  f"{source_validation['total_rows']} rows, " +
                                  f"{source_validation['validated_rows']} validated, " +
                                  f"pass_rate: {source_validation['pass_rate']}")
                        except Exception as e:
                            print(f"[PER-SOURCE VALIDATION ERROR] Failed to validate source {source_idx + 1}: {e}")

                    # Add per-source validation summary to metadata
                    result["metadata"]["source_validations"] = {
                        "total_sources": len(source_validations),
                        "sources": [
                            {
                                "provider": sv["provider"],
                                "model": sv["model"],
                                "total_tables": sv["total_tables"],
                                "total_rows": sv["total_rows"],
                                "validated_rows": sv["validated_rows"],
                                "pass_rate": sv["pass_rate"],
                                "validation_passed": sv["validation_passed"]
                            }
                            for sv in source_validations
                        ]
                    }

                    # Extract category data from responses (for aggregated validation)
                    category_data = self._extract_category_data(verified_responses)
                    print(f"[VALIDATION DEBUG] Extracted category_data with {len(category_data.get('content', ''))} chars")

                    # Extract source references
                    source_references = self._extract_source_references(verified_responses)
                    print(f"[VALIDATION DEBUG] Extracted {len(source_references)} source references")

                    # Run category validation (aggregated)
                    print(f"[VALIDATION DEBUG] Running aggregated category validation...")
                    validation_result = await self.validation_engine.validate_category_result(
                        category_result_id=category_result_id,
                        category_id=category_id,
                        category_data=category_data,
                        source_references=source_references
                    )
                    print(f"[VALIDATION DEBUG] Validation complete - passed: {validation_result['validation_passed']}, score: {validation_result['validation_score']}")

                    # Add validation metadata
                    result["metadata"]["category_validation"] = {
                        "validation_passed": validation_result["validation_passed"],
                        "validation_score": validation_result["validation_score"],
                        "confidence_penalty": validation_result["confidence_penalty"],
                        "failed_steps": validation_result["failed_steps"],
                        "recommendations": validation_result.get("recommendations", [])
                    }

                    # Apply confidence penalty to metadata
                    result["metadata"]["confidence_penalty_applied"] = validation_result["confidence_penalty"]
                    print(f"[VALIDATION DEBUG] Category validation metadata added to result")
                else:
                    print(f"[VALIDATION DEBUG] No category_id found for category_name: {category_name}")

            except Exception as e:
                # Don't fail verification if category validation fails
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                print(f"[VALIDATION DEBUG ERROR] {error_msg}")
                result["metadata"]["category_validation_error"] = str(e)
        else:
            print(f"[VALIDATION DEBUG] No category_result_id provided, skipping category validation")

        return result

    def _get_category_id(self, category_name: str) -> Optional[int]:
        """Map category name to database ID"""
        category_map = {
            "Market Overview": 1,
            "Competitive Landscape": 2,
            "Regulatory & Patent Status": 3,
            "Commercial Opportunities": 4,
            "Current Formulations": 5,
            "Investigational Formulations": 6,
            "Physicochemical Profile": 7,
            "Pharmacokinetics": 8,
            "Dosage Forms": 9,
            "Clinical Trials & Safety": 10,
        }
        return category_map.get(category_name)

    def _extract_category_data(self, verified_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract structured category data from responses"""
        # Combine all response content
        all_content = "\n\n".join([
            str(r.get("response", ""))
            for r in verified_responses
        ])

        return {
            "content": all_content,
            "response_count": len(verified_responses),
            "tables": []  # TODO: Extract tables from responses
        }

    def _extract_source_references(self, verified_responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract source references from responses"""
        references = []
        for response in verified_responses:
            references.append({
                "provider": response.get("provider"),
                "model": response.get("model"),
                "weight": response.get("weight", 0),
                "authority_score": response.get("authority_score", 0),
                "content_length": len(str(response.get("response", ""))),
                "verification_status": response.get("verification_status", "unknown")
            })
        return references

    async def _merging_stage(self,
                            verified_data: Dict[str, Any],
                            category_name: str,
                            drug_name: str,
                            request_id: Optional[str] = None,
                            category_result_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Stage 3: Merging - Intelligent LLM-assisted data consolidation with conflict resolution

        Uses GPT-5-nano to intelligently merge data from multiple providers
        Stores merged results in database with full audit trail
        """
        print(f"[DEBUG MERGE STAGE] Called with request_id={request_id}, category_result_id={category_result_id}")
        if not isinstance(verified_data, dict) or "responses" not in verified_data:
            # Fallback if verification was skipped
            return verified_data

        responses = verified_data["responses"]

        if not responses:
            # No API responses, but we still need to extract structured_data
            # from the LLM summary if it exists
            summary = verified_data.get("summary", "")

            if summary and category_result_id and request_id:
                try:
                    # Extract structured data from summary
                    structured_data = await self.llm_merger.extract_structured_data(
                        merged_content=summary,
                        category_name=category_name
                    )

                    # Store to merged_data_results
                    category_id = self._get_category_id(category_name)
                    if category_id:
                        storage_data = {
                            "merged_content": summary,
                            "structured_data": structured_data,
                            "confidence_score": verified_data.get("confidence_score", 0.7),
                            "source_references": [],
                            "merge_records": [{
                                "timestamp": datetime.now().isoformat(),
                                "sources_count": 0,
                                "method": "summary_extraction"
                            }],
                            "metadata": {
                                "note": "Extracted from LLM summary (no API responses)"
                            }
                        }

                        await self.merged_storage.store_merged_result(
                            category_result_id=category_result_id,
                            request_id=request_id,
                            category_id=category_id,
                            category_name=category_name,
                            merged_data=storage_data,
                            merge_method="summary_extraction"
                        )

                        # Add to verified_data for pipeline continuity
                        verified_data["structured_data"] = structured_data

                except Exception as e:
                    logger.error(f"Failed to extract structured_data from summary: {str(e)}")

            return verified_data

        try:
            # Use LLM to merge conflicting responses
            merged_result = await self.llm_merger.merge_conflicting_responses(
                category_name=category_name,
                drug_name=drug_name,
                responses=responses
            )

            # Extract structured data from merged content
            structured_data = await self.llm_merger.extract_structured_data(
                merged_content=merged_result.get("merged_content", ""),
                category_name=category_name
            )

            # Add structured data to result
            merged_result["structured_data"] = structured_data

            # Store merged result to database (if we have IDs)
            print(f"[MERGE STORAGE] category_result_id={category_result_id}, request_id={request_id}")
            if category_result_id and request_id:
                category_id = self._get_category_id(category_name)
                print(f"[MERGE STORAGE] category_id={category_id} for category={category_name}")
                if category_id:
                    # Prepare data for storage
                    storage_data = {
                        **merged_result,
                        "source_references": self._extract_source_references(responses),
                        "merge_records": [{
                            "timestamp": datetime.now().isoformat(),
                            "sources_count": len(responses),
                            "method": "llm_assisted"
                        }]
                    }

                    print(f"[MERGE STORAGE] Calling store_merged_result...")
                    merged_id = await self.merged_storage.store_merged_result(
                        category_result_id=category_result_id,
                        request_id=request_id,
                        category_id=category_id,
                        category_name=category_name,
                        merged_data=storage_data,
                        merge_method="llm_assisted"
                    )
                    print(f"[MERGE STORAGE] Stored successfully! merged_id={merged_id}")

                    merged_result["metadata"]["merged_data_id"] = merged_id
                else:
                    print(f"[MERGE STORAGE] Skipped: category_id is None")
            else:
                print(f"[MERGE STORAGE] Skipped: Missing IDs")

            # Format for pipeline return
            return {
                "responses": [{
                    "provider": "merged",
                    "content": merged_result.get("merged_content", ""),
                    "weight": 10,  # Merged data has highest weight
                    "confidence": merged_result.get("confidence_score", 0.8)
                }],
                "summary": merged_result.get("merged_content", ""),
                "confidence_score": merged_result.get("confidence_score", 0.8),
                "structured_data": structured_data,
                "metadata": {
                    "providers_merged": len(responses),
                    "overall_confidence": merged_result.get("confidence_score", 0.8),
                    "data_quality_score": merged_result.get("data_quality_score", 0.7),
                    "merge_strategy": "llm_assisted",
                    "conflicts_resolved": len(merged_result.get("conflicts_resolved", [])),
                    "key_findings": merged_result.get("key_findings", []),
                    **merged_result.get("metadata", {})
                }
            }

        except Exception as e:
            # Fallback to simple weighted merging if LLM fails
            print(f"[MERGE ERROR] LLM merge failed: {e}, falling back to weighted merge")
            import traceback
            traceback.print_exc()

            return await self._fallback_weighted_merge(
                responses=responses,
                category_name=category_name,
                drug_name=drug_name,
                request_id=request_id,
                category_result_id=category_result_id
            )

    async def _llm_summary_stage(self,
                                merged_data: Dict[str, Any],
                                category_name: str,
                                drug_name: str,
                                request_id: str) -> Dict[str, Any]:
        """
        Stage 4: LLM Summary - Generate intelligent summary using configured LLM provider
        """
        # Extract merged content
        merged_content = merged_data.get("merged_content", "")

        # If no merged content, use fallback
        if not merged_content:
            merged_content = str(merged_data)

        # Generate summary using new LLM summary generator
        result = await self.summary_generator.generate_summary(
            request_id=request_id,
            category_name=category_name,
            drug_name=drug_name,
            merged_content=merged_content
        )

        # Return in expected format
        return {
            "summary": result.get("summary", ""),
            "confidence_score": merged_data.get("confidence_score", 0.7),
            "metadata": {
                "style_name": result.get("style_name", "default"),
                "provider": result.get("provider", "unknown"),
                "model": result.get("model", "unknown"),
                "generation_time_ms": result.get("generation_time_ms", 0),
                "tokens_used": result.get("tokens_used", 0),
                "cost_estimate": result.get("cost_estimate", 0.0),
                "timestamp": datetime.now().isoformat()
            }
        }

    def _extract_key_findings(self, responses: List[Dict], summary: str) -> str:
        """Extract key findings from merged content"""
        if not responses:
            return "No findings available"

        findings = []
        for i, response in enumerate(responses[:3], 1):  # Top 3 sources
            content = response.get("content", "")[:200]
            findings.append(f"{i}. {content}...")

        return "\n".join(findings)

    def _generate_authority_breakdown(self, responses: List[Dict]) -> str:
        """Generate source authority breakdown"""
        if not responses:
            return "No sources"

        breakdown = []
        for response in responses:
            provider = response.get("provider", "Unknown")
            weight = response.get("weight", 0)
            breakdown.append(f"- {provider}: Authority Score {weight}/10")

        return "\n".join(breakdown)

    def _generate_recommendations(self, responses: List[Dict], category: str, drug: str) -> str:
        """Generate recommendations based on analysis"""
        if not responses:
            return "Insufficient data for recommendations"

        high_authority = [r for r in responses if r.get("weight", 0) >= 8]

        recommendations = [
            f"1. Review high-authority sources ({len(high_authority)} available) for detailed {category} information",
            f"2. Cross-reference findings with regulatory databases for {drug}",
            "3. Consider additional verification for critical decisions"
        ]

        return "\n".join(recommendations)

    def _create_basic_summary(self, responses: List[Dict], category: str, drug: str) -> str:
        """Create basic summary when LLM stage is disabled"""
        return f"""
# {category} for {drug}

Collected {len(responses)} responses from multiple API providers.

## Responses Summary
{self._summarize_responses(responses)}

Note: Advanced LLM summarization disabled. Enable 'llm_summary' stage for intelligent analysis.
        """.strip()

    def _summarize_responses(self, responses: List[Dict]) -> str:
        """Summarize raw responses"""
        if not responses:
            return "No responses collected"

        summary_lines = []
        for i, resp in enumerate(responses[:5], 1):  # First 5
            provider = resp.get("provider", "Unknown")
            content = str(resp.get("response", ""))[:150]
            summary_lines.append(f"{i}. **{provider}**: {content}...")

        return "\n".join(summary_lines)

    def _calculate_quality_score(self, pipeline_result: Dict) -> float:
        """Calculate overall quality score based on pipeline execution"""
        scores = []

        # Data collection quality (always present)
        collection_meta = pipeline_result.get("metadata", {}).get("collection", {})
        if collection_meta:
            response_count = collection_meta.get("total_responses", 0)
            scores.append(min(1.0, response_count / 10))  # Normalize to max 10 responses

        # Verification quality
        verification_meta = pipeline_result.get("metadata", {}).get("verification", {})
        if verification_meta:
            avg_authority = verification_meta.get("avg_authority_score", 0)
            scores.append(min(1.0, avg_authority / 100))

        # Merging quality
        merging_meta = pipeline_result.get("metadata", {}).get("merging", {})
        if merging_meta:
            confidence = merging_meta.get("overall_confidence", 0)
            scores.append(confidence)

        # LLM summary quality
        if "llm_summary" in pipeline_result["stages_executed"]:
            scores.append(pipeline_result.get("confidence_score", 0.7))

        return statistics.mean(scores) if scores else 0.5

    def get_stage_status(self) -> Dict[str, Any]:
        """Get current status of all pipeline stages"""
        return self.config_service.get_pipeline_summary()

    async def _fallback_weighted_merge(self,
                                       responses: List[Dict[str, Any]],
                                       category_name: str,
                                       drug_name: str,
                                       request_id: Optional[str] = None,
                                       category_result_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fallback merge strategy when LLM is unavailable
        Uses simple weighted authority scoring and stores to database
        """
        merged_content = []
        total_confidence = 0

        for response in responses:
            provider = response.get("provider", "unknown")
            weight = response.get("weight", 0)
            content = response.get("response", "")

            if content and weight > 0:
                merged_content.append({
                    "provider": provider,
                    "content": content,
                    "weight": weight,
                    "confidence": response.get("credibility_score", 0.5)
                })
                total_confidence += response.get("credibility_score", 0.5) * weight

        # Sort by weight
        merged_content.sort(key=lambda x: x["weight"], reverse=True)

        # Calculate overall confidence
        total_weight = sum(item["weight"] for item in merged_content)
        overall_confidence = (total_confidence / total_weight) if total_weight > 0 else 0

        # Create merged summary
        merged_summary = f"# {category_name} for {drug_name}\n\n"
        for item in merged_content:
            merged_summary += f"## {item['provider']} (Authority: {item['weight']}/10)\n"
            merged_summary += f"{item['content'][:500]}...\n\n"

        # Initialize merged_data_id
        merged_data_id = None

        # Store merged result to database (if we have IDs)
        if category_result_id and request_id:
            category_id = self._get_category_id(category_name)
            if category_id:
                # Prepare data for storage
                storage_data = {
                    "merged_content": merged_summary,
                    "confidence_score": overall_confidence,
                    "structured_data": {},  # Empty for fallback, no LLM extraction
                    "source_references": self._extract_source_references(responses),
                    "merge_records": [{
                        "timestamp": datetime.now().isoformat(),
                        "sources_count": len(responses),
                        "method": "fallback_weighted"
                    }],
                    "metadata": {
                        "providers_merged": len(merged_content),
                        "total_weight": total_weight,
                        "overall_confidence": overall_confidence,
                        "data_quality_score": 0.6
                    }
                }

                merged_data_id = await self.merged_storage.store_merged_result(
                    category_result_id=category_result_id,
                    request_id=request_id,
                    category_id=category_id,
                    category_name=category_name,
                    merged_data=storage_data,
                    merge_method="fallback_weighted"
                )

        return {
            "responses": merged_content,
            "summary": merged_summary,
            "confidence_score": overall_confidence,
            "metadata": {
                "providers_merged": len(merged_content),
                "total_weight": total_weight,
                "overall_confidence": overall_confidence,
                "merge_strategy": "fallback_weighted",
                "conflict_resolution": "authority_priority",
                "merged_data_id": merged_data_id
            }
        }

    async def is_phase2_category(self, category_name: str) -> bool:
        """Check if a category is a Phase 2 decision intelligence category"""
        try:
            from ..utils.db_connection import get_db_connection
            conn = await get_db_connection()

            try:
                result = await conn.fetchrow(
                    """
                    SELECT phase FROM pharmaceutical_categories
                    WHERE name = $1 AND is_active = true
                    """,
                    category_name
                )

                if result and result['phase'] == 2:
                    return True
                return False
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error checking category phase: {e}")
            return False

    async def process_phase2_category(self,
                                     category_name: str,
                                     drug_name: str,
                                     request_id: str,
                                     category_result_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process Phase 2 decision intelligence category

        Phase 2 categories use LLM decision engines instead of API collection.
        They process the results from all Phase 1 categories.
        """
        logger.info(f"Processing Phase 2 category: {category_name} for {drug_name}")

        stage_start = time.time()

        try:
            # Get all Phase 1 results for this request
            phase1_data = await self._get_phase1_results(request_id)

            if not phase1_data:
                logger.warning(f"No Phase 1 data found for request {request_id}")
                return {
                    "drug_name": drug_name,
                    "category": category_name,
                    "request_id": request_id,
                    "final_summary": "Insufficient Phase 1 data to process Phase 2 category",
                    "confidence_score": 0.0,
                    "quality_score": 0.0,
                    "error": "No Phase 1 data available",
                    "metadata": {}
                }

            # Process Phase 2 category using appropriate service
            if category_name == "Parameter-Based Scoring Matrix":
                # Use Phase2ScoringService for parameter-based scoring
                from .phase2_scoring_service import Phase2ScoringService

                scoring_service = Phase2ScoringService()

                # Determine delivery method (default to Transdermal for now)
                # TODO: Extract from drug data or user input
                delivery_method = "Transdermal"

                scoring_result = await scoring_service.process_parameter_scoring(
                    request_id=request_id,
                    drug_name=drug_name,
                    delivery_method=delivery_method,
                    phase1_data=phase1_data
                )

                result = {
                    "data": {
                        "summary": scoring_result['markdown_table'],
                        "extracted_parameters": scoring_result['extracted_parameters'],
                        "scores": scoring_result['scores'],
                        "rationales": scoring_result['rationales'],
                        "json_table": scoring_result['json_table'],
                        "weighted_scores": scoring_result['weighted_scores'],
                        "total_score": scoring_result['total_score'],
                        "delivery_method": delivery_method,
                        "phase1_categories_used": list(phase1_data.keys()),
                        "analysis_type": category_name
                    },
                    "confidence_score": 0.85,
                    "llm_provider": "openai",
                    "llm_model": "gpt-4",
                    "processing_time": int((time.time() - stage_start) * 1000)
                }

                # Store Phase 2 results to database
                logger.info(f"Storing Phase 2 results to database for request {request_id}")
                from ..utils.db_connection import get_db_connection
                conn = await get_db_connection()

                try:
                    unit_map = {
                        'Dose': 'mg/kg/day',
                        'Molecular Weight': 'Da',
                        'Melting Point': '°C',
                        'Log P': ''
                    }

                    for param_name in scoring_result['extracted_parameters'].keys():
                        value = scoring_result['extracted_parameters'][param_name]
                        score = scoring_result['scores'][param_name]
                        weighted_score = scoring_result['weighted_scores'][param_name]
                        rationale = scoring_result['rationales'][param_name]

                        await conn.execute("""
                            INSERT INTO phase2_results (
                                request_id, parameter_name, extracted_value,
                                score, weighted_score, unit, extraction_method, rationale
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """, request_id, param_name, value, score, weighted_score,
                             unit_map.get(param_name, ''), 'phase1_summary', rationale)

                    logger.info(f"Stored Phase 2 results to database for request {request_id}")

                    # Generate final output after Phase 2 completes
                    logger.info(f"Phase 2 scoring complete, generating final output...")

                    try:
                        from .final_output_generator import FinalOutputGenerator
                        output_generator = FinalOutputGenerator()
                        final_output = await output_generator.generate_final_output(request_id)

                        logger.info(f"[SUCCESS] Final output generated for {request_id}")
                        logger.info(f"   - Decision: {final_output['structured_data']['executive_summary_and_decision']['decision']}")
                        logger.info(f"   - TD Score: {final_output['structured_data']['suitability_matrix']['final_weighted_scores']['transdermal_td']}")
                        logger.info(f"   - TM Score: {final_output['structured_data']['suitability_matrix']['final_weighted_scores']['transmucosal_tm']}")

                    except Exception as e:
                        logger.error(f"Failed to generate final output: {str(e)}")
                        import traceback
                        logger.error(traceback.format_exc())
                        # Don't fail the Phase 2 process if final output fails

                finally:
                    await conn.close()

            else:
                # Use Phase2AnalysisService for all other Phase 2 categories
                from .phase2_analysis_service import Phase2AnalysisService

                analysis_service = Phase2AnalysisService()

                # Get scoring results from Parameter-Based Scoring Matrix if available
                # (needed for Weighted Scoring Assessment and other categories)
                scoring_results = None
                try:
                    from ..utils.db_connection import get_db_connection
                    conn = await get_db_connection()

                    try:
                        # Check if Parameter-Based Scoring Matrix has been processed
                        scoring_category = await conn.fetchrow(
                            """
                            SELECT summary, confidence_score
                            FROM category_results cr
                            JOIN pharmaceutical_categories pc ON cr.category_name = pc.name
                            WHERE cr.request_id = $1::uuid
                            AND cr.category_name = 'Parameter-Based Scoring Matrix'
                            AND cr.status = 'completed'
                            """,
                            request_id
                        )

                        if scoring_category:
                            # Fetch scoring results from phase2_results table
                            phase2_rows = await conn.fetch(
                                """
                                SELECT parameter_name, extracted_value, score, weighted_score, rationale
                                FROM phase2_results
                                WHERE request_id = $1::uuid
                                ORDER BY parameter_name
                                """,
                                request_id
                            )

                            if phase2_rows:
                                # Build scoring_results structure
                                extracted_parameters = {}
                                scores = {}
                                weighted_scores = {}
                                rationales = {}
                                total_score = 0.0

                                for row in phase2_rows:
                                    param_name = row['parameter_name']
                                    extracted_parameters[param_name] = float(row['extracted_value']) if row['extracted_value'] else None
                                    scores[param_name] = int(row['score']) if row['score'] else None
                                    weighted_scores[param_name] = float(row['weighted_score']) if row['weighted_score'] else 0.0
                                    rationales[param_name] = row['rationale'] or ""
                                    total_score += float(row['weighted_score']) if row['weighted_score'] else 0.0

                                scoring_results = {
                                    'extracted_parameters': extracted_parameters,
                                    'scores': scores,
                                    'weighted_scores': weighted_scores,
                                    'rationales': rationales,
                                    'total_score': total_score,
                                    'delivery_method': 'Transdermal'  # TODO: Get from request metadata
                                }

                                logger.info(f"[PHASE2] Retrieved scoring results for {category_name}: total_score={total_score}")
                    finally:
                        await conn.close()

                except Exception as e:
                    logger.warning(f"[PHASE2] Could not fetch scoring results: {str(e)}")

                analysis_result = await analysis_service.process_analysis_category(
                    category_name=category_name,
                    drug_name=drug_name,
                    request_id=request_id,
                    phase1_data=phase1_data,
                    scoring_results=scoring_results
                )

                result = {
                    "data": {
                        "summary": analysis_result['summary'],
                        "structured_data": analysis_result.get('structured_data', {}),
                        "phase1_categories_used": list(phase1_data.keys()),
                        "analysis_type": category_name
                    },
                    "confidence_score": analysis_result.get('confidence_score', 0.80),
                    "llm_provider": "llm_service",
                    "llm_model": "configured_model",
                    "processing_time": analysis_result.get('metadata', {}).get('generation_time_ms', 0)
                }

            # Store Phase 2 result in category_results table
            if not category_result_id:
                # Create a new category_results entry
                from ..utils.db_connection import get_db_connection
                conn = await get_db_connection()

                try:
                    # Get category_id
                    category_info = await conn.fetchrow(
                        "SELECT id FROM pharmaceutical_categories WHERE name = $1",
                        category_name
                    )
                    category_id = category_info['id'] if category_info else None

                    # Insert category_results record
                    import uuid
                    category_result_id = str(uuid.uuid4())

                    await conn.execute(
                        """
                        INSERT INTO category_results
                        (id, request_id, category_id, category_name, summary, confidence_score,
                         data_quality_score, status, processing_time_ms, retry_count,
                         api_calls_made, token_count, cost_estimate, started_at, completed_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                        """,
                        category_result_id,
                        request_id,
                        category_id,
                        category_name,
                        result.get('data', {}).get('summary', 'Phase 2 analysis completed'),
                        result.get('confidence_score', 0.0),
                        0.8,  # quality_score
                        'completed',
                        int((time.time() - stage_start) * 1000),
                        0,  # retry_count
                        0,  # api_calls_made
                        0,  # token_count
                        0.0,  # cost_estimate
                        datetime.utcnow(),
                        datetime.utcnow()
                    )
                finally:
                    await conn.close()

            # Log Phase 2 execution
            await PipelineStageLogger.log_stage_execution(
                request_id=request_id,
                category_result_id=category_result_id,
                stage_name=f"phase2_{category_name}",
                stage_order=10 + self._get_phase2_order(category_name),  # Orders 11-17
                executed=True,
                skipped=False,
                input_data={
                    "phase1_categories": len(phase1_data),
                    "drug_name": drug_name
                },
                output_data=result.get('data', {}),
                stage_metadata={
                    "llm_provider": result.get('llm_provider'),
                    "llm_model": result.get('llm_model'),
                    "confidence_score": result.get('confidence_score', 0.0)
                },
                execution_time_ms=int((time.time() - stage_start) * 1000)
            )

            return {
                "drug_name": drug_name,
                "category": category_name,
                "request_id": request_id,
                "stages_executed": [f"phase2_{category_name}"],
                "stages_skipped": [],
                "final_summary": result.get('data', {}).get('summary', 'Phase 2 analysis completed'),
                "confidence_score": result.get('confidence_score', 0.0),
                "quality_score": 0.8,  # Default for Phase 2
                "phase2_result": result,
                "metadata": {
                    "phase": 2,
                    "llm_provider": result.get('llm_provider'),
                    "llm_model": result.get('llm_model'),
                    "processing_time": result.get('processing_time')
                }
            }

        except Exception as e:
            logger.error(f"Error processing Phase 2 category {category_name}: {e}")
            import traceback
            traceback.print_exc()

            # Log failed execution
            await PipelineStageLogger.log_stage_execution(
                request_id=request_id,
                category_result_id=category_result_id,
                stage_name=f"phase2_{category_name}",
                stage_order=10 + self._get_phase2_order(category_name),
                executed=False,
                skipped=False,
                input_data={"drug_name": drug_name},
                output_data={"error": str(e)},
                stage_metadata={"error": str(e)},
                execution_time_ms=int((time.time() - stage_start) * 1000)
            )

            return {
                "drug_name": drug_name,
                "category": category_name,
                "request_id": request_id,
                "final_summary": f"Error processing Phase 2 category: {str(e)}",
                "confidence_score": 0.0,
                "quality_score": 0.0,
                "error": str(e),
                "metadata": {"phase": 2, "error": str(e)}
            }

    async def _get_phase1_results(self, request_id: str) -> Dict[str, Any]:
        """Get all Phase 1 category results for a request."""
        try:
            from ..utils.db_connection import get_db_connection
            conn = await get_db_connection()

            try:
                # Get all Phase 1 category results
                results = await conn.fetch(
                    """
                    SELECT
                        cr.category_name,
                        cr.summary,
                        cr.confidence_score,
                        md.structured_data,
                        md.merged_content
                    FROM category_results cr
                    LEFT JOIN merged_data_results md ON cr.id = md.category_result_id
                    JOIN pharmaceutical_categories pc ON cr.category_name = pc.name
                    WHERE cr.request_id = $1::uuid
                    AND pc.phase = 1
                    AND cr.status = 'completed'
                    """,
                    request_id
                )

                phase1_data = {}
                for row in results:
                    category_data = {
                        "summary": row['summary'],
                        "confidence_score": float(row['confidence_score']) if row['confidence_score'] else 0.0
                    }

                    # Parse structured_data if available
                    if row['structured_data']:
                        if isinstance(row['structured_data'], str):
                            import json
                            category_data['structured_data'] = json.loads(row['structured_data'])
                        else:
                            category_data['structured_data'] = row['structured_data']

                    if row['merged_content']:
                        category_data['merged_content'] = row['merged_content']

                    phase1_data[row['category_name']] = category_data

                logger.info(f"Retrieved {len(phase1_data)} Phase 1 categories for request {request_id}")
                return phase1_data

            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error retrieving Phase 1 results: {e}")
            return {}

    def _get_phase2_order(self, category_name: str) -> int:
        """Get the display order offset for Phase 2 categories"""
        # Phase 2 categories are orders 11-17 (matching database exactly)
        phase2_categories = {
            "Parameter-Based Scoring Matrix": 1,
            "Weighted Scoring Assessment": 2,
            "Risk Assessment Analysis": 3,
            "Go/No-Go Recommendation": 4,
            "Strategic Opportunities Analysis": 5,
            "Competitive Positioning Strategy": 6,
            "Executive Summary & Recommendations": 7
        }
        return phase2_categories.get(category_name, 0)

