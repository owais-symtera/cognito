"""
Merged Data Storage Service
Stores intelligently merged pharmaceutical data with full audit trail
"""

import uuid
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import text
import structlog

from ..database.connection import get_db_session

logger = structlog.get_logger(__name__)


class MergedDataStorage:
    """Service for storing merged data results to database"""

    @staticmethod
    def _sanitize_for_postgres(data: Any) -> Any:
        """
        Remove null bytes (\x00, \u0000) that PostgreSQL cannot store in text fields.

        Args:
            data: Any data structure (str, dict, list, etc.)

        Returns:
            Sanitized data with null bytes removed
        """
        if isinstance(data, str):
            # Remove null bytes from strings
            return data.replace('\x00', '').replace('\u0000', '')
        elif isinstance(data, dict):
            return {key: MergedDataStorage._sanitize_for_postgres(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [MergedDataStorage._sanitize_for_postgres(item) for item in data]
        else:
            return data

    @staticmethod
    async def store_merged_result(
        category_result_id: str,
        request_id: str,
        category_id: int,
        category_name: str,
        merged_data: Dict[str, Any],
        merge_method: str = "llm_assisted"
    ) -> Optional[str]:
        """
        Store merged data result to database

        Args:
            category_result_id: Category result ID
            request_id: Drug request ID
            category_id: Category ID
            category_name: Category name
            merged_data: Merged data from merger service
            merge_method: Method used (llm_assisted, data_merger, weighted, fallback)

        Returns:
            Merged data result ID if successful
        """
        result_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Sanitize merged_data to remove null bytes before processing
        merged_data = MergedDataStorage._sanitize_for_postgres(merged_data)

        # Extract data from merged_data
        merged_content = merged_data.get("merged_content", "")
        structured_data = merged_data.get("structured_data", {})
        merge_confidence = merged_data.get("confidence_score", 0.0)
        data_quality = merged_data.get("data_quality_score", 0.0)
        conflicts_resolved = merged_data.get("conflicts_resolved", [])
        key_findings = merged_data.get("key_findings", [])
        merge_records = merged_data.get("merge_records", [])
        source_references = merged_data.get("source_references", [])

        # LLM metadata
        metadata = merged_data.get("metadata", {})
        llm_model = metadata.get("model", None)
        llm_tokens = metadata.get("tokens_used", 0)
        llm_cost = metadata.get("cost_estimate", 0.0)
        sources_merged = metadata.get("sources_merged", 0)
        merge_strategy = metadata.get("merge_strategy_used", None)

        try:
            async for session in get_db_session():
                await session.execute(text("""
                    INSERT INTO merged_data_results (
                        id, category_result_id, request_id,
                        category_id, category_name,
                        merged_content, structured_data,
                        merge_confidence_score, data_quality_score,
                        overall_confidence,
                        merge_method, sources_merged,
                        conflicts_resolved, key_findings,
                        merge_records, source_references,
                        merge_strategy_used,
                        llm_model, llm_tokens_used, llm_cost_estimate,
                        merged_at, created_at
                    )
                    VALUES (
                        :id, :category_result_id, :request_id,
                        :category_id, :category_name,
                        :merged_content, :structured_data,
                        :merge_confidence, :data_quality,
                        :overall_confidence,
                        :merge_method, :sources_merged,
                        :conflicts_resolved, :key_findings,
                        :merge_records, :source_references,
                        :merge_strategy,
                        :llm_model, :llm_tokens, :llm_cost,
                        :merged_at, :created_at
                    )
                """), {
                    "id": result_id,
                    "category_result_id": category_result_id,
                    "request_id": request_id,
                    "category_id": category_id,
                    "category_name": category_name,
                    "merged_content": merged_content,
                    "structured_data": json.dumps(structured_data),
                    "merge_confidence": merge_confidence,
                    "data_quality": data_quality,
                    "overall_confidence": (merge_confidence + data_quality) / 2,
                    "merge_method": merge_method,
                    "sources_merged": sources_merged,
                    "conflicts_resolved": json.dumps(conflicts_resolved),
                    "key_findings": json.dumps(key_findings),
                    "merge_records": json.dumps(merge_records),
                    "source_references": json.dumps(source_references),
                    "merge_strategy": merge_strategy,
                    "llm_model": llm_model,
                    "llm_tokens": llm_tokens,
                    "llm_cost": llm_cost,
                    "merged_at": now,
                    "created_at": now
                })

                await session.commit()

                logger.info(
                    "Merged data stored",
                    merged_id=result_id,
                    category_name=category_name,
                    merge_method=merge_method,
                    sources_merged=sources_merged
                )

                return result_id

        except Exception as e:
            logger.error(
                "Failed to store merged data",
                error=str(e),
                category_result_id=category_result_id
            )
            return None

    @staticmethod
    async def get_merged_result(category_result_id: str) -> Optional[Dict[str, Any]]:
        """
        Get merged data result for a category

        Args:
            category_result_id: Category result ID

        Returns:
            Merged data result or None
        """
        try:
            async for session in get_db_session():
                result = await session.execute(text("""
                    SELECT
                        id, category_result_id, request_id,
                        category_id, category_name,
                        merged_content, structured_data,
                        merge_confidence_score, data_quality_score,
                        overall_confidence,
                        merge_method, sources_merged,
                        conflicts_resolved, key_findings,
                        merge_records, source_references,
                        merge_strategy_used,
                        llm_model, llm_tokens_used, llm_cost_estimate,
                        merged_at
                    FROM merged_data_results
                    WHERE category_result_id = :category_result_id
                    ORDER BY merged_at DESC
                    LIMIT 1
                """), {"category_result_id": category_result_id})

                row = result.fetchone()

                if not row:
                    return None

                return {
                    "id": str(row[0]),
                    "category_result_id": str(row[1]),
                    "request_id": str(row[2]),
                    "category_id": row[3],
                    "category_name": row[4],
                    "merged_content": row[5],
                    "structured_data": row[6],
                    "merge_confidence_score": row[7],
                    "data_quality_score": row[8],
                    "overall_confidence": row[9],
                    "merge_method": row[10],
                    "sources_merged": row[11],
                    "conflicts_resolved": row[12],
                    "key_findings": row[13],
                    "merge_records": row[14],
                    "source_references": row[15],
                    "merge_strategy_used": row[16],
                    "llm_model": row[17],
                    "llm_tokens_used": row[18],
                    "llm_cost_estimate": row[19],
                    "merged_at": row[20].isoformat() if row[20] else None
                }

        except Exception as e:
            logger.error(
                "Failed to get merged data",
                error=str(e),
                category_result_id=category_result_id
            )
            return None

    @staticmethod
    async def get_merge_stats(request_id: str) -> Dict[str, Any]:
        """
        Get merge statistics for a request

        Args:
            request_id: Drug request ID

        Returns:
            Merge statistics
        """
        try:
            async for session in get_db_session():
                result = await session.execute(text("""
                    SELECT
                        COUNT(*) as total_merges,
                        AVG(merge_confidence_score) as avg_confidence,
                        AVG(data_quality_score) as avg_quality,
                        SUM(sources_merged) as total_sources,
                        SUM(llm_tokens_used) as total_tokens,
                        SUM(llm_cost_estimate) as total_cost
                    FROM merged_data_results
                    WHERE request_id = :request_id
                """), {"request_id": request_id})

                row = result.fetchone()

                return {
                    "total_merges": row[0] or 0,
                    "avg_confidence": round(row[1] or 0, 4),
                    "avg_quality": round(row[2] or 0, 4),
                    "total_sources": row[3] or 0,
                    "total_tokens": row[4] or 0,
                    "total_cost": round(row[5] or 0, 6)
                }

        except Exception as e:
            logger.error(
                "Failed to get merge stats",
                error=str(e),
                request_id=request_id
            )
            return {
                "total_merges": 0,
                "avg_confidence": 0,
                "avg_quality": 0,
                "total_sources": 0,
                "total_tokens": 0,
                "total_cost": 0
            }
