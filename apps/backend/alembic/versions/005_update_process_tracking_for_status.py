"""Update process tracking for comprehensive status API

Revision ID: 005
Revises: 004
Create Date: 2025-01-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update process_tracking table for status API."""
    
    # Drop old indexes and constraints first
    op.drop_index('ix_process_tracking_request_type', table_name='process_tracking')
    op.drop_index('ix_process_tracking_status_started', table_name='process_tracking')
    op.drop_constraint('ck_process_tracking_completion_after_start', 'process_tracking', type_='check')
    
    # Drop old columns
    op.drop_column('process_tracking', 'process_type')
    op.drop_column('process_tracking', 'status')
    op.drop_column('process_tracking', 'started_at')
    op.drop_column('process_tracking', 'correlation_id')
    op.drop_column('process_tracking', 'parent_process_id')
    op.drop_column('process_tracking', 'error_message')
    
    # Modify existing columns
    op.alter_column('process_tracking', 'id',
                    existing_type=postgresql.UUID(),
                    type_=sa.String(length=50),
                    existing_nullable=False)
    
    op.alter_column('process_tracking', 'request_id',
                    existing_type=postgresql.UUID(),
                    type_=sa.String(length=50),
                    existing_nullable=False)
    
    # Add new columns
    op.add_column('process_tracking', sa.Column('current_status', sa.String(length=20), nullable=False, server_default='submitted'))
    op.add_column('process_tracking', sa.Column('progress_percentage', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('process_tracking', sa.Column('estimated_completion', sa.DateTime(timezone=True), nullable=True))
    op.add_column('process_tracking', sa.Column('current_stage_start', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column('process_tracking', sa.Column('error_details', sa.Text(), nullable=True))
    
    # Drug and category tracking
    op.add_column('process_tracking', sa.Column('drug_names', sa.ARRAY(sa.String()), nullable=True))
    op.add_column('process_tracking', sa.Column('categories_total', sa.Integer(), nullable=False, server_default='17'))
    op.add_column('process_tracking', sa.Column('categories_completed', sa.Integer(), nullable=False, server_default='0'))
    
    # Stage completion tracking
    op.add_column('process_tracking', sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column('process_tracking', sa.Column('collecting_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('process_tracking', sa.Column('collecting_completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('process_tracking', sa.Column('verifying_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('process_tracking', sa.Column('verifying_completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('process_tracking', sa.Column('merging_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('process_tracking', sa.Column('merging_completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('process_tracking', sa.Column('summarizing_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('process_tracking', sa.Column('summarizing_completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('process_tracking', sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('process_tracking', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    
    # Create new indexes
    op.create_index('ix_process_tracking_request', 'process_tracking', ['request_id'])
    op.create_index('ix_process_tracking_status', 'process_tracking', ['current_status'])
    op.create_index('ix_process_tracking_timestamps', 'process_tracking', ['submitted_at', 'completed_at'])
    op.create_index('ix_process_tracking_status_updated', 'process_tracking', ['current_status', 'updated_at'])
    
    # Add new constraints
    op.create_check_constraint(
        'ck_process_tracking_status_valid',
        'process_tracking',
        "current_status IN ('submitted', 'collecting', 'verifying', 'merging', 'summarizing', 'completed', 'failed', 'cancelled')"
    )
    
    op.create_check_constraint(
        'ck_process_tracking_progress_valid',
        'process_tracking',
        'progress_percentage >= 0 AND progress_percentage <= 100'
    )
    
    op.create_check_constraint(
        'ck_process_tracking_completion_after_start',
        'process_tracking',
        'completed_at IS NULL OR completed_at >= submitted_at'
    )


def downgrade() -> None:
    """Revert process_tracking table changes."""
    
    # Drop new constraints
    op.drop_constraint('ck_process_tracking_completion_after_start', 'process_tracking', type_='check')
    op.drop_constraint('ck_process_tracking_progress_valid', 'process_tracking', type_='check')
    op.drop_constraint('ck_process_tracking_status_valid', 'process_tracking', type_='check')
    
    # Drop new indexes
    op.drop_index('ix_process_tracking_status_updated', table_name='process_tracking')
    op.drop_index('ix_process_tracking_timestamps', table_name='process_tracking')
    op.drop_index('ix_process_tracking_status', table_name='process_tracking')
    op.drop_index('ix_process_tracking_request', table_name='process_tracking')
    
    # Drop new columns
    op.drop_column('process_tracking', 'updated_at')
    op.drop_column('process_tracking', 'failed_at')
    op.drop_column('process_tracking', 'summarizing_completed_at')
    op.drop_column('process_tracking', 'summarizing_started_at')
    op.drop_column('process_tracking', 'merging_completed_at')
    op.drop_column('process_tracking', 'merging_started_at')
    op.drop_column('process_tracking', 'verifying_completed_at')
    op.drop_column('process_tracking', 'verifying_started_at')
    op.drop_column('process_tracking', 'collecting_completed_at')
    op.drop_column('process_tracking', 'collecting_started_at')
    op.drop_column('process_tracking', 'submitted_at')
    op.drop_column('process_tracking', 'categories_completed')
    op.drop_column('process_tracking', 'categories_total')
    op.drop_column('process_tracking', 'drug_names')
    op.drop_column('process_tracking', 'error_details')
    op.drop_column('process_tracking', 'current_stage_start')
    op.drop_column('process_tracking', 'estimated_completion')
    op.drop_column('process_tracking', 'progress_percentage')
    op.drop_column('process_tracking', 'current_status')
    
    # Restore old columns
    op.add_column('process_tracking', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('process_tracking', sa.Column('parent_process_id', postgresql.UUID(), nullable=True))
    op.add_column('process_tracking', sa.Column('correlation_id', sa.String(length=255), nullable=True))
    op.add_column('process_tracking', sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column('process_tracking', sa.Column('status', sa.String(length=50), nullable=False))
    op.add_column('process_tracking', sa.Column('process_type', sa.String(length=100), nullable=False))
    
    # Restore column types
    op.alter_column('process_tracking', 'request_id',
                    existing_type=sa.String(length=50),
                    type_=postgresql.UUID(),
                    existing_nullable=False)
    
    op.alter_column('process_tracking', 'id',
                    existing_type=sa.String(length=50),
                    type_=postgresql.UUID(),
                    existing_nullable=False)
    
    # Restore old indexes and constraints
    op.create_check_constraint(
        'ck_process_tracking_completion_after_start',
        'process_tracking',
        'completed_at IS NULL OR completed_at >= started_at'
    )
    op.create_index('ix_process_tracking_status_started', 'process_tracking', ['status', 'started_at'])
    op.create_index('ix_process_tracking_request_type', 'process_tracking', ['request_id', 'process_type'])