-- Migration: Create request_final_output table
-- Purpose: Store complete final output JSON matching apixaban-complete-response.json format
-- Created: 2025-01-15

CREATE TABLE IF NOT EXISTS request_final_output (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL UNIQUE,
    drug_name VARCHAR(255) NOT NULL,
    delivery_method VARCHAR(100) NOT NULL,

    -- Store the complete JSON matching the sample format
    final_output JSONB NOT NULL,

    -- Quick-access fields for filtering/sorting
    overall_td_score FLOAT,
    overall_tm_score FLOAT,
    td_verdict VARCHAR(20), -- 'Go' or 'No-Go'
    tm_verdict VARCHAR(20),
    go_decision VARCHAR(20), -- 'GO', 'NO-GO', 'CONDITIONAL'
    investment_priority VARCHAR(20), -- 'Low', 'Medium', 'High'
    risk_level VARCHAR(20), -- 'Low', 'Medium', 'High'

    -- Metadata
    generated_at TIMESTAMP DEFAULT NOW(),
    version VARCHAR(20) DEFAULT '1.0',

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_final_output_request ON request_final_output(request_id);
CREATE INDEX IF NOT EXISTS idx_final_output_drug ON request_final_output(drug_name);
CREATE INDEX IF NOT EXISTS idx_final_output_verdict ON request_final_output(td_verdict, tm_verdict);
CREATE INDEX IF NOT EXISTS idx_final_output_decision ON request_final_output(go_decision);
CREATE INDEX IF NOT EXISTS idx_final_output_generated_at ON request_final_output(generated_at DESC);

-- Add comments for documentation
COMMENT ON TABLE request_final_output IS 'Stores complete final output JSON for each request, matching the apixaban-complete-response.json format';
COMMENT ON COLUMN request_final_output.final_output IS 'Complete JSON output with executive_summary, all Phase 1 categories, suitability_matrix, coverage scorecard, and recommendations';
COMMENT ON COLUMN request_final_output.overall_td_score IS 'Transdermal weighted total score (0-9)';
COMMENT ON COLUMN request_final_output.overall_tm_score IS 'Transmucosal weighted total score (0-9)';
COMMENT ON COLUMN request_final_output.td_verdict IS 'Transdermal Go/No-Go verdict';
COMMENT ON COLUMN request_final_output.tm_verdict IS 'Transmucosal Go/No-Go verdict';
COMMENT ON COLUMN request_final_output.go_decision IS 'Overall GO/NO-GO/CONDITIONAL decision from executive summary';
COMMENT ON COLUMN request_final_output.investment_priority IS 'Investment priority level: Low, Medium, or High';
COMMENT ON COLUMN request_final_output.risk_level IS 'Risk assessment level: Low, Medium, or High';
