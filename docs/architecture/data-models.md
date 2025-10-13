# Data Models

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
