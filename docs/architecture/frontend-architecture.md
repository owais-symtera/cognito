# Frontend Architecture

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
