"""
Pipeline Stage Logger Service
Stores intermediate pipeline stage execution data to database for auditing
"""
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
import asyncpg
import structlog
import json

logger = structlog.get_logger()


class PipelineStageLogger:
    """Service for logging pipeline stage executions to database"""

    @staticmethod
    async def log_stage_execution(
        request_id: str,
        category_result_id: Optional[str],
        stage_name: str,
        stage_order: int,
        executed: bool,
        skipped: bool,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        stage_metadata: Optional[Dict[str, Any]] = None,
        execution_time_ms: int = 0
    ) -> Optional[str]:
        """
        Log a pipeline stage execution to the database

        Args:
            request_id: Drug request ID
            category_result_id: Category result ID (if available)
            stage_name: Name of the stage (verification, merging, llm_summary)
            stage_order: Order of the stage (1-4)
            executed: Whether the stage was executed
            skipped: Whether the stage was skipped
            input_data: Input data passed to the stage
            output_data: Output data produced by the stage
            stage_metadata: Stage-specific metadata
            execution_time_ms: Execution time in milliseconds

        Returns:
            Stage log ID if successful, None otherwise
        """
        stage_id = str(uuid.uuid4())

        try:
            conn = await asyncpg.connect(
                host='localhost',
                port=5432,
                user='postgres',
                password='postgres',
                database='cognito-engine'
            )

            try:
                await conn.execute(
                    """
                    INSERT INTO pipeline_stage_executions (
                        id, request_id, category_result_id,
                        stage_name, stage_order,
                        executed, skipped,
                        input_data, output_data, stage_metadata,
                        execution_time_ms,
                        started_at, completed_at
                    )
                    VALUES (
                        $1, $2, $3,
                        $4, $5,
                        $6, $7,
                        $8, $9, $10,
                        $11,
                        $12, $13
                    )
                    """,
                    stage_id,
                    request_id,
                    category_result_id if category_result_id else None,
                    stage_name,
                    stage_order,
                    executed,
                    skipped,
                    json.dumps(input_data) if input_data else None,
                    json.dumps(output_data) if output_data else None,
                    json.dumps(stage_metadata) if stage_metadata else None,
                    execution_time_ms,
                    datetime.now(),
                    datetime.now() if executed else None
                )

                logger.info(
                    "Pipeline stage logged",
                    stage_id=stage_id,
                    request_id=request_id,
                    stage_name=stage_name,
                    executed=executed,
                    skipped=skipped
                )

                return stage_id

            finally:
                await conn.close()

        except Exception as e:
            logger.error(
                "Failed to log pipeline stage",
                stage_name=stage_name,
                request_id=request_id,
                error=str(e)
            )
            return None

    @staticmethod
    async def get_stage_logs_for_request(request_id: str) -> list:
        """
        Get all pipeline stage logs for a request

        Args:
            request_id: Drug request ID

        Returns:
            List of stage log dictionaries
        """
        try:
            conn = await asyncpg.connect(
                host='localhost',
                port=5432,
                user='postgres',
                password='postgres',
                database='cognito-engine'
            )

            try:
                rows = await conn.fetch(
                    """
                    SELECT
                        id, request_id, category_result_id,
                        stage_name, stage_order,
                        executed, skipped,
                        input_data, output_data, stage_metadata,
                        execution_time_ms,
                        started_at, completed_at
                    FROM pipeline_stage_executions
                    WHERE request_id = $1
                    ORDER BY stage_order ASC
                    """,
                    request_id
                )

                return [dict(row) for row in rows]

            finally:
                await conn.close()

        except Exception as e:
            logger.error(
                "Failed to get stage logs",
                request_id=request_id,
                error=str(e)
            )
            return []

    @staticmethod
    async def get_stage_logs_for_category(category_result_id: str) -> list:
        """
        Get all pipeline stage logs for a category result

        Args:
            category_result_id: Category result ID

        Returns:
            List of stage log dictionaries
        """
        try:
            conn = await asyncpg.connect(
                host='localhost',
                port=5432,
                user='postgres',
                password='postgres',
                database='cognito-engine'
            )

            try:
                rows = await conn.fetch(
                    """
                    SELECT
                        id, request_id, category_result_id,
                        stage_name, stage_order,
                        executed, skipped,
                        input_data, output_data, stage_metadata,
                        execution_time_ms,
                        started_at, completed_at
                    FROM pipeline_stage_executions
                    WHERE category_result_id = $1
                    ORDER BY stage_order ASC
                    """,
                    category_result_id
                )

                return [dict(row) for row in rows]

            finally:
                await conn.close()

        except Exception as e:
            logger.error(
                "Failed to get category stage logs",
                category_result_id=category_result_id,
                error=str(e)
            )
            return []
