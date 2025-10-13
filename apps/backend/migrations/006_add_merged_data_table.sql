-- Migration 006: Add Merged Data Table
-- Stores intelligently merged pharmaceutical data with full audit trail

CREATE TABLE IF NOT EXISTS merged_data_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_result_id UUID NOT NULL,
    request_id UUID NOT NULL,
    category_id INTEGER NOT NULL,
    category_name VARCHAR(255) NOT NULL,

    -- Merged content
    merged_content TEXT NOT NULL,
    structured_data JSONB DEFAULT '{}',

    -- Quality metrics
    merge_confidence_score FLOAT DEFAULT 0.0,
    data_quality_score FLOAT DEFAULT 0.0,
    overall_confidence FLOAT DEFAULT 0.0,

    -- Merge metadata
    merge_method VARCHAR(50) NOT NULL, -- 'llm_assisted', 'data_merger', 'weighted', 'fallback'
    sources_merged INTEGER DEFAULT 0,
    conflicts_resolved JSONB DEFAULT '[]', -- Array of conflict resolutions
    key_findings JSONB DEFAULT '[]', -- Array of key findings

    -- Audit trail
    merge_records JSONB DEFAULT '[]', -- Full merge operation audit
    source_references JSONB DEFAULT '[]', -- References to source data
    merge_strategy_used VARCHAR(100), -- Which strategy was used

    -- LLM metadata (if LLM-assisted)
    llm_model VARCHAR(50),
    llm_tokens_used INTEGER DEFAULT 0,
    llm_cost_estimate FLOAT DEFAULT 0.0,

    -- Timestamps
    merged_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Foreign keys
    FOREIGN KEY (category_result_id) REFERENCES category_results(id) ON DELETE CASCADE,
    FOREIGN KEY (request_id) REFERENCES drug_requests(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_merged_data_category_result ON merged_data_results(category_result_id);
CREATE INDEX IF NOT EXISTS idx_merged_data_request ON merged_data_results(request_id);
CREATE INDEX IF NOT EXISTS idx_merged_data_category ON merged_data_results(category_id);
CREATE INDEX IF NOT EXISTS idx_merged_data_method ON merged_data_results(merge_method);
CREATE INDEX IF NOT EXISTS idx_merged_data_merged_at ON merged_data_results(merged_at);

-- GIN index for JSONB fields
CREATE INDEX IF NOT EXISTS idx_merged_data_structured ON merged_data_results USING GIN (structured_data);
CREATE INDEX IF NOT EXISTS idx_merged_data_conflicts ON merged_data_results USING GIN (conflicts_resolved);

COMMENT ON TABLE merged_data_results IS 'Stores intelligently merged pharmaceutical data from multiple sources';
COMMENT ON COLUMN merged_data_results.merged_content IS 'Final merged content as text';
COMMENT ON COLUMN merged_data_results.structured_data IS 'Extracted structured data from merged content';
COMMENT ON COLUMN merged_data_results.conflicts_resolved IS 'Array of conflict resolutions with source info';
COMMENT ON COLUMN merged_data_results.merge_records IS 'Full audit trail of all merge operations';
COMMENT ON COLUMN merged_data_results.merge_method IS 'Method used for merging: llm_assisted, data_merger, weighted, or fallback';
