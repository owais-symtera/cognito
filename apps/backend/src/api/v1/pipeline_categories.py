"""
Pipeline categories API endpoints.
"""

from fastapi import APIRouter
import asyncpg
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


@router.get("/request-categories/{request_id}")
async def get_categories_for_request(request_id: str):
    """Get all categories for a request."""
    logger.info(f"Fetching categories for request_id: {request_id}")
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
                SELECT cr.id, cr.category_name, cr.category_id, pc.phase
                FROM category_results cr
                JOIN pharmaceutical_categories pc ON cr.category_id = pc.id
                WHERE cr.request_id = $1::uuid
                ORDER BY pc.phase ASC, cr.category_id ASC
                """,
                request_id
            )

            categories = []
            for row in rows:
                categories.append({
                    "category_result_id": str(row['id']),
                    "category_name": row['category_name'],
                    "category_id": row['category_id'],
                    "phase": row['phase']
                })

            return {
                "request_id": request_id,
                "total_categories": len(categories),
                "categories": categories
            }

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Failed to get categories: {str(e)}")
        return {
            "request_id": request_id,
            "total_categories": 0,
            "categories": []
        }


@router.get("/category-stages/{category_result_id}")
async def get_category_stage_executions(category_result_id: str):
    """Get pipeline stage executions for a category."""
    logger.info(f"Fetching stage executions for category_result_id: {category_result_id}")
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
                WHERE category_result_id = $1::uuid
                ORDER BY stage_order ASC
                """,
                category_result_id
            )

            stages = []
            for row in rows:
                # Parse JSON fields
                import json
                output_data = json.loads(row['output_data']) if row['output_data'] else {}
                stage_metadata = json.loads(row['stage_metadata']) if row['stage_metadata'] else {}
                input_data = json.loads(row['input_data']) if row['input_data'] else {}

                # For merging stage, prioritize structured_data display
                if row['stage_name'] == 'merging':
                    structured_data = output_data.get('structured_data', stage_metadata.get('structured_data', {}))

                    # If structured_data is empty but we have a merged_data_id, fetch from merged_data table
                    if not structured_data and output_data.get('merged_data_id'):
                        try:
                            merged_data_row = await conn.fetchrow(
                                "SELECT structured_data FROM merged_data WHERE id = $1::uuid",
                                output_data.get('merged_data_id')
                            )
                            if merged_data_row and merged_data_row['structured_data']:
                                structured_data = json.loads(merged_data_row['structured_data']) if isinstance(merged_data_row['structured_data'], str) else merged_data_row['structured_data']
                        except Exception as e:
                            logger.error(f"Failed to fetch merged_data: {str(e)}")

                    stages.append({
                        "id": str(row['id']),
                        "stage_name": row['stage_name'],
                        "stage_order": row['stage_order'],
                        "executed": row['executed'],
                        "skipped": row['skipped'],
                        "input_data": input_data,
                        "structured_data": structured_data,  # Renamed for frontend clarity
                        "output_metadata": {k: v for k, v in output_data.items() if k != 'structured_data'},
                        "execution_time_ms": row['execution_time_ms'],
                        "started_at": row['started_at'].isoformat() if row['started_at'] else None,
                        "completed_at": row['completed_at'].isoformat() if row['completed_at'] else None
                    })
                else:
                    stages.append({
                        "id": str(row['id']),
                        "stage_name": row['stage_name'],
                        "stage_order": row['stage_order'],
                        "executed": row['executed'],
                        "skipped": row['skipped'],
                        "input_data": input_data,
                        "output_data": output_data,
                        "stage_metadata": stage_metadata,
                        "execution_time_ms": row['execution_time_ms'],
                        "started_at": row['started_at'].isoformat() if row['started_at'] else None,
                        "completed_at": row['completed_at'].isoformat() if row['completed_at'] else None
                    })

            return {
                "category_result_id": category_result_id,
                "total_stages": len(stages),
                "stages": stages
            }

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Failed to get category stages: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "category_result_id": category_result_id,
            "total_stages": 0,
            "stages": [],
            "error": str(e)
        }
