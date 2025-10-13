"""
Data storage service for pharmaceutical processing results.

Handles storing category results, source references, and API usage logs to PostgreSQL.
"""

import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import text
import structlog

from ..database.connection import get_db_session
from .audit_service import AuditService

logger = structlog.get_logger(__name__)


class DataStorageService:
    """Service for storing processing results to database."""

    @staticmethod
    async def store_category_result(
        request_id: str,
        category_id: int,
        category_name: str,
        summary: str,
        confidence_score: float = 0.8,
        data_quality_score: float = 0.8,
        api_calls_made: int = 1,
        token_count: int = 0,
        cost_estimate: float = 0.0,
        processing_time_ms: int = 0
    ) -> Optional[str]:
        """
        Store category result to database.

        Args:
            request_id: Drug request ID
            category_id: Category ID
            category_name: Category name
            summary: Result summary text
            confidence_score: AI confidence score (0.0-1.0)
            data_quality_score: Data quality score (0.0-1.0)
            api_calls_made: Number of API calls made
            token_count: Total tokens used
            cost_estimate: Estimated cost
            processing_time_ms: Processing time in milliseconds

        Returns:
            Category result ID if successful, None otherwise
        """
        result_id = str(uuid.uuid4())
        now = datetime.utcnow()

        try:
            async for session in get_db_session():
                await session.execute(text("""
                    INSERT INTO category_results (
                        id, request_id, category_id, category_name,
                        summary, confidence_score, data_quality_score,
                        status, started_at, completed_at,
                        api_calls_made, token_count, cost_estimate,
                        processing_time_ms, retry_count
                    )
                    VALUES (
                        :id, :request_id, :category_id, :category_name,
                        :summary, :confidence, :quality,
                        :status, :started, :completed,
                        :api_calls, :tokens, :cost,
                        :processing_time, :retry_count
                    )
                """), {
                    "id": result_id,
                    "request_id": request_id,
                    "category_id": category_id,
                    "category_name": category_name,
                    "summary": summary,
                    "confidence": confidence_score,
                    "quality": data_quality_score,
                    "status": "completed",
                    "started": now,
                    "completed": now,
                    "api_calls": api_calls_made,
                    "tokens": token_count,
                    "cost": cost_estimate,
                    "processing_time": processing_time_ms,
                    "retry_count": 0
                })

                await session.commit()

                logger.info(
                    "Category result stored",
                    result_id=result_id,
                    category_name=category_name,
                    request_id=request_id
                )

                break

            # Log audit event
            try:
                await AuditService.log_event(
                    event_type="create",
                    entity_type="category_result",
                    entity_id=result_id,
                    event_description=f"Stored category result for {category_name}",
                    request_id=request_id,
                    audit_metadata={
                        "category_name": category_name,
                        "confidence_score": confidence_score
                    }
                )
            except Exception:
                pass  # Don't fail on audit errors

            return result_id

        except Exception as e:
            logger.error(
                "Failed to store category result",
                category_name=category_name,
                request_id=request_id,
                error=str(e)
            )
            return None

    @staticmethod
    async def update_category_result(
        category_result_id: str,
        summary: str,
        confidence_score: float,
        data_quality_score: float
    ) -> bool:
        """
        Update category result with pipeline output.

        Args:
            category_result_id: Category result ID to update
            summary: Updated summary text from pipeline
            confidence_score: Updated confidence score
            data_quality_score: Updated data quality score

        Returns:
            True if successful, False otherwise
        """
        try:
            async for session in get_db_session():
                await session.execute(text("""
                    UPDATE category_results
                    SET summary = :summary,
                        confidence_score = :confidence,
                        data_quality_score = :quality,
                        completed_at = :completed
                    WHERE id = :id
                """), {
                    "id": category_result_id,
                    "summary": summary,
                    "confidence": confidence_score,
                    "quality": data_quality_score,
                    "completed": datetime.utcnow()
                })

                await session.commit()

                logger.info(
                    "Category result updated",
                    result_id=category_result_id,
                    confidence_score=confidence_score
                )

                break

            return True

        except Exception as e:
            logger.error(
                "Failed to update category result",
                result_id=category_result_id,
                error=str(e)
            )
            return False

    @staticmethod
    async def store_source_reference(
        category_result_id: str,
        api_provider: str,
        source_url: str,
        source_title: str,
        source_type: str = "article",
        content_snippet: Optional[str] = None,
        relevance_score: float = 0.8,
        credibility_score: float = 0.8
    ) -> Optional[str]:
        """
        Store source reference to database.

        Args:
            category_result_id: Parent category result ID
            api_provider: API provider name
            source_url: Source URL
            source_title: Source title
            source_type: Type of source (article, clinical_trial, etc.)
            content_snippet: Snippet of content
            relevance_score: Relevance score (0.0-1.0)
            credibility_score: Credibility score (0.0-1.0)

        Returns:
            Source reference ID if successful, None otherwise
        """
        source_id = str(uuid.uuid4())
        now = datetime.utcnow()

        try:
            async for session in get_db_session():
                await session.execute(text("""
                    INSERT INTO source_references (
                        id, category_result_id, api_provider,
                        source_url, source_title, source_type,
                        content_snippet, relevance_score, credibility_score,
                        extracted_at
                    )
                    VALUES (
                        :id, :result_id, :provider,
                        :url, :title, :type,
                        :snippet, :relevance, :credibility,
                        :extracted
                    )
                """), {
                    "id": source_id,
                    "result_id": category_result_id,
                    "provider": api_provider,
                    "url": source_url,
                    "title": source_title,
                    "type": source_type,
                    "snippet": content_snippet[:500] if content_snippet else None,
                    "relevance": relevance_score,
                    "credibility": credibility_score,
                    "extracted": now
                })

                await session.commit()

                logger.debug(
                    "Source reference stored",
                    source_id=source_id,
                    source_title=source_title,
                    category_result_id=category_result_id
                )

                break

            return source_id

        except Exception as e:
            logger.error(
                "Failed to store source reference",
                source_title=source_title,
                error=str(e)
            )
            return None

    @staticmethod
    async def store_api_usage_log(
        request_id: str,
        category_result_id: Optional[str],
        api_provider: str,
        endpoint: str,
        response_status: int,
        response_time_ms: int,
        token_count: int = 0,
        cost_per_token: float = 0.0,
        total_cost: float = 0.0,
        error_message: Optional[str] = None,
        category_name: Optional[str] = None,
        prompt_text: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
        request_payload: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Store API usage log to database.

        Args:
            request_id: Drug request ID
            category_result_id: Category result ID (optional)
            api_provider: API provider name
            endpoint: API endpoint
            response_status: HTTP response status
            response_time_ms: Response time in milliseconds
            token_count: Tokens used
            cost_per_token: Cost per token
            total_cost: Cost of API call
            error_message: Error message if failed
            category_name: Category name for tracking
            prompt_text: Prompt sent to API
            response_data: Full response data from API
            request_payload: Full request payload sent to API

        Returns:
            API usage log ID if successful, None otherwise
        """
        log_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # DEBUG: Log what we're receiving
        logger.info(
            "Storing API usage log - request_payload value",
            log_id=log_id,
            request_payload_type=type(request_payload).__name__,
            request_payload_value=request_payload,
            request_payload_is_none=request_payload is None,
            request_payload_is_empty=not bool(request_payload) if request_payload else True
        )

        try:
            async for session in get_db_session():
                await session.execute(text("""
                    INSERT INTO api_usage_logs (
                        id, request_id, category_result_id,
                        api_provider, endpoint,
                        response_status, response_time_ms,
                        token_count, cost_per_token, total_cost,
                        timestamp, error_message,
                        category_name, prompt_text, response_data, request_payload
                    )
                    VALUES (
                        :id, :request_id, :result_id,
                        :provider, :endpoint,
                        :status, :response_time,
                        :tokens, :cost_per_token, :cost,
                        :timestamp, :error,
                        :category_name, :prompt_text, CAST(:response_data AS jsonb), CAST(:request_payload AS jsonb)
                    )
                """), {
                    "id": log_id,
                    "request_id": request_id,
                    "result_id": category_result_id,
                    "provider": api_provider,
                    "endpoint": endpoint,
                    "status": response_status,
                    "response_time": response_time_ms,
                    "tokens": token_count,
                    "cost_per_token": cost_per_token,
                    "cost": total_cost,
                    "timestamp": now,
                    "error": error_message,
                    "category_name": category_name,
                    "prompt_text": prompt_text,
                    "response_data": json.dumps(response_data) if response_data else None,
                    "request_payload": json.dumps(request_payload) if request_payload else None
                })

                await session.commit()

                logger.debug(
                    "API usage log stored",
                    log_id=log_id,
                    api_provider=api_provider,
                    request_id=request_id
                )

                break

            return log_id

        except Exception as e:
            logger.error(
                "Failed to store API usage log",
                api_provider=api_provider,
                error=str(e)
            )
            return None