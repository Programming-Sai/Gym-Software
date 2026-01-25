# alembic/script.py.mako
"""remove unique constraint from checkins.qr_nonce

Revision ID: b079f08eda57
Revises: 309b900313c3
Create Date: 2026-01-25 14:29:13.530258

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b079f08eda57'
down_revision = '309b900313c3'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "checkins_qr_nonce_key",
        "checkins",
        type_="unique",
    )



def downgrade():
    op.create_unique_constraint(
        "checkins_qr_nonce_key",
        "checkins",
        ["qr_nonce"],
    )
