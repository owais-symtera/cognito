# Components

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
