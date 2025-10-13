# Phase 2 Testing Guide

## Overview
This guide shows how to test Phase 2 scoring without re-running expensive Phase 1 API calls.

## New Testing Endpoints

### 1. Check Phase 2 Status
**GET** `/api/v1/drug-request/{request_id}/phase2-status`

Check if a request has Phase 1 data and is ready for Phase 2 reprocessing.

**Example:**
```bash
curl http://localhost:8001/api/v1/drug-request/00416f60-090d-42a4-abcd-cd3f027f50c3/phase2-status
```

**Response:**
```json
{
  "request_id": "00416f60-090d-42a4-abcd-cd3f027f50c3",
  "drug_name": "ExampleDrug",
  "request_status": "completed",
  "phase1": {
    "count": 10,
    "categories": [...]
  },
  "phase2": {
    "count": 2,
    "categories": [...]
  },
  "can_reprocess_phase2": true
}
```

### 2. Reprocess Phase 2 Only
**POST** `/api/v1/drug-request/{request_id}/reprocess-phase2`

Deletes existing Phase 2 results and re-runs Phase 2 processing using existing Phase 1 data.

**Example:**
```bash
curl -X POST http://localhost:8001/api/v1/drug-request/00416f60-090d-42a4-abcd-cd3f027f50c3/reprocess-phase2
```

**Response:**
```json
{
  "request_id": "00416f60-090d-42a4-abcd-cd3f027f50c3",
  "drug_name": "ExampleDrug",
  "phase1_categories_preserved": 10,
  "phase2_categories_processed": 2,
  "successful": 2,
  "failed": 0,
  "results": [
    {
      "category": "Parameter-Based Scoring Matrix",
      "status": "completed",
      "summary_preview": "## Parameter-Based Scoring Matrix...",
      "confidence_score": 0.85
    },
    {
      "category": "Weighted Scoring Assessment",
      "status": "completed",
      "summary_preview": "Weighted Scoring Assessment...",
      "confidence_score": 0.75
    }
  ]
}
```

## Testing Workflow

### Step 1: Find an existing request with Phase 1 data
```bash
# Check status
curl http://localhost:8001/api/v1/drug-request/YOUR_REQUEST_ID/phase2-status
```

### Step 2: Make code changes to Phase 2 logic
Edit files like:
- `src/services/phase2_scoring_service.py`
- `src/services/pipeline_integration_service.py`

### Step 3: Reprocess Phase 2
```bash
# Re-run Phase 2 only (no Phase 1 API calls)
curl -X POST http://localhost:8001/api/v1/drug-request/YOUR_REQUEST_ID/reprocess-phase2
```

### Step 4: Check results in frontend
Go to `/pipeline` monitoring page and view updated Phase 2 results.

### Step 5: Iterate
Repeat steps 2-4 as needed. Phase 1 data is never re-fetched!

## What Gets Deleted vs Preserved

### ✅ Preserved (Never Deleted):
- All Phase 1 `category_results`
- All `merged_data_results`
- All Phase 1 `pipeline_stage_executions`
- All expensive API data

### ❌ Deleted (Clean Slate for Testing):
- Phase 2 `category_results` only
- Phase 2 `pipeline_stage_executions`

## Benefits

✅ **No LLM API costs** - Reuses existing Phase 1 data
✅ **Fast iteration** - Test Phase 2 changes in seconds
✅ **Clean results** - Old Phase 2 data deleted, new data created
✅ **Same workflow** - Uses exact same code path as normal execution

## Environment Variables

Make sure these are set in your environment (or use defaults):

```bash
# Database
DB_HOST=localhost          # default
DB_PORT=5432              # default
DB_USER=postgres          # default
DB_PASSWORD=postgres      # default
DB_NAME=cognito-engine    # default

# LLM
OPENAI_API_KEY=your_key   # required for parameter extraction
LLM_MODEL=gpt-4           # optional, default gpt-4
```

## Example: Full Testing Session

```bash
# 1. Check if request has Phase 1 data
curl http://localhost:8001/api/v1/drug-request/00416f60-090d-42a4-abcd-cd3f027f50c3/phase2-status

# 2. Reprocess Phase 2
curl -X POST http://localhost:8001/api/v1/drug-request/00416f60-090d-42a4-abcd-cd3f027f50c3/reprocess-phase2

# 3. View results
# Open http://localhost:3000/pipeline and select your request
```

## Troubleshooting

### Error: "No Phase 1 data found"
- Request needs Phase 1 completion first
- Run a full drug request to get Phase 1 data

### Error: "Request not found"
- Check request_id is valid UUID
- Verify request exists in `drug_requests` table

### No scoring results
- Check LLM API key is configured
- Check logs for extraction/scoring errors
- Verify `scoring_ranges` table has 80 rows

## Implementation Details

The reprocess endpoint:
1. Validates request exists
2. Checks Phase 1 data availability
3. Deletes Phase 2 category_results (SQL: `DELETE WHERE phase = 2`)
4. Calls `pipeline.process_phase2_category()` for each Phase 2 category
5. Returns summary of results

All Phase 2 logic uses the same code path as normal execution!
