"""
Phase 2 Reprocessing API Endpoint

Allows reprocessing Phase 2 categories without re-running expensive Phase 1 API calls.
Useful for testing and development.
"""
from fastapi import APIRouter, HTTPException
import structlog
from typing import Dict, Any

from ...services.pipeline_integration_service import PipelineIntegrationService
from ...utils.db_connection import DatabaseConnection

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["phase2-testing"])


@router.post("/drug-request/{request_id}/reprocess-phase2")
async def reprocess_phase2_only(request_id: str) -> Dict[str, Any]:
    """
    Reprocess only Phase 2 categories using existing Phase 1 data.

    This endpoint:
    1. Deletes existing Phase 2 category results
    2. Keeps all Phase 1 data intact (no API calls)
    3. Re-runs Phase 2 processing with existing Phase 1 data
    4. Creates new Phase 2 results in database

    Perfect for testing Phase 2 logic changes without incurring LLM API costs for Phase 1.

    Args:
        request_id: UUID of the drug request

    Returns:
        Dict with processing results for each Phase 2 category
    """
    logger.info(f"[REPROCESS_PHASE2] Starting for request_id: {request_id}")

    try:
        async with DatabaseConnection() as conn:
            # Step 1: Verify request exists and get drug name
            request_info = await conn.fetchrow(
                "SELECT drug_name FROM drug_requests WHERE id = $1::uuid",
                request_id
            )

            if not request_info:
                raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

            drug_name = request_info['drug_name']
            logger.info(f"[REPROCESS_PHASE2] Found request for drug: {drug_name}")

            # Step 2: Check if Phase 1 data exists
            phase1_count = await conn.fetchval("""
                SELECT COUNT(*) FROM category_results cr
                JOIN pharmaceutical_categories pc ON cr.category_id = pc.id
                WHERE cr.request_id = $1::uuid AND pc.phase = 1
            """, request_id)

            if phase1_count == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No Phase 1 data found for this request. Cannot process Phase 2."
                )

            logger.info(f"[REPROCESS_PHASE2] Found {phase1_count} Phase 1 categories")

            # Step 3: Delete existing Phase 2 results (keeps Phase 1 intact)
            delete_result = await conn.execute("""
                DELETE FROM category_results
                WHERE request_id = $1::uuid
                AND category_id IN (
                    SELECT id FROM pharmaceutical_categories
                    WHERE phase = 2
                )
            """, request_id)

            logger.info(f"[REPROCESS_PHASE2] Deleted existing Phase 2 results: {delete_result}")

            # Step 4: Get Phase 2 categories to process
            phase2_cats = await conn.fetch("""
                SELECT id, name FROM pharmaceutical_categories
                WHERE phase = 2 AND is_active = true
                ORDER BY id
            """)

            if not phase2_cats:
                raise HTTPException(
                    status_code=400,
                    detail="No active Phase 2 categories configured in database"
                )

            logger.info(f"[REPROCESS_PHASE2] Found {len(phase2_cats)} Phase 2 categories to process")

        # Step 5: Re-run Phase 2 processing
        pipeline = PipelineIntegrationService()
        results = []

        for cat in phase2_cats:
            category_name = cat['name']
            logger.info(f"[REPROCESS_PHASE2] Processing category: {category_name}")

            try:
                result = await pipeline.process_phase2_category(
                    category_name=category_name,
                    drug_name=drug_name,
                    request_id=request_id,
                    category_result_id=None  # Will create new ID
                )

                # Extract summary for response
                summary = result.get('final_summary', '')
                if not summary:
                    summary = result.get('drug_name', 'N/A')

                results.append({
                    "category": category_name,
                    "status": "completed",
                    "summary_preview": summary[:200] + "..." if len(summary) > 200 else summary,
                    "confidence_score": result.get('confidence_score', 0.0)
                })

                logger.info(f"[REPROCESS_PHASE2] SUCCESS Completed: {category_name}")

            except Exception as e:
                logger.error(f"[REPROCESS_PHASE2] FAILED: {category_name} - {str(e)}")
                import traceback
                logger.error(f"[REPROCESS_PHASE2] Traceback: {traceback.format_exc()}")

                results.append({
                    "category": category_name,
                    "status": "failed",
                    "error": str(e)
                })

        # Step 6: Return results
        successful = len([r for r in results if r['status'] == 'completed'])
        failed = len([r for r in results if r['status'] == 'failed'])

        logger.info(f"[REPROCESS_PHASE2] Finished - Success: {successful}, Failed: {failed}")

        return {
            "request_id": request_id,
            "drug_name": drug_name,
            "phase1_categories_preserved": phase1_count,
            "phase2_categories_processed": len(results),
            "successful": successful,
            "failed": failed,
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REPROCESS_PHASE2] Unexpected error: {str(e)}")
        import traceback
        logger.error(f"[REPROCESS_PHASE2] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Phase 2 reprocessing failed: {str(e)}")


@router.get("/drug-request/{request_id}/phase2-status")
async def get_phase2_status(request_id: str) -> Dict[str, Any]:
    """
    Check Phase 2 processing status for a request.

    Returns information about Phase 1 and Phase 2 data availability.
    """
    try:
        async with DatabaseConnection() as conn:
            # Get request info
            request_info = await conn.fetchrow(
                "SELECT drug_name, status FROM drug_requests WHERE id = $1::uuid",
                request_id
            )

            if not request_info:
                raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

            # Count Phase 1 results
            phase1_results = await conn.fetch("""
                SELECT cr.category_name, cr.status, cr.completed_at
                FROM category_results cr
                JOIN pharmaceutical_categories pc ON cr.category_id = pc.id
                WHERE cr.request_id = $1::uuid AND pc.phase = 1
                ORDER BY cr.category_name
            """, request_id)

            # Count Phase 2 results
            phase2_results = await conn.fetch("""
                SELECT cr.category_name, cr.status, cr.completed_at
                FROM category_results cr
                JOIN pharmaceutical_categories pc ON cr.category_id = pc.id
                WHERE cr.request_id = $1::uuid AND pc.phase = 2
                ORDER BY cr.category_name
            """, request_id)

            return {
                "request_id": request_id,
                "drug_name": request_info['drug_name'],
                "request_status": request_info['status'],
                "phase1": {
                    "count": len(phase1_results),
                    "categories": [
                        {
                            "name": r['category_name'],
                            "status": r['status'],
                            "completed_at": r['completed_at'].isoformat() if r['completed_at'] else None
                        }
                        for r in phase1_results
                    ]
                },
                "phase2": {
                    "count": len(phase2_results),
                    "categories": [
                        {
                            "name": r['category_name'],
                            "status": r['status'],
                            "completed_at": r['completed_at'].isoformat() if r['completed_at'] else None
                        }
                        for r in phase2_results
                    ]
                },
                "can_reprocess_phase2": len(phase1_results) > 0
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Phase 2 status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
