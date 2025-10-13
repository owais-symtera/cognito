# Project Structure

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
