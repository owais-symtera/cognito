-- Migration: Create pipeline_stage_executions table
-- Description: Store intermediate data from each pipeline stage for auditing and debugging
-- Date: 2025-10-01

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS pipeline_stage_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL REFERENCES drug_requests(id) ON DELETE CASCADE,
    category_result_id UUID REFERENCES category_results(id) ON DELETE CASCADE,

    -- Stage identification
    stage_name VARCHAR(50) NOT NULL CHECK (stage_name IN ('data_collection', 'verification', 'merging', 'llm_summary')),
    stage_order INTEGER NOT NULL,

    -- Execution status
    executed BOOLEAN NOT NULL DEFAULT false,
    skipped BOOLEAN NOT NULL DEFAULT false,

    -- Stage data (stored as JSONB for flexibility)
    input_data JSONB,           -- What was passed to this stage
    output_data JSONB,           -- What the stage produced
    stage_metadata JSONB,        -- Stage-specific metadata (weights, scores, etc.)

    -- Performance metrics
    execution_time_ms INTEGER DEFAULT 0,

    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Indexes for efficient querying
    CONSTRAINT unique_stage_per_category UNIQUE(category_result_id, stage_name)
);

-- Index for querying by request
CREATE INDEX idx_pipeline_stages_request ON pipeline_stage_executions(request_id);

-- Index for querying by category result
CREATE INDEX idx_pipeline_stages_category ON pipeline_stage_executions(category_result_id);

-- Index for filtering by stage name
CREATE INDEX idx_pipeline_stages_name ON pipeline_stage_executions(stage_name);

-- Index for filtering by execution status
CREATE INDEX idx_pipeline_stages_executed ON pipeline_stage_executions(executed, skipped);

COMMENT ON TABLE pipeline_stage_executions IS 'Logs execution details for each pipeline stage including intermediate data';
COMMENT ON COLUMN pipeline_stage_executions.input_data IS 'Input data passed to this stage (JSONB)';
COMMENT ON COLUMN pipeline_stage_executions.output_data IS 'Output data produced by this stage (JSONB)';
COMMENT ON COLUMN pipeline_stage_executions.stage_metadata IS 'Stage-specific metadata like verification weights, merge conflicts, etc.';
