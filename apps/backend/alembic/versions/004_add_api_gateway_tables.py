"""Add API gateway tables for Story 1.4

Revision ID: 004
Revises: 003
Create Date: 2025-01-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create API key and analysis request tables."""
    
    # Add new columns to users table
    op.add_column('users', sa.Column('roles', sa.ARRAY(sa.String()), nullable=True))
    op.add_column('users', sa.Column('permissions', sa.ARRAY(sa.String()), nullable=True))
    
    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('permissions', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('rate_limit', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('request_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    
    # Create indexes for api_keys
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'])
    op.create_index('ix_api_keys_user_active', 'api_keys', ['user_id', 'is_active'])
    op.create_index('ix_api_keys_expires', 'api_keys', ['expires_at'])
    
    # Create analysis_requests table
    op.create_table(
        'analysis_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.String(length=50), nullable=False),
        sa.Column('correlation_id', sa.String(length=100), nullable=False),
        sa.Column('drug_names', sa.ARRAY(sa.String()), nullable=False),
        sa.Column('categories', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='normal'),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('api_key_hash', sa.String(length=64), nullable=False),
        sa.Column('callback_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_completion_time_ms', sa.Integer(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('progress_percentage', sa.Integer(), nullable=True),
        sa.Column('results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('errors', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('request_id')
    )
    
    # Create indexes for analysis_requests
    op.create_index('ix_analysis_requests_request_id', 'analysis_requests', ['request_id'])
    op.create_index('ix_analysis_requests_correlation_id', 'analysis_requests', ['correlation_id'])
    op.create_index('ix_analysis_requests_status', 'analysis_requests', ['status'])
    op.create_index('ix_analysis_requests_api_key_hash', 'analysis_requests', ['api_key_hash'])
    op.create_index('ix_analysis_requests_created_at', 'analysis_requests', ['created_at'])
    op.create_index('ix_analysis_requests_status_created', 'analysis_requests', ['status', 'created_at'])
    op.create_index('ix_analysis_requests_api_key_created', 'analysis_requests', ['api_key_hash', 'created_at'])
    op.create_index('ix_analysis_requests_priority_status', 'analysis_requests', ['priority', 'status'])


def downgrade() -> None:
    """Drop API gateway tables."""
    
    # Drop analysis_requests table and indexes
    op.drop_index('ix_analysis_requests_priority_status', table_name='analysis_requests')
    op.drop_index('ix_analysis_requests_api_key_created', table_name='analysis_requests')
    op.drop_index('ix_analysis_requests_status_created', table_name='analysis_requests')
    op.drop_index('ix_analysis_requests_created_at', table_name='analysis_requests')
    op.drop_index('ix_analysis_requests_api_key_hash', table_name='analysis_requests')
    op.drop_index('ix_analysis_requests_status', table_name='analysis_requests')
    op.drop_index('ix_analysis_requests_correlation_id', table_name='analysis_requests')
    op.drop_index('ix_analysis_requests_request_id', table_name='analysis_requests')
    op.drop_table('analysis_requests')
    
    # Drop api_keys table and indexes
    op.drop_index('ix_api_keys_expires', table_name='api_keys')
    op.drop_index('ix_api_keys_user_active', table_name='api_keys')
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    op.drop_table('api_keys')
    
    # Drop columns from users table
    op.drop_column('users', 'permissions')
    op.drop_column('users', 'roles')