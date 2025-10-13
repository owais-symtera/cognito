"""Add API provider configuration tables

Revision ID: 004
Revises: 003_populate_default_categories
Create Date: 2024-01-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003_populate_default_categories'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create API provider configuration tables for multi-API integration.
    """

    # Create api_provider_configs table
    op.create_table(
        'api_provider_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider_name', sa.String(length=50), nullable=False),
        sa.Column('enabled_globally', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('requests_per_minute', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('requests_per_hour', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('daily_quota', sa.Integer(), nullable=True),
        sa.Column('cost_per_request', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('cost_per_token', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('config_json', JSONB(), nullable=False, server_default='{}'),
        sa.Column('encrypted_api_key', sa.Text(), nullable=False, server_default=''),
        sa.Column('key_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_name'),
        sa.CheckConstraint('requests_per_minute > 0', name='check_rpm_positive'),
        sa.CheckConstraint('requests_per_hour > 0', name='check_rph_positive'),
        sa.CheckConstraint('cost_per_request >= 0', name='check_cost_non_negative'),
    )

    # Create indices
    op.create_index('ix_api_provider_configs_provider_name', 'api_provider_configs', ['provider_name'])

    # Create category_api_configs table
    op.create_table(
        'category_api_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_name', sa.String(length=100), nullable=False),
        sa.Column('provider_name', sa.String(length=50), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('custom_config', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category_name', 'provider_name', name='uq_category_provider'),
    )

    # Create indices
    op.create_index('ix_category_api_configs_category_name', 'category_api_configs', ['category_name'])
    op.create_index('ix_category_api_configs_provider_name', 'category_api_configs', ['provider_name'])
    op.create_index('ix_category_api_enabled', 'category_api_configs', ['category_name', 'enabled'])

    # Insert default provider configurations
    op.execute("""
        INSERT INTO api_provider_configs (
            provider_name, enabled_globally, requests_per_minute, requests_per_hour,
            daily_quota, cost_per_request, cost_per_token, config_json, encrypted_api_key
        ) VALUES
        ('chatgpt', true, 60, 1000, 10000, 0.0, 0.00003, '{"model": "gpt-4-turbo-preview"}', ''),
        ('perplexity', true, 50, 500, 5000, 0.005, 0.0, '{"model": "pplx-70b-online"}', ''),
        ('grok', false, 40, 400, 4000, 0.01, 0.0, '{}', ''),
        ('gemini', false, 60, 600, 6000, 0.0, 0.00002, '{"model": "gemini-pro"}', ''),
        ('tavily', false, 100, 1000, 10000, 0.003, 0.0, '{}', '')
    """)


def downgrade() -> None:
    """
    Drop API provider configuration tables.
    """
    op.drop_table('category_api_configs')
    op.drop_table('api_provider_configs')