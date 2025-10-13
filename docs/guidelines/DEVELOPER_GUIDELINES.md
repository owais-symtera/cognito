# CognitoAI-Engine Developer Guidelines

## 🚨 **CRITICAL ARCHITECTURAL PRINCIPLES**

These are **NON-NEGOTIABLE** rules that must be followed in all development:

### **1. EVERYTHING MUST BE DATABASE-DRIVEN AND DYNAMIC**

#### **✅ MANDATORY: Single Dynamic Category Processor**
- **ONE AND ONLY ONE** category processor class: `SourceAwareCategoryProcessor`
- **FORBIDDEN**: Multiple processor files like `market_overview.py`, `clinical_trials.py`, etc.
- **REQUIRED**: All 17 pharmaceutical categories processed by the SAME single processor
- **IMPLEMENTATION**: Dynamic configuration loading from `pharmaceutical_categories` table

```python
# ✅ CORRECT - Single processor handles ALL categories
class SourceAwareCategoryProcessor:
    async def process_drug_request(self, drug_name: str, request_id: str):
        # Load ALL category configs from database
        categories = await self._load_category_configs()
        for category in categories:
            await self._process_single_category(category, drug_name, request_id)

    async def _load_category_configs(self) -> List[Dict]:
        """Load dynamic configs from database - NEVER hardcode categories"""
        query = """
        SELECT id, name, search_parameters, processing_rules,
               prompt_templates, verification_criteria
        FROM pharmaceutical_categories
        WHERE active = true
        """
        return await self.db.execute(query).fetchall()

# ❌ FORBIDDEN - Multiple category-specific processors
# class MarketOverviewProcessor  # NO!
# class ClinicalTrialsProcessor  # NO!
# class RegulatoryStatusProcessor  # NO!
```

#### **✅ MANDATORY: Database-Driven Configuration**
- **ALL** prompts, parameters, rules, and settings stored in database
- **NO** hardcoded category logic in code files
- **DYNAMIC** configuration changes without code deployment
- **RUNTIME** configuration loading - no restart required

```sql
-- ✅ REQUIRED: pharmaceutical_categories table structure
CREATE TABLE pharmaceutical_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    search_parameters JSONB DEFAULT '{}',
    processing_rules JSONB DEFAULT '{}',
    prompt_templates JSONB DEFAULT '{}',
    verification_criteria JSONB DEFAULT '{}',
    conflict_resolution_strategy VARCHAR(50),
    active BOOLEAN DEFAULT true
);

-- ✅ REQUIRED: All 17 categories pre-populated
INSERT INTO pharmaceutical_categories (name, search_parameters, processing_rules) VALUES
('Market Overview', '{"focus": "market_size, competitors"}', '{"summary_length": "comprehensive"}'),
('Clinical Trials', '{"focus": "phase_trials, efficacy"}', '{"require_verification": true}'),
-- ... all 17 categories
```

#### **✅ MANDATORY: Dynamic Prompt Loading**
- **NO** hardcoded prompts in Python/TypeScript code
- **ALL** prompts stored in database JSONB fields
- **RUNTIME** prompt modification through admin interface

```python
# ✅ CORRECT - Dynamic prompt loading
async def _build_category_prompts(self, category: Dict, drug_name: str, config: Dict):
    """Load prompts from database configuration"""
    base_template = config.get('prompt_template', '')
    return base_template.format(
        drug_name=drug_name,
        search_parameters=config.get('search_parameters', ''),
        processing_rules=config.get('processing_rules', '')
    )

# ❌ FORBIDDEN - Hardcoded prompts
MARKET_OVERVIEW_PROMPT = "Analyze market for {drug}"  # NO!
CLINICAL_TRIALS_PROMPT = "Find trials for {drug}"     # NO!
```

### **2. COMPREHENSIVE SOURCE TRACKING IS MANDATORY**

#### **✅ MANDATORY: Every Data Point Must Be Traceable**
- **ALL** pharmaceutical data linked to original sources
- **COMPLETE** audit trail from request to final result
- **IMMUTABLE** audit logs for regulatory compliance

```python
# ✅ REQUIRED: Source tracking in ALL operations
class SourceReference(Base):
    id: str
    api_provider: str  # ChatGPT, Perplexity, Grok, Gemini, Tavily
    source_url: str
    content_snippet: str
    relevance_score: float
    credibility_score: float
    verification_status: str
    extracted_at: datetime

# ✅ REQUIRED: Audit trail for ALL changes
class AuditEvent(Base):
    entity_type: str
    entity_id: str
    old_values: Dict
    new_values: Dict
    timestamp: datetime
    correlation_id: str
```

#### **✅ MANDATORY: Source Conflict Resolution**
- **AUTOMATIC** detection of conflicting information
- **ALGORITHMIC** resolution based on source credibility
- **TRANSPARENT** conflict tracking and reasoning

### **3. REAL-TIME PROCESSING ARCHITECTURE**

#### **✅ MANDATORY: WebSocket Integration**
- **REAL-TIME** updates during processing
- **PROGRESS** tracking for long-running operations
- **ERROR** notification and recovery

```python
# ✅ REQUIRED: WebSocket manager for real-time updates
class ConnectionManager:
    async def broadcast_update(self, request_id: str, update: Dict):
        """Broadcast processing updates to connected clients"""

# ✅ REQUIRED: Celery background tasks
@celery_app.task(name='process_drug_request')
def process_drug_request_task(request_id: str, drug_name: str):
    """Background processing with real-time updates"""
```

## **🔒 SECURITY AND COMPLIANCE REQUIREMENTS**

### **✅ MANDATORY: Pharmaceutical Regulatory Compliance**
- **7-YEAR** audit trail retention
- **IMMUTABLE** audit logs
- **COMPLETE** change tracking
- **SOURCE** attribution for all data

### **✅ MANDATORY: API Security**
- **JWT** authentication with role-based permissions
- **RATE LIMITING** (100 requests/minute per IP)
- **INPUT VALIDATION** for all pharmaceutical data
- **ENCRYPTION** at rest and in transit

## **📊 PERFORMANCE REQUIREMENTS**

### **✅ MANDATORY: Processing Performance**
- **2 SECONDS** maximum for API request acknowledgment
- **15 MINUTES** maximum for complete 17-category analysis
- **100+ CONCURRENT** requests support
- **99.5% UPTIME** requirement

### **✅ MANDATORY: Database Optimization**
- **INDEXED** queries for pharmaceutical data lookup
- **MATERIALIZED VIEWS** for dashboard analytics
- **CONNECTION POOLING** for concurrent processing
- **CACHING** with Redis for configuration data

## **🧪 TESTING REQUIREMENTS**

### **✅ MANDATORY: Dynamic Configuration Testing**
```python
# ✅ REQUIRED: Test dynamic category loading
def test_dynamic_category_loading():
    """Verify categories loaded from database, not hardcoded"""
    processor = SourceAwareCategoryProcessor(db, redis, api_manager)
    categories = await processor._load_category_configs()
    assert len(categories) == 17
    assert all('prompt_templates' in cat for cat in categories)

# ✅ REQUIRED: Test single processor handles all categories
def test_single_processor_all_categories():
    """Verify one processor processes all pharmaceutical categories"""
    processor = SourceAwareCategoryProcessor(db, redis, api_manager)
    result = await processor.process_drug_request("Aspirin", "req-123")
    assert result.successful_categories <= 17
    assert isinstance(result.failed_categories, list)
```

### **✅ MANDATORY: Source Tracking Testing**
```python
# ✅ REQUIRED: Test comprehensive source attribution
def test_source_attribution():
    """Verify all results have complete source tracking"""
    result = await processor.process_category(category_data)
    assert len(result.sources) > 0
    for source in result.sources:
        assert source.api_provider in ['chatgpt', 'perplexity', 'grok', 'gemini', 'tavily']
        assert source.credibility_score is not None
        assert source.verification_status is not None
```

## **🚫 FORBIDDEN PRACTICES**

### **❌ NEVER DO THESE:**
1. **Create separate processor files** for different categories
2. **Hardcode prompts** or pharmaceutical data in source code
3. **Skip source tracking** for any data operation
4. **Bypass audit logging** for performance reasons
5. **Use synchronous processing** for long-running operations
6. **Store configuration** in environment variables or config files
7. **Create static category mappings** in code
8. **Skip error handling** in multi-API integrations
9. **Use direct SQL queries** without ORM for audit compliance
10. **Implement category-specific business logic** outside the processor

## **✅ REQUIRED CODE PATTERNS**

### **Database-First Development**
```python
# ✅ PATTERN: Always load from database
async def get_category_config(category_id: int):
    return await db.query(PharmaceuticalCategory).filter_by(id=category_id).first()

# ✅ PATTERN: Dynamic prompt building
async def build_prompts(category_config: Dict, drug_name: str):
    template = category_config['prompt_templates']['search_template']
    return template.format(drug_name=drug_name, **category_config['search_parameters'])
```

### **Source-Aware Processing**
```python
# ✅ PATTERN: Track sources for all operations
async def process_api_response(response: Dict, api_provider: str) -> List[SourceReference]:
    sources = []
    for item in response.get('results', []):
        source = SourceReference(
            api_provider=api_provider,
            source_url=item.get('url'),
            content_snippet=item.get('content'),
            extracted_at=datetime.utcnow()
        )
        sources.append(source)
    return sources
```

### **Audit-Compliant Operations**
```python
# ✅ PATTERN: Log all pharmaceutical data changes
async def update_request_status(request_id: str, new_status: str):
    old_request = await db.get(DrugRequest, request_id)
    old_status = old_request.status

    old_request.status = new_status
    await db.commit()

    # MANDATORY: Log the change
    audit_event = AuditEvent(
        entity_type="DrugRequest",
        entity_id=request_id,
        old_values={"status": old_status},
        new_values={"status": new_status},
        timestamp=datetime.utcnow()
    )
    await db.add(audit_event)
    await db.commit()
```

## **📋 CODE REVIEW CHECKLIST**

Before approving any PR, verify:

- [ ] **Single processor** handles all categories (no category-specific files)
- [ ] **Database-driven** configuration (no hardcoded prompts/rules)
- [ ] **Source tracking** implemented for all data operations
- [ ] **Audit logging** for all pharmaceutical data changes
- [ ] **Error handling** for multi-API failures
- [ ] **Real-time updates** via WebSocket where applicable
- [ ] **Comprehensive testing** including dynamic configuration tests
- [ ] **JSDoc/docstring** documentation on all public functions
- [ ] **Performance considerations** for concurrent processing
- [ ] **Security validation** for pharmaceutical data handling

## **🎯 SUCCESS CRITERIA**

A correctly implemented CognitoAI-Engine will have:

1. **ONE** dynamic category processor serving all 17 pharmaceutical categories
2. **ZERO** hardcoded category logic or prompts in source code
3. **100%** database-driven configuration with runtime modifications
4. **COMPLETE** source attribution for every piece of pharmaceutical data
5. **REAL-TIME** processing updates via WebSocket connections
6. **COMPREHENSIVE** audit trails meeting pharmaceutical regulatory requirements
7. **SCALABLE** architecture supporting 100+ concurrent drug analyses
8. **MAINTAINABLE** codebase following SOLID principles and comprehensive documentation

**Remember: The pharmaceutical industry demands precision, compliance, and traceability. Every line of code must reflect these values.**