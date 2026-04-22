# alembic/script.py.mako
"""update payouts table for new payout model

Revision ID: c80f294accc7
Revises: 2b160ffbbb69
Create Date: 2026-04-22 15:24:57.892684

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import expression


# revision identifiers, used by Alembic.
revision = 'c80f294accc7'
down_revision = '2b160ffbbb69'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Add new columns ---
    op.add_column("payouts", sa.Column("fee", sa.DECIMAL(12, 2), nullable=False, server_default="0"))
    op.add_column("payouts", sa.Column("net_amount", sa.DECIMAL(12, 2), nullable=False, server_default="0"))

    # NOTE: initiated_by is required by your model; safest backfill is gym.owner_id for existing rows
    op.add_column("payouts", sa.Column("initiated_by", sa.String(), nullable=True))
    op.add_column("payouts", sa.Column("approved_by", sa.String(), nullable=True))
    op.add_column("payouts", sa.Column("approved_at", sa.TIMESTAMP(), nullable=True))

    op.add_column("payouts", sa.Column("recipient_code", sa.String(length=128), nullable=True))
    op.add_column("payouts", sa.Column("transfer_reference", sa.String(length=128), nullable=True))
    op.add_column("payouts", sa.Column("provider_transfer_id", sa.String(length=128), nullable=True))

    op.add_column("payouts", sa.Column("completed_date", sa.TIMESTAMP(), nullable=True))

    op.add_column(
        "payouts",
        sa.Column(
            "payout_metadata",
            sa.JSON(),
            nullable=False,
            server_default=expression.text("'{}'::jsonb"),
        ),
    )

    # --- Backfills for existing rows (safe even if table is empty) ---
    # net_amount defaults to amount initially (fee defaults to 0)
    op.execute("UPDATE payouts SET net_amount = amount WHERE net_amount = 0 OR net_amount IS NULL")

    # initiated_by: backfill to gym owner when possible
    op.execute(
        """
        UPDATE payouts p
        SET initiated_by = g.owner_id
        FROM gyms g
        WHERE p.gym_id = g.gym_id AND p.initiated_by IS NULL
        """
    )

    # recipient_code: backfill from gyms.paystack_recipient_code when possible
    op.execute(
        """
        UPDATE payouts p
        SET recipient_code = g.paystack_recipient_code
        FROM gyms g
        WHERE p.gym_id = g.gym_id
          AND p.recipient_code IS NULL
          AND g.paystack_recipient_code IS NOT NULL
        """
    )

    # --- Make initiated_by NOT NULL if possible ---
    # If you have legacy payouts where gyms.owner_id is NULL, this will fail.
    # If you want strict alignment with the model, keep this ON.
    op.alter_column("payouts", "initiated_by", existing_type=sa.String(), nullable=False)

    # recipient_code is non-nullable in your model; enforcing DB-level NOT NULL will fail unless all rows have it.
    # If you want strict alignment, uncomment the next line after ensuring all rows have recipient_code:
    # op.alter_column("payouts", "recipient_code", existing_type=sa.String(length=128), nullable=False)

    # --- Drop old columns removed from the new model ---
    # old model had scheduled_date and provider_payout_id
    with op.batch_alter_table("payouts") as batch:
        batch.drop_column("scheduled_date")
        batch.drop_column("provider_payout_id")

    # --- Clean up server defaults we only used for backfill ---
    op.alter_column("payouts", "fee", server_default=None)
    op.alter_column("payouts", "net_amount", server_default=None)


def downgrade() -> None:
    # restore old columns
    op.add_column("payouts", sa.Column("provider_payout_id", sa.String(), nullable=True))
    op.add_column("payouts", sa.Column("scheduled_date", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")))

    # drop new columns
    op.drop_column("payouts", "payout_metadata")
    op.drop_column("payouts", "completed_date")
    op.drop_column("payouts", "provider_transfer_id")
    op.drop_column("payouts", "transfer_reference")
    op.drop_column("payouts", "recipient_code")
    op.drop_column("payouts", "approved_at")
    op.drop_column("payouts", "approved_by")
    op.drop_column("payouts", "initiated_by")
    op.drop_column("payouts", "net_amount")
    op.drop_column("payouts", "fee")
