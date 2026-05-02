# alembic/script.py.mako
"""add flagged reconciliation status

Revision ID: 8e5ec459d1b5
Revises: 6d925a3852ae
Create Date: 2026-04-27 10:57:42.048754

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8e5ec459d1b5'
down_revision = '6d925a3852ae'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE reconciliation_event_statuses ADD VALUE IF NOT EXISTS 'flagged'")


def downgrade():
    # Postgres enums cannot safely remove values without recreating the type; leave as-is.
    pass
