"""add payout recipient fields to gyms

Revision ID: 2b160ffbbb69
Revises: 7ba1dc065c0b
Create Date: 2026-04-22
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2b160ffbbb69"
down_revision = "7ba1dc065c0b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gyms", sa.Column("payout_method", sa.String(length=16), nullable=True))
    # payout_method intended values: "bank" | "momo"

    op.add_column("gyms", sa.Column("payout_currency", sa.String(length=8), nullable=False, server_default="GHS"))

    op.add_column("gyms", sa.Column("paystack_recipient_code", sa.String(length=128), nullable=True))

    op.add_column("gyms", sa.Column("payout_account_name", sa.String(length=128), nullable=True))
    op.add_column("gyms", sa.Column("payout_bank_code", sa.String(length=32), nullable=True))
    op.add_column("gyms", sa.Column("payout_account_number", sa.String(length=32), nullable=True))

    op.add_column("gyms", sa.Column("payout_momo_provider", sa.String(length=32), nullable=True))
    op.add_column("gyms", sa.Column("payout_momo_number", sa.String(length=32), nullable=True))

    op.add_column("gyms", sa.Column("payouts_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("gyms", sa.Column("payout_recipient_verified_at", sa.TIMESTAMP(), nullable=True))

    op.create_index("ix_gyms_paystack_recipient_code", "gyms", ["paystack_recipient_code"])


def downgrade() -> None:
    op.drop_index("ix_gyms_paystack_recipient_code", table_name="gyms")

    op.drop_column("gyms", "payout_recipient_verified_at")
    op.drop_column("gyms", "payouts_enabled")

    op.drop_column("gyms", "payout_momo_number")
    op.drop_column("gyms", "payout_momo_provider")

    op.drop_column("gyms", "payout_account_number")
    op.drop_column("gyms", "payout_bank_code")
    op.drop_column("gyms", "payout_account_name")

    op.drop_column("gyms", "paystack_recipient_code")
    op.drop_column("gyms", "payout_currency")
    op.drop_column("gyms", "payout_method")
