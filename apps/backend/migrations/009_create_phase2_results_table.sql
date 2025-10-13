-- Migration: Create phase2_results table
-- Purpose: Store Phase 2 parameter extraction and scoring results
-- Created: 2025-01-15

CREATE TABLE IF NOT EXISTS phase2_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL,
    parameter_name VARCHAR(100) NOT NULL,
    extracted_value FLOAT,
    score INTEGER,
    weighted_score FLOAT,
    unit VARCHAR(50),
    extraction_method VARCHAR(100),
    rationale TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT uq_phase2_results_request_param UNIQUE (request_id, parameter_name),
    CONSTRAINT ck_phase2_results_score_valid CHECK (score >= 0 AND score <= 9)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_phase2_results_request ON phase2_results(request_id);
CREATE INDEX IF NOT EXISTS idx_phase2_results_parameter ON phase2_results(parameter_name);
CREATE INDEX IF NOT EXISTS idx_phase2_results_request_param ON phase2_results(request_id, parameter_name);

-- Add comments for documentation
COMMENT ON TABLE phase2_results IS 'Stores Phase 2 parameter extraction and scoring results for drug suitability assessment';
COMMENT ON COLUMN phase2_results.parameter_name IS 'Parameter name (e.g., Dose, Molecular Weight, Melting Point, Log P)';
COMMENT ON COLUMN phase2_results.extracted_value IS 'Numeric value extracted from Phase 1 data';
COMMENT ON COLUMN phase2_results.score IS 'Score (0-5) based on scoring ranges';
COMMENT ON COLUMN phase2_results.weighted_score IS 'Score multiplied by parameter weight';
COMMENT ON COLUMN phase2_results.unit IS 'Unit of measurement (e.g., mg/kg/day, Da, °C)';
COMMENT ON COLUMN phase2_results.extraction_method IS 'Method used for extraction (e.g., phase1_summary, regex, llm)';
COMMENT ON COLUMN phase2_results.rationale IS 'Explanation of how the score was determined';
