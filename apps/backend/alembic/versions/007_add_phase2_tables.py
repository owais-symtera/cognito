"""Add Phase 2 Decision Intelligence tables

Revision ID: 007
Revises: 006
Create Date: 2025-01-06

Epic 5: LLM Processing & Decision Intelligence
Creates tables for Phase 2 category processing with LLM selection,
rule-based decisions, scoring matrices, and audit trails.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create Phase 2 Decision Intelligence tables.
    """

    # LLM Configurations table - Story 5.1
    op.create_table(
        'llm_configurations',
        sa.Column('id', sa.String(50), primary_key=True, comment='Unique LLM configuration identifier'),
        sa.Column('provider', sa.String(50), nullable=False, index=True, comment='LLM provider (openai, anthropic, gemini, etc.)'),
        sa.Column('model_name', sa.String(100), nullable=False, index=True, comment='Model name (gpt-4, claude-3, etc.)'),
        sa.Column('configuration', JSONB(), nullable=False, server_default='{}', comment='Model configuration (temperature, max_tokens, etc.)'),
        sa.Column('performance_metrics', JSONB(), nullable=False, server_default='{}', comment='Performance metrics (avg_response_time, accuracy_score, cost_per_token)'),
        sa.Column('categories_supported', ARRAY(sa.String), nullable=False, server_default='{}', comment='List of categories this LLM supports'),
        sa.Column('active', sa.Boolean(), nullable=False, default=True, comment='Whether this LLM configuration is active'),
        sa.Column('priority', sa.Integer(), nullable=False, default=0, comment='Selection priority (higher = preferred)'),
        sa.Column('is_fallback', sa.Boolean(), nullable=False, default=False, comment='Whether this is a fallback LLM'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='Configuration creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), comment='Last update timestamp'),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True, comment='Last time this LLM was used'),
        sa.Column('metadata', JSONB(), nullable=True, comment='Additional metadata'),
        sa.UniqueConstraint('provider', 'model_name', name='uq_llm_config_provider_model'),
        sa.CheckConstraint("provider IN ('openai', 'anthropic', 'gemini', 'grok', 'perplexity', 'tavily')", name='ck_llm_config_provider_valid'),
        comment='LLM provider configurations for Phase 2 processing'
    )

    # LLM Selection Rules table - Story 5.1
    op.create_table(
        'llm_selection_rules',
        sa.Column('id', sa.String(50), primary_key=True, comment='Unique rule identifier'),
        sa.Column('category', sa.String(100), nullable=False, index=True, comment='Category this rule applies to'),
        sa.Column('llm_provider', sa.String(50), nullable=False, comment='LLM provider to select'),
        sa.Column('llm_model', sa.String(100), nullable=False, comment='LLM model to select'),
        sa.Column('priority', sa.Integer(), nullable=False, default=0, comment='Rule priority (higher = evaluated first)'),
        sa.Column('conditions', JSONB(), nullable=False, server_default='{}', comment='Conditions for this rule (complexity, data_sensitivity, etc.)'),
        sa.Column('active', sa.Boolean(), nullable=False, default=True, comment='Whether this rule is active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='Rule creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), comment='Last update timestamp'),
        sa.Column('metadata', JSONB(), nullable=True, comment='Additional rule metadata'),
        sa.ForeignKeyConstraint(['llm_provider', 'llm_model'], ['llm_configurations.provider', 'llm_configurations.model_name'], name='fk_llm_selection_rules_config'),
        sa.Index('ix_llm_selection_rules_category_priority', 'category', 'priority'),
        comment='Rules for selecting optimal LLM per category'
    )

    # LLM Scoring Weights table - Story 5.3, 5.4
    op.create_table(
        'llm_scoring_weights',
        sa.Column('id', sa.String(50), primary_key=True, comment='Unique weight configuration identifier'),
        sa.Column('category', sa.String(100), nullable=False, unique=True, index=True, comment='Category these weights apply to'),
        sa.Column('accuracy_weight', sa.Float(), nullable=False, default=0.5, comment='Weight for accuracy in LLM selection'),
        sa.Column('speed_weight', sa.Float(), nullable=False, default=0.3, comment='Weight for speed in LLM selection'),
        sa.Column('cost_weight', sa.Float(), nullable=False, default=0.2, comment='Weight for cost in LLM selection'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='Weight creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), comment='Last update timestamp'),
        sa.Column('metadata', JSONB(), nullable=True, comment='Additional weight metadata'),
        sa.CheckConstraint('accuracy_weight >= 0 AND accuracy_weight <= 1', name='ck_llm_scoring_accuracy_valid'),
        sa.CheckConstraint('speed_weight >= 0 AND speed_weight <= 1', name='ck_llm_scoring_speed_valid'),
        sa.CheckConstraint('cost_weight >= 0 AND cost_weight <= 1', name='ck_llm_scoring_cost_valid'),
        comment='Scoring weights for LLM selection per category'
    )

    # LLM Processing Results table - Story 5.1
    op.create_table(
        'llm_processing_results',
        sa.Column('id', sa.String(50), primary_key=True, comment='Unique result identifier'),
        sa.Column('request_id', sa.String(50), nullable=False, index=True, comment='Analysis request ID'),
        sa.Column('category', sa.String(100), nullable=False, index=True, comment='Phase 2 category processed'),
        sa.Column('llm_provider', sa.String(50), nullable=False, comment='LLM provider used'),
        sa.Column('llm_model', sa.String(100), nullable=False, comment='LLM model used'),
        sa.Column('processing_time', sa.Float(), nullable=False, comment='Processing time in seconds'),
        sa.Column('confidence_score', sa.Float(), nullable=False, default=0.0, comment='Confidence score (0-1)'),
        sa.Column('data', JSONB(), nullable=False, server_default='{}', comment='Processed result data'),
        sa.Column('sources', JSONB(), nullable=False, server_default='[]', comment='Source references extracted from LLM response'),
        sa.Column('is_fallback', sa.Boolean(), nullable=False, default=False, comment='Whether fallback LLM was used'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='Result creation timestamp'),
        sa.Column('metadata', JSONB(), nullable=True, comment='Additional result metadata'),
        sa.Index('ix_llm_processing_results_request_category', 'request_id', 'category'),
        sa.CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='ck_llm_processing_confidence_valid'),
        comment='Phase 2 LLM processing results with audit trail'
    )

    # LLM Selection Log table - Story 5.1 Audit Trail
    op.create_table(
        'llm_selection_log',
        sa.Column('id', sa.String(50), primary_key=True, comment='Unique log entry identifier'),
        sa.Column('category', sa.String(100), nullable=False, index=True, comment='Category being processed'),
        sa.Column('criteria', JSONB(), nullable=False, server_default='{}', comment='Selection criteria used'),
        sa.Column('selected_provider', sa.String(50), nullable=False, comment='Selected LLM provider'),
        sa.Column('selected_model', sa.String(100), nullable=False, comment='Selected LLM model'),
        sa.Column('selection_score', sa.Float(), nullable=True, comment='Selection score calculated'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True, comment='Selection timestamp'),
        sa.Column('metadata', JSONB(), nullable=True, comment='Additional selection metadata'),
        sa.Index('ix_llm_selection_log_timestamp', 'timestamp'),
        comment='Audit log of LLM selection decisions'
    )

    # Scoring Parameters table - Story 5.3
    op.create_table(
        'scoring_parameters',
        sa.Column('id', sa.String(50), primary_key=True, comment='Unique parameter identifier'),
        sa.Column('category', sa.String(100), nullable=False, index=True, comment='Category this parameter belongs to'),
        sa.Column('name', sa.String(100), nullable=False, comment='Parameter name (dose, molecular_weight, etc.)'),
        sa.Column('type', sa.String(50), nullable=False, comment='Parameter type (numeric, categorical, boolean)'),
        sa.Column('weight', sa.Float(), nullable=False, default=1.0, comment='Parameter weight in scoring'),
        sa.Column('min_value', sa.Float(), nullable=True, comment='Minimum value for numeric parameters'),
        sa.Column('max_value', sa.Float(), nullable=True, comment='Maximum value for numeric parameters'),
        sa.Column('scoring_method', sa.String(50), nullable=False, default='linear', comment='Scoring method (linear, logarithmic, threshold)'),
        sa.Column('is_critical', sa.Boolean(), nullable=False, default=False, comment='Whether this is a critical exclusion parameter'),
        sa.Column('active', sa.Boolean(), nullable=False, default=True, comment='Whether this parameter is active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='Parameter creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), comment='Last update timestamp'),
        sa.Column('metadata', JSONB(), nullable=True, comment='Additional parameter metadata'),
        sa.UniqueConstraint('category', 'name', name='uq_scoring_parameters_category_name'),
        sa.CheckConstraint("type IN ('numeric', 'categorical', 'boolean')", name='ck_scoring_parameters_type_valid'),
        sa.CheckConstraint("scoring_method IN ('linear', 'logarithmic', 'threshold', 'step')", name='ck_scoring_parameters_method_valid'),
        comment='Scoring parameters for Phase 2 parameter-based scoring'
    )

    # Score Ranges table - Story 5.3
    op.create_table(
        'score_ranges',
        sa.Column('id', sa.String(50), primary_key=True, comment='Unique score range identifier'),
        sa.Column('parameter_id', sa.String(50), nullable=False, comment='Parameter this range belongs to'),
        sa.Column('min_value', sa.Float(), nullable=False, comment='Minimum value for this range'),
        sa.Column('max_value', sa.Float(), nullable=False, comment='Maximum value for this range'),
        sa.Column('score', sa.Integer(), nullable=False, comment='Score assigned to this range (0-5)'),
        sa.Column('label', sa.String(50), nullable=False, comment='Label for this range (Excellent, Good, Fair, Poor, Exclusion)'),
        sa.Column('color', sa.String(20), nullable=False, default='gray', comment='Color code for UI display'),
        sa.Column('is_exclusion', sa.Boolean(), nullable=False, default=False, comment='Whether this range causes automatic exclusion'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='Range creation timestamp'),
        sa.Column('metadata', JSONB(), nullable=True, comment='Additional range metadata'),
        sa.ForeignKeyConstraint(['parameter_id'], ['scoring_parameters.id'], name='fk_score_ranges_parameter', ondelete='CASCADE'),
        sa.CheckConstraint('score >= 0 AND score <= 5', name='ck_score_ranges_score_valid'),
        sa.CheckConstraint('min_value <= max_value', name='ck_score_ranges_values_valid'),
        comment='Score ranges for parameter-based scoring'
    )

    # Decision Rules table - Story 5.2
    op.create_table(
        'decision_rules',
        sa.Column('id', sa.String(50), primary_key=True, comment='Unique rule identifier'),
        sa.Column('category', sa.String(100), nullable=False, index=True, comment='Category this rule applies to'),
        sa.Column('name', sa.String(200), nullable=False, comment='Rule name'),
        sa.Column('field', sa.String(100), nullable=False, comment='Field to evaluate'),
        sa.Column('operator', sa.String(50), nullable=False, comment='Operator (equals, less_than, greater_than, between, in)'),
        sa.Column('value', sa.String(500), nullable=False, comment='Value to compare against'),
        sa.Column('action', sa.String(100), nullable=False, comment='Action to take if rule passes (approve, reject, flag)'),
        sa.Column('priority', sa.Integer(), nullable=False, default=0, comment='Rule priority (lower = higher priority)'),
        sa.Column('active', sa.Boolean(), nullable=False, default=True, comment='Whether this rule is active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='Rule creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), comment='Last update timestamp'),
        sa.Column('metadata', JSONB(), nullable=True, comment='Additional rule metadata'),
        sa.Index('ix_decision_rules_category_priority', 'category', 'priority'),
        sa.CheckConstraint("operator IN ('equals', 'not_equals', 'less_than', 'less_than_or_equal', 'greater_than', 'greater_than_or_equal', 'between', 'in', 'not_in', 'contains')", name='ck_decision_rules_operator_valid'),
        comment='Rule-based decision logic for Phase 2'
    )

    # Assessment Criteria table - Story 5.4
    op.create_table(
        'assessment_criteria',
        sa.Column('id', sa.String(50), primary_key=True, comment='Unique criteria identifier'),
        sa.Column('name', sa.String(100), nullable=False, comment='Criteria name'),
        sa.Column('assessment_type', sa.String(50), nullable=False, index=True, comment='Assessment type (technology, clinical, safety, commercial)'),
        sa.Column('weight', sa.Float(), nullable=False, default=1.0, comment='Criteria weight in assessment'),
        sa.Column('threshold_pass', sa.Float(), nullable=False, default=60.0, comment='Minimum score to pass'),
        sa.Column('threshold_excellent', sa.Float(), nullable=False, default=85.0, comment='Score for excellent rating'),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, default=False, comment='Whether this criteria is mandatory'),
        sa.Column('active', sa.Boolean(), nullable=False, default=True, comment='Whether this criteria is active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='Criteria creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), comment='Last update timestamp'),
        sa.Column('metadata', JSONB(), nullable=True, comment='Additional criteria metadata'),
        sa.UniqueConstraint('name', 'assessment_type', name='uq_assessment_criteria_name_type'),
        sa.CheckConstraint("assessment_type IN ('technology', 'clinical', 'safety', 'commercial', 'regulatory')", name='ck_assessment_criteria_type_valid'),
        comment='Assessment criteria for weighted multi-criteria assessment'
    )

    # Verdicts table - Story 5.5
    op.create_table(
        'verdicts',
        sa.Column('id', sa.String(50), primary_key=True, comment='Unique verdict identifier'),
        sa.Column('request_id', sa.String(50), nullable=False, index=True, comment='Analysis request ID'),
        sa.Column('category', sa.String(100), nullable=False, comment='Category this verdict applies to'),
        sa.Column('verdict_type', sa.String(50), nullable=False, comment='Verdict type (GO, NO_GO, CONDITIONAL, REQUIRES_REVIEW)'),
        sa.Column('confidence_level', sa.String(50), nullable=False, comment='Confidence level (VERY_HIGH, HIGH, MEDIUM, LOW)'),
        sa.Column('confidence_score', sa.Float(), nullable=False, comment='Confidence score (0-100)'),
        sa.Column('primary_rationale', sa.Text(), nullable=False, comment='Primary rationale for verdict'),
        sa.Column('supporting_factors', JSONB(), nullable=False, server_default='[]', comment='List of supporting factors'),
        sa.Column('risk_factors', JSONB(), nullable=False, server_default='[]', comment='List of risk factors'),
        sa.Column('opposing_factors', JSONB(), nullable=False, server_default='[]', comment='List of opposing factors'),
        sa.Column('conditions', JSONB(), nullable=False, server_default='[]', comment='Conditions for conditional verdicts'),
        sa.Column('recommendations', JSONB(), nullable=False, server_default='[]', comment='Recommendations'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='Verdict creation timestamp'),
        sa.Column('metadata', JSONB(), nullable=True, comment='Additional verdict metadata'),
        sa.Index('ix_verdicts_request_category', 'request_id', 'category'),
        sa.CheckConstraint("verdict_type IN ('GO', 'NO_GO', 'CONDITIONAL', 'REQUIRES_REVIEW')", name='ck_verdicts_type_valid'),
        sa.CheckConstraint("confidence_level IN ('VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW', 'VERY_LOW')", name='ck_verdicts_confidence_valid'),
        sa.CheckConstraint('confidence_score >= 0 AND confidence_score <= 100', name='ck_verdicts_score_valid'),
        comment='Go/No-Go verdicts for Phase 2 decision intelligence'
    )

    # Executive Summaries table - Story 5.6
    op.create_table(
        'executive_summaries',
        sa.Column('id', sa.String(50), primary_key=True, comment='Unique summary identifier'),
        sa.Column('request_id', sa.String(50), nullable=False, unique=True, index=True, comment='Analysis request ID'),
        sa.Column('style', sa.String(50), nullable=False, comment='Summary style (EXECUTIVE, TECHNICAL, COMPREHENSIVE)'),
        sa.Column('length', sa.String(50), nullable=False, comment='Summary length (BRIEF, STANDARD, COMPREHENSIVE)'),
        sa.Column('headline', sa.String(500), nullable=False, comment='Executive headline'),
        sa.Column('executive_brief', sa.Text(), nullable=False, comment='Executive brief paragraph'),
        sa.Column('key_findings', JSONB(), nullable=False, server_default='[]', comment='Key findings list'),
        sa.Column('sections', JSONB(), nullable=False, server_default='[]', comment='Summary sections'),
        sa.Column('appendices', JSONB(), nullable=False, server_default='{}', comment='Appendices data'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment='Summary creation timestamp'),
        sa.Column('metadata', JSONB(), nullable=True, comment='Additional summary metadata'),
        sa.CheckConstraint("style IN ('EXECUTIVE', 'TECHNICAL', 'COMPREHENSIVE')", name='ck_executive_summaries_style_valid'),
        sa.CheckConstraint("length IN ('BRIEF', 'STANDARD', 'COMPREHENSIVE')", name='ck_executive_summaries_length_valid'),
        comment='Executive summaries for Phase 2 results'
    )


def downgrade() -> None:
    """
    Drop Phase 2 Decision Intelligence tables.
    """
    op.drop_table('executive_summaries')
    op.drop_table('verdicts')
    op.drop_table('assessment_criteria')
    op.drop_table('decision_rules')
    op.drop_table('score_ranges')
    op.drop_table('scoring_parameters')
    op.drop_table('llm_selection_log')
    op.drop_table('llm_processing_results')
    op.drop_table('llm_scoring_weights')
    op.drop_table('llm_selection_rules')
    op.drop_table('llm_configurations')
