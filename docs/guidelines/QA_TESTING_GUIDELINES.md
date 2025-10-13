# CognitoAI-Engine QA Testing Guidelines

## 🚨 **CRITICAL TESTING PRIORITIES**

These testing requirements are **NON-NEGOTIABLE** for pharmaceutical regulatory compliance:

### **1. DYNAMIC CONFIGURATION TESTING**

#### **✅ MANDATORY: Database-Driven Category Testing**

**Test Category:** Configuration Integrity
**Risk Level:** CRITICAL - System failure if categories hardcoded

```python
# ✅ REQUIRED: Test dynamic category loading
def test_categories_loaded_from_database():
    """CRITICAL: Verify all categories loaded from database, not hardcoded"""
    processor = SourceAwareCategoryProcessor(db, redis, api_manager)
    categories = await processor._load_category_configs()

    # Must load exactly 17 pharmaceutical categories
    assert len(categories) == 17, "Must load all 17 pharmaceutical categories"

    # Each category must have database-driven configuration
    for category in categories:
        assert 'id' in category, "Category missing database ID"
        assert 'search_parameters' in category, "Missing search parameters"
        assert 'processing_rules' in category, "Missing processing rules"
        assert 'prompt_templates' in category, "Missing prompt templates"

    # Verify no hardcoded category logic
    assert_no_hardcoded_categories_in_codebase()

def test_runtime_configuration_changes():
    """CRITICAL: Verify configuration changes without system restart"""
    # Disable a category in database
    await db.execute("UPDATE pharmaceutical_categories SET active = false WHERE name = 'Market Overview'")

    # Processor should immediately reflect the change
    processor = SourceAwareCategoryProcessor(db, redis, api_manager)
    categories = await processor._load_category_configs()

    market_overview = [c for c in categories if c['name'] == 'Market Overview']
    assert len(market_overview) == 0, "Disabled category should not be loaded"

    # Re-enable and verify
    await db.execute("UPDATE pharmaceutical_categories SET active = true WHERE name = 'Market Overview'")
    categories = await processor._load_category_configs()
    market_overview = [c for c in categories if c['name'] == 'Market Overview']
    assert len(market_overview) == 1, "Re-enabled category should be loaded"

def test_prompt_template_modification():
    """CRITICAL: Verify dynamic prompt modifications"""
    # Modify prompt template in database
    new_template = "Modified template for {drug_name} analysis"
    await db.execute("""
        UPDATE pharmaceutical_categories
        SET prompt_templates = jsonb_set(prompt_templates, '{search_template}', '"%s"')
        WHERE name = 'Clinical Trials'
    """ % new_template)

    # Processor should use new template immediately
    processor = SourceAwareCategoryProcessor(db, redis, api_manager)
    category_config = await processor._load_category_config(clinical_trials_id)

    built_prompt = await processor._build_category_prompts(
        category_config, "Aspirin", category_config
    )
    assert "Modified template for Aspirin analysis" in built_prompt

def assert_no_hardcoded_categories_in_codebase():
    """Scan codebase for forbidden hardcoded category logic"""
    forbidden_patterns = [
        "market_overview.py", "clinical_trials.py", "regulatory_status.py",
        "class MarketOverviewProcessor", "class ClinicalTrialsProcessor",
        "MARKET_OVERVIEW_PROMPT", "CLINICAL_TRIALS_PROMPT"
    ]

    # Scan all Python files
    for file_path in glob.glob("**/*.py", recursive=True):
        with open(file_path, 'r') as f:
            content = f.read()
            for pattern in forbidden_patterns:
                assert pattern not in content, f"FORBIDDEN: Hardcoded category logic found in {file_path}: {pattern}"
```

#### **✅ MANDATORY: Single Processor Architecture Testing**

```python
def test_single_processor_handles_all_categories():
    """CRITICAL: Verify only ONE processor handles ALL categories"""
    # Verify only one processor class exists
    processor_classes = find_classes_matching("*Processor", exclude=["BaseProcessor", "TestProcessor"])

    # Must have exactly ONE category processor
    category_processors = [cls for cls in processor_classes if "Category" in cls.__name__]
    assert len(category_processors) == 1, f"MUST have exactly ONE category processor, found: {category_processors}"
    assert category_processors[0].__name__ == "SourceAwareCategoryProcessor"

    # Verify processor handles all 17 categories
    processor = SourceAwareCategoryProcessor(db, redis, api_manager)
    test_categories = await db.execute("SELECT name FROM pharmaceutical_categories WHERE active = true")

    for category_name in test_categories:
        # Processor must handle each category dynamically
        result = await processor._process_single_category(
            {"name": category_name, "id": get_category_id(category_name)},
            "TestDrug",
            "test-request-123"
        )
        assert result is not None, f"Processor failed to handle category: {category_name}"

def test_no_category_specific_files():
    """CRITICAL: Verify no separate files for different categories"""
    forbidden_files = [
        "**/market_overview.py", "**/clinical_trials.py", "**/regulatory_status.py",
        "**/pricing_access.py", "**/safety_profile.py", "**/mechanism_action.py",
        "**/therapeutic_indications.py", "**/manufacturing.py", "**/market_access.py",
        "**/competitive_intelligence.py", "**/patent_landscape.py", "**/pipeline_status.py",
        "**/commercial_performance.py", "**/real_world_evidence.py", "**/key_opinion_leaders.py",
        "**/market_dynamics.py", "**/strategic_intelligence.py"
    ]

    for pattern in forbidden_files:
        matching_files = glob.glob(pattern, recursive=True)
        assert len(matching_files) == 0, f"FORBIDDEN: Category-specific file found: {matching_files}"
```

### **2. SOURCE TRACKING AND COMPLIANCE TESTING**

#### **✅ MANDATORY: Comprehensive Source Attribution Testing**

```python
def test_every_result_has_source_tracking():
    """CRITICAL: Verify ALL pharmaceutical data has source attribution"""
    processor = SourceAwareCategoryProcessor(db, redis, api_manager)

    # Process a drug request
    result = await processor.process_drug_request("Aspirin", "test-req-456")

    # Every successful category must have source tracking
    for category_name, category_result in result.categories.items():
        if category_result.status == "completed":
            assert len(category_result.sources) > 0, f"No sources tracked for {category_name}"

            for source in category_result.sources:
                # Each source must have complete attribution
                assert source.api_provider in ['chatgpt', 'perplexity', 'grok', 'gemini', 'tavily']
                assert source.content_snippet is not None and source.content_snippet != ""
                assert source.credibility_score is not None
                assert source.relevance_score is not None
                assert source.verification_status is not None
                assert source.extracted_at is not None

def test_source_conflict_detection():
    """CRITICAL: Verify conflicting sources are detected and resolved"""
    # Create mock conflicting sources
    source_a = create_mock_source("chatgpt", "Drug approved by FDA", credibility=0.9)
    source_b = create_mock_source("news", "Drug approval rejected", credibility=0.3)

    conflict_resolver = SourceConflictResolver()
    conflicts = await conflict_resolver.detect_conflicts([source_a, source_b])

    assert len(conflicts) > 0, "Failed to detect conflicting sources"

    # Verify conflict resolution
    for conflict in conflicts:
        assert conflict.conflict_type in ['factual', 'temporal', 'methodological']
        assert conflict.severity in ['low', 'medium', 'high', 'critical']
        assert conflict.resolution_strategy is not None
        assert conflict.resolution_confidence is not None

def test_audit_trail_completeness():
    """CRITICAL: Verify complete audit trail for regulatory compliance"""
    request_id = "audit-test-789"

    # Process a request
    await processor.process_drug_request("Metformin", request_id)

    # Verify audit events created
    audit_events = await db.execute(
        "SELECT * FROM audit_events WHERE request_id = %s ORDER BY timestamp",
        request_id
    )

    # Must have audit events for each processing stage
    required_events = [
        "processing_start", "category_completion", "processing_success"
    ]

    event_types = [event['event_type'] for event in audit_events]
    for required_event in required_events:
        assert required_event in event_types, f"Missing audit event: {required_event}"

    # Each audit event must have complete data
    for event in audit_events:
        assert event['timestamp'] is not None
        assert event['correlation_id'] is not None
        assert event['entity_type'] is not None
        assert event['entity_id'] is not None
```

#### **✅ MANDATORY: Data Lineage Testing**

```python
def test_complete_data_lineage():
    """CRITICAL: Verify complete traceability from request to result"""
    request_id = "lineage-test-101"

    # Submit request
    response = await api_client.post("/api/v1/analyze", {
        "requestId": request_id,
        "drugName": "Ibuprofen"
    })
    process_id = response.json()["processId"]

    # Wait for processing completion
    await wait_for_completion(process_id)

    # Verify complete lineage tracking
    lineage_query = """
        SELECT dr.id as request_id, cr.id as category_id, sr.id as source_id, ae.id as audit_id
        FROM drug_requests dr
        JOIN category_results cr ON dr.id = cr.request_id
        JOIN source_references sr ON cr.id = sr.category_result_id
        JOIN audit_events ae ON dr.id = ae.request_id
        WHERE dr.id = %s
    """

    lineage_data = await db.execute(lineage_query, request_id)

    # Must have complete linkage
    assert len(lineage_data) > 0, "No lineage data found"

    # Verify each component is linked
    for record in lineage_data:
        assert record['request_id'] == request_id
        assert record['category_id'] is not None
        assert record['source_id'] is not None
        assert record['audit_id'] is not None
```

### **3. REAL-TIME PROCESSING TESTING**

#### **✅ MANDATORY: WebSocket and Background Processing Testing**

```python
def test_real_time_websocket_updates():
    """CRITICAL: Verify real-time updates during processing"""
    request_id = "websocket-test-202"
    updates_received = []

    # Connect WebSocket
    async with websockets.connect(f"ws://localhost:8000/api/v1/requests/{request_id}/updates") as websocket:

        # Submit processing request
        await api_client.post("/api/v1/analyze", {
            "requestId": request_id,
            "drugName": "Acetaminophen"
        })

        # Collect real-time updates
        async for message in websocket:
            update = json.loads(message)
            updates_received.append(update)

            # Stop when processing completes
            if update.get("type") == "processing_complete":
                break

    # Verify received expected updates
    update_types = [update["type"] for update in updates_received]

    required_updates = [
        "processing_started", "category_progress", "processing_complete"
    ]

    for required_update in required_updates:
        assert required_update in update_types, f"Missing WebSocket update: {required_update}"

def test_celery_background_processing():
    """CRITICAL: Verify background task processing"""
    request_id = "celery-test-303"

    # Submit background task
    task = process_drug_request_task.delay(request_id, "Lorazepam")

    # Wait for task completion
    result = task.get(timeout=900)  # 15 minutes max

    # Verify task completed successfully
    assert result["status"] == "completed"
    assert result["request_id"] == request_id
    assert result["successful_categories"] > 0
    assert result["total_sources"] > 0

def test_concurrent_processing_capability():
    """CRITICAL: Verify system handles 100+ concurrent requests"""
    request_ids = [f"concurrent-test-{i}" for i in range(100)]
    drug_names = [f"TestDrug{i}" for i in range(100)]

    # Submit 100 concurrent requests
    tasks = []
    for req_id, drug_name in zip(request_ids, drug_names):
        task = process_drug_request_task.delay(req_id, drug_name)
        tasks.append(task)

    # Wait for all tasks to complete
    results = []
    for task in tasks:
        result = task.get(timeout=1200)  # 20 minutes for concurrent processing
        results.append(result)

    # Verify all tasks completed successfully
    successful_results = [r for r in results if r["status"] == "completed"]
    assert len(successful_results) >= 95, f"Only {len(successful_results)}/100 requests succeeded"
```

### **4. PERFORMANCE AND SCALABILITY TESTING**

#### **✅ MANDATORY: Performance Benchmarks**

```python
def test_api_response_time_requirements():
    """CRITICAL: Verify API responds within 2 seconds"""
    start_time = time.time()

    response = await api_client.post("/api/v1/analyze", {
        "requestId": "perf-test-404",
        "drugName": "Simvastatin"
    })

    response_time = time.time() - start_time

    assert response_time < 2.0, f"API response took {response_time}s, must be < 2s"
    assert response.status_code == 200
    assert "Request submitted" in response.json()["message"]

def test_processing_time_requirements():
    """CRITICAL: Verify complete processing within 15 minutes"""
    request_id = "timing-test-505"
    start_time = time.time()

    # Submit request
    await api_client.post("/api/v1/analyze", {
        "requestId": request_id,
        "drugName": "Atorvastatin"
    })

    # Wait for completion
    await wait_for_completion(request_id, timeout=900)  # 15 minutes

    processing_time = time.time() - start_time

    assert processing_time < 900, f"Processing took {processing_time}s, must be < 900s (15 minutes)"

def test_database_query_performance():
    """CRITICAL: Verify database queries complete within 100ms"""
    performance_queries = [
        "SELECT * FROM drug_requests WHERE status = 'processing'",
        "SELECT * FROM category_results WHERE completed_at > NOW() - INTERVAL '1 day'",
        "SELECT * FROM source_references WHERE verification_status = 'verified'",
        "SELECT * FROM audit_events WHERE timestamp > NOW() - INTERVAL '1 hour'"
    ]

    for query in performance_queries:
        start_time = time.time()
        await db.execute(query)
        query_time = time.time() - start_time

        assert query_time < 0.1, f"Query took {query_time}s, must be < 0.1s: {query}"
```

### **5. SECURITY AND COMPLIANCE TESTING**

#### **✅ MANDATORY: Authentication and Authorization Testing**

```python
def test_jwt_authentication_required():
    """CRITICAL: Verify all APIs require valid JWT tokens"""
    # Test without token
    response = await api_client.post("/api/v1/analyze", {
        "requestId": "auth-test-606",
        "drugName": "Warfarin"
    })

    assert response.status_code == 401, "API must require authentication"

    # Test with invalid token
    headers = {"Authorization": "Bearer invalid_token"}
    response = await api_client.post("/api/v1/analyze",
        {"requestId": "auth-test-607", "drugName": "Warfarin"},
        headers=headers
    )

    assert response.status_code == 401, "API must reject invalid tokens"

def test_rate_limiting():
    """CRITICAL: Verify rate limiting prevents abuse"""
    # Make 101 requests rapidly (limit is 100/minute)
    responses = []
    for i in range(101):
        response = await api_client.post("/api/v1/analyze", {
            "requestId": f"rate-test-{i}",
            "drugName": "TestDrug"
        }, headers=valid_headers)
        responses.append(response)

    # Last request should be rate limited
    assert responses[-1].status_code == 429, "Rate limiting not working"

def test_data_encryption():
    """CRITICAL: Verify sensitive data is encrypted"""
    # Submit request with sensitive pharmaceutical data
    response = await api_client.post("/api/v1/analyze", {
        "requestId": "encryption-test-808",
        "drugName": "ProprietaryCompound123"
    }, headers=valid_headers)

    # Check database storage is encrypted
    raw_db_data = await db.execute_raw("SELECT raw_data FROM encrypted_table WHERE request_id = %s",
                                      "encryption-test-808")

    # Raw data should not contain plaintext pharmaceutical information
    assert "ProprietaryCompound123" not in str(raw_db_data), "Sensitive data not encrypted in database"
```

### **6. INTEGRATION TESTING**

#### **✅ MANDATORY: Multi-API Integration Testing**

```python
def test_all_five_apis_integration():
    """CRITICAL: Verify integration with all 5 required APIs"""
    required_apis = ['chatgpt', 'perplexity', 'grok', 'gemini', 'tavily']

    processor = SourceAwareCategoryProcessor(db, redis, api_manager)
    result = await processor.process_drug_request("TestIntegrationDrug", "integration-test-909")

    # Check that sources were gathered from all APIs
    api_providers_used = set()
    for category_result in result.categories.values():
        for source in category_result.sources:
            api_providers_used.add(source.api_provider)

    # Must have attempted to use all APIs
    missing_apis = set(required_apis) - api_providers_used
    assert len(missing_apis) == 0, f"Missing API integrations: {missing_apis}"

def test_api_failure_resilience():
    """CRITICAL: Verify system continues when individual APIs fail"""
    # Mock one API to fail
    with mock.patch('api_manager.chatgpt_client.search') as mock_chatgpt:
        mock_chatgpt.side_effect = APIException("ChatGPT temporarily unavailable")

        # Processing should continue with other APIs
        processor = SourceAwareCategoryProcessor(db, redis, api_manager)
        result = await processor.process_drug_request("ResilienceTestDrug", "resilience-test-1010")

        # Should have partial success
        assert result.successful_categories > 0, "System should continue with other APIs"
        assert "ChatGPT API failure" in result.error_summary
```

## **🚫 CRITICAL TEST FAILURES**

### **Tests That Must NEVER Fail:**

1. **Dynamic Configuration Test Failure** = CRITICAL SYSTEM DESIGN FLAW
   - If categories are hardcoded, the entire pharmaceutical flexibility requirement is broken

2. **Single Processor Test Failure** = ARCHITECTURAL VIOLATION
   - Multiple category processors violate the core design principle

3. **Source Tracking Test Failure** = REGULATORY COMPLIANCE VIOLATION
   - Missing source attribution makes the system unusable for pharmaceutical industry

4. **Audit Trail Test Failure** = REGULATORY COMPLIANCE VIOLATION
   - Incomplete audit trails violate pharmaceutical industry requirements

5. **Performance Test Failure** = USER EXPERIENCE VIOLATION
   - Slow responses make the system unusable for pharmaceutical professionals

## **📋 QA TESTING CHECKLIST**

### **Pre-Release Validation:**

- [ ] **Dynamic Configuration**: All 17 categories loaded from database
- [ ] **Single Processor**: Only one processor class handles all categories
- [ ] **No Hardcoded Logic**: No category-specific files or hardcoded prompts
- [ ] **Source Tracking**: Every result has complete source attribution
- [ ] **Audit Compliance**: Complete audit trail with 7-year retention
- [ ] **Real-Time Updates**: WebSocket updates during processing
- [ ] **Performance Benchmarks**: API < 2s, Processing < 15min, DB < 100ms
- [ ] **Concurrent Processing**: Handles 100+ simultaneous requests
- [ ] **Security Compliance**: JWT auth, rate limiting, data encryption
- [ ] **API Integration**: All 5 APIs (ChatGPT, Perplexity, Grok, Gemini, Tavily)
- [ ] **Error Resilience**: Continues processing when individual APIs fail
- [ ] **Data Validation**: All pharmaceutical data properly validated
- [ ] **Regulatory Compliance**: Meets pharmaceutical industry standards

### **Continuous Testing Requirements:**

```bash
# ✅ REQUIRED: Run these tests on every commit
pytest tests/test_dynamic_configuration.py --strict
pytest tests/test_single_processor.py --strict
pytest tests/test_source_tracking.py --strict
pytest tests/test_audit_compliance.py --strict
pytest tests/test_performance.py --strict

# ✅ REQUIRED: Run integration tests daily
pytest tests/test_api_integration.py --timeout=1200
pytest tests/test_concurrent_processing.py --timeout=1800
```

## **🎯 TESTING SUCCESS CRITERIA**

A fully tested CognitoAI-Engine will demonstrate:

1. **100%** dynamic configuration with zero hardcoded categories
2. **Complete** source attribution for every pharmaceutical data point
3. **Full** audit trail meeting pharmaceutical regulatory requirements
4. **Real-time** processing updates with WebSocket integration
5. **Scalable** performance supporting 100+ concurrent requests
6. **Secure** operation with enterprise-grade authentication
7. **Resilient** multi-API integration with graceful failure handling
8. **Compliant** operation meeting pharmaceutical industry standards

**Remember: Testing in the pharmaceutical industry is not just about functionality - it's about regulatory compliance, audit trails, and patient safety. Every test must reflect these critical requirements.**