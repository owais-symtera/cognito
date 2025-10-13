"""Add temperature strategy to pharmaceutical categories

Revision ID: 006
Revises: 005
Create Date: 2024-01-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add temperature strategy configuration to pharmaceutical categories.
    """

    # Add temperature_strategy column to pharmaceutical_categories table
    op.add_column(
        'pharmaceutical_categories',
        sa.Column(
            'temperature_strategy',
            JSONB(),
            nullable=False,
            server_default='{}',
            comment='Temperature variation strategy for searches'
        )
    )

    # Add temperature metadata to api_responses for tracking
    op.add_column(
        'api_responses',
        sa.Column(
            'temperature_metadata',
            JSONB(),
            nullable=True,
            comment='Temperature strategy metadata'
        )
    )


def downgrade() -> None:
    """
    Remove temperature strategy fields.
    """
    op.drop_column('api_responses', 'temperature_metadata')
    op.drop_column('pharmaceutical_categories', 'temperature_strategy')