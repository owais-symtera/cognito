"""
Results API endpoints for retrieving final output.

Provides endpoints to retrieve complete final output JSON for requests.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["results"]
)


@router.get("/results/{request_id}")
async def get_final_output(request_id: str) -> Dict[str, Any]:
    """
    Get complete final output for a request.

    Returns JSON matching apixaban-complete-response.json format with:
    - Executive summary and GO/NO-GO decision
    - All Phase 1 categories
    - Suitability matrix (Phase 2 scoring)
    - Data coverage scorecard
    - Recommendations

    Args:
        request_id: Request UUID

    Returns:
        Complete final output JSON

    Raises:
        HTTPException: If results not found or error occurs
    """
    try:
        from ...services.final_output_generator import FinalOutputGenerator
        from ...utils.db_connection import get_db_connection

        generator = FinalOutputGenerator()

        # First check if final output exists in database
        conn = await get_db_connection()
        try:
            row = await conn.fetchrow("""
                SELECT final_output
                FROM request_final_output
                WHERE request_id = $1
            """, request_id)

            if row:
                logger.info(f"Retrieved existing final output for request {request_id}")
                final_output = row['final_output']
                # Ensure it's a dict (asyncpg returns JSONB as string sometimes)
                if isinstance(final_output, str):
                    import json
                    final_output = json.loads(final_output)
                return final_output

        finally:
            await conn.close()

        # If not found, try to generate it
        logger.info(f"Final output not found in database, attempting to generate for {request_id}")

        try:
            output = await generator.generate_final_output(request_id)
            logger.info(f"Successfully generated final output for {request_id}")
            return output

        except Exception as gen_error:
            logger.error(f"Failed to generate final output: {str(gen_error)}")
            raise HTTPException(
                status_code=404,
                detail=f"Final output not found and generation failed: {str(gen_error)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving final output for {request_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/results/{request_id}/summary")
async def get_final_output_summary(request_id: str) -> Dict[str, Any]:
    """
    Get summary of final output for a request.

    Returns quick-access fields without the full JSON payload.

    Args:
        request_id: Request UUID

    Returns:
        Summary with scores, verdicts, and decision
    """
    try:
        from ...utils.db_connection import get_db_connection

        conn = await get_db_connection()
        try:
            row = await conn.fetchrow("""
                SELECT
                    request_id,
                    drug_name,
                    delivery_method,
                    overall_td_score,
                    overall_tm_score,
                    td_verdict,
                    tm_verdict,
                    go_decision,
                    investment_priority,
                    risk_level,
                    generated_at,
                    version
                FROM request_final_output
                WHERE request_id = $1
            """, request_id)

            if not row:
                raise HTTPException(status_code=404, detail="Results not found")

            return {
                "request_id": str(row['request_id']),
                "drug_name": row['drug_name'],
                "delivery_method": row['delivery_method'],
                "overall_td_score": float(row['overall_td_score']) if row['overall_td_score'] else None,
                "overall_tm_score": float(row['overall_tm_score']) if row['overall_tm_score'] else None,
                "td_verdict": row['td_verdict'],
                "tm_verdict": row['tm_verdict'],
                "go_decision": row['go_decision'],
                "investment_priority": row['investment_priority'],
                "risk_level": row['risk_level'],
                "generated_at": row['generated_at'].isoformat() if row['generated_at'] else None,
                "version": row['version']
            }

        finally:
            await conn.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving summary for {request_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
