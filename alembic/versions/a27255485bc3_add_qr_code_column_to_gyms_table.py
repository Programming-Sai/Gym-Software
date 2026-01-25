# alembic/script.py.mako
"""Add qr_code column to gyms table

Revision ID: a27255485bc3
Revises: 20c47329156a
Create Date: 2026-01-23 17:10:38.323670

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a27255485bc3'
down_revision = '20c47329156a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("gyms", sa.Column("qr_code", sa.String(), nullable=True, unique=True))



def downgrade():
    op.drop_column("gyms", "qr_code")
