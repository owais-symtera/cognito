# CognitoAI Engine

**Pharmaceutical Intelligence Processing Platform with Source Tracking**

A comprehensive pharmaceutical intelligence platform that aggregates and processes drug information from multiple AI APIs (ChatGPT, Perplexity, Grok, Gemini, Tavily) with complete source tracking and regulatory compliance for pharmaceutical industry requirements.

## 🏗️ Architecture Overview

CognitoAI Engine is built as a monorepo with independent frontend and backend applications, sharing types and utilities through packages. The platform emphasizes:

- **Database-driven dynamic configuration** - All 17 pharmaceutical categories processed by a single dynamic processor
- **Comprehensive source tracking** - Complete audit trails for regulatory compliance
- **Real-time processing** - WebSocket updates during pharmaceutical analysis
- **Multi-API intelligence** - Coordinated data gathering from 5 external AI APIs

## 📁 Project Structure

```
CognitoAI-Engine/
├── apps/
│   ├── backend/           # FastAPI application
│   │   ├── src/
│   │   │   ├── main.py    # Application entry point
│   │   │   ├── core/      # Business logic & processor
│   │   │   ├── database/  # Database models & repositories
│   │   │   ├── api/       # API routes
│   │   │   └── ...
│   │   └── tests/         # Backend test suite
│   └── frontend/          # Next.js application
│       ├── src/
│       │   ├── app/       # Next.js App Router
│       │   ├── components/# React components
│       │   └── ...
│       └── tests/         # Frontend test suite
├── packages/
│   ├── shared-types/      # TypeScript type definitions
│   ├── api-contracts/     # OpenAPI specifications
│   └── testing-utils/     # Shared test utilities
└── docs/                  # Documentation
    ├── stories/           # User stories
    ├── prd/              # Product requirements (sharded)
    └── architecture/      # Architecture documentation (sharded)
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ for frontend development
- Python 3.11+ for backend development
- PostgreSQL 15+ for database
- Redis 7.0+ for caching and background jobs

### Development Setup

1. **Clone and setup workspace:**
   ```bash
   git clone <repository-url>
   cd CognitoAI-Engine
   npm install
   ```

2. **Backend setup:**
   ```bash
   cd apps/backend
   pip install -r requirements-dev.txt
   ```

3. **Environment configuration:**
   ```bash
   cp .env.example .env
   # Update .env with your configuration
   ```

4. **Start development servers:**
   ```bash
   # Run both frontend and backend
   npm run dev

   # Or run individually
   npm run dev:frontend
   npm run dev:backend
   ```

## 🧪 Testing

```bash
# Run all tests
npm run test

# Backend tests
cd apps/backend && python -m pytest

# Frontend tests
cd apps/frontend && npm test
```

## 🏭 Infrastructure Validation

Validate the monorepo structure:

```bash
python validate_structure.py
```

## 📊 Pharmaceutical Categories

The platform processes **17 pharmaceutical categories** dynamically:

1. Clinical Trials & Studies
2. Drug Interactions & Contraindications
3. Side Effects & Adverse Events
4. Pharmacokinetics & Pharmacodynamics
5. Regulatory Status & Approvals
6. Patent & Intellectual Property
7. Manufacturing & Quality Control
8. Pricing & Market Access
9. Competitive Analysis
10. Real-World Evidence
11. Safety Surveillance
12. Therapeutic Guidelines
13. Research Pipeline
14. Biomarker Information
15. Patient Demographics
16. Healthcare Economics
17. Post-Market Surveillance

## 🔒 Compliance Features

- **7-year audit trail retention** for pharmaceutical regulatory requirements
- **Complete source tracking** with verification and conflict resolution
- **Immutable audit logs** for regulatory compliance
- **Real-time processing updates** via WebSocket
- **Database-driven configuration** for operational flexibility

## 🛠️ Technology Stack

### Backend
- **FastAPI 0.104+** - Modern async Python web framework
- **PostgreSQL 15+** - Database with JSONB support
- **Redis 7.0+** - Caching and background job queues
- **Celery 5.3+** - Background task processing
- **SQLAlchemy 2.0+** - Async ORM with database migrations

### Frontend
- **Next.js 14.0+** - React framework with App Router
- **TypeScript 5.3+** - Type safety across the platform
- **Tailwind CSS 3.3+** - Utility-first CSS framework
- **Zustand 4.4+** - State management
- **TanStack Query 5.0+** - Server state synchronization

### Development & Deployment
- **Turborepo** - Monorepo build system with caching
- **systemd** - Production service management (no containerization as requested)
- **Nginx** - Reverse proxy and static file serving

## 🔗 External Integrations

- **ChatGPT** - OpenAI's conversational AI
- **Perplexity** - AI-powered search and reasoning
- **Grok** - AI assistant integration
- **Gemini** - Google's multimodal AI
- **Tavily** - Specialized search API

## 📝 Development Status

### ✅ Completed (Epic 1.1)
- [x] Monorepo structure with Turborepo
- [x] FastAPI backend with health checks
- [x] Next.js frontend with TypeScript
- [x] Shared type definitions
- [x] Environment configuration
- [x] Testing framework setup
- [x] Infrastructure validation

### 🚧 In Progress
- Database schema and models (Epic 1.2)
- Category configuration system (Epic 1.3)
- API gateway implementation (Epic 1.4)

### 📋 Planned
- Multi-API integration framework
- Source verification engine
- Real-time processing with WebSocket
- Administrative dashboard
- Complete audit trail system

## 📖 Documentation

- **Stories**: [docs/stories/](docs/stories/) - User stories and implementation details
- **Architecture**: [docs/architecture/](docs/architecture/) - Technical architecture documentation
- **PRD**: [docs/prd/](docs/prd/) - Product requirements documentation

## 🤝 Contributing

This is a pharmaceutical intelligence platform requiring strict adherence to:

1. **Database-driven architecture** - No hardcoded category logic
2. **Comprehensive source tracking** - All data must be traceable
3. **Audit trail compliance** - Complete change logging
4. **Performance standards** - <2s API response, <15min processing

## 📞 Support

For technical support and pharmaceutical compliance questions, please refer to the documentation or contact the development team.

---

**Version**: 1.0.0
**License**: Proprietary
**Contact**: support@cognito-ai.com