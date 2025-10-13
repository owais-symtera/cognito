# CognitoAI-Engine Fullstack Architecture Document

## Introduction

This document outlines the complete fullstack architecture for CognitoAI-Engine, including backend systems, frontend implementation, and their integration. It serves as the single source of truth for AI-driven development, ensuring consistency across the entire technology stack.

This unified approach combines what would traditionally be separate backend and frontend architecture documents, streamlining the development process for modern fullstack applications where these concerns are increasingly intertwined.

### Starter Template or Existing Project

N/A - Greenfield project with custom pharmaceutical intelligence requirements.

## Tech Stack

### Backend Stack
- **Runtime**: Python 3.11+ with asyncio for high-performance concurrent processing
- **Web Framework**: FastAPI 0.104+ for modern async API development with automatic OpenAPI documentation
- **Database**: PostgreSQL 15+ with JSONB support for dynamic pharmaceutical category configurations
- **Caching**: Redis 7.0+ for session management and Celery job queues
- **Background Processing**: Celery 5.3+ with Redis broker for long-running pharmaceutical data processing
- **ORM**: SQLAlchemy 2.0+ with asyncpg driver for async database operations
- **Validation**: Pydantic 2.0+ for comprehensive data validation and serialization

### Frontend Stack
- **Framework**: Next.js 14.0+ with App Router for modern React development
- **Language**: TypeScript 5.3+ for type safety across pharmaceutical data structures
- **UI Framework**: shadcn/ui with Radix primitives for accessible pharmaceutical compliance interfaces
- **Styling**: Tailwind CSS 3.3+ for rapid UI development
- **State Management**: Zustand 4.4+ for lightweight state management
- **API Integration**: TanStack Query 5.0+ for server state synchronization and caching
- **Forms**: React Hook Form 7.45+ with Zod validation for pharmaceutical data entry

### Development & Deployment
- **Package Management**: npm/pnpm for frontend, pip with virtual environments for backend
- **Process Management**: systemd for production service management (no containerization as requested)
- **Reverse Proxy**: Nginx for static file serving and API proxy
- **Monitoring**: Built-in logging with structured pharmaceutical compliance audit trails
- **Build System**: Turborepo for monorepo build optimization

### External Integrations
- **AI APIs**: ChatGPT, Perplexity, Grok, Gemini, Tavily for multi-source pharmaceutical intelligence
- **Authentication**: JWT-based authentication with refresh token rotation
- **File Storage**: Local filesystem with structured pharmaceutical document organization

## Data Models

### Core Entities

#### Drug Request Entity
```python
# Backend: Pydantic/SQLAlchemy Model
class DrugRequest(Base):
    __tablename__ = "drug_requests"

    id: str = Field(primary_key=True, default_factory=lambda: str(uuid4()))
    drug_name: str = Field(..., min_length=1, max_length=255)
    status: RequestStatus = Field(default=RequestStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    user_id: Optional[str] = Field(foreign_key="users.id")

    # Processing metadata
    total_categories: int = Field(default=17)
    completed_categories: int = Field(default=0)
    failed_categories: List[str] = Field(default_factory=list)

    # Relationships
    categories: List["CategoryResult"] = Relationship(back_populates="request")
    audit_trail: List["AuditEvent"] = Relationship(back_populates="request")
```

```typescript
// Frontend: TypeScript Interface
interface DrugRequest {
  id: string;
  drugName: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
  userId?: string;
  totalCategories: number;
  completedCategories: number;
  failedCategories: string[];
  categories?: CategoryResult[];
}
```

#### Category Result Entity with Source Tracking
```python
# Backend: Comprehensive Source Tracking
class CategoryResult(Base):
    __tablename__ = "category_results"

    id: str = Field(primary_key=True, default_factory=lambda: str(uuid4()))
    request_id: str = Field(foreign_key="drug_requests.id")
    category_name: str = Field(..., max_length=100)
    category_id: int = Field(...)

    # Result data
    summary: str = Field(...)
    confidence_score: float = Field(ge=0.0, le=1.0)
    data_quality_score: float = Field(ge=0.0, le=1.0)

    # Processing metadata
    status: CategoryStatus = Field(default=CategoryStatus.PENDING)
    processing_time_ms: int = Field(default=0)
    retry_count: int = Field(default=0)
    error_message: Optional[str] = None

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Source tracking relationships
    sources: List["SourceReference"] = Relationship(back_populates="category_result")
    conflicts: List["SourceConflict"] = Relationship(back_populates="category_result")

    # Relationships
    request: DrugRequest = Relationship(back_populates="categories")
```

```typescript
// Frontend: Category Result Interface
interface CategoryResult {
  id: string;
  requestId: string;
  categoryName: string;
  categoryId: number;
  summary: string;
  confidenceScore: number;
  dataQualityScore: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  processingTimeMs: number;
  retryCount: number;
  errorMessage?: string;
  startedAt: string;
  completedAt?: string;
  sources: SourceReference[];
  conflicts: SourceConflict[];
}
```

#### Source Reference Entity
```python
# Backend: Detailed Source Tracking
class SourceReference(Base):
    __tablename__ = "source_references"

    id: str = Field(primary_key=True, default_factory=lambda: str(uuid4()))
    category_result_id: str = Field(foreign_key="category_results.id")

    # Source identification
    api_provider: APIProvider = Field(...)  # ChatGPT, Perplexity, Grok, Gemini, Tavily
    source_url: Optional[str] = Field(max_length=2048)
    source_title: Optional[str] = Field(max_length=500)
    source_type: SourceType = Field(...)  # research_paper, clinical_trial, news, regulatory

    # Content tracking
    content_snippet: str = Field(..., max_length=2000)
    relevance_score: float = Field(ge=0.0, le=1.0)
    credibility_score: float = Field(ge=0.0, le=1.0)

    # Publication metadata
    published_date: Optional[date] = None
    authors: Optional[str] = Field(max_length=1000)
    journal_name: Optional[str] = Field(max_length=300)
    doi: Optional[str] = Field(max_length=100)

    # Processing metadata
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    api_response_id: Optional[str] = None  # Original API response reference

    # Audit trail
    verification_status: VerificationStatus = Field(default=VerificationStatus.PENDING)
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None

    # Relationships
    category_result: CategoryResult = Relationship(back_populates="sources")
    conflicts: List["SourceConflict"] = Relationship(back_populates="source_a")
```

```typescript
// Frontend: Source Reference Interface
interface SourceReference {
  id: string;
  categoryResultId: string;
  apiProvider: 'chatgpt' | 'perplexity' | 'grok' | 'gemini' | 'tavily';
  sourceUrl?: string;
  sourceTitle?: string;
  sourceType: 'research_paper' | 'clinical_trial' | 'news' | 'regulatory' | 'other';
  contentSnippet: string;
  relevanceScore: number;
  credibilityScore: number;
  publishedDate?: string;
  authors?: string;
  journalName?: string;
  doi?: string;
  extractedAt: string;
  apiResponseId?: string;
  verificationStatus: 'pending' | 'verified' | 'disputed' | 'invalid';
  verifiedAt?: string;
  verifiedBy?: string;
}
```

#### Source Conflict Resolution Entity
```python
# Backend: Conflict Tracking and Resolution
class SourceConflict(Base):
    __tablename__ = "source_conflicts"

    id: str = Field(primary_key=True, default_factory=lambda: str(uuid4()))
    category_result_id: str = Field(foreign_key="category_results.id")

    # Conflicting sources
    source_a_id: str = Field(foreign_key="source_references.id")
    source_b_id: str = Field(foreign_key="source_references.id")

    # Conflict details
    conflict_type: ConflictType = Field(...)  # factual, temporal, methodological
    conflict_description: str = Field(..., max_length=1000)
    severity: ConflictSeverity = Field(...)  # low, medium, high, critical

    # Resolution
    resolution_strategy: ResolutionStrategy = Field(...)
    resolved_value: Optional[str] = Field(max_length=2000)
    resolution_confidence: float = Field(ge=0.0, le=1.0)
    resolution_rationale: str = Field(..., max_length=1500)

    # Metadata
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None  # system or user ID

    # Relationships
    category_result: CategoryResult = Relationship(back_populates="conflicts")
    source_a: SourceReference = Relationship(foreign_key="source_a_id")
    source_b: SourceReference = Relationship(foreign_key="source_b_id")
```

#### Audit Trail Entity
```python
# Backend: Comprehensive Audit Trail for Regulatory Compliance
class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: str = Field(primary_key=True, default_factory=lambda: str(uuid4()))
    request_id: str = Field(foreign_key="drug_requests.id")

    # Event details
    event_type: AuditEventType = Field(...)
    event_description: str = Field(..., max_length=1000)
    entity_type: str = Field(...)  # DrugRequest, CategoryResult, SourceReference
    entity_id: str = Field(...)

    # Changes tracking
    old_values: Optional[Dict] = Field(default=None)  # JSON field
    new_values: Optional[Dict] = Field(default=None)  # JSON field

    # Context
    user_id: Optional[str] = None
    ip_address: Optional[str] = Field(max_length=45)
    user_agent: Optional[str] = Field(max_length=500)
    api_endpoint: Optional[str] = Field(max_length=200)

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(...)  # For tracing across services

    # Relationships
    request: DrugRequest = Relationship(back_populates="audit_trail")
```

### API Specification

#### Core Endpoints

##### Drug Request Management
```python
# Backend: FastAPI Endpoints
@router.post("/api/v1/requests", response_model=DrugRequestResponse)
async def create_drug_request(
    request: CreateDrugRequestSchema,
    db: AsyncSession = Depends(get_db)
) -> DrugRequestResponse:
    """
    Create new drug intelligence request
    - Initiates processing for all 17 categories
    - Returns request ID for status tracking
    - Triggers background processing via Celery
    """

@router.get("/api/v1/requests/{request_id}", response_model=DrugRequestDetailResponse)
async def get_drug_request(
    request_id: str,
    db: AsyncSession = Depends(get_db)
) -> DrugRequestDetailResponse:
    """
    Get detailed request status with all category results
    - Includes source references and conflict resolutions
    - Real-time processing status
    - Comprehensive audit trail
    """

@router.get("/api/v1/requests", response_model=List[DrugRequestResponse])
async def list_drug_requests(
    skip: int = 0,
    limit: int = 50,
    status: Optional[RequestStatus] = None,
    db: AsyncSession = Depends(get_db)
) -> List[DrugRequestResponse]:
    """List drug requests with filtering and pagination"""
```

```typescript
// Frontend: API Client Types
interface CreateDrugRequestSchema {
  drugName: string;
  userId?: string;
  priorityCategories?: number[];  // Optional category prioritization
}

interface DrugRequestResponse {
  id: string;
  drugName: string;
  status: RequestStatus;
  progress: {
    totalCategories: number;
    completedCategories: number;
    failedCategories: string[];
    estimatedCompletion?: string;
  };
  createdAt: string;
  updatedAt: string;
}

interface DrugRequestDetailResponse extends DrugRequestResponse {
  categories: CategoryResult[];
  auditTrail: AuditEvent[];
  sourcesSummary: {
    totalSources: number;
    verifiedSources: number;
    conflictingPairs: number;
    apiBreakdown: Record<APIProvider, number>;
  };
}
```

##### Real-time Updates
```python
# Backend: WebSocket Support
@router.websocket("/api/v1/requests/{request_id}/updates")
async def request_updates(
    websocket: WebSocket,
    request_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Real-time updates for drug request processing
    - Category completion notifications
    - Source discovery events
    - Conflict detection alerts
    - Processing error notifications
    """
```

##### Source Management
```python
# Backend: Source-specific Endpoints
@router.get("/api/v1/requests/{request_id}/sources", response_model=SourceAnalysisResponse)
async def get_request_sources(
    request_id: str,
    include_conflicts: bool = True,
    group_by_category: bool = False,
    db: AsyncSession = Depends(get_db)
) -> SourceAnalysisResponse:
    """
    Comprehensive source analysis for a request
    - All sources with credibility scores
    - Conflict identification and resolution
    - Source verification status
    - API provider performance metrics
    """

@router.post("/api/v1/sources/{source_id}/verify", response_model=SourceVerificationResponse)
async def verify_source(
    source_id: str,
    verification: SourceVerificationSchema,
    db: AsyncSession = Depends(get_db)
) -> SourceVerificationResponse:
    """Manual source verification for regulatory compliance"""
```

### Data Validation and Serialization

#### Pydantic Schemas for Backend
```python
# Backend: Request/Response Schemas
class CreateDrugRequestSchema(BaseModel):
    drug_name: str = Field(..., min_length=1, max_length=255)
    user_id: Optional[str] = None
    priority_categories: Optional[List[int]] = Field(default=None, max_items=17)

    @validator('drug_name')
    def validate_drug_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9\s\-_.()]+$', v):
            raise ValueError('Drug name contains invalid characters')
        return v.strip()

class SourceAnalysisResponse(BaseModel):
    total_sources: int
    sources_by_category: Dict[str, int]
    api_provider_breakdown: Dict[APIProvider, int]
    credibility_distribution: Dict[str, int]  # high, medium, low
    conflicts: List[SourceConflictSummary]
    verification_status: Dict[VerificationStatus, int]

class SourceConflictSummary(BaseModel):
    id: str
    category_name: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    sources_involved: List[SourceReference]
    resolution_status: str
    resolution_confidence: Optional[float]
```

#### Frontend State Management Types
```typescript
// Frontend: Zustand Store Interfaces
interface DrugRequestStore {
  // State
  requests: DrugRequest[];
  currentRequest: DrugRequest | null;
  loading: boolean;
  error: string | null;

  // Actions
  createRequest: (drugName: string) => Promise<void>;
  fetchRequest: (requestId: string) => Promise<void>;
  subscribeToUpdates: (requestId: string) => void;
  unsubscribeFromUpdates: () => void;

  // Source management
  fetchSources: (requestId: string) => Promise<void>;
  verifySource: (sourceId: string, verification: SourceVerification) => Promise<void>;
}

interface SourceStore {
  sources: Record<string, SourceReference[]>; // keyed by request ID
  conflicts: Record<string, SourceConflict[]>;
  loading: boolean;

  // Analysis
  getSourcesByCategory: (requestId: string, category: string) => SourceReference[];
  getConflictingSources: (requestId: string) => SourceConflict[];
  getSourceCredibilityStats: (requestId: string) => CredibilityStats;
}
```

**Rationale for Data Models Design:**

1. **Source-Centric Architecture**: Every piece of information is traceable to its source with comprehensive metadata for regulatory compliance
2. **Conflict Resolution System**: Built-in conflict detection and resolution for handling contradictory information from multiple APIs
3. **Audit Trail Compliance**: 7-year audit trail capability with complete change tracking for pharmaceutical regulatory requirements
4. **Real-time Processing**: WebSocket integration for live updates during long-running processing tasks
5. **Frontend/Backend Separation**: Clear interface contracts allowing independent team development
6. **Scalable Design**: Database-driven category processing supports dynamic addition of new pharmaceutical categories

## Components

### Backend Components

#### Core Processing Engine
```python
# apps/backend/src/core/processor.py
class SourceAwareCategoryProcessor:
    """
    Dynamic category processor handling all 17 pharmaceutical categories
    with comprehensive source tracking and conflict resolution
    """

    def __init__(self, db: AsyncSession, redis: Redis, api_clients: Dict[str, APIClient]):
        self.db = db
        self.redis = redis
        self.api_clients = api_clients
        self.conflict_resolver = SourceConflictResolver()
        self.source_verifier = SourceVerifier()

    async def process_drug_request(self, drug_name: str, request_id: str) -> DrugRequestResult:
        """
        Main processing pipeline:
        1. Load dynamic category configurations from database
        2. Execute parallel API calls with source tracking
        3. Detect and resolve conflicts between sources
        4. Generate comprehensive results with audit trail
        """

    async def _process_single_category(self, category_config: Dict, drug_name: str, request_id: str) -> CategoryResult:
        # Load configuration dynamically from database
        config = await self.db.get_category_config(category_config['id'])
        parameters = await self._load_parameters(drug_name, request_id, config)

        # Execute multi-API search with source tracking
        search_results = await self._execute_multi_api_search(drug_name, category_config['name'], config)

        # Process and verify sources
        processed_sources = await self._process_sources(search_results, category_config)

        # Detect conflicts between sources
        conflicts = await self.conflict_resolver.detect_conflicts(processed_sources)

        # Generate category summary with confidence scoring
        summary = await self._generate_category_summary(processed_sources, conflicts)

        return CategoryResult(
            category_name=category_config['name'],
            summary=summary,
            sources=processed_sources,
            conflicts=conflicts,
            confidence_score=self._calculate_confidence(processed_sources, conflicts)
        )
```

#### API Integration Layer
```python
# apps/backend/src/integrations/api_manager.py
class MultiAPIManager:
    """
    Manages all external API integrations with rate limiting,
    error handling, and comprehensive response tracking
    """

    def __init__(self):
        self.providers = {
            APIProvider.CHATGPT: ChatGPTClient(),
            APIProvider.PERPLEXITY: PerplexityClient(),
            APIProvider.GROK: GrokClient(),
            APIProvider.GEMINI: GeminiClient(),
            APIProvider.TAVILY: TavilyClient()
        }
        self.rate_limiter = RateLimiter()
        self.response_tracker = ResponseTracker()

    async def search_all_providers(self, query: str, category: str) -> List[SourceReference]:
        """
        Execute search across all API providers in parallel
        with comprehensive source attribution and error handling
        """
        tasks = [
            self._search_provider(provider, query, category)
            for provider in self.providers.values()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._consolidate_results(results)

    async def _search_provider(self, provider: APIClient, query: str, category: str) -> List[SourceReference]:
        """Search single provider with full source tracking"""
        try:
            response = await self.rate_limiter.execute(
                provider.search, query, category
            )

            # Track API response for audit trail
            response_id = await self.response_tracker.log_response(provider.name, response)

            # Extract sources with metadata
            sources = await self._extract_sources(response, provider.name, response_id)

            return sources

        except Exception as e:
            await self._log_api_error(provider.name, query, e)
            return []
```

#### Source Conflict Resolution
```python
# apps/backend/src/core/conflict_resolver.py
class SourceConflictResolver:
    """
    Detects and resolves conflicts between pharmaceutical sources
    using multiple resolution strategies and confidence scoring
    """

    async def detect_conflicts(self, sources: List[SourceReference]) -> List[SourceConflict]:
        """
        Analyze sources for factual, temporal, and methodological conflicts
        """
        conflicts = []

        # Group sources by content similarity
        source_groups = await self._group_similar_content(sources)

        for group in source_groups:
            # Detect factual conflicts
            factual_conflicts = await self._detect_factual_conflicts(group)
            conflicts.extend(factual_conflicts)

            # Detect temporal conflicts (different dates for same claims)
            temporal_conflicts = await self._detect_temporal_conflicts(group)
            conflicts.extend(temporal_conflicts)

            # Detect methodological conflicts (different study approaches)
            methodological_conflicts = await self._detect_methodological_conflicts(group)
            conflicts.extend(methodological_conflicts)

        return conflicts

    async def resolve_conflict(self, conflict: SourceConflict) -> ConflictResolution:
        """
        Apply resolution strategy based on conflict type and source credibility
        """
        strategy = self._select_resolution_strategy(conflict)

        if strategy == ResolutionStrategy.CREDIBILITY_WEIGHTED:
            return await self._resolve_by_credibility(conflict)
        elif strategy == ResolutionStrategy.TEMPORAL_PRECEDENCE:
            return await self._resolve_by_temporal_precedence(conflict)
        elif strategy == ResolutionStrategy.METHODOLOGICAL_RIGOR:
            return await self._resolve_by_methodological_rigor(conflict)
        else:
            return await self._resolve_by_consensus(conflict)
```

#### Real-time WebSocket Handler
```python
# apps/backend/src/websockets/request_updates.py
class RequestUpdateHandler:
    """
    Manages real-time updates for drug request processing
    with comprehensive event streaming and client management
    """

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis = Redis()

    async def connect(self, websocket: WebSocket, request_id: str):
        """Connect client to request-specific update stream"""
        await websocket.accept()

        if request_id not in self.active_connections:
            self.active_connections[request_id] = []

        self.active_connections[request_id].append(websocket)

        # Send initial status
        status = await self._get_current_status(request_id)
        await websocket.send_json(status)

    async def broadcast_update(self, request_id: str, update: RequestUpdate):
        """Broadcast update to all connected clients for this request"""
        if request_id in self.active_connections:
            disconnected = []

            for connection in self.active_connections[request_id]:
                try:
                    await connection.send_json(update.dict())
                except ConnectionClosed:
                    disconnected.append(connection)

            # Clean up disconnected clients
            for conn in disconnected:
                self.active_connections[request_id].remove(conn)
```

### Frontend Components

#### Main Dashboard Component
```typescript
// apps/frontend/src/components/dashboard/DrugRequestDashboard.tsx
'use client';

interface DrugRequestDashboardProps {
  initialRequests?: DrugRequest[];
}

export function DrugRequestDashboard({ initialRequests = [] }: DrugRequestDashboardProps) {
  const {
    requests,
    currentRequest,
    loading,
    error,
    createRequest,
    fetchRequest,
    subscribeToUpdates
  } = useDrugRequestStore();

  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);

  useEffect(() => {
    if (selectedRequestId) {
      subscribeToUpdates(selectedRequestId);
    }

    return () => {
      // Cleanup WebSocket connections
      useDrugRequestStore.getState().unsubscribeFromUpdates();
    };
  }, [selectedRequestId, subscribeToUpdates]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
      {/* Request List Panel */}
      <div className="lg:col-span-1">
        <RequestListPanel
          requests={requests}
          selectedId={selectedRequestId}
          onSelect={setSelectedRequestId}
          onCreateNew={createRequest}
          loading={loading}
        />
      </div>

      {/* Request Details Panel */}
      <div className="lg:col-span-2">
        {currentRequest ? (
          <RequestDetailsPanel
            request={currentRequest}
            onRefresh={() => fetchRequest(currentRequest.id)}
          />
        ) : (
          <EmptyStatePanel />
        )}
      </div>
    </div>
  );
}
```

#### Real-time Processing Status Component
```typescript
// apps/frontend/src/components/processing/ProcessingStatusCard.tsx
interface ProcessingStatusCardProps {
  request: DrugRequest;
  realTimeUpdates?: boolean;
}

export function ProcessingStatusCard({ request, realTimeUpdates = true }: ProcessingStatusCardProps) {
  const [updates, setUpdates] = useState<RequestUpdate[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (realTimeUpdates && request.status === 'processing') {
      // Establish WebSocket connection for real-time updates
      wsRef.current = new WebSocket(`ws://localhost:8000/api/v1/requests/${request.id}/updates`);

      wsRef.current.onmessage = (event) => {
        const update = JSON.parse(event.data) as RequestUpdate;
        setUpdates(prev => [...prev, update]);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [request.id, request.status, realTimeUpdates]);

  const progressPercentage = (request.completedCategories / request.totalCategories) * 100;

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>{request.drugName} Processing</span>
          <Badge variant={getStatusVariant(request.status)}>
            {request.status.toUpperCase()}
          </Badge>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>Progress</span>
            <span>{request.completedCategories}/{request.totalCategories} categories</span>
          </div>
          <Progress value={progressPercentage} className="w-full" />
        </div>

        {/* Category Status Grid */}
        <div className="grid grid-cols-4 gap-2">
          {request.categories?.map((category) => (
            <CategoryStatusBadge
              key={category.id}
              category={category}
              onClick={() => onCategoryClick(category)}
            />
          ))}
        </div>

        {/* Real-time Update Feed */}
        {updates.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Recent Updates</h4>
            <div className="max-h-32 overflow-y-auto space-y-1">
              {updates.slice(-5).map((update, index) => (
                <div key={index} className="text-xs p-2 bg-muted rounded text-muted-foreground">
                  <span className="font-medium">{formatTime(update.timestamp)}</span>: {update.message}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

#### Source Analysis Component
```typescript
// apps/frontend/src/components/sources/SourceAnalysisPanel.tsx
interface SourceAnalysisPanelProps {
  requestId: string;
  categoryId?: number;
}

export function SourceAnalysisPanel({ requestId, categoryId }: SourceAnalysisPanelProps) {
  const {
    sources,
    conflicts,
    loading,
    fetchSources,
    verifySource,
    getSourcesByCategory,
    getConflictingSources
  } = useSourceStore();

  const [selectedTab, setSelectedTab] = useState<'sources' | 'conflicts' | 'analysis'>('sources');
  const [verificationDialog, setVerificationDialog] = useState<{ open: boolean; sourceId?: string }>({ open: false });

  useEffect(() => {
    fetchSources(requestId);
  }, [requestId, fetchSources]);

  const displaySources = categoryId
    ? getSourcesByCategory(requestId, categoryId.toString())
    : sources[requestId] || [];

  const displayConflicts = getConflictingSources(requestId);

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Source Analysis</CardTitle>
        <Tabs value={selectedTab} onValueChange={(value) => setSelectedTab(value as any)}>
          <TabsList>
            <TabsTrigger value="sources">Sources ({displaySources.length})</TabsTrigger>
            <TabsTrigger value="conflicts">Conflicts ({displayConflicts.length})</TabsTrigger>
            <TabsTrigger value="analysis">Analysis</TabsTrigger>
          </TabsList>
        </Tabs>
      </CardHeader>

      <CardContent>
        <TabsContent value="sources">
          <div className="space-y-4">
            {displaySources.map((source) => (
              <SourceCard
                key={source.id}
                source={source}
                onVerify={() => setVerificationDialog({ open: true, sourceId: source.id })}
              />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="conflicts">
          <div className="space-y-4">
            {displayConflicts.map((conflict) => (
              <ConflictCard
                key={conflict.id}
                conflict={conflict}
                onResolve={(resolution) => handleConflictResolution(conflict.id, resolution)}
              />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="analysis">
          <SourceCredibilityAnalysis requestId={requestId} />
        </TabsContent>
      </CardContent>

      {/* Source Verification Dialog */}
      <SourceVerificationDialog
        open={verificationDialog.open}
        sourceId={verificationDialog.sourceId}
        onClose={() => setVerificationDialog({ open: false })}
        onVerify={async (verification) => {
          if (verificationDialog.sourceId) {
            await verifySource(verificationDialog.sourceId, verification);
          }
        }}
      />
    </Card>
  );
}
```

#### State Management Stores
```typescript
// apps/frontend/src/stores/drug-request-store.ts
interface DrugRequestStore {
  requests: DrugRequest[];
  currentRequest: DrugRequest | null;
  loading: boolean;
  error: string | null;

  // Actions
  createRequest: (drugName: string) => Promise<void>;
  fetchRequest: (requestId: string) => Promise<void>;
  fetchRequests: () => Promise<void>;
  subscribeToUpdates: (requestId: string) => void;
  unsubscribeFromUpdates: () => void;
}

export const useDrugRequestStore = create<DrugRequestStore>()((set, get) => ({
  requests: [],
  currentRequest: null,
  loading: false,
  error: null,

  createRequest: async (drugName: string) => {
    set({ loading: true, error: null });

    try {
      const response = await fetch('/api/v1/requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ drugName })
      });

      if (!response.ok) throw new Error('Failed to create request');

      const newRequest = await response.json();

      set(state => ({
        requests: [...state.requests, newRequest],
        currentRequest: newRequest,
        loading: false
      }));

      // Automatically subscribe to updates for new request
      get().subscribeToUpdates(newRequest.id);

    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },

  fetchRequest: async (requestId: string) => {
    set({ loading: true, error: null });

    try {
      const response = await fetch(`/api/v1/requests/${requestId}`);
      if (!response.ok) throw new Error('Failed to fetch request');

      const request = await response.json();

      set(state => ({
        currentRequest: request,
        requests: state.requests.map(r => r.id === requestId ? request : r),
        loading: false
      }));

    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },

  subscribeToUpdates: (requestId: string) => {
    const ws = new WebSocket(`ws://localhost:8000/api/v1/requests/${requestId}/updates`);

    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);

      // Update the current request with real-time data
      set(state => {
        if (state.currentRequest?.id === requestId) {
          return {
            currentRequest: { ...state.currentRequest, ...update },
            requests: state.requests.map(r =>
              r.id === requestId ? { ...r, ...update } : r
            )
          };
        }
        return state;
      });
    };

    // Store WebSocket reference for cleanup
    (get() as any)._ws = ws;
  },

  unsubscribeFromUpdates: () => {
    const ws = (get() as any)._ws;
    if (ws) {
      ws.close();
      delete (get() as any)._ws;
    }
  }
}));
```

### Component Integration Architecture

#### Frontend Component Hierarchy
```
DrugRequestDashboard (Main Container)
├── RequestListPanel
│   ├── RequestCard (per request)
│   └── CreateRequestForm
├── RequestDetailsPanel
│   ├── ProcessingStatusCard
│   │   ├── ProgressBar
│   │   ├── CategoryStatusGrid
│   │   └── UpdateFeed
│   ├── CategoryResultsGrid
│   │   └── CategoryCard (per category)
│   └── SourceAnalysisPanel
│       ├── SourceCard (per source)
│       ├── ConflictCard (per conflict)
│       └── CredibilityAnalysis
└── GlobalErrorBoundary
```

#### Backend Service Architecture
```
FastAPI Application
├── Core Processing Engine
│   ├── SourceAwareCategoryProcessor
│   ├── SourceConflictResolver
│   └── SourceVerifier
├── API Integration Layer
│   ├── MultiAPIManager
│   ├── RateLimiter
│   └── ResponseTracker
├── Database Layer
│   ├── AsyncSession Manager
│   ├── Repository Pattern
│   └── Audit Trail Logger
└── WebSocket Manager
    ├── RequestUpdateHandler
    └── ConnectionManager
```

**Rationale for Component Design:**

1. **Clear Separation**: Frontend components are completely independent of backend implementation details
2. **Real-time Capabilities**: WebSocket integration provides live updates during processing
3. **Source-Centric UI**: Dedicated components for source analysis and conflict resolution
4. **Scalable Architecture**: Dynamic category processing eliminates component multiplication
5. **Regulatory Compliance**: All components support comprehensive audit trails and verification workflows
6. **Error Resilience**: Comprehensive error handling and recovery mechanisms throughout

## Frontend Architecture

### Application Structure

#### Next.js App Router Architecture
```typescript
// apps/frontend/app/layout.tsx - Root Layout
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <div className="flex min-h-screen bg-background">
            <Sidebar />
            <main className="flex-1 overflow-y-auto">
              <Header />
              {children}
            </main>
          </div>
        </Providers>
        <Toaster />
      </body>
    </html>
  );
}

// apps/frontend/app/providers.tsx - Context Providers
'use client';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        <AuthProvider>
          {children}
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
```

#### Route Structure
```
apps/frontend/app/
├── (dashboard)/              # Dashboard layout group
│   ├── page.tsx             # Dashboard home - /
│   ├── requests/            # Drug requests management
│   │   ├── page.tsx        # Requests list - /requests
│   │   ├── [id]/           # Individual request
│   │   │   ├── page.tsx    # Request details - /requests/[id]
│   │   │   ├── sources/    # Source analysis
│   │   │   │   └── page.tsx # Sources view - /requests/[id]/sources
│   │   │   └── conflicts/   # Conflict resolution
│   │   │       └── page.tsx # Conflicts - /requests/[id]/conflicts
│   │   └── new/            # Create new request
│   │       └── page.tsx    # New request form - /requests/new
│   ├── categories/          # Category management
│   │   ├── page.tsx        # Categories overview - /categories
│   │   └── [id]/           # Individual category
│   │       └── page.tsx    # Category details - /categories/[id]
│   └── analytics/          # Analytics dashboard
│       └── page.tsx        # Analytics - /analytics
├── auth/                   # Authentication pages
│   ├── login/
│   │   └── page.tsx        # Login - /auth/login
│   └── register/
│       └── page.tsx        # Register - /auth/register
└── api/                    # API routes (proxy to backend)
    └── v1/
        ├── requests/
        │   └── route.ts    # Proxy to backend API
        └── auth/
            └── route.ts    # Authentication endpoints
```

### State Management Architecture

#### Zustand Store Structure
```typescript
// apps/frontend/src/stores/index.ts - Store Registry
export const useStores = () => ({
  drugRequests: useDrugRequestStore(),
  sources: useSourceStore(),
  categories: useCategoryStore(),
  auth: useAuthStore(),
  ui: useUIStore()
});

// Store persistence configuration
const persistConfig = {
  name: 'cognito-ai-storage',
  storage: createJSONStorage(() => localStorage),
  partialize: (state: any) => ({
    // Only persist auth and UI preferences
    auth: state.auth,
    ui: { theme: state.ui.theme, sidebarCollapsed: state.ui.sidebarCollapsed }
  })
};
```

#### Category Store for Dynamic Processing
```typescript
// apps/frontend/src/stores/category-store.ts
interface CategoryStore {
  categories: PharmaceuticalCategory[];
  categoryConfigs: Record<number, CategoryConfig>;
  loading: boolean;
  error: string | null;

  // Dynamic category management
  fetchCategories: () => Promise<void>;
  fetchCategoryConfig: (categoryId: number) => Promise<void>;
  updateCategoryConfig: (categoryId: number, config: Partial<CategoryConfig>) => Promise<void>;

  // Category filtering and search
  searchCategories: (query: string) => PharmaceuticalCategory[];
  getCategoriesByStatus: (status: CategoryStatus) => PharmaceuticalCategory[];
  getCategoryProgress: (requestId: string) => CategoryProgress;
}

export const useCategoryStore = create<CategoryStore>()(
  devtools(
    persist(
      (set, get) => ({
        categories: [],
        categoryConfigs: {},
        loading: false,
        error: null,

        fetchCategories: async () => {
          set({ loading: true, error: null });

          try {
            const response = await fetch('/api/v1/categories');
            if (!response.ok) throw new Error('Failed to fetch categories');

            const categories = await response.json();
            set({ categories, loading: false });

          } catch (error) {
            set({ error: error.message, loading: false });
          }
        },

        fetchCategoryConfig: async (categoryId: number) => {
          try {
            const response = await fetch(`/api/v1/categories/${categoryId}/config`);
            if (!response.ok) throw new Error('Failed to fetch category config');

            const config = await response.json();

            set(state => ({
              categoryConfigs: {
                ...state.categoryConfigs,
                [categoryId]: config
              }
            }));

          } catch (error) {
            console.error('Failed to fetch category config:', error);
          }
        },

        searchCategories: (query: string) => {
          const { categories } = get();
          return categories.filter(category =>
            category.name.toLowerCase().includes(query.toLowerCase()) ||
            category.description?.toLowerCase().includes(query.toLowerCase())
          );
        },

        getCategoriesByStatus: (status: CategoryStatus) => {
          const { categories } = get();
          return categories.filter(category => category.status === status);
        },

        getCategoryProgress: (requestId: string) => {
          const { drugRequests } = useDrugRequestStore.getState();
          const request = drugRequests.find(r => r.id === requestId);

          if (!request) return { completed: 0, total: 17, percentage: 0 };

          return {
            completed: request.completedCategories,
            total: request.totalCategories,
            percentage: (request.completedCategories / request.totalCategories) * 100
          };
        }
      }),
      { name: 'category-store', partialize: (state) => ({ categories: state.categories }) }
    ),
    { name: 'category-store' }
  )
);
```

### Data Fetching Architecture

#### TanStack Query Configuration
```typescript
// apps/frontend/src/lib/query-client.ts
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      retry: (failureCount, error) => {
        // Don't retry on 4xx errors
        if (error.response?.status && error.response.status < 500) {
          return false;
        }
        return failureCount < 3;
      },
      refetchOnWindowFocus: false
    },
    mutations: {
      retry: 1
    }
  }
});

// Query keys factory
export const queryKeys = {
  // Drug requests
  drugRequests: ['drug-requests'] as const,
  drugRequest: (id: string) => ['drug-requests', id] as const,
  drugRequestSources: (id: string) => ['drug-requests', id, 'sources'] as const,
  drugRequestConflicts: (id: string) => ['drug-requests', id, 'conflicts'] as const,

  // Categories
  categories: ['categories'] as const,
  category: (id: number) => ['categories', id] as const,
  categoryConfig: (id: number) => ['categories', id, 'config'] as const,

  // Sources
  sources: ['sources'] as const,
  source: (id: string) => ['sources', id] as const,
  sourceVerification: (id: string) => ['sources', id, 'verification'] as const
};
```

#### Custom Hooks for Data Fetching
```typescript
// apps/frontend/src/hooks/use-drug-request.ts
export function useDrugRequest(requestId: string) {
  return useQuery({
    queryKey: queryKeys.drugRequest(requestId),
    queryFn: async () => {
      const response = await fetch(`/api/v1/requests/${requestId}`);
      if (!response.ok) throw new Error('Failed to fetch drug request');
      return response.json() as DrugRequestDetailResponse;
    },
    enabled: !!requestId,
    refetchInterval: (data) => {
      // Refetch every 5 seconds if still processing
      return data?.status === 'processing' ? 5000 : false;
    }
  });
}

// Real-time updates hook with WebSocket
export function useDrugRequestUpdates(requestId: string) {
  const queryClient = useQueryClient();
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');

  useEffect(() => {
    if (!requestId) return;

    setConnectionStatus('connecting');

    const ws = new WebSocket(`ws://localhost:8000/api/v1/requests/${requestId}/updates`);

    ws.onopen = () => {
      setConnectionStatus('connected');
    };

    ws.onmessage = (event) => {
      const update = JSON.parse(event.data) as RequestUpdate;

      // Update React Query cache with real-time data
      queryClient.setQueryData(queryKeys.drugRequest(requestId), (oldData: any) => {
        if (!oldData) return oldData;

        return {
          ...oldData,
          ...update,
          updatedAt: new Date().toISOString()
        };
      });

      // Trigger toast notification for important updates
      if (update.type === 'category_completed' || update.type === 'error') {
        toast({
          title: update.type === 'category_completed' ? 'Category Completed' : 'Processing Error',
          description: update.message,
          variant: update.type === 'error' ? 'destructive' : 'default'
        });
      }
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
    };

    ws.onerror = () => {
      setConnectionStatus('disconnected');
    };

    return () => {
      ws.close();
    };
  }, [requestId, queryClient]);

  return { connectionStatus };
}
```

### Component Architecture Patterns

#### Compound Component Pattern for Complex UI
```typescript
// apps/frontend/src/components/request-details/RequestDetails.tsx
interface RequestDetailsProps {
  requestId: string;
}

export function RequestDetails({ requestId }: RequestDetailsProps) {
  const { data: request, isLoading, error } = useDrugRequest(requestId);
  const { connectionStatus } = useDrugRequestUpdates(requestId);

  if (isLoading) return <RequestDetailsSkeleton />;
  if (error) return <ErrorState error={error} retry={() => refetch()} />;
  if (!request) return <NotFoundState />;

  return (
    <div className="space-y-6">
      {/* Connection Status Indicator */}
      <ConnectionStatusBanner status={connectionStatus} />

      {/* Main Request Info */}
      <RequestInfo request={request} />

      {/* Processing Status */}
      <ProcessingStatus request={request} />

      {/* Category Results Grid */}
      <CategoryResults request={request} />

      {/* Source Analysis */}
      <SourceAnalysis requestId={requestId} />
    </div>
  );
}

// Compound component structure
RequestDetails.Info = RequestInfo;
RequestDetails.ProcessingStatus = ProcessingStatus;
RequestDetails.CategoryResults = CategoryResults;
RequestDetails.SourceAnalysis = SourceAnalysis;
```

#### Error Boundary with Recovery
```typescript
// apps/frontend/src/components/error-boundary/ErrorBoundary.tsx
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<PropsWithChildren, ErrorBoundaryState> {
  constructor(props: PropsWithChildren) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error Boundary caught an error:', error, errorInfo);

    // Log to external service in production
    if (process.env.NODE_ENV === 'production') {
      // logErrorToService(error, errorInfo);
    }

    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[400px] items-center justify-center">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle className="text-destructive">Something went wrong</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground mb-4">
                An unexpected error occurred while processing pharmaceutical data.
              </p>
              {process.env.NODE_ENV === 'development' && (
                <details className="mb-4">
                  <summary className="cursor-pointer text-sm font-medium">
                    Technical Details
                  </summary>
                  <pre className="mt-2 text-xs bg-muted p-2 rounded overflow-auto">
                    {this.state.error?.toString()}
                    {this.state.errorInfo?.componentStack}
                  </pre>
                </details>
              )}
              <div className="flex gap-2">
                <Button
                  onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}
                  variant="outline"
                >
                  Try Again
                </Button>
                <Button onClick={() => window.location.reload()}>
                  Reload Page
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
```

### UI Component System

#### Design System Configuration
```typescript
// apps/frontend/src/lib/design-system.ts
export const designTokens = {
  colors: {
    // Pharmaceutical industry appropriate colors
    primary: {
      50: '#eff6ff',
      500: '#3b82f6',
      600: '#2563eb',
      900: '#1e3a8a'
    },
    success: {
      50: '#f0fdf4',
      500: '#22c55e',
      600: '#16a34a'
    },
    warning: {
      50: '#fffbeb',
      500: '#f59e0b',
      600: '#d97706'
    },
    error: {
      50: '#fef2f2',
      500: '#ef4444',
      600: '#dc2626'
    }
  },

  spacing: {
    pharmaceutical: {
      compact: '0.5rem',
      comfortable: '1rem',
      spacious: '1.5rem'
    }
  },

  typography: {
    pharmaceutical: {
      heading: 'font-semibold text-foreground',
      body: 'text-muted-foreground',
      caption: 'text-xs text-muted-foreground',
      code: 'font-mono text-sm bg-muted px-1 py-0.5 rounded'
    }
  }
} as const;

// Component variants for pharmaceutical compliance
export const componentVariants = {
  badge: {
    verified: 'bg-green-100 text-green-800 border-green-200',
    pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    disputed: 'bg-red-100 text-red-800 border-red-200',
    processing: 'bg-blue-100 text-blue-800 border-blue-200'
  },

  card: {
    pharmaceutical: 'border-l-4 border-l-primary bg-card',
    warning: 'border-l-4 border-l-warning bg-warning/5',
    error: 'border-l-4 border-l-destructive bg-destructive/5'
  }
} as const;
```

#### Accessibility Configuration
```typescript
// apps/frontend/src/lib/accessibility.ts
export const accessibilityConfig = {
  // WCAG 2.1 AA compliance for pharmaceutical data
  focusManagement: {
    trapFocus: true,
    restoreFocus: true,
    autoFocus: 'first-interactive'
  },

  announcements: {
    processingUpdates: true,
    conflictDetection: true,
    sourceVerification: true,
    categoryCompletion: true
  },

  keyboardNavigation: {
    skipLinks: true,
    roving: true,
    shortcuts: {
      'Alt+N': 'New Request',
      'Alt+S': 'Search',
      'Alt+H': 'Help',
      'Escape': 'Close Modal'
    }
  }
} as const;

// Screen reader announcements for pharmaceutical processing
export function announceProcessingUpdate(update: RequestUpdate) {
  const message = `${update.categoryName} processing ${update.status}. ${update.message}`;

  // Use live region for non-disruptive announcements
  const announcement = document.getElementById('live-announcements');
  if (announcement) {
    announcement.textContent = message;
  }
}
```

### Performance Optimization

#### Code Splitting Strategy
```typescript
// apps/frontend/src/app/layout.tsx
import dynamic from 'next/dynamic';

// Lazy load heavy components
const SourceAnalysisPanel = dynamic(() =>
  import('@/components/sources/SourceAnalysisPanel').then(mod => ({
    default: mod.SourceAnalysisPanel
  })),
  {
    loading: () => <SourceAnalysisSkeleton />,
    ssr: false
  }
);

const ConflictResolutionDialog = dynamic(() =>
  import('@/components/conflicts/ConflictResolutionDialog'),
  { loading: () => <DialogSkeleton /> }
);

// Route-level code splitting is automatic with App Router
```

#### Memoization Strategy
```typescript
// apps/frontend/src/hooks/use-optimized-sources.ts
export function useOptimizedSources(requestId: string, categoryId?: number) {
  const { data: sources } = useQuery({
    queryKey: queryKeys.drugRequestSources(requestId),
    queryFn: () => fetchSources(requestId)
  });

  // Memoize expensive computations
  const categorizedSources = useMemo(() => {
    if (!sources) return {};

    return sources.reduce((acc, source) => {
      const category = source.categoryName;
      if (!acc[category]) acc[category] = [];
      acc[category].push(source);
      return acc;
    }, {} as Record<string, SourceReference[]>);
  }, [sources]);

  const filteredSources = useMemo(() => {
    if (!categoryId) return sources || [];
    return sources?.filter(s => s.categoryId === categoryId) || [];
  }, [sources, categoryId]);

  const sourceStats = useMemo(() => {
    if (!sources) return null;

    return {
      total: sources.length,
      verified: sources.filter(s => s.verificationStatus === 'verified').length,
      disputed: sources.filter(s => s.verificationStatus === 'disputed').length,
      byProvider: sources.reduce((acc, source) => {
        acc[source.apiProvider] = (acc[source.apiProvider] || 0) + 1;
        return acc;
      }, {} as Record<string, number>)
    };
  }, [sources]);

  return {
    sources,
    categorizedSources,
    filteredSources,
    sourceStats
  };
}
```

**Rationale for Frontend Architecture:**

1. **Complete Independence**: Frontend can be developed and deployed separately from backend
2. **Real-time Integration**: WebSocket hooks provide seamless real-time updates
3. **Accessibility First**: WCAG 2.1 AA compliance for pharmaceutical regulatory requirements
4. **Performance Optimized**: Code splitting, memoization, and efficient data fetching
5. **Error Resilience**: Comprehensive error boundaries and recovery mechanisms
6. **Scalable State Management**: Zustand stores handle complex pharmaceutical data relationships

## Backend Architecture

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

## Project Structure

### Monorepo Architecture with Independent Development

#### Root Directory Structure
```
CognitoAI-Engine/
├── apps/
│   ├── frontend/                 # Next.js application (independent development)
│   └── backend/                  # FastAPI application (independent development)
├── packages/                     # Shared utilities and types
│   ├── shared-types/            # TypeScript/Python type definitions
│   ├── api-contracts/           # OpenAPI specifications
│   └── testing-utils/           # Shared testing utilities
├── tools/                       # Development and deployment tools
│   ├── scripts/                 # Build and deployment scripts
│   ├── docker/                  # Docker configurations (optional)
│   └── deployment/              # Deployment configurations
├── docs/                        # Documentation
│   ├── prd.md                  # Product Requirements Document
│   ├── architecture.md         # This document
│   └── api/                    # API documentation
├── .github/                     # GitHub workflows
│   └── workflows/
│       ├── frontend-ci.yml     # Frontend CI/CD
│       ├── backend-ci.yml      # Backend CI/CD
│       └── integration-tests.yml # End-to-end tests
├── turbo.json                  # Turborepo configuration
├── package.json                # Root package.json for tooling
├── .env.example               # Environment variables template
└── README.md                  # Project overview
```

#### Frontend Application Structure
```
apps/frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── (dashboard)/       # Dashboard layout group
│   │   │   ├── page.tsx       # Dashboard home
│   │   │   ├── requests/      # Drug requests routes
│   │   │   │   ├── page.tsx   # Requests list
│   │   │   │   ├── [id]/      # Individual request
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   ├── sources/
│   │   │   │   │   │   └── page.tsx
│   │   │   │   │   └── conflicts/
│   │   │   │   │       └── page.tsx
│   │   │   │   └── new/
│   │   │   │       └── page.tsx
│   │   │   ├── categories/    # Category management
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx
│   │   │   └── analytics/
│   │   │       └── page.tsx
│   │   ├── auth/              # Authentication routes
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   └── register/
│   │   │       └── page.tsx
│   │   ├── api/               # API routes (proxy to backend)
│   │   │   └── v1/
│   │   │       ├── requests/
│   │   │       │   └── route.ts
│   │   │       └── auth/
│   │   │           └── route.ts
│   │   ├── layout.tsx         # Root layout
│   │   ├── loading.tsx        # Global loading UI
│   │   ├── error.tsx          # Global error UI
│   │   ├── not-found.tsx      # 404 page
│   │   └── providers.tsx      # Context providers
│   ├── components/            # React components
│   │   ├── ui/               # shadcn/ui components
│   │   ├── dashboard/        # Dashboard components
│   │   ├── requests/         # Request management components
│   │   ├── sources/          # Source analysis components
│   │   ├── conflicts/        # Conflict resolution components
│   │   ├── categories/       # Category components
│   │   ├── auth/            # Authentication components
│   │   └── common/          # Shared components
│   ├── hooks/               # Custom React hooks
│   │   ├── use-drug-request.ts
│   │   ├── use-sources.ts
│   │   ├── use-categories.ts
│   │   └── use-auth.ts
│   ├── stores/              # Zustand state management
│   │   ├── drug-request-store.ts
│   │   ├── source-store.ts
│   │   ├── category-store.ts
│   │   ├── auth-store.ts
│   │   └── ui-store.ts
│   ├── lib/                 # Utility libraries
│   │   ├── api-client.ts    # API client configuration
│   │   ├── query-client.ts  # TanStack Query setup
│   │   ├── design-system.ts # Design tokens
│   │   ├── accessibility.ts # Accessibility helpers
│   │   └── utils.ts         # General utilities
│   └── styles/              # Global styles
│       ├── globals.css      # Global CSS
│       └── components.css   # Component-specific styles
├── public/                  # Static assets
│   ├── images/
│   ├── icons/
│   └── favicon.ico
├── .env.local              # Local environment variables
├── .env.example            # Environment template
├── next.config.js          # Next.js configuration
├── tailwind.config.js      # Tailwind configuration
├── tsconfig.json           # TypeScript configuration
├── package.json            # Frontend dependencies
└── README.md               # Frontend documentation
```

#### Backend Application Structure
```
apps/backend/
├── src/
│   ├── main.py              # FastAPI application entry
│   ├── core/                # Core business logic
│   │   ├── __init__.py
│   │   ├── processor.py     # Main category processor
│   │   ├── conflict_resolver.py
│   │   ├── source_verifier.py
│   │   └── audit_logger.py
│   ├── integrations/        # External API integrations
│   │   ├── __init__.py
│   │   ├── api_manager.py   # Multi-API coordination
│   │   ├── providers/       # Individual API clients
│   │   │   ├── __init__.py
│   │   │   ├── base.py      # Base API client
│   │   │   ├── chatgpt.py
│   │   │   ├── perplexity.py
│   │   │   ├── grok.py
│   │   │   ├── gemini.py
│   │   │   └── tavily.py
│   │   └── rate_limiter.py
│   ├── database/            # Database layer
│   │   ├── __init__.py
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── connection.py    # Database connection
│   │   └── repositories/    # Repository pattern
│   │       ├── __init__.py
│   │       ├── base.py      # Base repository
│   │       ├── request_repo.py
│   │       ├── source_repo.py
│   │       ├── category_repo.py
│   │       └── audit_repo.py
│   ├── api/                 # API routes
│   │   ├── __init__.py
│   │   ├── deps.py          # Dependencies
│   │   ├── v1/              # API version 1
│   │   │   ├── __init__.py
│   │   │   ├── requests.py
│   │   │   ├── categories.py
│   │   │   ├── sources.py
│   │   │   └── auth.py
│   │   └── websockets/
│   │       ├── __init__.py
│   │       └── updates.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── base.py          # Base schemas
│   │   ├── requests.py
│   │   ├── sources.py
│   │   ├── categories.py
│   │   └── auth.py
│   ├── background/          # Background processing
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   ├── tasks.py
│   │   └── scheduler.py
│   ├── config/              # Configuration
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── database.py
│   │   └── redis.py
│   └── utils/               # Utility functions
│       ├── __init__.py
│       ├── logging.py
│       ├── exceptions.py
│       └── validators.py
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── conftest.py         # Pytest configuration
│   ├── unit/               # Unit tests
│   │   ├── test_core/
│   │   ├── test_integrations/
│   │   └── test_database/
│   ├── integration/        # Integration tests
│   │   ├── test_api/
│   │   └── test_background/
│   └── fixtures/           # Test fixtures
│       ├── drug_requests.py
│       └── sources.py
├── alembic/                # Database migrations
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── .env                    # Environment variables
├── .env.example            # Environment template
├── requirements.txt        # Python dependencies
├── requirements-dev.txt    # Development dependencies
├── Dockerfile              # Container configuration (optional)
├── pytest.ini             # Pytest configuration
└── README.md               # Backend documentation
```

### Shared Packages Architecture

#### Shared Types Package
```typescript
// packages/shared-types/src/index.ts
export interface DrugRequest {
  id: string;
  drugName: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
  userId?: string;
  totalCategories: number;
  completedCategories: number;
  failedCategories: string[];
}

export interface CategoryResult {
  id: string;
  requestId: string;
  categoryName: string;
  categoryId: number;
  summary: string;
  confidenceScore: number;
  dataQualityScore: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  processingTimeMs: number;
  retryCount: number;
  errorMessage?: string;
  startedAt: string;
  completedAt?: string;
  sources: SourceReference[];
  conflicts: SourceConflict[];
}

export interface SourceReference {
  id: string;
  categoryResultId: string;
  apiProvider: 'chatgpt' | 'perplexity' | 'grok' | 'gemini' | 'tavily';
  sourceUrl?: string;
  sourceTitle?: string;
  sourceType: 'research_paper' | 'clinical_trial' | 'news' | 'regulatory' | 'other';
  contentSnippet: string;
  relevanceScore: number;
  credibilityScore: number;
  publishedDate?: string;
  authors?: string;
  journalName?: string;
  doi?: string;
  extractedAt: string;
  apiResponseId?: string;
  verificationStatus: 'pending' | 'verified' | 'disputed' | 'invalid';
  verifiedAt?: string;
  verifiedBy?: string;
}

// Export Python-compatible types for backend
export const PythonTypes = {
  DrugRequest: `
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class RequestStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DrugRequest(BaseModel):
    id: str = Field(..., description="Unique request identifier")
    drug_name: str = Field(..., description="Name of the drug")
    status: RequestStatus = Field(default=RequestStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    user_id: Optional[str] = None
    total_categories: int = Field(default=17)
    completed_categories: int = Field(default=0)
    failed_categories: List[str] = Field(default_factory=list)
  `
};
```

#### API Contracts Package
```yaml
# packages/api-contracts/openapi.yml
openapi: 3.0.3
info:
  title: CognitoAI Engine API
  description: Pharmaceutical Intelligence Processing API with Source Tracking
  version: 1.0.0
  contact:
    name: API Support
    email: support@cognito-ai.com

servers:
  - url: http://localhost:8000/api/v1
    description: Local development server
  - url: https://api.cognito-ai.com/v1
    description: Production server

paths:
  /requests:
    post:
      summary: Create new drug intelligence request
      operationId: createDrugRequest
      tags:
        - requests
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateDrugRequestSchema'
      responses:
        '201':
          description: Request created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DrugRequestResponse'
        '400':
          description: Invalid request data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    get:
      summary: List drug requests
      operationId: listDrugRequests
      tags:
        - requests
      parameters:
        - name: skip
          in: query
          schema:
            type: integer
            default: 0
        - name: limit
          in: query
          schema:
            type: integer
            default: 50
        - name: status
          in: query
          schema:
            $ref: '#/components/schemas/RequestStatus'
      responses:
        '200':
          description: List of drug requests
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/DrugRequestResponse'

  /requests/{request_id}:
    get:
      summary: Get drug request details
      operationId: getDrugRequest
      tags:
        - requests
      parameters:
        - name: request_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Request details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DrugRequestDetailResponse'
        '404':
          description: Request not found

  /requests/{request_id}/sources:
    get:
      summary: Get request sources analysis
      operationId: getRequestSources
      tags:
        - sources
      parameters:
        - name: request_id
          in: path
          required: true
          schema:
            type: string
        - name: include_conflicts
          in: query
          schema:
            type: boolean
            default: true
        - name: group_by_category
          in: query
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: Sources analysis
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SourceAnalysisResponse'

components:
  schemas:
    RequestStatus:
      type: string
      enum:
        - pending
        - processing
        - completed
        - failed

    CreateDrugRequestSchema:
      type: object
      required:
        - drugName
      properties:
        drugName:
          type: string
          minLength: 1
          maxLength: 255
          description: Name of the drug to analyze
        userId:
          type: string
          description: Optional user identifier
        priorityCategories:
          type: array
          items:
            type: integer
          maxItems: 17
          description: Optional category prioritization

    DrugRequestResponse:
      type: object
      properties:
        id:
          type: string
        drugName:
          type: string
        status:
          $ref: '#/components/schemas/RequestStatus'
        progress:
          type: object
          properties:
            totalCategories:
              type: integer
            completedCategories:
              type: integer
            failedCategories:
              type: array
              items:
                type: string
            estimatedCompletion:
              type: string
              format: date-time
        createdAt:
          type: string
          format: date-time
        updatedAt:
          type: string
          format: date-time

    ErrorResponse:
      type: object
      properties:
        error:
          type: string
        detail:
          type: string
        timestamp:
          type: string
          format: date-time
```

### Development Workflow Configuration

#### Turborepo Configuration
```json
// turbo.json
{
  "globalDependencies": ["**/.env.*local"],
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "!.next/cache/**", "dist/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "test": {
      "dependsOn": ["build"],
      "inputs": ["src/**/*.tsx", "src/**/*.ts", "test/**/*.ts", "test/**/*.tsx"]
    },
    "test:unit": {
      "dependsOn": ["build"]
    },
    "test:integration": {
      "dependsOn": ["build"]
    },
    "lint": {
      "inputs": ["src/**/*.tsx", "src/**/*.ts", "*.js", "*.json"]
    },
    "type-check": {
      "dependsOn": ["^build"],
      "inputs": ["src/**/*.tsx", "src/**/*.ts", "*.json"]
    }
  }
}
```

#### Root Package.json
```json
// package.json
{
  "name": "cognito-ai-engine",
  "private": true,
  "scripts": {
    "dev": "turbo run dev --parallel",
    "dev:frontend": "turbo run dev --filter=frontend",
    "dev:backend": "cd apps/backend && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000",
    "build": "turbo run build",
    "test": "turbo run test",
    "test:unit": "turbo run test:unit",
    "test:integration": "turbo run test:integration",
    "lint": "turbo run lint",
    "type-check": "turbo run type-check",
    "clean": "turbo run clean && rm -rf node_modules",
    "format": "prettier --write \"**/*.{js,jsx,ts,tsx,json,md}\"",
    "setup": "npm install && cd apps/backend && pip install -r requirements.txt"
  },
  "devDependencies": {
    "turbo": "^1.10.0",
    "prettier": "^3.0.0",
    "@types/node": "^20.0.0",
    "typescript": "^5.0.0"
  },
  "workspaces": [
    "apps/*",
    "packages/*"
  ],
  "packageManager": "npm@9.0.0"
}
```

#### CI/CD Configuration
```yaml
# .github/workflows/frontend-ci.yml
name: Frontend CI

on:
  push:
    branches: [main, develop]
    paths: ['apps/frontend/**', 'packages/**']
  pull_request:
    branches: [main]
    paths: ['apps/frontend/**', 'packages/**']

jobs:
  frontend-test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Type check
        run: turbo run type-check --filter=frontend

      - name: Lint
        run: turbo run lint --filter=frontend

      - name: Test
        run: turbo run test --filter=frontend

      - name: Build
        run: turbo run build --filter=frontend

      - name: E2E Tests
        run: turbo run test:e2e --filter=frontend
        env:
          NEXT_PUBLIC_API_URL: http://localhost:8000
```

```yaml
# .github/workflows/backend-ci.yml
name: Backend CI

on:
  push:
    branches: [main, develop]
    paths: ['apps/backend/**', 'packages/**']
  pull_request:
    branches: [main]
    paths: ['apps/backend/**', 'packages/**']

jobs:
  backend-test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_USER: testuser
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd apps/backend
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run migrations
        run: |
          cd apps/backend
          alembic upgrade head
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb

      - name: Lint with ruff
        run: |
          cd apps/backend
          ruff check src/

      - name: Type check with mypy
        run: |
          cd apps/backend
          mypy src/

      - name: Test with pytest
        run: |
          cd apps/backend
          pytest tests/ -v --cov=src --cov-report=xml
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379/0

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./apps/backend/coverage.xml
```

### Environment Configuration

#### Environment Variables Template
```bash
# .env.example
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/cognito_ai_engine
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=cognito_ai_engine
DATABASE_USER=user
DATABASE_PASSWORD=password

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# API Keys
OPENAI_API_KEY=your_openai_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
GROK_API_KEY=your_grok_api_key
GEMINI_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key

# Authentication
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Application
APP_NAME=CognitoAI Engine
APP_VERSION=1.0.0
DEBUG=false
CORS_ORIGINS=http://localhost:3000

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Frontend (Next.js)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXTAUTH_SECRET=your_nextauth_secret
NEXTAUTH_URL=http://localhost:3000
```

**Rationale for Project Structure:**

1. **Complete Separation**: Frontend and backend can be developed, tested, and deployed independently
2. **Monorepo Benefits**: Shared tooling and coordination while maintaining independence
3. **Type Safety**: Shared types ensure contract consistency between frontend and backend
4. **Developer Experience**: Turborepo provides fast, cached builds and parallel development
5. **CI/CD Independence**: Separate workflows for frontend and backend with appropriate triggers
6. **Scalable Architecture**: Structure supports team growth and additional applications
7. **Documentation Integration**: API contracts and shared documentation maintain consistency
8. **Environment Management**: Comprehensive environment configuration for all deployment scenarios

## Deployment Architecture

### Single-Server Deployment (As Requested)

#### System Architecture Overview
```
┌─────────────────────────────────────────────────────────────┐
│                    Dedicated Server                         │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │     Nginx       │  │   PostgreSQL    │  │    Redis    │ │
│  │ Reverse Proxy   │  │   Database      │  │   Cache     │ │
│  │ Static Files    │  │                 │  │   Sessions  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│           │                      │                  │      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Next.js       │  │    FastAPI      │  │   Celery    │ │
│  │   Frontend      │  │    Backend      │  │  Workers    │ │
│  │   Port 3000     │  │    Port 8000    │  │             │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### SystemD Service Configuration
```ini
# /etc/systemd/system/cognito-ai-backend.service
[Unit]
Description=CognitoAI Engine Backend API
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=exec
User=cognito-ai
Group=cognito-ai
WorkingDirectory=/opt/cognito-ai/backend
Environment=PATH=/opt/cognito-ai/backend/venv/bin
EnvironmentFile=/opt/cognito-ai/backend/.env
ExecStart=/opt/cognito-ai/backend/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cognito-ai-backend

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/cognito-ai/backend/logs
ProtectHome=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/cognito-ai-frontend.service
[Unit]
Description=CognitoAI Engine Frontend
After=network.target
Requires=cognito-ai-backend.service

[Service]
Type=exec
User=cognito-ai
Group=cognito-ai
WorkingDirectory=/opt/cognito-ai/frontend
Environment=NODE_ENV=production
EnvironmentFile=/opt/cognito-ai/frontend/.env
ExecStart=/usr/bin/node server.js
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cognito-ai-frontend

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/cognito-ai/frontend/logs
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/cognito-ai-celery.service
[Unit]
Description=CognitoAI Engine Celery Worker
After=network.target redis.service postgresql.service
Requires=redis.service postgresql.service

[Service]
Type=exec
User=cognito-ai
Group=cognito-ai
WorkingDirectory=/opt/cognito-ai/backend
Environment=PATH=/opt/cognito-ai/backend/venv/bin
EnvironmentFile=/opt/cognito-ai/backend/.env
ExecStart=/opt/cognito-ai/backend/venv/bin/celery -A src.background.celery_app worker -l info -c 4 --max-tasks-per-child=1000
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cognito-ai-celery

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/cognito-ai/backend/logs
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

#### Nginx Configuration
```nginx
# /etc/nginx/sites-available/cognito-ai-engine
upstream backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

upstream frontend {
    server 127.0.0.1:3000;
    keepalive 32;
}

server {
    listen 80;
    server_name cognito-ai.local;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # API routes to backend
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Timeout settings for long-running pharmaceutical processing
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # WebSocket routes for real-time updates
    location /api/v1/requests/*/updates {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket specific settings
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # Frontend application
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Static files (if needed)
    location /static/ {
        alias /opt/cognito-ai/frontend/public/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

### Database Schema and Migrations

#### Core Database Schema
```sql
-- Database initialization script
-- /opt/cognito-ai/backend/database/init.sql

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Pharmaceutical Categories Configuration Table
CREATE TABLE pharmaceutical_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    search_parameters JSONB DEFAULT '{}',
    processing_rules JSONB DEFAULT '{}',
    prompt_templates JSONB DEFAULT '{}',
    verification_criteria JSONB DEFAULT '{}',
    conflict_resolution_strategy VARCHAR(50) DEFAULT 'credibility_weighted',
    priority INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default 17 pharmaceutical categories
INSERT INTO pharmaceutical_categories (name, description, priority, search_parameters, processing_rules) VALUES
('Market Overview', 'Overall market analysis and competitive landscape', 17, '{"focus": "market_size, competitors, trends"}', '{"summary_length": "comprehensive"}'),
('Clinical Trials', 'Clinical trial data and regulatory submissions', 16, '{"focus": "phase_trials, efficacy, safety"}', '{"require_source_verification": true}'),
('Regulatory Status', 'FDA and international regulatory approvals', 15, '{"focus": "approvals, submissions, guidelines"}', '{"require_official_sources": true}'),
('Pricing & Access', 'Drug pricing and market access information', 14, '{"focus": "pricing, reimbursement, access"}', '{"require_recent_data": true}'),
('Safety Profile', 'Adverse events and safety data', 13, '{"focus": "side_effects, warnings, contraindications"}', '{"require_source_verification": true}'),
('Mechanism of Action', 'Drug mechanism and pharmacology', 12, '{"focus": "moa, pharmacokinetics, pharmacodynamics"}', '{"require_scientific_sources": true}'),
('Therapeutic Indications', 'Approved and investigational uses', 11, '{"focus": "indications, off_label, investigational"}', '{"comprehensive_search": true}'),
('Manufacturing', 'Manufacturing and supply chain information', 10, '{"focus": "manufacturing, supply, quality"}', '{"require_reliable_sources": true}'),
('Market Access', 'Payer and formulary coverage', 9, '{"focus": "formularies, coverage, restrictions"}', '{"require_current_data": true}'),
('Competitive Intelligence', 'Competitor analysis and positioning', 8, '{"focus": "competitors, differentiation, positioning"}', '{"comprehensive_analysis": true}'),
('Patent Landscape', 'Patent information and exclusivity', 7, '{"focus": "patents, exclusivity, generics"}', '{"require_legal_sources": true}'),
('Pipeline Status', 'Development pipeline and future outlook', 6, '{"focus": "pipeline, development, timeline"}', '{"forward_looking": true}'),
('Commercial Performance', 'Sales and revenue data', 5, '{"focus": "sales, revenue, market_share"}', '{"require_financial_sources": true}'),
('Real World Evidence', 'Post-market surveillance and real-world data', 4, '{"focus": "rwe, post_market, effectiveness"}', '{"require_peer_review": true}'),
('Key Opinion Leaders', 'Expert opinions and thought leadership', 3, '{"focus": "kols, expert_opinions, guidelines"}', '{"require_expert_sources": true}'),
('Market Dynamics', 'Market trends and future projections', 2, '{"focus": "trends, projections, dynamics"}', '{"analytical_focus": true}'),
('Strategic Intelligence', 'Strategic insights and recommendations', 1, '{"focus": "strategy, insights, recommendations"}', '{"synthesis_required": true});

-- Drug Requests Table
CREATE TABLE drug_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drug_name VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'partial_failure')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    user_id UUID,
    total_categories INTEGER DEFAULT 17,
    completed_categories INTEGER DEFAULT 0,
    failed_categories TEXT[] DEFAULT '{}',

    -- Indexing for performance
    CONSTRAINT valid_completed_categories CHECK (completed_categories >= 0 AND completed_categories <= total_categories)
);

-- Category Results Table
CREATE TABLE category_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL REFERENCES drug_requests(id) ON DELETE CASCADE,
    category_name VARCHAR(100) NOT NULL,
    category_id INTEGER NOT NULL REFERENCES pharmaceutical_categories(id),
    summary TEXT NOT NULL,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    data_quality_score DECIMAL(3,2) CHECK (data_quality_score >= 0 AND data_quality_score <= 1),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    processing_time_ms INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Composite index for efficient querying
    UNIQUE(request_id, category_id)
);

-- Source References Table
CREATE TABLE source_references (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_result_id UUID NOT NULL REFERENCES category_results(id) ON DELETE CASCADE,
    api_provider VARCHAR(20) NOT NULL CHECK (api_provider IN ('chatgpt', 'perplexity', 'grok', 'gemini', 'tavily')),
    source_url TEXT,
    source_title VARCHAR(500),
    source_type VARCHAR(20) DEFAULT 'other' CHECK (source_type IN ('research_paper', 'clinical_trial', 'news', 'regulatory', 'other')),
    content_snippet TEXT NOT NULL,
    relevance_score DECIMAL(3,2) CHECK (relevance_score >= 0 AND relevance_score <= 1),
    credibility_score DECIMAL(3,2) CHECK (credibility_score >= 0 AND credibility_score <= 1),
    published_date DATE,
    authors VARCHAR(1000),
    journal_name VARCHAR(300),
    doi VARCHAR(100),
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    api_response_id VARCHAR(100),
    verification_status VARCHAR(20) DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verified', 'disputed', 'invalid')),
    verified_at TIMESTAMP WITH TIME ZONE,
    verified_by VARCHAR(100)
);

-- Source Conflicts Table
CREATE TABLE source_conflicts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_result_id UUID NOT NULL REFERENCES category_results(id) ON DELETE CASCADE,
    source_a_id UUID NOT NULL REFERENCES source_references(id) ON DELETE CASCADE,
    source_b_id UUID NOT NULL REFERENCES source_references(id) ON DELETE CASCADE,
    conflict_type VARCHAR(20) NOT NULL CHECK (conflict_type IN ('factual', 'temporal', 'methodological')),
    conflict_description VARCHAR(1000) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    resolution_strategy VARCHAR(30) NOT NULL,
    resolved_value TEXT,
    resolution_confidence DECIMAL(3,2) CHECK (resolution_confidence >= 0 AND resolution_confidence <= 1),
    resolution_rationale VARCHAR(1500) NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(100),

    -- Ensure sources are different
    CHECK (source_a_id != source_b_id)
);

-- Audit Events Table (7-year retention for regulatory compliance)
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID REFERENCES drug_requests(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    event_description VARCHAR(1000) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    user_id VARCHAR(100),
    ip_address INET,
    user_agent VARCHAR(500),
    api_endpoint VARCHAR(200),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    correlation_id UUID NOT NULL,

    -- Partition by year for efficient management
    PARTITION BY RANGE (timestamp)
);

-- Create audit partitions for next 7 years
CREATE TABLE audit_events_2024 PARTITION OF audit_events
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE audit_events_2025 PARTITION OF audit_events
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
-- ... continue for 7 years

-- Indexes for performance
CREATE INDEX idx_drug_requests_status ON drug_requests(status);
CREATE INDEX idx_drug_requests_created_at ON drug_requests(created_at);
CREATE INDEX idx_category_results_request_id ON category_results(request_id);
CREATE INDEX idx_category_results_status ON category_results(status);
CREATE INDEX idx_source_references_category_result_id ON source_references(category_result_id);
CREATE INDEX idx_source_references_api_provider ON source_references(api_provider);
CREATE INDEX idx_source_references_verification_status ON source_references(verification_status);
CREATE INDEX idx_source_conflicts_category_result_id ON source_conflicts(category_result_id);
CREATE INDEX idx_audit_events_timestamp ON audit_events(timestamp);
CREATE INDEX idx_audit_events_entity ON audit_events(entity_type, entity_id);
```

## Security Architecture

### Authentication and Authorization
```python
# apps/backend/src/core/security.py
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
import bcrypt

security = HTTPBearer()

class SecurityManager:
    """
    Handles authentication and authorization for pharmaceutical data access
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expire_minutes = 1440  # 24 hours

    def create_access_token(self, user_id: str, permissions: List[str]) -> str:
        """Create JWT token with pharmaceutical data access permissions"""
        expire = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)

        payload = {
            "user_id": user_id,
            "permissions": permissions,
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": "cognito-ai-engine"
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return user information"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check expiration
            if datetime.utcfromtimestamp(payload["exp"]) < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired"
                )

            return payload

        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Dependency for protected routes
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and verify current user from JWT token"""
    security_manager = SecurityManager(settings.JWT_SECRET_KEY)
    user_data = security_manager.verify_token(credentials.credentials)
    return user_data

# Permission-based access control
class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, current_user: dict = Depends(get_current_user)):
        if self.required_permission not in current_user.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {self.required_permission}"
            )
        return current_user

# Usage in routes
@router.get("/api/v1/requests/{request_id}")
async def get_request(
    request_id: str,
    current_user: dict = Depends(PermissionChecker("read_drug_requests"))
):
    # Implementation here
    pass
```

### API Rate Limiting and Security
```python
# apps/backend/src/middleware/security.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379/2"
)

class SecurityMiddleware:
    """
    Security middleware for pharmaceutical data protection
    """

    @staticmethod
    @limiter.limit("100/minute")  # API rate limiting
    async def rate_limit_requests(request: Request):
        """Rate limit API requests to prevent abuse"""
        pass

    @staticmethod
    async def audit_api_access(request: Request, call_next):
        """Audit all API access for regulatory compliance"""
        start_time = time.time()

        # Log request details
        audit_data = {
            "method": request.method,
            "url": str(request.url),
            "client_ip": get_remote_address(request),
            "user_agent": request.headers.get("user-agent"),
            "timestamp": datetime.utcnow().isoformat()
        }

        response = await call_next(request)

        # Log response details
        audit_data.update({
            "status_code": response.status_code,
            "processing_time": time.time() - start_time
        })

        # Store in audit log
        await store_audit_log(audit_data)

        return response
```

## Monitoring and Logging

### Structured Logging Configuration
```python
# apps/backend/src/config/logging.py
import logging
import structlog
from datetime import datetime

def configure_logging():
    """Configure structured logging for pharmaceutical compliance"""

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=False,
    )

class PharmaceuticalLogger:
    """
    Specialized logger for pharmaceutical data processing with regulatory compliance
    """

    def __init__(self):
        self.logger = structlog.get_logger()

    def log_processing_start(self, request_id: str, drug_name: str):
        """Log start of pharmaceutical data processing"""
        self.logger.info(
            "pharmaceutical_processing_started",
            request_id=request_id,
            drug_name=drug_name,
            event_type="processing_start",
            compliance_level="regulatory"
        )

    def log_category_completion(self, request_id: str, category: str, sources_count: int):
        """Log completion of category processing"""
        self.logger.info(
            "category_processing_completed",
            request_id=request_id,
            category=category,
            sources_count=sources_count,
            event_type="category_completion"
        )

    def log_source_conflict(self, request_id: str, conflict_data: dict):
        """Log source conflicts for regulatory tracking"""
        self.logger.warning(
            "source_conflict_detected",
            request_id=request_id,
            conflict_type=conflict_data["type"],
            severity=conflict_data["severity"],
            event_type="conflict_detection",
            compliance_level="critical"
        )

    def log_api_error(self, provider: str, error: str, request_id: str):
        """Log API integration errors"""
        self.logger.error(
            "api_integration_error",
            provider=provider,
            error=error,
            request_id=request_id,
            event_type="api_error",
            requires_investigation=True
        )
```

## Performance Optimization

### Database Optimization
```sql
-- Performance optimization queries
-- /opt/cognito-ai/backend/database/optimizations.sql

-- Optimize category results queries
CREATE INDEX CONCURRENTLY idx_category_results_composite
ON category_results(request_id, status, completed_at DESC)
WHERE status = 'completed';

-- Optimize source reference lookups
CREATE INDEX CONCURRENTLY idx_source_references_composite
ON source_references(category_result_id, verification_status, credibility_score DESC)
WHERE verification_status IN ('verified', 'pending');

-- Optimize audit queries with partial index
CREATE INDEX CONCURRENTLY idx_audit_events_recent
ON audit_events(timestamp DESC, event_type)
WHERE timestamp >= CURRENT_DATE - INTERVAL '90 days';

-- Materialized view for dashboard analytics
CREATE MATERIALIZED VIEW mv_request_analytics AS
SELECT
    DATE_TRUNC('day', created_at) as date,
    status,
    COUNT(*) as request_count,
    AVG(EXTRACT(EPOCH FROM (completed_at - created_at))/60) as avg_processing_minutes,
    COUNT(DISTINCT drug_name) as unique_drugs
FROM drug_requests
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at), status;

-- Refresh materialized view hourly
CREATE OR REPLACE FUNCTION refresh_analytics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_request_analytics;
END;
$$ LANGUAGE plpgsql;
```

### Caching Strategy
```python
# apps/backend/src/core/caching.py
import redis
import json
from typing import Optional, Any
from datetime import timedelta

class PharmaceuticalCache:
    """
    Specialized caching for pharmaceutical data with appropriate TTLs
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = 3600  # 1 hour

        # Different TTLs for different data types
        self.ttl_config = {
            "category_config": 86400,     # 24 hours - relatively stable
            "drug_request": 1800,         # 30 minutes - frequently updated
            "source_analysis": 3600,      # 1 hour - processed data
            "conflict_resolution": 7200,  # 2 hours - complex computations
            "api_response": 300,          # 5 minutes - fresh data needed
        }

    async def get_cached_result(self, key: str, data_type: str = "default") -> Optional[Any]:
        """Get cached pharmaceutical processing result"""
        try:
            cached_data = await self.redis.get(f"pharma:{data_type}:{key}")
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            # Log error but don't fail the operation
            logger.error(f"Cache retrieval error: {str(e)}")
            return None

    async def cache_result(self, key: str, data: Any, data_type: str = "default") -> bool:
        """Cache pharmaceutical processing result with appropriate TTL"""
        try:
            ttl = self.ttl_config.get(data_type, self.default_ttl)
            await self.redis.setex(
                f"pharma:{data_type}:{key}",
                ttl,
                json.dumps(data, default=str)
            )
            return True
        except Exception as e:
            logger.error(f"Cache storage error: {str(e)}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        try:
            keys = await self.redis.keys(f"pharma:{pattern}*")
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache invalidation error: {str(e)}")
            return 0
```

## Architecture Summary and Validation

### Architecture Compliance Matrix

| Requirement | Implementation | Status | Notes |
|-------------|----------------|--------|-------|
| **Frontend/Backend Separation** | Independent Next.js and FastAPI apps | ✅ Complete | Teams can develop independently |
| **Source Tracking** | Comprehensive source attribution system | ✅ Complete | Full regulatory compliance |
| **Dynamic Categories** | Database-driven category processor | ✅ Complete | Single processor handles all 17 categories |
| **Real-time Updates** | WebSocket with Redis pub/sub | ✅ Complete | Live processing status updates |
| **Audit Trail** | 7-year retention audit system | ✅ Complete | Pharmaceutical regulatory compliance |
| **Multi-API Integration** | Coordinated ChatGPT/Perplexity/Grok/Gemini/Tavily | ✅ Complete | Parallel processing with rate limiting |
| **Conflict Resolution** | Automated conflict detection and resolution | ✅ Complete | Source credibility and temporal analysis |
| **Single Server Deployment** | SystemD services without containerization | ✅ Complete | As requested by user |
| **Background Processing** | Celery with controlled concurrency | ✅ Complete | Handles long-running pharmaceutical processing |
| **Type Safety** | Shared TypeScript/Python types | ✅ Complete | Contract consistency across stack |

### Performance Benchmarks

**Expected Performance Characteristics:**
- **Drug Request Processing**: 3-5 minutes for all 17 categories
- **API Response Time**: < 200ms for standard queries
- **WebSocket Latency**: < 50ms for real-time updates
- **Database Query Performance**: < 100ms for complex joins
- **Concurrent Processing**: 10+ parallel drug requests
- **Source Verification**: < 30 seconds per source batch

### Security Compliance

**Implemented Security Measures:**
- JWT-based authentication with role-based permissions
- API rate limiting (100 requests/minute per IP)
- Comprehensive audit logging for all pharmaceutical data access
- Input validation and SQL injection prevention
- CORS configuration for frontend integration
- Security headers (X-Frame-Options, HSTS, X-Content-Type-Options)
- Password hashing with bcrypt
- Database row-level security for multi-tenant support

### Scalability Path

**Future Scaling Options:**
1. **Horizontal Backend Scaling**: Multiple FastAPI instances behind load balancer
2. **Database Scaling**: Read replicas and connection pooling
3. **Cache Scaling**: Redis cluster for distributed caching
4. **Background Processing**: Additional Celery workers and queues
5. **Frontend Scaling**: CDN integration and edge deployment
6. **API Gateway**: Rate limiting and API versioning at gateway level

### Maintenance and Operations

**Operational Procedures:**
- **Backup Strategy**: Daily PostgreSQL backups with 7-year retention
- **Log Rotation**: Structured logs with automatic rotation and archival
- **Health Monitoring**: Endpoint monitoring and alerting
- **Database Maintenance**: Monthly VACUUM and index analysis
- **Security Updates**: Quarterly dependency updates and security patches
- **Performance Review**: Monthly performance analysis and optimization

**Rationale for Final Architecture:**

1. **Complete Independence**: Frontend and backend teams can develop, test, and deploy independently while maintaining integration through well-defined contracts
2. **Pharmaceutical Compliance**: Comprehensive source tracking, audit trails, and conflict resolution meet pharmaceutical industry regulatory requirements
3. **Scalable Foundation**: Architecture supports future growth in users, data volume, and additional pharmaceutical categories
4. **Real-time Capabilities**: WebSocket integration provides immediate feedback during long-running pharmaceutical processing tasks
5. **Maintainable Design**: Clear separation of concerns, comprehensive logging, and structured error handling ensure long-term maintainability
6. **Performance Optimized**: Caching, database optimization, and background processing provide responsive user experience for pharmaceutical professionals

## Coding Standards and Best Practices

### JSDoc Documentation Requirements

#### Frontend TypeScript/JavaScript Standards

All public functions, interfaces, types, and classes **MUST** include comprehensive JSDoc comments following these standards:

```typescript
/**
 * Processes pharmaceutical drug requests with comprehensive source tracking
 * and real-time status updates for regulatory compliance.
 *
 * @template T - The type of the drug request data
 * @param {string} drugName - The name of the pharmaceutical drug to process
 * @param {RequestOptions<T>} options - Configuration options for processing
 * @param {string} options.userId - Optional user identifier for audit tracking
 * @param {number[]} options.priorityCategories - Category IDs to process first
 * @param {boolean} options.enableRealTime - Enable WebSocket updates (default: true)
 * @returns {Promise<ProcessingResult<T>>} Promise resolving to processing results
 * @throws {ValidationError} When drugName is invalid or empty
 * @throws {AuthorizationError} When user lacks pharmaceutical data access permissions
 *
 * @example
 * ```typescript
 * const result = await processDrugRequest('Aspirin', {
 *   userId: 'user-123',
 *   priorityCategories: [1, 2, 3],
 *   enableRealTime: true
 * });
 * console.log(`Processed ${result.completedCategories} categories`);
 * ```
 *
 * @since 1.0.0
 * @version 1.2.0
 * @author CognitoAI Development Team
 * @see {@link SourceTrackingManager} for source attribution details
 * @see {@link ConflictResolver} for handling source conflicts
 */
async function processDrugRequest<T>(
  drugName: string,
  options: RequestOptions<T>
): Promise<ProcessingResult<T>> {
  // Implementation
}

/**
 * Represents a pharmaceutical intelligence request with comprehensive
 * source tracking and audit trail for regulatory compliance.
 *
 * @interface DrugRequestInterface
 * @since 1.0.0
 * @version 1.1.0
 *
 * @example
 * ```typescript
 * const request: DrugRequestInterface = {
 *   id: 'req-123',
 *   drugName: 'Ibuprofen',
 *   status: 'processing',
 *   createdAt: '2024-01-01T10:00:00Z',
 *   totalCategories: 17,
 *   completedCategories: 5
 * };
 * ```
 */
interface DrugRequestInterface {
  /**
   * Unique identifier for the pharmaceutical request.
   * Generated using UUID v4 for global uniqueness.
   * @since 1.0.0
   */
  id: string;

  /**
   * Name of the pharmaceutical drug being analyzed.
   * Must be non-empty and contain only valid characters.
   * @since 1.0.0
   * @example "Aspirin", "Ibuprofen", "Acetaminophen"
   */
  drugName: string;

  /**
   * Current processing status of the pharmaceutical request.
   * Used for real-time status tracking and user feedback.
   * @since 1.0.0
   */
  status: 'pending' | 'processing' | 'completed' | 'failed';

  /**
   * ISO 8601 timestamp when the request was created.
   * Used for audit trail and performance tracking.
   * @since 1.0.0
   */
  createdAt: string;

  /**
   * Total number of pharmaceutical categories to process.
   * Default is 17 for comprehensive drug intelligence.
   * @default 17
   * @since 1.0.0
   */
  totalCategories: number;

  /**
   * Number of categories successfully completed.
   * Updated in real-time during processing for progress tracking.
   * @since 1.0.0
   */
  completedCategories: number;
}

/**
 * Custom React hook for managing pharmaceutical drug request state
 * with real-time updates and comprehensive error handling.
 *
 * @param {string} requestId - The unique identifier of the drug request
 * @returns {DrugRequestHookReturn} Hook return object with state and actions
 *
 * @example
 * ```typescript
 * function DrugRequestDetails({ requestId }: { requestId: string }) {
 *   const {
 *     data,
 *     loading,
 *     error,
 *     refetch,
 *     subscribeToUpdates
 *   } = useDrugRequest(requestId);
 *
 *   useEffect(() => {
 *     const unsubscribe = subscribeToUpdates();
 *     return unsubscribe;
 *   }, [subscribeToUpdates]);
 *
 *   if (loading) return <LoadingSpinner />;
 *   if (error) return <ErrorMessage error={error} />;
 *
 *   return <RequestDisplay request={data} />;
 * }
 * ```
 *
 * @since 1.0.0
 * @version 1.1.0
 */
function useDrugRequest(requestId: string): DrugRequestHookReturn {
  // Hook implementation
}

/**
 * Zustand store for managing pharmaceutical drug request state
 * with persistence and real-time synchronization capabilities.
 *
 * @namespace DrugRequestStore
 * @since 1.0.0
 * @version 1.2.0
 *
 * @example
 * ```typescript
 * // Using the store in a component
 * const { requests, createRequest, fetchRequests } = useDrugRequestStore();
 *
 * // Create a new pharmaceutical request
 * await createRequest('Metformin');
 *
 * // Fetch all user's requests
 * await fetchRequests();
 * ```
 */
class DrugRequestStore {
  /**
   * Array of all pharmaceutical drug requests.
   * Automatically synchronized with backend state.
   * @since 1.0.0
   */
  requests: DrugRequest[];

  /**
   * Creates a new pharmaceutical intelligence request.
   * Automatically initiates processing for all 17 categories.
   *
   * @param {string} drugName - Name of the pharmaceutical drug
   * @param {CreateRequestOptions} options - Additional request options
   * @returns {Promise<void>} Promise that resolves when request is created
   * @throws {ValidationError} When drugName is invalid
   *
   * @since 1.0.0
   */
  createRequest(drugName: string, options?: CreateRequestOptions): Promise<void>;
}
```

#### Backend Python Standards

All public functions, classes, and methods **MUST** include comprehensive docstrings following Google/Sphinx style:

```python
class SourceAwareCategoryProcessor:
    """
    Central processor for handling all 17 pharmaceutical categories dynamically
    with comprehensive source tracking and regulatory compliance.

    This class implements the core pharmaceutical intelligence gathering logic,
    coordinating multiple AI APIs, detecting source conflicts, and maintaining
    comprehensive audit trails for regulatory compliance.

    Attributes:
        db (AsyncSession): Database session for persistence operations
        redis (Redis): Redis client for caching and real-time updates
        api_manager (MultiAPIManager): Coordinator for external API calls
        audit_logger (AuditLogger): Logger for regulatory compliance tracking
        conflict_resolver (SourceConflictResolver): Handler for source conflicts
        source_verifier (SourceVerifier): Validator for source authenticity

    Example:
        >>> processor = SourceAwareCategoryProcessor(
        ...     db=db_session,
        ...     redis=redis_client,
        ...     api_manager=api_manager,
        ...     audit_logger=logger
        ... )
        >>> result = await processor.process_drug_request("Aspirin", "req-123")
        >>> print(f"Processed {result.successful_categories} categories")

    Note:
        This processor is designed for pharmaceutical regulatory environments
        requiring comprehensive audit trails and source attribution.

    Warning:
        All operations are logged for regulatory compliance. Ensure proper
        data handling procedures are followed.

    See Also:
        - :class:`MultiAPIManager`: API coordination and rate limiting
        - :class:`SourceConflictResolver`: Conflict detection and resolution
        - :class:`AuditLogger`: Regulatory compliance logging

    Since:
        Version 1.0.0

    Version:
        1.2.0 - Added conflict resolution capabilities
    """

    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        api_manager: MultiAPIManager,
        audit_logger: AuditLogger
    ) -> None:
        """
        Initialize the pharmaceutical category processor.

        Args:
            db: Async database session for data persistence
            redis: Redis client for caching and pub/sub messaging
            api_manager: Manager for coordinating external API calls
            audit_logger: Logger for regulatory compliance tracking

        Raises:
            ConnectionError: If database or Redis connection fails
            ConfigurationError: If required configuration is missing

        Example:
            >>> processor = SourceAwareCategoryProcessor(
            ...     db=get_db_session(),
            ...     redis=get_redis_client(),
            ...     api_manager=MultiAPIManager(),
            ...     audit_logger=AuditLogger()
            ... )
        """
        self.db = db
        self.redis = redis
        self.api_manager = api_manager
        self.audit_logger = audit_logger
        self.conflict_resolver = SourceConflictResolver()
        self.source_verifier = SourceVerifier()

    async def process_drug_request(
        self,
        drug_name: str,
        request_id: str
    ) -> ProcessingResult:
        """
        Process a complete pharmaceutical intelligence request for all categories.

        This method orchestrates the entire pharmaceutical data gathering pipeline:
        1. Loads dynamic category configurations from database
        2. Executes parallel API calls with rate limiting
        3. Detects and resolves conflicts between sources
        4. Generates comprehensive results with audit trails

        Args:
            drug_name: Name of the pharmaceutical drug to analyze.
                      Must be non-empty and contain valid characters.
            request_id: Unique identifier for tracking this request.
                       Used for audit trails and real-time updates.

        Returns:
            ProcessingResult containing:
            - request_id: The processed request identifier
            - successful_categories: Number of categories processed successfully
            - failed_categories: List of category names that failed processing
            - total_sources: Total number of sources discovered
            - processing_time: Total time spent processing (timedelta)

        Raises:
            ProcessingException: If critical processing failure occurs
            ValidationError: If drug_name or request_id is invalid
            DatabaseError: If database operations fail
            APIException: If all API providers fail

        Example:
            >>> result = await processor.process_drug_request(
            ...     "Metformin",
            ...     "req-abc123"
            ... )
            >>> print(f"Success: {result.successful_categories}/17 categories")
            >>> print(f"Sources: {result.total_sources} discovered")
            >>> print(f"Time: {result.processing_time.total_seconds()}s")

        Note:
            This method implements comprehensive audit logging for pharmaceutical
            regulatory compliance. All operations are tracked with timestamps,
            user context, and detailed change records.

        Warning:
            Long-running operation (3-5 minutes typical). Use background
            processing for production deployments.

        See Also:
            - :meth:`_process_single_category`: Individual category processing
            - :class:`ProcessingResult`: Return value structure
            - :class:`AuditLogger`: Compliance logging details

        Since:
            Version 1.0.0

        Version:
            1.2.0 - Added source conflict resolution
            1.1.0 - Added real-time progress updates
        """
        # Implementation details...

    def _load_category_configs(self) -> List[Dict[str, Any]]:
        """
        Load all 17 pharmaceutical category configurations from database.

        Private method that retrieves dynamic category configurations including
        search parameters, processing rules, prompt templates, and verification
        criteria for each pharmaceutical category.

        Returns:
            List of dictionaries containing category configuration data.
            Each dictionary includes:
            - id: Unique category identifier
            - name: Human-readable category name
            - description: Category description
            - search_parameters: JSON configuration for API searches
            - processing_rules: JSON rules for data processing
            - prompt_templates: Templates for AI API prompts
            - verification_criteria: Rules for source verification
            - conflict_resolution_strategy: Strategy for resolving conflicts

        Raises:
            DatabaseError: If database query fails
            ConfigurationError: If category configuration is invalid

        Note:
            This method caches results in Redis for performance optimization.
            Cache TTL is set to 24 hours as category configs are relatively stable.

        Since:
            Version 1.0.0
        """
        # Implementation details...

@dataclass
class ProcessingResult:
    """
    Result container for pharmaceutical drug request processing operations.

    This dataclass encapsulates all results from processing a pharmaceutical
    intelligence request, including success metrics, failure information,
    and performance data for monitoring and audit purposes.

    Attributes:
        request_id: Unique identifier of the processed request
        successful_categories: Count of categories processed without errors
        failed_categories: List of category names that encountered failures
        total_sources: Total number of sources discovered across all categories
        processing_time: Total time spent processing the request

    Example:
        >>> result = ProcessingResult(
        ...     request_id="req-123",
        ...     successful_categories=15,
        ...     failed_categories=["Patent Landscape", "Regulatory Status"],
        ...     total_sources=247,
        ...     processing_time=timedelta(minutes=4, seconds=32)
        ... )
        >>> print(f"Success rate: {result.success_rate:.1%}")

    Note:
        All timestamps use UTC timezone for consistent audit trails.

    Since:
        Version 1.0.0
    """
    request_id: str
    successful_categories: int
    failed_categories: List[str]
    total_sources: int
    processing_time: timedelta

    @property
    def success_rate(self) -> float:
        """
        Calculate the success rate as a percentage of completed categories.

        Returns:
            Float between 0.0 and 1.0 representing success percentage.

        Example:
            >>> result = ProcessingResult(successful_categories=15, ...)
            >>> print(f"Success: {result.success_rate:.1%}")  # "Success: 88.2%"
        """
        total = self.successful_categories + len(self.failed_categories)
        return self.successful_categories / total if total > 0 else 0.0
```

### Object-Oriented Programming Standards

#### Frontend OOP Principles

**1. Single Responsibility Principle (SRP)**
```typescript
/**
 * Handles pharmaceutical drug request creation and validation.
 * Responsible solely for request management, not UI rendering or data fetching.
 *
 * @class DrugRequestManager
 * @since 1.0.0
 */
class DrugRequestManager {
  /**
   * Validates pharmaceutical drug name according to regulatory standards.
   *
   * @param {string} drugName - The drug name to validate
   * @returns {ValidationResult} Validation result with errors if any
   * @since 1.0.0
   */
  validateDrugName(drugName: string): ValidationResult {
    // Single responsibility: validation only
  }

  /**
   * Creates a new pharmaceutical intelligence request.
   *
   * @param {CreateRequestData} data - Request creation data
   * @returns {Promise<DrugRequest>} The created request
   * @since 1.0.0
   */
  async createRequest(data: CreateRequestData): Promise<DrugRequest> {
    // Single responsibility: request creation only
  }
}

/**
 * Manages real-time WebSocket connections for pharmaceutical processing updates.
 * Responsible solely for WebSocket communication, not business logic.
 *
 * @class WebSocketManager
 * @since 1.0.0
 */
class WebSocketManager {
  /**
   * Establishes WebSocket connection for real-time pharmaceutical updates.
   *
   * @param {string} requestId - The drug request ID to monitor
   * @returns {Promise<WebSocket>} The established WebSocket connection
   * @since 1.0.0
   */
  async connect(requestId: string): Promise<WebSocket> {
    // Single responsibility: WebSocket management only
  }
}
```

**2. Open/Closed Principle (OCP)**
```typescript
/**
 * Abstract base class for pharmaceutical data processors.
 * Open for extension through inheritance, closed for modification.
 *
 * @abstract
 * @class PharmaceuticalProcessor
 * @since 1.0.0
 */
abstract class PharmaceuticalProcessor {
  /**
   * Processes pharmaceutical category data.
   * Template method that defines the processing algorithm.
   *
   * @param {CategoryData} data - The category data to process
   * @returns {Promise<ProcessedResult>} The processed result
   * @since 1.0.0
   */
  async processCategory(data: CategoryData): Promise<ProcessedResult> {
    const validated = await this.validateData(data);
    const processed = await this.performProcessing(validated);
    const verified = await this.verifyResults(processed);
    return this.formatOutput(verified);
  }

  /**
   * Validates category data before processing.
   * Can be overridden by subclasses for specific validation logic.
   *
   * @protected
   * @param {CategoryData} data - Data to validate
   * @returns {Promise<ValidatedData>} Validated data
   * @since 1.0.0
   */
  protected abstract validateData(data: CategoryData): Promise<ValidatedData>;

  /**
   * Performs the core processing logic.
   * Must be implemented by concrete subclasses.
   *
   * @protected
   * @param {ValidatedData} data - Validated input data
   * @returns {Promise<ProcessedData>} Processed data
   * @since 1.0.0
   */
  protected abstract performProcessing(data: ValidatedData): Promise<ProcessedData>;
}

/**
 * Concrete implementation for clinical trials category processing.
 * Extends base processor with clinical trials-specific logic.
 *
 * @class ClinicalTrialsProcessor
 * @extends PharmaceuticalProcessor
 * @since 1.0.0
 */
class ClinicalTrialsProcessor extends PharmaceuticalProcessor {
  /**
   * Validates clinical trials data with FDA compliance checks.
   *
   * @protected
   * @param {CategoryData} data - Clinical trials data
   * @returns {Promise<ValidatedData>} FDA-validated data
   * @since 1.0.0
   */
  protected async validateData(data: CategoryData): Promise<ValidatedData> {
    // Clinical trials specific validation
  }

  /**
   * Processes clinical trials with phase-specific analysis.
   *
   * @protected
   * @param {ValidatedData} data - Validated clinical data
   * @returns {Promise<ProcessedData>} Phase-analyzed results
   * @since 1.0.0
   */
  protected async performProcessing(data: ValidatedData): Promise<ProcessedData> {
    // Clinical trials specific processing
  }
}
```

**3. Interface Segregation Principle (ISP)**
```typescript
/**
 * Interface for pharmaceutical data reading operations.
 * Segregated from writing operations to follow ISP.
 *
 * @interface PharmaceuticalReader
 * @since 1.0.0
 */
interface PharmaceuticalReader {
  /**
   * Reads pharmaceutical request by ID.
   *
   * @param {string} id - Request identifier
   * @returns {Promise<DrugRequest | null>} The request or null if not found
   * @since 1.0.0
   */
  readRequest(id: string): Promise<DrugRequest | null>;

  /**
   * Reads all requests for a specific user.
   *
   * @param {string} userId - User identifier
   * @returns {Promise<DrugRequest[]>} Array of user's requests
   * @since 1.0.0
   */
  readUserRequests(userId: string): Promise<DrugRequest[]>;
}

/**
 * Interface for pharmaceutical data writing operations.
 * Segregated from reading operations to follow ISP.
 *
 * @interface PharmaceuticalWriter
 * @since 1.0.0
 */
interface PharmaceuticalWriter {
  /**
   * Creates a new pharmaceutical request.
   *
   * @param {CreateRequestData} data - Request creation data
   * @returns {Promise<DrugRequest>} The created request
   * @since 1.0.0
   */
  createRequest(data: CreateRequestData): Promise<DrugRequest>;

  /**
   * Updates existing pharmaceutical request.
   *
   * @param {string} id - Request identifier
   * @param {UpdateRequestData} data - Update data
   * @returns {Promise<DrugRequest>} The updated request
   * @since 1.0.0
   */
  updateRequest(id: string, data: UpdateRequestData): Promise<DrugRequest>;
}

/**
 * Interface for real-time pharmaceutical updates.
 * Segregated from CRUD operations to follow ISP.
 *
 * @interface PharmaceuticalRealTimeUpdater
 * @since 1.0.0
 */
interface PharmaceuticalRealTimeUpdater {
  /**
   * Subscribes to real-time updates for a pharmaceutical request.
   *
   * @param {string} requestId - Request to monitor
   * @param {UpdateCallback} callback - Function to call on updates
   * @returns {Promise<UnsubscribeFunction>} Function to unsubscribe
   * @since 1.0.0
   */
  subscribeToUpdates(
    requestId: string,
    callback: UpdateCallback
  ): Promise<UnsubscribeFunction>;
}
```

**4. Dependency Inversion Principle (DIP)**
```typescript
/**
 * High-level pharmaceutical service that depends on abstractions.
 * Follows DIP by depending on interfaces, not concrete implementations.
 *
 * @class PharmaceuticalService
 * @since 1.0.0
 */
class PharmaceuticalService {
  /**
   * Creates pharmaceutical service with dependency injection.
   *
   * @param {PharmaceuticalRepository} repository - Data access abstraction
   * @param {NotificationService} notifications - Notification abstraction
   * @param {AuditLogger} logger - Audit logging abstraction
   * @since 1.0.0
   */
  constructor(
    private readonly repository: PharmaceuticalRepository,
    private readonly notifications: NotificationService,
    private readonly logger: AuditLogger
  ) {}

  /**
   * Processes pharmaceutical request using injected dependencies.
   *
   * @param {ProcessRequestCommand} command - Processing command
   * @returns {Promise<ProcessingResult>} Processing result
   * @since 1.0.0
   */
  async processRequest(command: ProcessRequestCommand): Promise<ProcessingResult> {
    await this.logger.logProcessingStart(command.requestId);
    const result = await this.repository.processRequest(command);
    await this.notifications.notifyProcessingComplete(result);
    return result;
  }
}

/**
 * Abstract repository interface for pharmaceutical data operations.
 * High-level abstraction that concrete implementations depend on.
 *
 * @interface PharmaceuticalRepository
 * @since 1.0.0
 */
interface PharmaceuticalRepository {
  /**
   * Processes pharmaceutical request with source tracking.
   *
   * @param {ProcessRequestCommand} command - Processing command
   * @returns {Promise<ProcessingResult>} Processing result with sources
   * @since 1.0.0
   */
  processRequest(command: ProcessRequestCommand): Promise<ProcessingResult>;
}
```

#### Backend Python OOP Standards

**1. Class Design Principles**
```python
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

class PharmaceuticalDataProcessor(ABC):
    """
    Abstract base class for pharmaceutical data processing operations.

    This class defines the template method pattern for processing pharmaceutical
    data with consistent audit logging, error handling, and source tracking.
    Concrete subclasses implement category-specific processing logic.

    Attributes:
        _audit_logger (AuditLogger): Logger for regulatory compliance
        _source_tracker (SourceTracker): Tracker for source attribution

    Example:
        >>> class ClinicalTrialsProcessor(PharmaceuticalDataProcessor):
        ...     async def _process_category_data(self, data):
        ...         return await self._process_clinical_trials(data)
        >>> processor = ClinicalTrialsProcessor(logger, tracker)
        >>> result = await processor.process_data(category_data)

    Note:
        All subclasses must implement regulatory compliance logging
        and comprehensive source attribution for audit purposes.

    Since:
        Version 1.0.0
    """

    def __init__(self, audit_logger: AuditLogger, source_tracker: SourceTracker) -> None:
        """
        Initialize pharmaceutical data processor.

        Args:
            audit_logger: Logger for regulatory compliance tracking
            source_tracker: Tracker for comprehensive source attribution

        Raises:
            ValueError: If logger or tracker is None
        """
        if not audit_logger or not source_tracker:
            raise ValueError("Logger and source tracker are required")

        self._audit_logger = audit_logger
        self._source_tracker = source_tracker

    async def process_data(self, data: CategoryData) -> ProcessingResult:
        """
        Template method for processing pharmaceutical category data.

        This method defines the standard processing pipeline that all
        pharmaceutical categories must follow for regulatory compliance.

        Args:
            data: Category-specific data to process

        Returns:
            ProcessingResult with sources and audit trail

        Raises:
            ProcessingError: If processing fails
            ValidationError: If data validation fails

        Since:
            Version 1.0.0
        """
        await self._audit_logger.log_processing_start(data.category_name)

        try:
            validated_data = await self._validate_data(data)
            processed_result = await self._process_category_data(validated_data)
            sources = await self._source_tracker.track_sources(processed_result)

            await self._audit_logger.log_processing_success(
                data.category_name,
                len(sources)
            )

            return ProcessingResult(
                result=processed_result,
                sources=sources,
                category=data.category_name
            )

        except Exception as e:
            await self._audit_logger.log_processing_error(data.category_name, str(e))
            raise ProcessingError(f"Failed to process {data.category_name}: {e}")

    @abstractmethod
    async def _process_category_data(self, data: ValidatedCategoryData) -> Any:
        """
        Process category-specific pharmaceutical data.

        This method must be implemented by concrete subclasses to handle
        the specific processing logic for each pharmaceutical category.

        Args:
            data: Validated category data ready for processing

        Returns:
            Category-specific processing result

        Raises:
            NotImplementedError: If not implemented by subclass

        Note:
            Implementation must maintain source attribution for all
            data transformations and API calls.

        Since:
            Version 1.0.0
        """
        raise NotImplementedError("Subclasses must implement _process_category_data")

    async def _validate_data(self, data: CategoryData) -> ValidatedCategoryData:
        """
        Validate pharmaceutical category data before processing.

        Default validation can be overridden by subclasses for
        category-specific validation requirements.

        Args:
            data: Raw category data to validate

        Returns:
            Validated data ready for processing

        Raises:
            ValidationError: If validation fails

        Since:
            Version 1.0.0
        """
        if not data.drug_name:
            raise ValidationError("Drug name is required")
        if not data.category_name:
            raise ValidationError("Category name is required")

        return ValidatedCategoryData(
            drug_name=data.drug_name.strip(),
            category_name=data.category_name.strip(),
            parameters=data.parameters or {}
        )

@runtime_checkable
class SourceTracker(Protocol):
    """
    Protocol for source tracking implementations.

    Defines the interface that all source tracking implementations
    must follow for pharmaceutical regulatory compliance.

    Since:
        Version 1.0.0
    """

    async def track_sources(self, result: Any) -> List[SourceReference]:
        """
        Track and attribute sources for pharmaceutical data.

        Args:
            result: Processing result to analyze for sources

        Returns:
            List of source references with attribution metadata

        Since:
            Version 1.0.0
        """
        ...

class ClinicalTrialsProcessor(PharmaceuticalDataProcessor):
    """
    Concrete processor for clinical trials pharmaceutical category.

    Implements specialized processing logic for clinical trials data
    including FDA phase analysis, efficacy metrics, and safety profiles.

    This processor handles:
    - Phase I/II/III/IV trial analysis
    - Primary and secondary endpoint evaluation
    - Adverse event profile compilation
    - Regulatory submission status tracking

    Example:
        >>> processor = ClinicalTrialsProcessor(audit_logger, source_tracker)
        >>> trials_data = CategoryData(
        ...     drug_name="Metformin",
        ...     category_name="Clinical Trials",
        ...     parameters={"include_phases": ["III", "IV"]}
        ... )
        >>> result = await processor.process_data(trials_data)
        >>> print(f"Found {len(result.sources)} clinical trial sources")

    Note:
        All clinical trials processing follows FDA guidelines and
        maintains comprehensive audit trails for regulatory compliance.

    Since:
        Version 1.0.0

    Version:
        1.1.0 - Added real-world evidence integration
    """

    async def _process_category_data(
        self,
        data: ValidatedCategoryData
    ) -> ClinicalTrialsResult:
        """
        Process clinical trials data with FDA phase analysis.

        Args:
            data: Validated clinical trials data

        Returns:
            ClinicalTrialsResult with phase breakdown and safety profile

        Raises:
            ClinicalDataError: If clinical data processing fails

        Since:
            Version 1.0.0
        """
        try:
            # Phase-specific processing
            phase_data = await self._analyze_trial_phases(data)

            # Safety profile compilation
            safety_profile = await self._compile_safety_data(phase_data)

            # Efficacy analysis
            efficacy_metrics = await self._analyze_efficacy(phase_data)

            return ClinicalTrialsResult(
                drug_name=data.drug_name,
                phases=phase_data,
                safety_profile=safety_profile,
                efficacy_metrics=efficacy_metrics,
                regulatory_status=await self._get_regulatory_status(data)
            )

        except Exception as e:
            raise ClinicalDataError(f"Clinical trials processing failed: {e}")

    async def _analyze_trial_phases(
        self,
        data: ValidatedCategoryData
    ) -> Dict[str, PhaseData]:
        """
        Analyze clinical trial data by FDA phases.

        Args:
            data: Validated category data with trial parameters

        Returns:
            Dictionary mapping phase names to phase-specific data

        Since:
            Version 1.0.0
        """
        phases = {}
        for phase in ["I", "II", "III", "IV"]:
            phase_trials = await self._fetch_phase_trials(data.drug_name, phase)
            phases[phase] = PhaseData(
                trial_count=len(phase_trials),
                enrollment=sum(t.enrollment for t in phase_trials),
                completion_rate=self._calculate_completion_rate(phase_trials),
                trials=phase_trials
            )
        return phases
```

### Documentation Standards Summary

**Required Documentation Elements:**

1. **Class/Interface Documentation:**
   - Purpose and responsibility
   - Usage examples with realistic pharmaceutical data
   - Relationship to other classes/interfaces
   - Version history and changelog
   - Author and maintenance information

2. **Method/Function Documentation:**
   - Clear purpose statement
   - Complete parameter documentation with types and constraints
   - Return value documentation with type and structure
   - Exception documentation with specific error conditions
   - Usage examples with pharmaceutical context
   - Performance considerations for long-running operations
   - Security considerations for sensitive pharmaceutical data

3. **Property/Attribute Documentation:**
   - Purpose and usage
   - Type information and constraints
   - Default values where applicable
   - Examples for complex types
   - Relationship to other properties

4. **Code Organization Standards:**
   - Group related functionality into cohesive classes
   - Use composition over inheritance where appropriate
   - Implement proper error handling with pharmaceutical context
   - Follow SOLID principles for maintainable code
   - Use dependency injection for testability
   - Implement proper logging for audit compliance

**Enforcement:**
- All public APIs must have comprehensive JSDoc/docstring documentation
- Code reviews must verify documentation completeness and accuracy
- Automated tools should validate documentation coverage
- Documentation must be updated with any API changes
- Examples in documentation must be tested and maintained