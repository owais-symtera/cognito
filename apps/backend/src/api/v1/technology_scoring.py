"""
Technology Go/No-Go Scoring Matrix API endpoints
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import asyncpg
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/technology-scoring", tags=["technology-scoring"])


@router.get("/categories")
async def get_scoring_categories():
    """Get all scoring categories with their weightages"""
    logger.info("Fetching scoring categories")
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
                SELECT id, name, weightage, description
                FROM scoring_categories
                ORDER BY weightage DESC
                """
            )

            categories = []
            for row in rows:
                categories.append({
                    "id": row['id'],
                    "name": row['name'],
                    "weightage": float(row['weightage']),
                    "description": row['description']
                })

            return {
                "total_categories": len(categories),
                "categories": categories
            }

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Failed to get categories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parameters")
async def get_scoring_parameters():
    """Get all scoring parameters with their categories"""
    logger.info("Fetching scoring parameters")
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
                    p.id,
                    p.name,
                    p.unit,
                    p.description,
                    c.id as category_id,
                    c.name as category_name,
                    c.weightage
                FROM scoring_parameters p
                JOIN scoring_categories c ON p.category_id = c.id
                ORDER BY c.weightage DESC, p.id
                """
            )

            parameters = []
            for row in rows:
                parameters.append({
                    "id": row['id'],
                    "name": row['name'],
                    "unit": row['unit'],
                    "description": row['description'],
                    "category": {
                        "id": row['category_id'],
                        "name": row['category_name'],
                        "weightage": float(row['weightage'])
                    }
                })

            return {
                "total_parameters": len(parameters),
                "parameters": parameters
            }

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Failed to get parameters: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ranges/{parameter_id}")
async def get_scoring_ranges(parameter_id: int):
    """Get scoring ranges for a specific parameter"""
    logger.info(f"Fetching scoring ranges for parameter_id: {parameter_id}")
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='cognito-engine'
        )

        try:
            # Get parameter info
            param_row = await conn.fetchrow(
                """
                SELECT
                    p.id,
                    p.name,
                    p.unit,
                    p.description,
                    c.id as category_id,
                    c.name as category_name,
                    c.weightage
                FROM scoring_parameters p
                JOIN scoring_categories c ON p.category_id = c.id
                WHERE p.id = $1
                """,
                parameter_id
            )

            if not param_row:
                raise HTTPException(status_code=404, detail=f"Parameter {parameter_id} not found")

            # Get ranges
            range_rows = await conn.fetch(
                """
                SELECT
                    id,
                    delivery_method,
                    score,
                    min_value,
                    max_value,
                    range_text,
                    is_exclusion
                FROM scoring_ranges
                WHERE parameter_id = $1
                ORDER BY delivery_method, score DESC
                """,
                parameter_id
            )

            # Group ranges by delivery method
            transdermal_ranges = []
            transmucosal_ranges = []
            both_ranges = []

            for row in range_rows:
                range_obj = {
                    "id": row['id'],
                    "score": row['score'],
                    "min_value": float(row['min_value']) if row['min_value'] is not None else None,
                    "max_value": float(row['max_value']) if row['max_value'] is not None else None,
                    "range_text": row['range_text'],
                    "is_exclusion": row['is_exclusion']
                }

                if row['delivery_method'] == 'Transdermal':
                    transdermal_ranges.append(range_obj)
                elif row['delivery_method'] == 'Transmucosal':
                    transmucosal_ranges.append(range_obj)
                elif row['delivery_method'] == 'Both':
                    both_ranges.append(range_obj)

            return {
                "parameter": {
                    "id": param_row['id'],
                    "name": param_row['name'],
                    "unit": param_row['unit'],
                    "description": param_row['description'],
                    "category": {
                        "id": param_row['category_id'],
                        "name": param_row['category_name'],
                        "weightage": float(param_row['weightage'])
                    }
                },
                "ranges": {
                    "transdermal": transdermal_ranges,
                    "transmucosal": transmucosal_ranges,
                    "both": both_ranges
                }
            }

        finally:
            await conn.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ranges: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/matrix")
async def get_full_scoring_matrix():
    """Get the complete scoring matrix with all categories, parameters, and ranges"""
    logger.info("Fetching full scoring matrix")
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='cognito-engine'
        )

        try:
            # Get all data in one go
            category_rows = await conn.fetch(
                """
                SELECT id, name, weightage, description
                FROM scoring_categories
                ORDER BY weightage DESC
                """
            )

            matrix = []

            for cat_row in category_rows:
                # Get parameters for this category
                param_rows = await conn.fetch(
                    """
                    SELECT id, name, unit, description
                    FROM scoring_parameters
                    WHERE category_id = $1
                    """,
                    cat_row['id']
                )

                parameters = []
                for param_row in param_rows:
                    # Get ranges for this parameter
                    range_rows = await conn.fetch(
                        """
                        SELECT
                            delivery_method,
                            score,
                            min_value,
                            max_value,
                            range_text,
                            is_exclusion
                        FROM scoring_ranges
                        WHERE parameter_id = $1
                        ORDER BY delivery_method, score DESC
                        """,
                        param_row['id']
                    )

                    # Group ranges by delivery method
                    transdermal_ranges = []
                    transmucosal_ranges = []
                    both_ranges = []

                    for range_row in range_rows:
                        range_obj = {
                            "score": range_row['score'],
                            "min_value": float(range_row['min_value']) if range_row['min_value'] is not None else None,
                            "max_value": float(range_row['max_value']) if range_row['max_value'] is not None else None,
                            "range_text": range_row['range_text'],
                            "is_exclusion": range_row['is_exclusion']
                        }

                        if range_row['delivery_method'] == 'Transdermal':
                            transdermal_ranges.append(range_obj)
                        elif range_row['delivery_method'] == 'Transmucosal':
                            transmucosal_ranges.append(range_obj)
                        elif range_row['delivery_method'] == 'Both':
                            both_ranges.append(range_obj)

                    parameters.append({
                        "id": param_row['id'],
                        "name": param_row['name'],
                        "unit": param_row['unit'],
                        "description": param_row['description'],
                        "ranges": {
                            "transdermal": transdermal_ranges if transdermal_ranges else both_ranges,
                            "transmucosal": transmucosal_ranges if transmucosal_ranges else both_ranges
                        }
                    })

                matrix.append({
                    "id": cat_row['id'],
                    "name": cat_row['name'],
                    "weightage": float(cat_row['weightage']),
                    "description": cat_row['description'],
                    "parameters": parameters
                })

            return {
                "total_categories": len(matrix),
                "matrix": matrix
            }

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Failed to get scoring matrix: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate")
async def calculate_score(data: Dict[str, Any]):
    """
    Calculate weighted score based on input values

    Expected input format:
    {
        "delivery_method": "Transdermal" or "Transmucosal",
        "values": {
            "Dose": 5.0,
            "Molecular Weight": 250.0,
            "Melting Point": 120.0,
            "Log P": 2.5
        }
    }
    """
    logger.info(f"Calculating score for: {data}")

    delivery_method = data.get('delivery_method', 'Transdermal')
    values = data.get('values', {})

    if not values:
        raise HTTPException(status_code=400, detail="No values provided")

    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='cognito-engine'
        )

        try:
            results = []
            total_weighted_score = 0.0

            for param_name, value in values.items():
                # Get parameter info
                param_row = await conn.fetchrow(
                    """
                    SELECT
                        p.id,
                        p.name,
                        p.unit,
                        c.id as category_id,
                        c.name as category_name,
                        c.weightage
                    FROM scoring_parameters p
                    JOIN scoring_categories c ON p.category_id = c.id
                    WHERE p.name = $1
                    """,
                    param_name
                )

                if not param_row:
                    continue

                # Find matching range
                range_row = await conn.fetchrow(
                    """
                    SELECT score, range_text, is_exclusion
                    FROM scoring_ranges
                    WHERE parameter_id = $1
                      AND (delivery_method = $2 OR delivery_method = 'Both')
                      AND (
                        (min_value IS NULL OR $3 >= min_value)
                        AND (max_value IS NULL OR $3 <= max_value)
                        OR (min_value IS NULL AND max_value >= $3)
                      )
                    ORDER BY score DESC
                    LIMIT 1
                    """,
                    param_row['id'], delivery_method, float(value)
                )

                if range_row:
                    raw_score = range_row['score']
                    weightage = float(param_row['weightage']) / 100.0
                    weighted_score = raw_score * weightage

                    results.append({
                        "parameter": param_row['name'],
                        "category": param_row['category_name'],
                        "value": float(value),
                        "unit": param_row['unit'],
                        "raw_score": raw_score,
                        "weightage": float(param_row['weightage']),
                        "weighted_score": weighted_score,
                        "range": range_row['range_text'],
                        "is_exclusion": range_row['is_exclusion']
                    })

                    if not range_row['is_exclusion']:
                        total_weighted_score += weighted_score

            return {
                "delivery_method": delivery_method,
                "total_weighted_score": round(total_weighted_score, 2),
                "max_possible_score": 9.0,
                "percentage": round((total_weighted_score / 9.0) * 100, 2) if total_weighted_score > 0 else 0,
                "results": results,
                "has_exclusions": any(r['is_exclusion'] for r in results)
            }

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Failed to calculate score: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
