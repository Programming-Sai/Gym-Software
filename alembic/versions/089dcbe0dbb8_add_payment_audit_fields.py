# alembic/script.py.mako
"""add payment audit fields

Revision ID: 089dcbe0dbb8
Revises: b92e8791ec9b
Create Date: 2026-02-22 12:37:55.304794

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import expression, table, column
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '089dcbe0dbb8'
down_revision = 'b92e8791ec9b'
branch_labels = None
depends_on = None


def upgrade():
    # -------------------------
    # Payment audit fields
    # -------------------------
    op.add_column(
        "payments",
        sa.Column("succeeded_at", sa.TIMESTAMP(), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("failed_at", sa.TIMESTAMP(), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("failure_code", sa.Text(), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("raw_provider_payload", sa.JSON(), nullable=True),
    )

    # -------------------------
    # Subscription tier updates
    # -------------------------
    op.add_column(
        "subscription_tiers",
        sa.Column("duration_days", sa.Integer(), nullable=False, server_default="30"),
    )
    
    # Ensure features is strictly a JSON array
    op.alter_column(
        "subscription_tiers",
        "features",
        type_=postgresql.JSONB(),
        server_default=expression.text("'[]'::jsonb"),
        existing_type=postgresql.JSONB(),
    )

    # Update existing rows with {} → []
    subscription_tiers = table(
        "subscription_tiers",
        column("tier_id", sa.String),
        column("features", postgresql.JSONB),
    )
    op.execute(
        subscription_tiers.update()
        .where(subscription_tiers.c.features == {})
        .values(features=[])
    )


def downgrade():
    # -------------------------
    # Payment audit fields
    # -------------------------
    op.drop_column("payments", "raw_provider_payload")
    op.drop_column("payments", "failure_code")
    op.drop_column("payments", "failed_at")
    op.drop_column("payments", "succeeded_at")

    # -------------------------
    # Subscription tier updates
    # -------------------------
    op.drop_column("subscription_tiers", "duration_days")
    op.alter_column(
        "subscription_tiers",
        "features",
        type_=postgresql.JSONB(),
        server_default=expression.text("'{}'::jsonb"),
        existing_type=postgresql.JSONB(),
    )