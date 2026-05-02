# alembic/script.py.mako
"""add_cancelled_payout_and_notification_sender_fields

Revision ID: 6d925a3852ae
Revises: 6d9fb55e6e3b
Create Date: 2026-04-27 03:25:58.510395

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d925a3852ae'
down_revision = '6d9fb55e6e3b'
branch_labels = None
depends_on = None


def upgrade():
    # Add new payout status value.
    op.execute("ALTER TYPE payout_statuses ADD VALUE IF NOT EXISTS 'cancelled'")

    # Notification attribution fields.
    op.add_column("notifications", sa.Column("sent_by_user_id", sa.String(), nullable=True))
    op.add_column("notifications", sa.Column("sent_by_role", sa.String(length=32), nullable=True))
    op.create_foreign_key(
        "fk_notifications_sent_by_user_id_users",
        "notifications",
        "users",
        ["sent_by_user_id"],
        ["user_id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_notifications_sent_by_user_id_users", "notifications", type_="foreignkey")
    op.drop_column("notifications", "sent_by_role")
    op.drop_column("notifications", "sent_by_user_id")
    # NOTE: Postgres enums cannot safely remove values without recreating the type; leave as-is.
