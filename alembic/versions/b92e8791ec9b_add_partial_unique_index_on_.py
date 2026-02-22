# alembic/script.py.mako
"""Add partial unique index on subscriptions user_id + status

Revision ID: b92e8791ec9b
Revises: 05e5f3a5b876
Create Date: 2026-02-22 04:04:03.053953

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b92e8791ec9b'
down_revision = '05e5f3a5b876'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ix_subscriptions_user_status", table_name="subscriptions")
    op.create_index(
        "ix_subscriptions_user_status_unique",
        "subscriptions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('active','pending')")
    )

def downgrade():
    op.drop_index("ix_subscriptions_user_status_unique", table_name="subscriptions")
    op.create_index(
        "ix_subscriptions_user_status",
        "subscriptions",
        ["user_id", "status"]
    )