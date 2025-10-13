# Backend Directory Organization

**Last Updated:** 2025-01-15

This document describes the organization and structure of the CognitoAI Engine backend directory.

## Directory Structure

```
apps/backend/
├── src/                          # Application source code
│   ├── api/                      # API endpoints and routers
│   ├── services/                 # Business logic services
│   ├── utils/                    # Utility functions
│   └── main.py                   # FastAPI application entry point
│
├── scripts/                      # Utility scripts and tools (102+ scripts)
│   ├── diagnostics/              # Database inspection and verification scripts
│   ├── testing/                  # Manual testing and integration tests
│   ├── migrations/               # Database migration and seeding scripts
│   └── utilities/                # Maintenance and fix scripts
│
├── migrations/                   # Alembic database migrations
│   └── *.sql                     # SQL migration files
│
├── tests/                        # Automated test suite
│   └── ...                       # Unit and integration tests
│
├── docs/                         # Documentation files
│   ├── BACKEND_ORGANIZATION.md   # This file
│   ├── FINAL_OUTPUT_INTEGRATION_STATUS.md
│   ├── PHASE1_FIX_SUMMARY.md
│   ├── PHASE2_TESTING_GUIDE.md
│   └── scoring_verification_report.txt
│
├── logs/                         # Application and test logs
│   └── *.log                     # Log files with timestamps
│
├── alembic/                      # Alembic configuration
├── extra/                        # Extra/legacy files
├── venv/                         # Python virtual environment
│
├── main.py                       # Application entry point (imports from src/)
├── run_server.py                 # Server startup script
├── alembic.ini                   # Alembic configuration
├── pytest.ini                    # Pytest configuration
├── provider_config.json          # API provider configuration
├── requirements.txt              # Python dependencies
└── requirements-dev.txt          # Development dependencies
```

## Root Directory Files

### Essential Files (Keep in Root)

| File | Purpose |
|------|---------|
| `main.py` | Application entry point, imports from `src/main.py` |
| `run_server.py` | Server startup script with configuration |
| `alembic.ini` | Alembic database migration configuration |
| `pytest.ini` | Pytest test runner configuration |
| `provider_config.json` | API provider settings and credentials |
| `requirements.txt` | Production Python dependencies |
| `requirements-dev.txt` | Development Python dependencies |
| `.env` | Environment variables (not in git) |

### Configuration Files

- **alembic.ini** - Database migration settings
- **pytest.ini** - Test framework configuration
- **provider_config.json** - API provider configuration (ChatGPT, Perplexity, etc.)

## Scripts Organization

All utility scripts have been organized into `scripts/` with subdirectories:

### 📊 scripts/diagnostics/ (50+ scripts)

Database inspection and verification tools. **Safe to run** - read-only operations.

**Examples:**
- `check_active_categories.py` - Verify active pharmaceutical categories
- `check_db_schema.py` - Inspect database schema
- `check_phase1_data.py` - Verify Phase 1 data
- `check_phase2_extraction.py` - Check Phase 2 parameter extraction
- `check_request_*.py` - Inspect specific requests (many variants)

### 🧪 scripts/testing/ (16 scripts)

Manual testing and integration verification scripts.

**Examples:**
- `test_full_workflow.py` - End-to-end workflow test
- `test_phase2_integration.py` - Phase 2 integration test
- `test_category_query.py` - Category data queries
- `test_dose_extraction.py` - Parameter extraction logic

### 🔧 scripts/migrations/ (10 scripts)

Database migration and initial data seeding scripts. **Run with caution** - modifies database.

**Examples:**
- `run_final_output_migration.py` - Create request_final_output table
- `seed_phase2_config.py` - Populate Phase 2 configuration
- `seed_categories.py` - Seed pharmaceutical categories
- `apply_phase2_migration.py` - Apply Phase 2 schema changes

### 🛠️ scripts/utilities/ (17 scripts)

Maintenance, fixes, and database operation scripts. **Review before running** - may modify data.

**Examples:**
- `fix_scoring_ranges.py` - Fix scoring configurations
- `update_prompt_templates.py` - Update category prompts
- `show_phase2_status.py` - Display Phase 2 status
- `view_database_data.py` - Browse database contents
- `start_server_with_logs.py` - Start server with logging

## Running the Application

### Start the Server

```bash
# From backend directory
python run_server.py

# Or using uvicorn directly
uvicorn src.main:app --reload --port 8000
```

### Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_categories.py

# Run with coverage
pytest --cov=src
```

### Run Scripts

```bash
# Diagnostic scripts (safe)
python scripts/diagnostics/check_active_categories.py

# Testing scripts
python scripts/testing/test_full_workflow.py

# Migration scripts (caution!)
python scripts/migrations/run_final_output_migration.py

# Utility scripts
python scripts/utilities/show_phase2_status.py
```

## Documentation Files

All markdown documentation is now in `docs/`:

- **BACKEND_ORGANIZATION.md** - This file, directory structure guide
- **FINAL_OUTPUT_INTEGRATION_STATUS.md** - Final output generation implementation status
- **PHASE1_FIX_SUMMARY.md** - Phase 1 implementation summary
- **PHASE2_TESTING_GUIDE.md** - Phase 2 testing guide
- **scoring_verification_report.txt** - Scoring verification results

## Removed Files

The following types of files have been removed from the root directory:

- ❌ Old SQLite database files (`*.db`)
- ❌ Temporary files (`nul`)
- ❌ Old test scripts (moved to `scripts/testing/`)
- ❌ Diagnostic scripts (moved to `scripts/diagnostics/`)
- ❌ Migration scripts (moved to `scripts/migrations/`)
- ❌ Utility scripts (moved to `scripts/utilities/`)

## Before Reorganization

Previously, the backend root directory contained:
- **60+ Python scripts** scattered in root
- **Multiple database files** (.db files)
- **Various text/log files** in root
- **Documentation files** mixed with code

## After Reorganization

Now the backend root directory contains:
- **7 essential configuration files** only
- **Well-organized directories** with clear purposes
- **102+ scripts organized** into 4 subdirectories
- **Documentation centralized** in `docs/`
- **Clean, professional structure**

## Best Practices

1. **Never add new scripts to root** - Use appropriate subdirectory in `scripts/`
2. **Keep root clean** - Only essential config files in root
3. **Document new scripts** - Add description to scripts/README.md
4. **Use version control** - All scripts should be committed to git
5. **Name consistently** - Follow naming patterns (check_*, test_*, fix_*, etc.)

## Benefits of This Organization

✅ **Cleaner root directory** - Easy to find essential files
✅ **Better organization** - Scripts grouped by purpose
✅ **Easier onboarding** - New developers can navigate easily
✅ **Professional structure** - Industry-standard layout
✅ **Reduced clutter** - No confusion about which files are important
✅ **Better documentation** - Clear README in scripts/ folder

## Migration Notes

- **Date Reorganized:** 2025-01-15
- **Scripts Moved:** 102+ files
- **Files Removed:** All temporary .db files, nul file
- **Breaking Changes:** None - all scripts still functional
- **Path Updates:** Scripts use relative imports, no path changes needed

## Support

For questions about:
- **Application structure:** See `src/` directory
- **Scripts usage:** See `scripts/README.md`
- **Database migrations:** See `migrations/` directory
- **API documentation:** See `src/api/` directory
- **Testing:** See `tests/` directory

---

**Maintained By:** CognitoAI Development Team
**Last Major Reorganization:** 2025-01-15
