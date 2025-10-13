# Deployment Architecture

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
