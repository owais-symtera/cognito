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

# Import services
from src.services.auth_service import AuthService
from src.services.provider_service import ProviderService
from src.services.request_service import RequestService
from src.services.pipeline_service import PipelineService
from src.services.analysis_service import AnalysisService
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(
    title="CognitoAI Drug Intelligence API",
    description="API for drug intelligence gathering and analysis",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
auth_service = AuthService()
provider_service = ProviderService()
request_service = RequestService(provider_service)
pipeline_service = PipelineService()
analysis_service = AnalysisService()


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

    token = auth_service.create_session(user)
    return {
        "user": user,
        "accessToken": token,
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


# Request endpoints
@app.get("/api/v1/requests")
async def get_requests():
    """Get all requests."""
    return request_service.get_all_requests()


@app.get("/api/v1/requests/{request_id}")
async def get_request(request_id: str):
    """Get specific request."""
    request = request_service.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request


@app.post("/api/v1/requests")
async def create_request(request_data: DrugRequest):
    """Create new drug analysis request."""
    return request_service.create_request(
        request_data.requestId,
        request_data.drugName,
        request_data.webhookUrl
    )


@app.post("/api/v1/requests/{request_id}/process")
async def process_request(request_id: str, background_tasks: BackgroundTasks):
    """Start processing a request."""
    request = request_service.get_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Create pipeline
    pipeline = pipeline_service.create_pipeline(
        request_id,
        request["drugName"]
    )

    # Create analysis record
    analysis = analysis_service.create_analysis(
        request_id,
        request["drugName"]
    )

    # Process in background
    async def process_async():
        try:
            # Update request status
            request_service.update_request(request_id, {
                "status": "processing",
                "progressPercentage": 10
            })

            # Stage 1: Data Collection
            pipeline_service.update_pipeline_step(pipeline["id"], 0, "running", 25)

            # Call providers
            api_responses = await provider_service.call_enabled_providers(request["drugName"])

            pipeline_service.update_pipeline_step(pipeline["id"], 0, "completed", 100)
            request_service.update_request(request_id, {"progressPercentage": 30})

            # Stages 2-6 (simplified for now)
            stages = [
                {"index": 1, "name": "Source Verification", "progress": 40},
                {"index": 2, "name": "Data Merging", "progress": 55},
                {"index": 3, "name": "Quality Analysis", "progress": 70},
                {"index": 4, "name": "Regulatory Check", "progress": 85},
                {"index": 5, "name": "Final Processing", "progress": 100}
            ]

            for stage in stages:
                await asyncio.sleep(2)
                pipeline_service.update_pipeline_step(
                    pipeline["id"],
                    stage["index"],
                    "completed",
                    100
                )
                request_service.update_request(request_id, {
                    "progressPercentage": stage["progress"]
                })

            # Complete analysis
            analysis_service.complete_analysis(
                analysis["id"],
                overall_score=92,
                confidence_level=95,
                risk_assessment="low",
                processing_duration=300
            )

            # Complete request
            request_service.update_request(request_id, {
                "status": "completed",
                "progressPercentage": 100,
                "completedAt": datetime.now().isoformat()
            })

            # Complete pipeline
            pipeline_service.update_pipeline_status(pipeline["id"], "completed")

            # Send webhook if configured
            if request.get("webhookUrl"):
                await send_webhook(
                    request["webhookUrl"],
                    {
                        "requestId": request_id,
                        "status": "completed",
                        "drugName": request["drugName"],
                        "apiResponses": api_responses
                    }
                )

        except Exception as e:
            print(f"Error processing request {request_id}: {e}")
            request_service.update_request(request_id, {
                "status": "failed",
                "progressPercentage": 0
            })
            pipeline_service.update_pipeline_status(pipeline["id"], "failed")

    background_tasks.add_task(process_async)

    return {
        "message": "Processing started",
        "requestId": request_id,
        "drugName": request["drugName"],
        "status": "processing"
    }


# Pipeline endpoints
@app.get("/api/v1/pipelines")
async def get_pipelines():
    """Get all pipelines."""
    return pipeline_service.get_all_pipelines()


@app.get("/api/v1/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """Get specific pipeline."""
    pipeline = pipeline_service.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


# Analysis endpoints
@app.get("/api/v1/analyses")
async def get_analyses():
    """Get all analyses."""
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main_clean:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )