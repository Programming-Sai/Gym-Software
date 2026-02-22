# alembic/script.py.mako
"""add payment reconciliation events

Revision ID: d1c4c4f7b9aa
Revises: 089dcbe0dbb8
Create Date: 2026-02-22 15:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d1c4c4f7b9aa"
down_revision = "089dcbe0dbb8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_reconciliation_events",
        sa.Column("reconciliation_event_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False, server_default="paystack"),
        sa.Column("provider_event", sa.String(), nullable=False),
        sa.Column("provider_event_id", sa.String(), nullable=True),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("open", "resolved", "ignored", name="reconciliation_event_statuses"),
            nullable=False,
            server_default="open",
        ),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("reconciliation_event_id"),
        sa.UniqueConstraint(
            "provider",
            "provider_event",
            "reference",
            name="uq_reconciliation_provider_event_reference",
        ),
    )
    op.create_index(
        "ix_reconciliation_reference_status",
        "payment_reconciliation_events",
        ["reference", "status"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_reconciliation_reference_status", table_name="payment_reconciliation_events")
    op.drop_table("payment_reconciliation_events")
    op.execute("DROP TYPE IF EXISTS reconciliation_event_statuses;")
