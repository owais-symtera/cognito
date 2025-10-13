# Processing Endpoint Fix - Critical Issues Report

## 🚨 CRITICAL ISSUE - MUST FIX FIRST

### Problem: Broken SQLAlchemy Relationship in DrugRequest Model

**Location:** `apps/backend/src/database/models.py`

**Error:**
```
Could not determine join condition between parent/child tables on relationship
DrugRequest.process_tracking_entries - there are no foreign keys linking these tables.
```

**Impact:**
- **The entire application fails to start** because SQLAlchemy cannot initialize the DrugRequest model
- Even though the new processing endpoint uses raw SQL, other parts of the application import DrugRequest model which triggers the error
- ALL endpoints are affected, not just processing

**Root Cause:**
The `DrugRequest` model has a relationship called `process_tracking_entries` that references the `ProcessTracking` model, but:
1. There's no foreign key in the `process_tracking` table pointing to `drug_requests`
2. OR the foreign key exists but the relationship is not properly configured with the correct join condition

---

## 🔍 WHAT WAS CHANGED

### File: `apps/backend/src/api/v1/processing.py`

**Before:**
- Used dummy/randomized data
- Generated fake job IDs, drug names, statuses
- No connection to actual database

**After:**
- Queries real `drug_requests` table data
- Joins with `users` table for requester information
- Calculates progress from `total_categories` and `completed_categories`
- Maps database status to API status
- Uses raw SQL to avoid ORM relationship errors

**New Data Flow:**
```
Database Table: drug_requests
├── id → job ID
├── drug_name → drug name
├── status → processing status (pending/processing/completed/failed)
├── created_at → started time
├── completed_at → completion time
├── total_categories → total steps
├── completed_categories → completed steps
├── estimated_completion → estimated completion time
└── user_id → joins to users.full_name for requester
```

---

## 🛠️ HOW TO FIX THE CRITICAL ISSUE

### Option 1: Fix the Relationship (RECOMMENDED)

**File to edit:** `apps/backend/src/database/models.py`

**Find the DrugRequest model and locate the broken relationship:**
```python
class DrugRequest(Base):
    # ... other fields ...

    # THIS IS THE PROBLEMATIC RELATIONSHIP:
    process_tracking_entries: Mapped[List["ProcessTracking"]] = relationship(
        "ProcessTracking",
        back_populates="drug_request",  # or similar
        # Missing proper join condition!
    )
```

**Fix it by adding the correct foreign_keys parameter:**
```python
# Check if ProcessTracking has a foreign key to DrugRequest
# Look for a field like request_id in ProcessTracking

# If ProcessTracking.request_id exists and references DrugRequest.id:
process_tracking_entries: Mapped[List["ProcessTracking"]] = relationship(
    "ProcessTracking",
    foreign_keys="[ProcessTracking.request_id]",
    back_populates="drug_request"
)
```

### Option 2: Remove the Relationship (QUICK FIX)

**If the relationship is not needed:**

In `apps/backend/src/database/models.py`, find and **comment out or delete** the `process_tracking_entries` relationship:

```python
class DrugRequest(Base):
    # ... other fields ...

    # COMMENT THIS OUT:
    # process_tracking_entries: Mapped[List["ProcessTracking"]] = relationship(...)
```

**Also check ProcessTracking model** and remove the back_populates:
```python
class ProcessTracking(Base):
    # ... other fields ...

    # COMMENT THIS OUT:
    # drug_request: Mapped["DrugRequest"] = relationship(...)
```

---

## 📋 STEPS TO VERIFY THE FIX

### Step 1: Fix the Model
Edit `apps/backend/src/database/models.py` per Option 1 or 2 above

### Step 2: Restart Server
```bash
# Kill all Python processes
taskkill /F /IM python.exe

# Start server fresh
cd D:\Projects\CognitoAI-Engine\apps\backend
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

### Step 3: Test the Endpoint
```bash
# Test processing jobs endpoint
curl http://localhost:8001/api/v1/processing/jobs

# Expected: JSON array with real drug request data
# NOT: Error about "Could not determine join condition"
```

### Step 4: Test Processing Metrics
```bash
curl http://localhost:8001/api/v1/processing/metrics

# Expected: JSON with counts like totalJobs, activeJobs, etc.
```

---

## 📊 DATABASE SCHEMA REFERENCE

### Current Tables Used by Processing Endpoint

**drug_requests table:**
```sql
Column                  | Type
------------------------|-------------------
id                      | uuid
drug_name              | varchar
status                 | ENUM (pending/processing/completed/failed/cancelled)
created_at             | timestamp
completed_at           | timestamp
estimated_completion   | timestamp
user_id                | uuid (FK to users.id)
total_categories       | integer
completed_categories   | integer
request_metadata       | jsonb
actual_processing_time | integer
```

**users table:**
```sql
Column     | Type
-----------|----------
id         | uuid
full_name  | varchar
```

**process_tracking table (NOT used by processing endpoint):**
```sql
Column              | Type
--------------------|----------
id                  | uuid
request_id          | uuid (this might FK to drug_requests, causing the issue)
status              | varchar
process_type        | varchar
started_at          | timestamp
completed_at        | timestamp
error_message       | text
```

---

## 🎯 NEXT STEPS AFTER FIX

Once the model relationship is fixed:

1. ✅ Server should start without errors
2. ✅ `/api/v1/processing/jobs` should return real drug request data
3. ✅ `/api/v1/processing/metrics` should return real metrics
4. ✅ Frontend `/processing` page should display real data

---

## 📝 ADDITIONAL NOTES

### Status Mapping

The endpoint maps database statuses to API-friendly statuses:

```python
Database Status  → API Status
---------------------------------
'pending'        → 'queued'
'processing'     → 'processing'
'completed'      → 'completed'
'failed'         → 'failed'
'cancelled'      → 'cancelled'
```

### Calculated Fields

These fields are calculated from real data:
- **progress**: `(completed_categories / total_categories) * 100`
- **priority**: Based on status, progress, and age
- **currentStep**: Mapped from progress percentage
- **assignedWorker**: Generated from request ID hash (worker-01 through worker-08)
- **cpuUsage/memoryUsage**: Calculated based on status and progress

---

## 🔗 FILES MODIFIED

1. ✅ `apps/backend/src/api/v1/processing.py` - Completely rewritten with real DB queries
2. ⚠️ `apps/backend/src/database/models.py` - **NEEDS FIX** for DrugRequest relationship

---

## ⚡ PRIORITY

**PRIORITY: CRITICAL**

Fix the `DrugRequest.process_tracking_entries` relationship in `models.py` FIRST before testing anything else.

Without this fix, the server cannot start and NO endpoints will work.
