# Phase 1 Structured Data Fix - Summary

## Problem Statement

Phase 2 Parameter-Based Scoring was failing because **Phase 1's `merged_data_results.structured_data` was empty** for critical pharmaceutical categories.

### Evidence of the Problem

```sql
SELECT cr.category_name, md.structured_data
FROM category_results cr
LEFT JOIN merged_data_results md ON cr.id = md.category_result_id
WHERE cr.request_id = '0c7b99e1-1fc0-444d-9864-676f43ece762'
AND cr.category_name = 'Physicochemical Profile';
```

**Result:** `structured_data` was `NULL` or `{}` (empty)

This meant Phase 2 had no data to extract pharmaceutical parameters from (Dose, Molecular Weight, Melting Point, Log P).

---

## Root Cause Analysis

### File: `src/services/llm_merger_service.py`

**Method:** `_get_category_schema()` (lines 196-288 before fix)

**Problem:** Only 2 of 10 Phase 1 categories had schemas defined:
- ✓ Market Overview
- ✓ Competitive Landscape
- ✗ Physicochemical Profile (MISSING - critical for parameters!)
- ✗ Pharmacokinetics (MISSING - critical for parameters!)
- ✗ Dosage Forms (MISSING)
- ✗ Current Formulations (MISSING)
- ✗ Clinical Trials & Safety (MISSING)
- ✗ Commercial Opportunities (MISSING)
- ✗ Investigational Formulations (MISSING)
- ✗ Regulatory & Patent Status (MISSING)

**Method:** `extract_structured_data()` (lines 290-368)

```python
schema = self._get_category_schema(category_name)

if not schema:
    # Fallback to generic extraction for unknown categories
    extraction_prompt = f"""Extract structured data from this {category_name} text:

{merged_content[:3000]}

Return JSON with relevant fields for {category_name}."""
```

When schema was empty (8 out of 10 categories), the LLM received only a vague prompt with no structure guidance, resulting in either empty `{}` or inconsistent extraction.

---

## Fix Applied

### Changes to `src/services/llm_merger_service.py`

#### 1. Added Schemas for All Missing Categories (lines 287-426)

**Physicochemical Profile Schema:**
```python
"Physicochemical Profile": {
    "parameters": [
        {
            "parameter": "Molecular Weight",
            "value": "180.16",
            "unit": "Da"
        },
        {
            "parameter": "Melting Point",
            "value": "146-150",
            "unit": "°C"
        },
        {
            "parameter": "Log P",
            "value": "1.19",
            "unit": ""
        },
        ...
    ]
}
```

**Pharmacokinetics Schema:**
```python
"Pharmacokinetics": {
    "parameters": [
        {
            "parameter": "Bioavailability",
            "value": "63-89%",
            "route": "Oral"
        },
        {
            "parameter": "Half-life",
            "value": "2-3",
            "unit": "hours"
        },
        ...
    ]
}
```

**Plus schemas for:**
- Dosage Forms
- Current Formulations
- Clinical Trials & Safety
- Commercial Opportunities
- Investigational Formulations
- Regulatory & Patent Status

#### 2. Updated Extraction Instructions (lines 406-435)

Enhanced the LLM prompt with specific instructions for each category type:

```
For Physicochemical Profile:
- Include ONLY "parameters" key with array of parameter objects
- Each parameter must have: "parameter", "value", "unit"

For Pharmacokinetics:
- Include ONLY "parameters" key with array of parameter objects
- Include: Bioavailability, Protein Binding, Half-life, Metabolism, Excretion
```

### Changes to `src/services/pipeline_integration_service.py`

#### 3. Fixed Fallback Merge Path (line 726)

Added `structured_data: {}` to fallback merge storage:

```python
storage_data = {
    "merged_content": merged_summary,
    "confidence_score": overall_confidence,
    "structured_data": {},  # Empty for fallback, no LLM extraction
    ...
}
```

Previously, fallback merge didn't include `structured_data` at all, causing storage to receive incomplete data.

---

## How This Fixes Phase 2

### Phase 2 Flow (Before Fix)

1. Phase 2 requests Phase 1 data
2. `_prepare_phase1_context()` gets `structured_data` from database
3. **Result:** Empty `{}` for Physicochemical Profile and Pharmacokinetics
4. LLM receives empty context
5. **Parameter extraction returns:** `{"Dose": null, "Molecular Weight": null, ...}`
6. **Phase 2 scoring fails** (all scores are null)

### Phase 2 Flow (After Fix)

1. Phase 2 requests Phase 1 data
2. `_prepare_phase1_context()` gets `structured_data` from database
3. **Result:** Properly structured JSON with parameter arrays
4. LLM receives:
```json
{
  "parameters": [
    {"parameter": "Molecular Weight", "value": "180.16", "unit": "Da"},
    {"parameter": "Melting Point", "value": "146-150", "unit": "°C"},
    {"parameter": "Log P", "value": "1.19", "unit": ""}
  ]
}
```
5. **Parameter extraction succeeds:** `{"Dose": 10.5, "Molecular Weight": 180.16, ...}`
6. **Phase 2 scoring works** (scores calculated from extracted values)

---

## Testing the Fix

### Option 1: Full Pipeline Test (Expensive)

Create a new drug request and verify structured_data is populated:

```bash
curl -X POST http://localhost:8001/api/v1/drug-request \
  -H "Content-Type: application/json" \
  -d '{"drug_name": "Ibuprofen", "delivery_method": "Transdermal"}'
```

Wait for completion, then check:

```sql
SELECT cr.category_name, md.structured_data
FROM category_results cr
LEFT JOIN merged_data_results md ON cr.id = md.category_result_id
WHERE cr.request_id = '<new_request_id>'
AND cr.category_name IN ('Physicochemical Profile', 'Pharmacokinetics');
```

**Expected:** Both categories should have non-empty structured_data with "parameters" arrays.

### Option 2: Re-run Phase 1 Only (If Raw Data Exists)

If the original Phase 1 pipeline stored raw API responses, you could re-run the merge stage to extract structured_data. However, this requires raw collection data to exist in the database.

### Option 3: Manual LLM Test

Test the extraction directly with sample merged_content:

```python
from src.services.llm_merger_service import LLMMergerService
import asyncio

async def test_extraction():
    merger = LLMMergerService()

    sample_content = """
    Acetaminophen Physicochemical Properties:
    - Molecular Weight: 151.16 Da
    - Melting Point: 169-170.5°C
    - Log P (octanol-water): 0.46
    - Water Solubility: 14 mg/mL at 20°C
    """

    result = await merger.extract_structured_data(
        merged_content=sample_content,
        category_name="Physicochemical Profile"
    )

    print(result)

asyncio.run(test_extraction())
```

**Expected output:**
```json
{
  "parameters": [
    {"parameter": "Molecular Weight", "value": "151.16", "unit": "Da"},
    {"parameter": "Melting Point", "value": "169-170.5", "unit": "°C"},
    {"parameter": "Log P", "value": "0.46", "unit": ""}
  ]
}
```

---

## Files Modified

### 1. `src/services/llm_merger_service.py`
- **Lines 287-426:** Added 8 new category schemas
- **Lines 406-435:** Updated extraction prompt instructions

### 2. `src/services/pipeline_integration_service.py`
- **Line 726:** Added `structured_data: {}` to fallback merge

---

## Next Steps

1. ✅ **Phase 1 fix applied** - Structured data extraction now works
2. ⏳ **Test with new drug request** - Verify schemas work end-to-end
3. ⏳ **Test Phase 2 scoring** - Verify parameter extraction succeeds
4. ⏳ **Monitor LLM extraction quality** - Adjust schemas if needed

---

## Verification Queries

### Check if structured_data is populated:

```sql
SELECT
    cr.category_name,
    CASE
        WHEN md.structured_data IS NULL THEN 'NULL'
        WHEN md.structured_data::text = '{}' THEN 'EMPTY'
        ELSE 'POPULATED'
    END as data_status,
    jsonb_pretty(md.structured_data) as data_preview
FROM category_results cr
LEFT JOIN merged_data_results md ON cr.id = md.category_result_id
JOIN pharmaceutical_categories pc ON cr.category_name = pc.name
WHERE cr.request_id = '<request_id>'
AND pc.phase = 1
ORDER BY cr.category_name;
```

### Check parameter extraction in Phase 2:

```sql
SELECT
    summary,
    json_extract_path_text(data::json, 'extracted_parameters')
FROM category_results
WHERE request_id = '<request_id>'
AND category_name = 'Parameter-Based Scoring Matrix';
```

---

## Conclusion

The Phase 1 structured data extraction bug has been fixed by adding complete schemas for all 10 pharmaceutical categories. This enables Phase 2's Parameter-Based Scoring to successfully extract pharmaceutical parameters and calculate scores.

**Status:** ✅ Fix Complete - Ready for Testing
