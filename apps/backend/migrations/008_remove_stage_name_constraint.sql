-- Migration: Remove stage_name CHECK constraint to allow Phase 2 stages
-- Description: The original constraint only allowed Phase 1 stages. Phase 2 uses category names as stage names.
-- Date: 2025-10-07

-- Drop the CHECK constraint on stage_name
ALTER TABLE pipeline_stage_executions
DROP CONSTRAINT IF EXISTS pipeline_stage_executions_stage_name_check;

-- Add comment explaining the change
COMMENT ON COLUMN pipeline_stage_executions.stage_name IS 'Stage name - can be Phase 1 stage (data_collection, verification, merging, llm_summary) or Phase 2 category name';
