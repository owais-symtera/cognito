# Technical Assumptions

### Repository Structure: Monorepo

**Rationale:** A monorepo supports the tightly integrated multi-pipeline architecture with shared database schemas, common API interfaces, and cross-cutting concerns like processId tracking. The 17-category framework with shared validation and merging logic benefits from unified codebase management, while still allowing independent deployment of API services, webhook handlers, and admin interfaces.

### Service Architecture

**Microservices within Monorepo:** The system requires independent scaling of different components - API request handlers need high availability, while LLM processing services need compute optimization, and webhook delivery needs reliability guarantees. Key services include:

- **API Gateway Service** (request acceptance, immediate response)
- **Pipeline Orchestration Service** (4-stage Phase 1 coordination)
- **Multi-API Integration Service** (ChatGPT, Perplexity, Grok, Gemini, Tavily)
- **Verification & Merging Service** (source hierarchy, conflict resolution)
- **LLM Processing Service** (summary generation, Phase 2 decision intelligence)
- **Webhook Delivery Service** (reliable result delivery with retry)
- **Admin Dashboard Service** (configuration, monitoring, failure management)

### Testing Requirements

**Full Testing Pyramid:** Given pharmaceutical industry reliability requirements and regulatory compliance needs:

- **Unit Tests** for all business logic, especially source prioritization algorithms and data merging logic
- **Integration Tests** for multi-API coordination, database persistence, and webhook delivery
- **End-to-End Tests** for complete pipeline execution from API request through webhook delivery
- **Contract Tests** for external API integrations (paid APIs, search APIs)
- **Load Tests** for concurrent processing capabilities (100+ simultaneous requests)
- **Compliance Tests** for audit trail integrity and data retention requirements

**Manual Testing Convenience:** Pharmaceutical data accuracy requires human validation capabilities - test harnesses for reviewing AI-generated summaries, comparing source data conflicts, and validating Go/No-Go decision logic.

### Additional Technical Assumptions and Requests

**Database Technology:**
- **PostgreSQL** for transactional data (requests, processId tracking, configurations)
- **Time-series database (InfluxDB)** for performance metrics and API usage tracking
- **Redis** for caching and session management across microservices

**API Integration Framework:**
- **Async/await pattern** with timeout handling for multi-API coordination
- **Circuit breaker pattern** for external API failure resilience
- **Rate limiting** to manage API costs and prevent quota exhaustion

**Security & Compliance:**
- **End-to-end encryption** for pharmaceutical data in transit and at rest
- **Audit logging** with immutable records for 7-year regulatory retention
- **Role-based access control** for enterprise user management
- **API key rotation** capabilities for external service integrations

**Scalability Architecture:**
- **Horizontal pod autoscaling** for compute-intensive LLM processing
- **Message queues (RabbitMQ)** for reliable async processing coordination
- **CDN integration** for global webhook delivery optimization

**Development & Deployment:**
- **CI/CD pipeline** with automated testing and deployment approval gates
- **Infrastructure as Code (Terraform)** for consistent environment management
- **Monitoring & Observability** (Prometheus, Grafana) for operational visibility
- **Feature flags** for safe rollout of new categories and source integrations

**Cost Optimization Technology:**
- **Intelligent API routing** to minimize paid API usage while maintaining coverage targets
- **Result caching** to avoid duplicate processing for recently analyzed compounds
- **Configurable processing tiers** allowing users to select speed vs. cost optimization
