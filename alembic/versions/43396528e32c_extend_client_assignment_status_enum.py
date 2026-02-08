# alembic/script.py.mako
"""extend client_assignment status enum

Revision ID: 43396528e32c
Revises: 39b25ec7180c
Create Date: 2026-02-06 11:04:16.098229

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '43396528e32c'
down_revision = '39b25ec7180c'
branch_labels = None
depends_on = None



def upgrade():
    op.execute(
        "ALTER TYPE client_assignment_statuses ADD VALUE IF NOT EXISTS 'pending'"
    )
    op.execute(
        "ALTER TYPE client_assignment_statuses ADD VALUE IF NOT EXISTS 'rejected'"
    )



def downgrade():
    pass