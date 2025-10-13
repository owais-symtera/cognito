# Tech Stack

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
