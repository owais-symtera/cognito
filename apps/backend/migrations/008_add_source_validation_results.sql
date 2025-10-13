-- Migration 008: Add Source Validation Results Table
-- Stores per-source validation results with table-to-JSON conversion

CREATE TABLE IF NOT EXISTS source_validation_results (
    id UUID PRIMARY KEY,
    category_result_id UUID NOT NULL,
    source_index INTEGER NOT NULL,

    -- Source information
    provider VARCHAR(100),
    model VARCHAR(100),
    authority_score NUMERIC(5, 2) DEFAULT 0.0,

    -- Table validation data
    tables_json JSONB NOT NULL DEFAULT '[]',
    total_tables INTEGER DEFAULT 0,
    total_rows INTEGER DEFAULT 0,
    validated_rows INTEGER DEFAULT 0,

    -- Validation scores
    validation_score NUMERIC(5, 4) DEFAULT 0.0,
    validation_passed BOOLEAN DEFAULT FALSE,
    pass_rate VARCHAR(20) DEFAULT '0.0%',

    -- Timestamps
    validated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Foreign key
    CONSTRAINT fk_category_result
        FOREIGN KEY (category_result_id)
        REFERENCES category_results(id)
        ON DELETE CASCADE
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_source_validation_category_result
    ON source_validation_results(category_result_id);

CREATE INDEX IF NOT EXISTS idx_source_validation_provider
    ON source_validation_results(provider);

CREATE INDEX IF NOT EXISTS idx_source_validation_passed
    ON source_validation_results(validation_passed);

CREATE INDEX IF NOT EXISTS idx_source_validation_score
    ON source_validation_results(validation_score);

-- Comment on table
COMMENT ON TABLE source_validation_results IS 'Stores per-source validation results with table-to-JSON conversion and row-level validation metadata';
COMMENT ON COLUMN source_validation_results.tables_json IS 'JSON array of tables with row-level validation data';
COMMENT ON COLUMN source_validation_results.pass_rate IS 'Percentage of rows that passed validation';
