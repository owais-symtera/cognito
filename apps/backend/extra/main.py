"""
CognitoAI Engine FastAPI Application Entry Point

This module serves as the main entry point for the CognitoAI Engine API,
providing pharmaceutical intelligence processing with comprehensive source tracking
and regulatory compliance for the pharmaceutical industry.

The application implements:
- Multi-API integration for comprehensive pharmaceutical data gathering
- Real-time processing updates via WebSocket connections
- Comprehensive audit trails for regulatory compliance
- Source-aware processing with conflict resolution
- Database-driven dynamic configuration

Version: 1.0.0
Author: CognitoAI Development Team
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .api.v1 import categories, analysis, status, health, diagnostics
# Import new API endpoints
try:
    from .api.v1 import collection_status, pipeline, hierarchical_search, temperature_search
    ADVANCED_FEATURES = True
except ImportError:
    ADVANCED_FEATURES = False
    print("⚠️  Some advanced features not available")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown tasks.

    Handles:
    - Database connection initialization
    - Redis connection setup
    - Background task worker initialization
    - Cleanup on shutdown

    Args:
        app: FastAPI application instance

    Yields:
        None during application lifecycle

    Since:
        Version 1.0.0
    """
    # Startup tasks
    print("🚀 CognitoAI Engine starting up...")
    print("📊 Initializing pharmaceutical intelligence platform...")

    yield

    # Shutdown tasks
    print("📊 CognitoAI Engine shutting down...")
    print("🔒 Pharmaceutical data processing completed")


# FastAPI Application Instance
app = FastAPI(
    title="CognitoAI Engine API",
    description="Pharmaceutical Intelligence Processing API with Source Tracking",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
    contact={
        "name": "CognitoAI Support",
        "email": "support@cognito-ai.com",
    },
    license_info={
        "name": "Proprietary",
    },
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend development server
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted Host Middleware for security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.cognito-ai.com"]
)


@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint providing API information.

    Returns basic information about the CognitoAI Engine API
    including version, status, and available endpoints.

    Returns:
        Dict containing API metadata and status

    Example:
        ```python
        response = await client.get("/")
        print(response["message"])  # "CognitoAI Engine API v1.0.0"
        ```

    Since:
        Version 1.0.0
    """
    return {
        "message": "CognitoAI Engine API v1.0.0",
        "description": "Pharmaceutical Intelligence Processing with Source Tracking",
        "status": "operational",
        "docs": "/api/docs",
        "health": "/health",
        "pharmaceutical_categories": 17,
        "compliance": "pharmaceutical_regulatory"
    }


# Include API routers
app.include_router(
    categories.router,
    prefix="/api/v1",
    tags=["categories"]
)

app.include_router(
    analysis.router,
    prefix="/api/v1",
    tags=["analysis"]
)

app.include_router(
    status.router,
    prefix="/api/v1",
    tags=["status"]
)

app.include_router(
    health.router,
    prefix="",
    tags=["health"]
)

app.include_router(
    diagnostics.router,
    prefix="/api/v1",
    tags=["diagnostics"]
)

# Include advanced feature routers if available
if ADVANCED_FEATURES:
    if 'collection_status' in locals():
        app.include_router(
            collection_status.router,
            prefix="/api/v1",
            tags=["collection_monitoring"]
        )

    if 'pipeline' in locals():
        app.include_router(
            pipeline.router,
            prefix="/api/v1",
            tags=["pipeline"]
        )

    if 'hierarchical_search' in locals():
        app.include_router(
            hierarchical_search.router,
            prefix="/api/v1",
            tags=["hierarchical"]
        )

    if 'temperature_search' in locals():
        app.include_router(
            temperature_search.router,
            prefix="/api/v1",
            tags=["temperature"]
        )

    print("✅ Advanced features loaded: Collection Monitoring, Pipeline, Hierarchical Search, Temperature Variation")




if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )