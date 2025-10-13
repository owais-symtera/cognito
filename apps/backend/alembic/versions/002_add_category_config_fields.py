"""Add phase and updated_by to categories, add dependencies table

Revision ID: 002
Revises: 001
Create Date: 2024-01-26 16:25:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add category configuration fields and dependencies table."""

    # Add phase column to pharmaceutical_categories
    op.add_column('pharmaceutical_categories', sa.Column('phase', sa.Integer(), nullable=False, server_default='1'))

    # Add updated_by column to pharmaceutical_categories
    op.add_column('pharmaceutical_categories', sa.Column('updated_by', sa.String(255), nullable=True))

    # Create category_dependencies table
    op.create_table('category_dependencies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('dependent_category_id', sa.Integer(), nullable=False),
        sa.Column('required_category_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['dependent_category_id'], ['pharmaceutical_categories.id'], ),
        sa.ForeignKeyConstraint(['required_category_id'], ['pharmaceutical_categories.id'], )
    )
    op.create_index('ix_category_dependencies_dependent_category_id', 'category_dependencies', ['dependent_category_id'])
    op.create_index('ix_category_dependencies_required_category_id', 'category_dependencies', ['required_category_id'])

    # Add unique constraint to prevent duplicate dependencies
    op.create_unique_constraint('uq_category_dependencies_pair', 'category_dependencies', ['dependent_category_id', 'required_category_id'])

    # Add check constraint for phase
    op.create_check_constraint('ck_pharmaceutical_categories_phase', 'pharmaceutical_categories', 'phase IN (1, 2)')


def downgrade() -> None:
    """Remove category configuration fields and dependencies table."""

    # Drop check constraint
    op.drop_constraint('ck_pharmaceutical_categories_phase', 'pharmaceutical_categories')

    # Drop unique constraint
    op.drop_constraint('uq_category_dependencies_pair', 'category_dependencies')

    # Drop indexes and table
    op.drop_index('ix_category_dependencies_required_category_id', 'category_dependencies')
    op.drop_index('ix_category_dependencies_dependent_category_id', 'category_dependencies')
    op.drop_table('category_dependencies')

    # Remove columns from pharmaceutical_categories
    op.drop_column('pharmaceutical_categories', 'updated_by')
    op.drop_column('pharmaceutical_categories', 'phase')