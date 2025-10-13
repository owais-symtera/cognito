# Backend Architecture

### FastAPI Application Structure

#### Application Layout
```python
# apps/backend/src/main.py - FastAPI Application Entry Point
from fastapi import FastAPI, Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await database.connect()
    await redis.ping()
    celery_app.control.purge()  # Clean old tasks

    yield

    # Shutdown
    await database.disconnect()
    await redis.close()

app = FastAPI(
    title="CognitoAI Engine API",
    description="Pharmaceutical Intelligence Processing API with Source Tracking",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])  # Configure for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include routers
app.include_router(requests_router, prefix="/api/v1", tags=["requests"])
app.include_router(categories_router, prefix="/api/v1", tags=["categories"])
app.include_router(sources_router, prefix="/api/v1", tags=["sources"])
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(websocket_router, prefix="/api/v1", tags=["websockets"])
```

#### Directory Structure
```
apps/backend/
├── src/
│   ├── main.py                    # FastAPI application entry
│   ├── core/                      # Core business logic
│   │   ├── processor.py          # Main category processor
│   │   ├── conflict_resolver.py  # Source conflict resolution
│   │   ├── source_verifier.py    # Source verification logic
│   │   └── audit_logger.py       # Comprehensive audit trail
│   ├── integrations/             # External API integrations
│   │   ├── api_manager.py        # Multi-API coordination
│   │   ├── providers/            # Individual API clients
│   │   │   ├── chatgpt.py       # ChatGPT integration
│   │   │   ├── perplexity.py    # Perplexity integration
│   │   │   ├── grok.py          # Grok integration
│   │   │   ├── gemini.py        # Gemini integration
│   │   │   └── tavily.py        # Tavily integration
│   │   └── rate_limiter.py       # Rate limiting coordination
│   ├── database/                 # Database layer
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── repositories/        # Repository pattern
│   │   │   ├── request_repo.py  # Drug request operations
│   │   │   ├── source_repo.py   # Source management
│   │   │   └── audit_repo.py    # Audit trail operations
│   │   ├── migrations/          # Alembic migrations
│   │   └── connection.py        # Database connection
│   ├── api/                     # API routes
│   │   ├── v1/
│   │   │   ├── requests.py      # Drug request endpoints
│   │   │   ├── categories.py    # Category management
│   │   │   ├── sources.py       # Source operations
│   │   │   └── auth.py          # Authentication
│   │   └── websockets/
│   │       └── updates.py       # Real-time updates
│   ├── schemas/                 # Pydantic schemas
│   │   ├── requests.py          # Request/response schemas
│   │   ├── sources.py           # Source schemas
│   │   └── categories.py        # Category schemas
│   ├── background/              # Background processing
│   │   ├── celery_app.py       # Celery configuration
│   │   ├── tasks.py            # Celery tasks
│   │   └── scheduler.py        # Periodic tasks
│   ├── config/                  # Configuration
│   │   ├── settings.py         # Application settings
│   │   ├── database.py         # Database configuration
│   │   └── redis.py            # Redis configuration
│   └── utils/                   # Utility functions
│       ├── logging.py          # Structured logging
│       ├── exceptions.py       # Custom exceptions
│       └── validators.py       # Custom validators
├── tests/                       # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── fixtures/               # Test fixtures
├── alembic/                    # Database migrations
├── requirements.txt            # Python dependencies
└── Dockerfile                  # Container configuration (optional)
```

### Core Processing Architecture

#### Dynamic Category Processor Implementation
```python
# apps/backend/src/core/processor.py
class SourceAwareCategoryProcessor:
    """
    Central processor handling all 17 pharmaceutical categories dynamically
    with comprehensive source tracking and regulatory compliance
    """

    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        api_manager: MultiAPIManager,
        audit_logger: AuditLogger
    ):
        self.db = db
        self.redis = redis
        self.api_manager = api_manager
        self.audit_logger = audit_logger
        self.conflict_resolver = SourceConflictResolver()
        self.source_verifier = SourceVerifier()

    async def process_drug_request(self, drug_name: str, request_id: str) -> ProcessingResult:
        """
        Main processing pipeline for pharmaceutical intelligence gathering
        """
        async with self.db.begin():
            # Load category configurations from database
            categories = await self._load_category_configs()

            # Create processing context
            context = ProcessingContext(
                drug_name=drug_name,
                request_id=request_id,
                categories=categories,
                start_time=datetime.utcnow()
            )

            # Log processing start
            await self.audit_logger.log_processing_start(context)

            try:
                # Process categories in parallel with controlled concurrency
                semaphore = asyncio.Semaphore(3)  # Limit concurrent API calls
                tasks = [
                    self._process_category_with_semaphore(semaphore, category, context)
                    for category in categories
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Consolidate results and handle exceptions
                successful_results = []
                failed_categories = []

                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        failed_categories.append(categories[i]['name'])
                        await self.audit_logger.log_category_error(
                            context, categories[i], result
                        )
                    else:
                        successful_results.append(result)

                # Update request status
                await self._update_request_completion(
                    request_id, successful_results, failed_categories
                )

                return ProcessingResult(
                    request_id=request_id,
                    successful_categories=len(successful_results),
                    failed_categories=failed_categories,
                    total_sources=sum(len(r.sources) for r in successful_results),
                    processing_time=datetime.utcnow() - context.start_time
                )

            except Exception as e:
                await self.audit_logger.log_processing_error(context, e)
                raise ProcessingException(f"Critical processing failure: {str(e)}")

    async def _process_category_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        category: Dict,
        context: ProcessingContext
    ) -> CategoryResult:
        """Process single category with concurrency control"""
        async with semaphore:
            return await self._process_single_category(category, context)

    async def _process_single_category(
        self,
        category: Dict,
        context: ProcessingContext
    ) -> CategoryResult:
        """
        Process individual pharmaceutical category with full source tracking
        """
        category_start_time = datetime.utcnow()

        try:
            # Load category-specific configuration and prompts
            config = await self._load_category_config(category['id'])
            prompts = await self._build_category_prompts(category, context.drug_name, config)

            # Execute searches across all API providers
            search_results = await self.api_manager.search_all_providers(
                query=prompts['search_query'],
                category=category['name'],
                config=config
            )

            # Process and validate sources
            processed_sources = await self._process_raw_sources(
                search_results, category, context
            )

            # Detect conflicts between sources
            conflicts = await self.conflict_resolver.detect_conflicts(processed_sources)

            # Resolve conflicts using configured strategies
            resolved_conflicts = []
            for conflict in conflicts:
                resolution = await self.conflict_resolver.resolve_conflict(conflict)
                resolved_conflicts.append(resolution)

            # Generate category summary with confidence scoring
            summary = await self._generate_category_summary(
                processed_sources, resolved_conflicts, category, config
            )

            # Calculate confidence and quality scores
            confidence_score = await self._calculate_confidence_score(
                processed_sources, resolved_conflicts
            )

            quality_score = await self._calculate_quality_score(processed_sources)

            # Store results in database
            category_result = await self._store_category_result(
                category, context, summary, processed_sources,
                conflicts, confidence_score, quality_score,
                category_start_time
            )

            # Broadcast real-time update
            await self._broadcast_category_completion(context.request_id, category_result)

            return category_result

        except Exception as e:
            await self.audit_logger.log_category_error(context, category, e)
            raise CategoryProcessingException(
                f"Failed to process category {category['name']}: {str(e)}"
            )

    async def _load_category_configs(self) -> List[Dict]:
        """Load all 17 pharmaceutical category configurations from database"""
        query = """
        SELECT id, name, description, search_parameters, processing_rules,
               prompt_templates, verification_criteria, conflict_resolution_strategy
        FROM pharmaceutical_categories
        WHERE active = true
        ORDER BY priority DESC
        """
        result = await self.db.execute(text(query))
        return [dict(row) for row in result.fetchall()]

    async def _build_category_prompts(
        self,
        category: Dict,
        drug_name: str,
        config: Dict
    ) -> Dict[str, str]:
        """Build dynamic prompts for pharmaceutical category processing"""
        base_template = config.get('prompt_template', DEFAULT_CATEGORY_TEMPLATE)

        prompts = {
            'search_query': base_template.format(
                drug_name=drug_name,
                category_name=category['name'],
                search_parameters=config.get('search_parameters', ''),
                specific_instructions=config.get('specific_instructions', '')
            ),
            'verification_prompt': config.get('verification_template', '').format(
                drug_name=drug_name,
                category_name=category['name']
            )
        }

        return prompts
```

### Database Architecture

#### Repository Pattern Implementation
```python
# apps/backend/src/database/repositories/request_repo.py
class DrugRequestRepository:
    """
    Repository for drug request operations with comprehensive audit trail
    """

    def __init__(self, db: AsyncSession, audit_logger: AuditLogger):
        self.db = db
        self.audit_logger = audit_logger

    async def create_request(self, request_data: CreateDrugRequestSchema) -> DrugRequest:
        """Create new drug request with audit trail"""
        async with self.db.begin():
            # Create request entity
            request = DrugRequest(
                id=str(uuid4()),
                drug_name=request_data.drug_name,
                user_id=request_data.user_id,
                status=RequestStatus.PENDING,
                total_categories=17,
                completed_categories=0
            )

            self.db.add(request)
            await self.db.flush()  # Get ID before commit

            # Log creation in audit trail
            await self.audit_logger.log_entity_creation(
                entity_type="DrugRequest",
                entity_id=request.id,
                new_values=request.dict(),
                user_id=request_data.user_id
            )

            await self.db.commit()
            return request

    async def update_request_progress(
        self,
        request_id: str,
        completed_categories: int,
        failed_categories: List[str]
    ) -> DrugRequest:
        """Update request progress with audit trail"""
        async with self.db.begin():
            # Fetch current request
            query = select(DrugRequest).where(DrugRequest.id == request_id)
            result = await self.db.execute(query)
            request = result.scalar_one_or_none()

            if not request:
                raise RequestNotFoundException(f"Request {request_id} not found")

            # Store old values for audit
            old_values = {
                'completed_categories': request.completed_categories,
                'failed_categories': request.failed_categories,
                'status': request.status,
                'updated_at': request.updated_at
            }

            # Update request
            request.completed_categories = completed_categories
            request.failed_categories = failed_categories
            request.updated_at = datetime.utcnow()

            # Determine new status
            if completed_categories + len(failed_categories) >= request.total_categories:
                if len(failed_categories) == 0:
                    request.status = RequestStatus.COMPLETED
                    request.completed_at = datetime.utcnow()
                else:
                    request.status = RequestStatus.PARTIAL_FAILURE
                    request.completed_at = datetime.utcnow()

            # Store new values for audit
            new_values = {
                'completed_categories': request.completed_categories,
                'failed_categories': request.failed_categories,
                'status': request.status,
                'updated_at': request.updated_at,
                'completed_at': request.completed_at
            }

            # Log update in audit trail
            await self.audit_logger.log_entity_update(
                entity_type="DrugRequest",
                entity_id=request_id,
                old_values=old_values,
                new_values=new_values
            )

            await self.db.commit()
            return request

    async def get_request_with_sources(self, request_id: str) -> Optional[DrugRequestDetailResponse]:
        """Get request with all related sources and conflicts"""
        query = (
            select(DrugRequest)
            .options(
                selectinload(DrugRequest.categories).options(
                    selectinload(CategoryResult.sources),
                    selectinload(CategoryResult.conflicts)
                ),
                selectinload(DrugRequest.audit_trail)
            )
            .where(DrugRequest.id == request_id)
        )

        result = await self.db.execute(query)
        request = result.scalar_one_or_none()

        if not request:
            return None

        # Calculate sources summary
        all_sources = []
        all_conflicts = []
        for category in request.categories:
            all_sources.extend(category.sources)
            all_conflicts.extend(category.conflicts)

        sources_summary = SourcesSummary(
            total_sources=len(all_sources),
            verified_sources=len([s for s in all_sources if s.verification_status == 'verified']),
            conflicting_pairs=len(all_conflicts),
            api_breakdown={
                provider: len([s for s in all_sources if s.api_provider == provider])
                for provider in APIProvider
            }
        )

        return DrugRequestDetailResponse(
            **request.dict(),
            sources_summary=sources_summary
        )
```

### Background Processing Architecture

#### Celery Task Implementation
```python
# apps/backend/src/background/tasks.py
from celery import Celery
from celery.exceptions import Retry

celery_app = Celery(
    "cognito-ai-engine",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
    include=["src.background.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,  # Process one task at a time per worker
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_routes={
        'process_drug_request': {'queue': 'processing'},
        'verify_sources': {'queue': 'verification'},
        'cleanup_old_requests': {'queue': 'maintenance'}
    }
)

@celery_app.task(
    bind=True,
    autoretry_for=(APIException, DatabaseException),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    name='process_drug_request'
)
def process_drug_request_task(self, request_id: str, drug_name: str):
    """
    Background task for processing pharmaceutical intelligence requests
    """
    try:
        # Initialize database connection for task
        db_session = get_async_db_session()
        redis_client = get_redis_client()

        # Create processor instance
        processor = SourceAwareCategoryProcessor(
            db=db_session,
            redis=redis_client,
            api_manager=MultiAPIManager(),
            audit_logger=AuditLogger(db_session)
        )

        # Update task status
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Starting pharmaceutical intelligence processing'}
        )

        # Process the request
        result = asyncio.run(processor.process_drug_request(drug_name, request_id))

        return {
            'request_id': request_id,
            'status': 'completed',
            'successful_categories': result.successful_categories,
            'failed_categories': result.failed_categories,
            'total_sources': result.total_sources,
            'processing_time': result.processing_time.total_seconds()
        }

    except Exception as exc:
        # Log error for debugging
        logger.error(f"Processing failed for request {request_id}: {str(exc)}")

        # Update request status to failed
        asyncio.run(update_request_status(request_id, RequestStatus.FAILED, str(exc)))

        # Re-raise for Celery retry mechanism
        raise self.retry(exc=exc)

@celery_app.task(name='verify_sources_batch')
def verify_sources_batch(source_ids: List[str]):
    """
    Background verification of pharmaceutical sources
    """
    db_session = get_async_db_session()
    verifier = SourceVerifier(db_session)

    results = []
    for source_id in source_ids:
        try:
            result = asyncio.run(verifier.verify_source(source_id))
            results.append({
                'source_id': source_id,
                'status': 'verified',
                'verification_result': result.dict()
            })
        except Exception as e:
            results.append({
                'source_id': source_id,
                'status': 'failed',
                'error': str(e)
            })

    return results

@celery_app.task(name='cleanup_old_requests')
def cleanup_old_requests():
    """
    Periodic cleanup of old requests and audit data
    """
    db_session = get_async_db_session()

    # Clean up requests older than 1 year (keep audit trail for 7 years)
    cleanup_date = datetime.utcnow() - timedelta(days=365)

    cleanup_count = asyncio.run(
        cleanup_old_data(db_session, cleanup_date)
    )

    return {
        'cleanup_date': cleanup_date.isoformat(),
        'cleaned_records': cleanup_count
    }

# Periodic task scheduling
celery_app.conf.beat_schedule = {
    'cleanup-old-requests': {
        'task': 'cleanup_old_requests',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
```

### WebSocket Architecture

#### Real-time Update System
```python
# apps/backend/src/api/websockets/updates.py
class ConnectionManager:
    """
    Manages WebSocket connections for real-time pharmaceutical processing updates
    """

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis = get_redis_client()

    async def connect(self, websocket: WebSocket, request_id: str):
        """Connect client to request-specific update stream"""
        await websocket.accept()

        if request_id not in self.active_connections:
            self.active_connections[request_id] = []

        self.active_connections[request_id].append(websocket)

        # Send initial status
        await self._send_initial_status(websocket, request_id)

        # Subscribe to Redis updates for this request
        await self._subscribe_to_redis_updates(request_id)

    async def disconnect(self, websocket: WebSocket, request_id: str):
        """Disconnect client and cleanup"""
        if request_id in self.active_connections:
            self.active_connections[request_id].remove(websocket)

            # Clean up empty connection lists
            if not self.active_connections[request_id]:
                del self.active_connections[request_id]
                await self._unsubscribe_from_redis_updates(request_id)

    async def broadcast_update(self, request_id: str, update: Dict):
        """Broadcast update to all connected clients for this request"""
        if request_id in self.active_connections:
            disconnected = []

            for connection in self.active_connections[request_id]:
                try:
                    await connection.send_json(update)
                except ConnectionClosed:
                    disconnected.append(connection)
                except Exception as e:
                    logger.error(f"Error broadcasting to WebSocket: {str(e)}")
                    disconnected.append(connection)

            # Clean up disconnected clients
            for conn in disconnected:
                await self.disconnect(conn, request_id)

    async def _send_initial_status(self, websocket: WebSocket, request_id: str):
        """Send current request status to newly connected client"""
        db_session = get_async_db_session()
        request_repo = DrugRequestRepository(db_session, AuditLogger(db_session))

        request = await request_repo.get_request_with_sources(request_id)
        if request:
            await websocket.send_json({
                'type': 'initial_status',
                'data': request.dict()
            })

    async def _subscribe_to_redis_updates(self, request_id: str):
        """Subscribe to Redis pub/sub for request updates"""
        channel = f"updates:{request_id}"

        async def message_handler(message):
            update = json.loads(message['data'])
            await self.broadcast_update(request_id, update)

        await self.redis.subscribe(channel, message_handler)

# Global connection manager instance
connection_manager = ConnectionManager()

@websocket_router.websocket("/requests/{request_id}/updates")
async def request_updates_websocket(websocket: WebSocket, request_id: str):
    """
    WebSocket endpoint for real-time pharmaceutical processing updates
    """
    try:
        await connection_manager.connect(websocket, request_id)

        while True:
            # Keep connection alive and handle ping/pong
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send ping to check if connection is alive
                await websocket.ping()

    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, request_id)
    except Exception as e:
        logger.error(f"WebSocket error for request {request_id}: {str(e)}")
        await connection_manager.disconnect(websocket, request_id)

# Redis publisher for broadcasting updates
async def publish_processing_update(request_id: str, update_type: str, data: Dict):
    """Publish processing update to Redis for WebSocket broadcasting"""
    redis = get_redis_client()

    update = {
        'type': update_type,
        'timestamp': datetime.utcnow().isoformat(),
        'data': data
    }

    channel = f"updates:{request_id}"
    await redis.publish(channel, json.dumps(update))
```

**Rationale for Backend Architecture:**

1. **Complete Independence**: Backend can be developed and deployed separately using FastAPI
2. **Dynamic Processing**: Single processor handles all 17 pharmaceutical categories from database configuration
3. **Source-Centric Design**: Every operation includes comprehensive source tracking and audit trails
4. **Scalable Processing**: Celery background tasks with controlled concurrency for API rate limits
5. **Real-time Updates**: WebSocket architecture with Redis pub/sub for seamless frontend integration
6. **Regulatory Compliance**: Repository pattern with comprehensive audit logging for 7-year retention
7. **Error Resilience**: Comprehensive exception handling and retry mechanisms throughout
8. **API Integration**: Coordinated multi-API processing with rate limiting and response tracking
