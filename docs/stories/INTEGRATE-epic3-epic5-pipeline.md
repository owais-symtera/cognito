# Story: Integrate Epic 3 & Epic 5 into Processing Pipeline

## Status
**Draft** - Ready for Development

## Priority
**CRITICAL** - Core PRD functionality missing

## Story
**As a** Pharmaceutical Research Director,
**I want** the complete 4-stage pipeline (Collection → Verification → Merging → LLM Summary) to execute automatically,
**so that** I receive verified, merged, and intelligently summarized pharmaceutical intelligence instead of raw unprocessed API responses.

## Problem Statement

### Current State (BROKEN)
The system currently ONLY executes Stage 1 (Data Collection):
- Calls multiple APIs with temperature variations ✅
- Stores raw responses to database ✅
- **Then STOPS** ❌

The `process_drug_with_categories()` method at `apps/backend/src/services/provider_service.py:850-1050` just concatenates responses:

```python
summary = f"Collected {len(all_responses)} responses..."
summary += f"\n\nSample response: {all_responses[0][:500]}..."
```

### Required PRD State
Per **FR2**, the system SHALL process through **4 stages**:
1. ✅ **Data Collection** - Implemented
2. ❌ **Verification** - Code exists but NOT called
3. ❌ **Merging** - Code exists but NOT called
4. ❌ **LLM Summary** - Code exists but NOT called

### Impact
- Users receive raw, unverified data dumps
- No conflict resolution or source prioritization
- No weighted merging or confidence scoring
- No intelligent LLM summaries or Go/No-Go decisions
- **System violates core PRD requirements**

## Acceptance Criteria

### AC1: Verification Stage Integration
- [ ] After data collection completes, automatically invoke `SourceAuthenticator` from `apps/backend/src/core/verification/source_authenticator.py`
- [ ] Apply hierarchical source weighting (Paid APIs: 10x, .gov: 8x, Peer-reviewed: 6x, etc.)
- [ ] Store verification results with audit trail to database
- [ ] Update request progress to 40% after verification complete

### AC2: Conflict Resolution Integration
- [ ] After verification, automatically invoke `ConflictResolver` from `apps/backend/src/core/verification/conflict_resolver.py`
- [ ] Detect contradictory data points across API responses
- [ ] Apply weighted conflict resolution using source hierarchy
- [ ] Document conflict resolution decisions in audit trail
- [ ] Update request progress to 55% after conflict resolution

### AC3: Data Validation Integration
- [ ] Invoke `DataValidator` from `apps/backend/src/core/verification/data_validator.py`
- [ ] Apply pharmaceutical-specific validation rules
- [ ] Flag anomalies and regulatory compliance issues
- [ ] Store validation results with audit trail
- [ ] Update request progress to 65% after validation

### AC4: Data Merging Integration
- [ ] Invoke `DataMerger` from `apps/backend/src/core/verification/data_merger.py`
- [ ] Combine complementary data from multiple verified sources
- [ ] Enrich incomplete records using merging algorithms
- [ ] Generate confidence scores for merged data
- [ ] Store merged results with complete audit trail
- [ ] Update request progress to 75% after merging complete

### AC5: LLM Summary Generation (Phase 2)
- [ ] After Phase 1 merging completes, invoke `LLMDecisionProcessor` from `apps/backend/src/core/decision/llm_decision_processor.py`
- [ ] Generate intelligent summary using merged Phase 1 data
- [ ] Apply scoring matrices from `apps/backend/src/core/decision/scoring_matrix.py`
- [ ] Generate weighted assessments using `apps/backend/src/core/decision/weighted_assessment.py`
- [ ] Create Go/No-Go verdicts using `apps/backend/src/core/decision/verdict_generator.py`
- [ ] Synthesize executive summary using `apps/backend/src/core/decision/summary_synthesizer.py`
- [ ] Update request progress to 90% after LLM processing

### AC6: Complete Audit Trail
- [ ] Maintain processId tracking through all 4 stages
- [ ] Link all verification, merging, and LLM decisions to original requestID
- [ ] Store complete decision chain for regulatory compliance
- [ ] Generate final verification report using `VerificationReporter`

### AC7: Error Handling & Retry
- [ ] If verification fails, retry with degraded quality threshold
- [ ] If merging fails, fallback to best single source
- [ ] If LLM summary fails, provide merged data without summary
- [ ] Never leave request in "processing" state forever
- [ ] Log all failures to audit trail

### AC8: Database Storage
- [ ] Store verification results to `category_results` table with verification_score
- [ ] Store conflict resolution decisions to new `conflict_resolutions` table
- [ ] Store merge audit trail to `source_references` with merge metadata
- [ ] Store LLM summaries to `category_results` with confidence_score
- [ ] Link all records via processId and category_result_id

## Technical Implementation

### Files to Modify

#### 1. `apps/backend/src/services/provider_service.py`

**Current**: Lines 878-1043 (Phase 1 processing)
**Changes**:
```python
async def process_drug_with_categories(self, drug_name: str, request_id: str):
    # ... existing data collection (lines 878-1001) ...

    # NEW: Stage 2 - Verification
    from core.verification.source_authenticator import SourceAuthenticator
    from core.verification.conflict_resolver import ConflictResolver
    from core.verification.data_validator import DataValidator

    authenticator = SourceAuthenticator()
    conflict_resolver = ConflictResolver()
    validator = DataValidator()

    # Authenticate sources from all_responses
    verification_data = await authenticator.authenticate_sources(all_responses, category)

    # Resolve conflicts
    conflict_data = await conflict_resolver.resolve_conflicts(verification_data)

    # Validate data
    validation_data = await validator.validate_data(conflict_data, category)

    # NEW: Stage 3 - Merging
    from core.verification.data_merger import DataMerger
    merger = DataMerger()
    merged_data = await merger.merge_validated_data(validation_data, category)

    # Store merged result (replace simple concatenation at line 1007)
    summary = merged_data.get('executive_summary', '')

    # NEW: Stage 4 - LLM Summary (Phase 2)
    from core.decision.llm_decision_processor import LLMDecisionProcessor
    llm_processor = LLMDecisionProcessor()
    final_summary = await llm_processor.generate_decision_intelligence(
        merged_data, category, drug_name
    )

    # Store final results
    category_result_id = await DataStorageService.store_category_result(
        request_id=request_id,
        category_id=category["id"],
        category_name=category["name"],
        summary=final_summary['executive_summary'],
        confidence_score=final_summary['confidence_score'],
        data_quality_score=merged_data['quality_score'],
        verification_metadata=verification_data,
        merge_metadata=merged_data,
        decision_metadata=final_summary
    )
```

#### 2. `apps/backend/src/services/data_storage_service.py`

**Add methods**:
```python
@staticmethod
async def store_verification_result(verification_data: Dict[str, Any]) -> str:
    """Store verification stage results"""

@staticmethod
async def store_conflict_resolution(conflict_data: Dict[str, Any]) -> str:
    """Store conflict resolution decisions"""

@staticmethod
async def store_merge_audit(merge_data: Dict[str, Any]) -> str:
    """Store data merging audit trail"""
```

#### 3. Database Schema Updates (if needed)

Check if these tables exist:
- `conflict_resolutions` - Store conflict detection/resolution decisions
- `verification_metadata` - Store source authentication results
- `merge_audit_trail` - Store data merging decisions

## Testing Requirements

### Unit Tests
- [ ] Test source authentication with mock API responses
- [ ] Test conflict resolution with contradictory data
- [ ] Test data validation with invalid pharmaceutical data
- [ ] Test merging algorithm with complementary sources
- [ ] Test LLM summary generation with merged data

### Integration Tests
- [ ] Test complete 4-stage pipeline end-to-end
- [ ] Verify audit trail completeness across all stages
- [ ] Test error handling and graceful degradation
- [ ] Verify database storage at each stage

### Manual Verification
- [ ] Create test request for "Apixaban"
- [ ] Verify API responses are collected (Stage 1) ✅
- [ ] Verify sources are authenticated and weighted (Stage 2)
- [ ] Verify conflicts are detected and resolved (Stage 3)
- [ ] Verify data is merged with confidence scores (Stage 4a)
- [ ] Verify LLM generates intelligent summary (Stage 4b)
- [ ] Verify complete audit trail in database

## Dependencies

### Required Services (Already Implemented)
- ✅ `apps/backend/src/core/verification/source_authenticator.py`
- ✅ `apps/backend/src/core/verification/conflict_resolver.py`
- ✅ `apps/backend/src/core/verification/data_validator.py`
- ✅ `apps/backend/src/core/verification/data_merger.py`
- ✅ `apps/backend/src/core/verification/verification_reporter.py`
- ✅ `apps/backend/src/core/decision/llm_decision_processor.py`
- ✅ `apps/backend/src/core/decision/scoring_matrix.py`
- ✅ `apps/backend/src/core/decision/weighted_assessment.py`
- ✅ `apps/backend/src/core/decision/verdict_generator.py`
- ✅ `apps/backend/src/core/decision/summary_synthesizer.py`

### Integration Points
- `process_drug_with_categories()` in provider_service.py (main integration point)
- `DataStorageService` for storing verification/merge results
- Progress tracking in `main.py:process_request()` endpoint

## Dev Notes

### Key Insight
The Epic 3 and Epic 5 code is COMPLETE but NEVER CALLED. This story is about INTEGRATION, not building new features.

### Implementation Order
1. First integrate verification (AC1-AC3) and verify it works
2. Then integrate merging (AC4) and verify merged data quality
3. Finally integrate LLM processing (AC5) for Phase 2 intelligence
4. Add comprehensive error handling (AC7)
5. Verify complete audit trail (AC6)

### Performance Considerations
- Each stage adds processing time - target 15min total (per NFR2)
- Run verification and validation in parallel where possible
- Cache LLM responses for similar drug analyses
- Use async/await throughout entire pipeline

### Audit Compliance
Every stage MUST:
- Log to audit trail with timestamp and processId
- Store decision reasoning (why this source chosen, why conflict resolved this way)
- Link to original requestID for regulatory compliance
- Maintain immutable audit records

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-01-XX | 1.0 | Initial story creation - Epic 3/5 integration | James (Developer) |

## Related Stories
- Story 3.1: Source Authentication (CODE COMPLETE)
- Story 3.2: Conflict Resolution (CODE COMPLETE)
- Story 3.3: Data Validation (CODE COMPLETE)
- Story 3.4: Data Merging (CODE COMPLETE)
- Story 5.1: LLM Processing Framework (CODE COMPLETE)
- Story 5.6: Executive Summary (CODE COMPLETE)

## Success Criteria

**BEFORE** this story:
```
Request → API Calls → Raw String Concat → Done
          (Stage 1)    (Broken)
```

**AFTER** this story:
```
Request → API Calls → Verification → Merging → LLM Summary → Done
          (Stage 1)    (Stage 2)      (Stage 3)   (Stage 4)

With complete audit trail, confidence scores, and regulatory compliance.
```

---

**CRITICAL**: This story implements the core value proposition of the PRD. Without it, the system is just an expensive API aggregator, not an intelligent pharmaceutical analysis platform.
