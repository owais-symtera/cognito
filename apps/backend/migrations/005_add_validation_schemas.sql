-- Migration: Add Category Validation Schemas
-- Description: Stores validation rules and algorithms for each category

-- Table: category_validation_schemas
CREATE TABLE IF NOT EXISTS category_validation_schemas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id INTEGER NOT NULL,
    category_name VARCHAR(255) NOT NULL,
    version VARCHAR(50) DEFAULT '1.0',
    validation_config JSONB NOT NULL,  -- Full validation algorithm and rules
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    -- Note: No FK constraint to categories table (managed in application layer)
);

-- Table: validation_results
-- Stores validation execution results for audit trail
CREATE TABLE IF NOT EXISTS validation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_result_id UUID NOT NULL,
    validation_schema_id UUID NOT NULL,
    validation_passed BOOLEAN DEFAULT false,
    validation_score FLOAT DEFAULT 0.0,  -- 0.0 to 1.0
    confidence_penalty FLOAT DEFAULT 0.0,  -- How much to reduce confidence
    step_results JSONB,  -- Detailed results per validation step
    failed_steps TEXT[],  -- Array of failed step names
    data_quality_issues JSONB,  -- Specific issues found
    recommendations JSONB,  -- Suggestions for improvement
    validated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_category_result FOREIGN KEY (category_result_id) REFERENCES category_results(id) ON DELETE CASCADE,
    CONSTRAINT fk_validation_schema FOREIGN KEY (validation_schema_id) REFERENCES category_validation_schemas(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_validation_schemas_category ON category_validation_schemas(category_id);
CREATE INDEX idx_validation_schemas_enabled ON category_validation_schemas(enabled);
CREATE INDEX idx_validation_results_category_result ON validation_results(category_result_id);
CREATE INDEX idx_validation_results_schema ON validation_results(validation_schema_id);
CREATE INDEX idx_validation_results_validated_at ON validation_results(validated_at);

-- Insert default validation schema for "Market Overview" category
INSERT INTO category_validation_schemas (category_id, category_name, version, validation_config, enabled)
VALUES (
    1,  -- Market Overview category ID
    'Market Overview',
    '1.0',
    '{
        "category": "Market Overview",
        "version": "1.0",
        "description": "Validates market size data, CAGRs, and regional consistency",
        "required_inputs": {
            "drug_name": {"type": "string", "required": true},
            "regions": {"type": "array", "min_length": 1},
            "market_sizes": {"type": "object", "required": true},
            "cagrs": {"type": "object", "required": true},
            "year_ranges": {"type": "object", "required": true}
        },
        "validation_steps": [
            {
                "step_number": 1,
                "step_name": "collect_market_data",
                "description": "Gather data from multiple credible sources",
                "type": "data_collection",
                "rules": {
                    "expected_sources": ["market_research", "company_reports", "regulatory"],
                    "min_sources": 1
                },
                "weight": 0.15
            },
            {
                "step_number": 2,
                "step_name": "validate_sources",
                "description": "Cross-check source consistency",
                "type": "consistency_check",
                "rules": {
                    "supported_threshold": 0.10,
                    "plausible_threshold": 0.20,
                    "weak_threshold": 1.0
                },
                "scoring": {
                    "supported": 1.0,
                    "plausible": 0.6,
                    "weak": 0.3
                },
                "weight": 0.25
            },
            {
                "step_number": 3,
                "step_name": "normalize_time_periods",
                "description": "Align all figures to consistent year ranges",
                "type": "normalization",
                "rules": {
                    "standard_current_range": "2019-2024",
                    "standard_forecast_range": "2024-2034"
                },
                "weight": 0.10
            },
            {
                "step_number": 4,
                "step_name": "validate_current_market_table",
                "description": "Build and validate current market overview",
                "type": "table_validation",
                "rules": {
                    "global_sum_tolerance": 0.05,
                    "required_columns": ["region", "market_size_usd", "cagr", "year_range"],
                    "required_regions": ["Global", "North America", "Europe", "Asia Pacific"]
                },
                "weight": 0.20
            },
            {
                "step_number": 5,
                "step_name": "build_forecast_table",
                "description": "Apply CAGR formula for 10-year projections",
                "type": "calculation",
                "formula": "Market_Size_Future = Market_Size_Current × (1 + CAGR)^(Years)",
                "rules": {
                    "forecast_years": 10,
                    "global_sum_tolerance": 0.05,
                    "min_cagr": -0.10,
                    "max_cagr": 0.50
                },
                "weight": 0.20
            },
            {
                "step_number": 6,
                "step_name": "add_validity_notes",
                "description": "Assign validity status to each data point",
                "type": "classification",
                "validity_levels": {
                    "supported": "Consistent across at least 2 credible reports",
                    "plausible": "Single source or varying numbers",
                    "weak": "Speculative or mismatched data"
                },
                "weight": 0.10
            }
        ],
        "output_structure": {
            "tables": [
                {
                    "name": "current_market_overview",
                    "columns": ["region", "market_size_usd", "cagr", "year_range", "validity", "sources"]
                },
                {
                    "name": "ten_year_forecast",
                    "columns": ["region", "projected_size_usd", "cagr", "year_range", "validity", "calculation_method"]
                }
            ]
        },
        "scoring": {
            "pass_threshold": 0.70,
            "confidence_penalty_formula": "(1.0 - validation_score) * 0.5"
        }
    }'::jsonb,
    true
);

-- Comments
COMMENT ON TABLE category_validation_schemas IS 'Stores validation algorithms and rules for each pharmaceutical category';
COMMENT ON TABLE validation_results IS 'Audit trail of validation execution results with detailed findings';
COMMENT ON COLUMN validation_results.validation_score IS 'Overall validation score from 0.0 (failed) to 1.0 (perfect)';
COMMENT ON COLUMN validation_results.confidence_penalty IS 'Amount to reduce confidence score if validation fails';
