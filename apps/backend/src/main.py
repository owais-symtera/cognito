"""
Refactored main application with proper OOP structure.
All business logic is in service classes.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
import aiohttp
import asyncpg
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Import services
from .services.auth_service import AuthService
from .services.provider_service import ProviderService
from .services.request_service import RequestService
from .services.request_db_service import RequestDatabaseService
from .services.pipeline_service import PipelineService
from .services.pipeline_db_service import PipelineDatabaseService
from .services.analysis_service import AnalysisService
from .services.audit_service import AuditService

# Import API routers
from .api.v1.processing import router as processing_router
from .api.v1.pipeline_categories import router as pipeline_categories_router
from .api.v1.summary_config import router as summary_config_router
from .api.v1.technology_scoring import router as technology_scoring_router
from .api.v1.phase2_reprocess import router as phase2_reprocess_router
from .api.v1.results import router as results_router

# Initialize FastAPI app
app = FastAPI(
    title="CognitoAI Drug Intelligence API",
    description="API for drug intelligence gathering and analysis",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
auth_service = AuthService()
provider_service = ProviderService()
request_service = RequestService(provider_service)  # Keep for backward compatibility
request_db_service = RequestDatabaseService()  # New database-backed service
pipeline_service = PipelineService()  # Keep for backward compatibility
pipeline_db_service = PipelineDatabaseService()  # New database-backed service
analysis_service = AnalysisService()
from .services.category_postgres_service import CategoryPostgresService
category_service = CategoryPostgresService()

# Include routers
app.include_router(processing_router)
app.include_router(pipeline_categories_router)
app.include_router(summary_config_router)  # Summary configuration management
app.include_router(technology_scoring_router)  # Technology Go/No-Go scoring matrix
app.include_router(phase2_reprocess_router)  # Phase 2 reprocessing for testing
app.include_router(results_router)  # Final output results retrieval


# Pydantic models for requests
class DrugRequest(BaseModel):
    requestId: str
    drugName: str
    webhookUrl: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str


# Startup event to log all routes
@app.on_event("startup")
async def startup_event():
    """Log all registered routes on startup."""
    print("=" * 80)
    print("REGISTERED ROUTES:")
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            print(f"  {list(route.methods)} {route.path}")
    print("=" * 80)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "CognitoAI API v2.0"}


# Authentication endpoints
@app.post("/api/v1/auth/signin")
async def signin(credentials: LoginRequest):
    """User sign in."""
    user = auth_service.authenticate_user(credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Ensure user has required fields for frontend compatibility
    if "id" not in user:
        user["id"] = user.get("email", "")
    if "name" not in user:
        user["name"] = user.get("full_name", user.get("email", ""))

    token = auth_service.create_session(user)
    return {
        "user": user,
        "access_token": token,  # Frontend expects access_token not accessToken
        "refresh_token": None,  # Add refresh_token field
        "tokenType": "bearer"
    }


@app.post("/api/v1/auth/register")
async def register(user_data: RegisterRequest):
    """Register new user."""
    success = auth_service.register_user(
        user_data.email,
        user_data.password,
        user_data.full_name
    )
    if not success:
        raise HTTPException(status_code=400, detail="User already exists")

    return {"message": "User registered successfully", "email": user_data.email}


@app.post("/api/v1/auth/logout")
async def logout(token: str):
    """User logout."""
    success = auth_service.logout(token)
    return {"message": "Logged out successfully" if success else "Invalid token"}


# Provider endpoints
@app.get("/api/v1/providers")
async def get_providers():
    """Get all provider configurations."""
    return provider_service.get_all_providers()


@app.get("/api/v1/providers/{provider_id}")
async def get_provider(provider_id: str):
    """Get specific provider configuration."""
    provider = provider_service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@app.put("/api/v1/providers/{provider_id}")
async def update_provider(provider_id: str, config: Dict[str, Any]):
    """Update provider configuration."""
    success = provider_service.update_provider(provider_id, config)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")

    return provider_service.get_provider(provider_id)


@app.post("/api/v1/providers/{provider_id}/test")
async def test_provider(provider_id: str):
    """Test provider connectivity."""
    result = await provider_service.test_provider(provider_id)
    return result


@app.get("/api/v1/providers/stats/summary")
async def get_provider_stats():
    """Get API provider statistics."""
    providers = provider_service.config.values()

    return {
        "total": len(providers),
        "enabled": sum(1 for p in providers if p.get("enabled")),
        "disabled": sum(1 for p in providers if not p.get("enabled")),
        "configured": sum(1 for p in providers if p.get("api_key"))
    }


@app.post("/api/v1/providers/{provider_id}/temperatures")
async def add_temperature(provider_id: str, temperature_data: Dict[str, Any]):
    """Add a new temperature configuration to a provider."""
    success = provider_service.add_temperature(provider_id, temperature_data)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")

    return provider_service.get_provider(provider_id)


@app.delete("/api/v1/providers/{provider_id}/temperatures/{temp_id}")
async def remove_temperature(provider_id: str, temp_id: str):
    """Remove a temperature configuration from a provider."""
    success = provider_service.remove_temperature(provider_id, temp_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider or temperature not found")

    return provider_service.get_provider(provider_id)


# Request endpoints
@app.get("/api/v1/requests")
async def get_requests():
    """Get all requests from PostgreSQL."""
    return await request_db_service.get_all_requests()


@app.get("/api/v1/requests/{request_id}")
async def get_request(request_id: str):
    """Get specific request from PostgreSQL."""
    request = await request_db_service.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request


@app.post("/api/v1/requests")
async def create_request(request_data: DrugRequest):
    """Create new drug analysis request with PostgreSQL storage."""
    return await request_db_service.create_request(
        request_data.requestId,
        request_data.drugName,
        request_data.webhookUrl
    )


@app.post("/api/v1/requests/{request_id}/process")
async def process_request(request_id: str, background_tasks: BackgroundTasks):
    """Start processing a request with full database storage."""
    # Get request from database - request_id is the database UUID
    request = await request_db_service.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    drug_name = request["drugName"]

    # Process in background
    async def process_async():
        try:
            # Log processing started
            try:
                await AuditService.log_event(
                    event_type="process_start",
                    entity_type="drug_request",
                    entity_id=request_id,
                    event_description=f"Started processing {drug_name}",
                    request_id=request_id,
                    audit_metadata={"drug_name": drug_name}
                )
            except Exception:
                pass  # Don't fail on audit errors

            # Update request status to processing
            await request_db_service.update_request(request_id, {
                "status": "processing",
                "progressPercentage": 10
            })

            # Call providers with category-based prompts - THIS STORES TO DB
            # provider_service will store category_results, source_references, and api_usage_logs
            api_responses = await provider_service.process_drug_with_categories(drug_name, request_id)

            await request_db_service.update_request(request_id, {"progressPercentage": 50})

            # Simulate additional processing stages
            await asyncio.sleep(2)
            await request_db_service.update_request(request_id, {"progressPercentage": 75})

            await asyncio.sleep(2)
            await request_db_service.update_request(request_id, {"progressPercentage": 95})

            # Complete request
            await request_db_service.update_request(request_id, {
                "status": "completed",
                "progressPercentage": 100,
                "completedAt": datetime.now().isoformat()
            })

            # Log processing completed
            try:
                await AuditService.log_event(
                    event_type="process_complete",
                    entity_type="drug_request",
                    entity_id=request_id,
                    event_description=f"Completed processing {drug_name}",
                    request_id=request_id,
                    audit_metadata={"drug_name": drug_name}
                )
            except Exception:
                pass

            # Send webhook if configured
            if request.get("webhookUrl"):
                await send_webhook(
                    request["webhookUrl"],
                    {
                        "requestId": request_id,
                        "status": "completed",
                        "drugName": drug_name,
                        "completedAt": datetime.now().isoformat()
                    }
                )

        except Exception as e:
            import traceback
            error_msg = f"Error processing request {request_id}: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)

            # Update request to failed
            await request_db_service.update_request(request_id, {
                "status": "failed",
                "progressPercentage": 0
            })

            # Log processing failed
            try:
                await AuditService.log_event(
                    event_type="process_error",
                    entity_type="drug_request",
                    entity_id=request_id,
                    event_description=f"Failed processing {drug_name}: {str(e)}",
                    request_id=request_id,
                    audit_metadata={"drug_name": drug_name, "error": str(e)}
                )
            except Exception:
                pass

    background_tasks.add_task(process_async)

    return {
        "message": "Processing started",
        "requestId": request_id,
        "drugName": drug_name,
        "status": "processing"
    }


# Pipeline endpoints
@app.get("/api/v1/pipelines")
async def get_pipelines():
    """Get all pipelines from database."""
    return await pipeline_db_service.get_all_pipelines()


@app.get("/api/v1/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """Get specific pipeline from database."""
    pipeline = await pipeline_db_service.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


# Analysis endpoints (for results page)
@app.get("/api/v1/analyses")
async def get_analyses():
    """Get all analyses."""
    return analysis_service.get_all_analyses()

@app.get("/api/v1/analysis")
async def get_analysis_list():
    """Get all analyses (alternate endpoint for frontend compatibility)."""
    return analysis_service.get_all_analyses()


@app.get("/api/v1/analyses/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Get specific analysis."""
    analysis = analysis_service.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


# Webhook helper
async def send_webhook(url: str, data: Dict[str, Any]):
    """Send webhook notification."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=10) as response:
                print(f"Webhook sent to {url}: {response.status}")
    except Exception as e:
        print(f"Webhook error: {e}")


# Category endpoints
@app.get("/api/v1/categories")
async def get_categories():
    """Get all pharmaceutical categories."""
    categories = category_service.get_all_categories()

    # Format for frontend compatibility
    formatted_categories = []
    for key, cat in categories.items():
        formatted_categories.append({
            "id": cat["id"],
            "key": key,
            "name": cat["name"],
            "phase": cat["phase"],
            "enabled": cat.get("enabled", False),
            "description": cat.get("prompt_template", "")[:200] + "...",  # First 200 chars as description
            "prompt_template": cat.get("prompt_template", ""),  # Full prompt template
            "weight": cat.get("weight", 1.0),
            "source_priorities": cat.get("source_priorities", []),
            "requires_phase1": cat.get("requires_phase1", False)
        })

    return {
        "categories": sorted(formatted_categories, key=lambda x: x["id"]),
        "total": len(formatted_categories),
        "phase1_count": len([c for c in formatted_categories if c["phase"] == 1]),
        "phase2_count": len([c for c in formatted_categories if c["phase"] == 2])
    }


@app.get("/api/v1/categories/{category_key}")
async def get_category(category_key: str):
    """Get specific category configuration."""
    category = category_service.get_category(category_key)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Add the key to the response
    category_with_key = category.copy()
    category_with_key["key"] = category_key
    return category_with_key


@app.put("/api/v1/categories/{category_key}")
async def update_category(category_key: str, updates: Dict[str, Any]):
    """Update category configuration."""
    success = category_service.update_category(category_key, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found or update failed")
    return category_service.get_category(category_key)


# Pipeline stages endpoints
from .services.pipeline_config_service import PipelineConfigService
pipeline_config_service = PipelineConfigService()


@app.get("/api/v1/pipeline/stages")
async def get_pipeline_stages():
    """Get all pipeline stages configuration."""
    return pipeline_config_service.get_pipeline_summary()


@app.get("/api/v1/pipeline/stages/{stage_name}")
async def get_pipeline_stage(stage_name: str):
    """Get specific pipeline stage configuration."""
    stage = pipeline_config_service.get_stage_config(stage_name)
    if not stage:
        raise HTTPException(status_code=404, detail="Pipeline stage not found")
    return {
        "name": stage.stage_name,
        "order": stage.stage_order,
        "enabled": stage.enabled,
        "description": stage.description,
        "progress_weight": stage.progress_weight
    }


@app.put("/api/v1/pipeline/stages/{stage_name}")
async def update_pipeline_stage(stage_name: str, enabled: bool):
    """Enable or disable a pipeline stage."""
    success = pipeline_config_service.update_stage_enabled(stage_name, enabled)
    if not success:
        raise HTTPException(status_code=404, detail="Pipeline stage not found")

    stage = pipeline_config_service.get_stage_config(stage_name)
    return {
        "name": stage.stage_name,
        "enabled": stage.enabled,
        "message": f"Stage '{stage_name}' {'enabled' if enabled else 'disabled'} successfully"
    }


@app.put("/api/v1/pipeline/phase2-categories/{category_id}")
async def update_phase2_category(category_id: int, enabled: bool):
    """Enable or disable a Phase 2 category."""
    success = pipeline_config_service.update_phase2_category_enabled(category_id, enabled)
    if not success:
        raise HTTPException(status_code=404, detail="Phase 2 category not found")

    return {
        "category_id": category_id,
        "enabled": enabled,
        "message": f"Phase 2 category {'enabled' if enabled else 'disabled'} successfully"
    }


# Pipeline stage execution logs endpoints
from .services.pipeline_stage_logger import PipelineStageLogger

# Category validation endpoints
from .services.category_validation_engine import CategoryValidationEngine
validation_engine = CategoryValidationEngine()

# Categories endpoint - Must be before other {param} routes
@app.get("/api/v1/pipeline/request-categories/{request_id}")
async def get_request_categories_for_pipeline(request_id: str):
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
                SELECT id, category_name, category_id
                FROM category_results
                WHERE request_id = $1::uuid
                ORDER BY category_id ASC
                """,
                request_id
            )

            categories = []
            for row in rows:
                categories.append({
                    "category_result_id": str(row['id']),
                    "category_name": row['category_name'],
                    "category_id": row['category_id']
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


@app.get("/api/v1/pipeline/executions/{request_id}")
async def get_pipeline_executions(request_id: str):
    """Get all pipeline stage executions for a request."""
    logs = await PipelineStageLogger.get_stage_logs_for_request(request_id)
    return {
        "request_id": request_id,
        "total_stages": len(logs),
        "executed_count": len([log for log in logs if log["executed"]]),
        "skipped_count": len([log for log in logs if log["skipped"]]),
        "logs": logs
    }


@app.get("/api/v1/pipeline/executions/category/{category_result_id}")
async def get_category_pipeline_executions(category_result_id: str):
    """Get all pipeline stage executions for a category result."""
    logs = await PipelineStageLogger.get_stage_logs_for_category(category_result_id)
    return {
        "category_result_id": category_result_id,
        "total_stages": len(logs),
        "executed_count": len([log for log in logs if log["executed"]]),
        "skipped_count": len([log for log in logs if log["skipped"]]),
        "logs": logs
    }


@app.get("/api/v1/pipeline/api-calls/{request_id}")
async def get_api_calls_for_request(request_id: str):
    """Get all API calls/usage logs for a request (Stage 1: Data Collection)."""
    logger.info(f"Fetching API calls for request_id: {request_id}")
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='cognito-engine'
        )

        try:
            # Query with all columns including category_name, prompt_text, response_data
            rows = await conn.fetch(
                """
                SELECT
                    id, request_id, category_result_id,
                    api_provider, endpoint, request_payload,
                    response_status, response_time_ms,
                    token_count, cost_per_token, total_cost,
                    timestamp, error_message, rate_limit_remaining,
                    correlation_id, category_name, prompt_text, response_data
                FROM api_usage_logs
                WHERE request_id = $1::uuid
                ORDER BY timestamp ASC
                """,
                request_id
            )

            logger.info(f"Found {len(rows)} API calls for request {request_id}")

            api_calls = []
            for row in rows:
                api_calls.append({
                    "id": str(row['id']),
                    "request_id": str(row['request_id']),
                    "category_result_id": str(row['category_result_id']) if row['category_result_id'] else None,
                    "provider": row['api_provider'],
                    "endpoint": row['endpoint'],
                    "category_name": row['category_name'],
                    "prompt_text": row['prompt_text'],
                    "request_payload": row['request_payload'],
                    "response_data": row['response_data'],
                    "response_status": row['response_status'],
                    "response_time_ms": row['response_time_ms'],
                    "token_count": row['token_count'],
                    "cost_per_token": row['cost_per_token'],
                    "total_cost": row['total_cost'],
                    "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None,
                    "error_message": row['error_message'],
                    "rate_limit_remaining": row['rate_limit_remaining'],
                    "correlation_id": row['correlation_id']
                })

            return {
                "request_id": request_id,
                "total_calls": len(api_calls),
                "total_cost": sum(call['total_cost'] for call in api_calls),
                "total_tokens": sum(call['token_count'] for call in api_calls),
                "providers_used": list(set(call['provider'] for call in api_calls)),
                "api_calls": api_calls
            }

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Failed to get API calls: {str(e)}")
        return {
            "request_id": request_id,
            "total_calls": 0,
            "total_cost": 0.0,
            "total_tokens": 0,
            "providers_used": [],
            "api_calls": []
        }


# Dashboard data endpoint
@app.get("/api/v1/dashboard")
async def get_dashboard_data():
    """Get dashboard statistics."""
    all_requests = request_service.get_all_requests()
    all_pipelines = pipeline_service.get_all_pipelines()
    all_analyses = analysis_service.get_all_analyses()

    return {
        "totalRequests": len(all_requests),
        "completedRequests": len([r for r in all_requests if r["status"] == "completed"]),
        "processingRequests": len([r for r in all_requests if r["status"] == "processing"]),
        "failedRequests": len([r for r in all_requests if r["status"] == "failed"]),
        "activePipelines": len([p for p in all_pipelines if p["status"] == "running"]),
        "completedAnalyses": len([a for a in all_analyses if a["status"] == "completed"]),
        "averageProcessingTime": 300,  # Calculate from actual data
        "successRate": 92  # Calculate from actual data
    }


# Category Validation Management Endpoints
@app.get("/api/v1/validation/schemas")
async def get_validation_schemas():
    """Get all validation schemas"""
    conn = await validation_engine._get_connection()
    try:
        rows = await conn.fetch("""
            SELECT id, category_id, category_name, version, enabled, created_at, updated_at
            FROM category_validation_schemas
            ORDER BY category_id
        """)

        schemas = []
        for row in rows:
            schemas.append({
                'id': str(row['id']),
                'category_id': row['category_id'],
                'category_name': row['category_name'],
                'version': row['version'],
                'enabled': row['enabled'],
                'created_at': row['created_at'].isoformat(),
                'updated_at': row['updated_at'].isoformat()
            })

        return {
            'schemas': schemas,
            'total': len(schemas)
        }
    finally:
        await conn.close()


@app.get("/api/v1/validation/schemas/{category_id}")
async def get_validation_schema(category_id: int):
    """Get validation schema for a specific category"""
    schema = await validation_engine.get_validation_schema(category_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Validation schema not found")
    return schema


@app.get("/api/v1/validation/results/{category_result_id}")
async def get_validation_results(category_result_id: str):
    """Get validation results for a category result"""
    results = await validation_engine.get_validation_results(category_result_id)
    return {
        'category_result_id': category_result_id,
        'results': results,
        'total': len(results)
    }


@app.put("/api/v1/validation/schemas/{schema_id}")
async def update_validation_schema(schema_id: str, updates: Dict[str, Any]):
    """Update validation schema configuration"""
    conn = await validation_engine._get_connection()
    try:
        # Update schema
        await conn.execute("""
            UPDATE category_validation_schemas
            SET validation_config = $1,
                enabled = $2,
                updated_at = NOW()
            WHERE id = $3
        """, updates.get('validation_config', {}), updates.get('enabled', True), schema_id)

        # Fetch updated schema
        row = await conn.fetchrow("""
            SELECT id, category_id, category_name, version, validation_config, enabled
            FROM category_validation_schemas
            WHERE id = $1
        """, schema_id)

        if not row:
            raise HTTPException(status_code=404, detail="Schema not found")

        return {
            'id': str(row['id']),
            'category_id': row['category_id'],
            'category_name': row['category_name'],
            'version': row['version'],
            'config': row['validation_config'],
            'enabled': row['enabled'],
            'message': 'Schema updated successfully'
        }
    finally:
        await conn.close()


@app.post("/api/v1/validation/schemas/{schema_id}/toggle")
async def toggle_validation_schema(schema_id: str):
    """Enable/disable a validation schema"""
    conn = await validation_engine._get_connection()
    try:
        # Toggle enabled status
        row = await conn.fetchrow("""
            UPDATE category_validation_schemas
            SET enabled = NOT enabled,
                updated_at = NOW()
            WHERE id = $1
            RETURNING id, enabled
        """, schema_id)

        if not row:
            raise HTTPException(status_code=404, detail="Schema not found")

        return {
            'id': str(row['id']),
            'enabled': row['enabled'],
            'message': f"Schema {'enabled' if row['enabled'] else 'disabled'} successfully"
        }
    finally:
        await conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main_refactored:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
