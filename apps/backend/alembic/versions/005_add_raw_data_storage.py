"""Add raw data storage tables

Revision ID: 005
Revises: 004_add_api_provider_tables
Create Date: 2024-01-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004_add_api_provider_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create raw data storage tables for API response persistence.
    """

    # Create api_responses table
    op.create_table(
        'api_responses',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('process_id', sa.String(36), nullable=False),
        sa.Column('request_id', sa.String(36), nullable=False),
        sa.Column('correlation_id', sa.String(36), nullable=False),

        # API details
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=False),
        sa.Column('query_parameters', JSONB(), nullable=False, server_default='{}'),

        # Response data
        sa.Column('raw_response', JSONB(), nullable=False),
        sa.Column('standardized_response', JSONB(), nullable=False),

        # Metadata
        sa.Column('response_time_ms', sa.Integer(), nullable=False),
        sa.Column('cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('result_count', sa.Integer(), nullable=False, server_default='0'),

        # Pharmaceutical context
        sa.Column('pharmaceutical_compound', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),

        # Quality metrics
        sa.Column('relevance_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('quality_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.0'),

        # Data integrity
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('is_valid', sa.Boolean(), nullable=False, server_default='true'),

        # Audit trail
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retention_expires_at', sa.DateTime(timezone=True), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['process_id'], ['process_tracking.id']),
        sa.ForeignKeyConstraint(['request_id'], ['drug_requests.id']),
        sa.CheckConstraint('relevance_score >= 0 AND relevance_score <= 1', name='check_relevance_range'),
        sa.CheckConstraint('quality_score >= 0 AND quality_score <= 1', name='check_quality_range'),
        sa.CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='check_confidence_range'),
    )

    # Create indices
    op.create_index('ix_api_responses_process_id', 'api_responses', ['process_id'])
    op.create_index('ix_api_responses_request_id', 'api_responses', ['request_id'])
    op.create_index('ix_api_responses_correlation_id', 'api_responses', ['correlation_id'])
    op.create_index('ix_api_responses_provider', 'api_responses', ['provider'])
    op.create_index('ix_api_responses_pharmaceutical_compound', 'api_responses', ['pharmaceutical_compound'])
    op.create_index('ix_api_responses_category', 'api_responses', ['category'])
    op.create_index('ix_api_responses_compound_category', 'api_responses', ['pharmaceutical_compound', 'category'])
    op.create_index('ix_api_responses_created_at', 'api_responses', ['created_at'])
    op.create_index('ix_api_responses_provider_created', 'api_responses', ['provider', 'created_at'])

    # Create api_response_metadata table
    op.create_table(
        'api_response_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('api_response_id', sa.String(36), nullable=False),

        # Source tracking
        sa.Column('source_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unique_domains', ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('source_types', JSONB(), nullable=False, server_default='{}'),

        # Content analysis
        sa.Column('key_findings', ARRAY(sa.Text()), nullable=True),
        sa.Column('entity_mentions', JSONB(), nullable=True),
        sa.Column('confidence_factors', JSONB(), nullable=True),

        # Performance metrics
        sa.Column('parse_time_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('storage_size_bytes', sa.Integer(), nullable=False, server_default='0'),

        # Compliance tracking
        sa.Column('contains_pii', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('contains_proprietary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('regulatory_flags', ARRAY(sa.String()), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['api_response_id'], ['api_responses.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('api_response_id'),
    )


def downgrade() -> None:
    """
    Drop raw data storage tables.
    """
    op.drop_table('api_response_metadata')
    op.drop_table('api_responses')