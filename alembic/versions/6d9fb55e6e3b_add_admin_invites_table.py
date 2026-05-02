"""add admin invites table

Revision ID: 6d9fb55e6e3b
Revises: 9a0c3a6f1d21
Create Date: 2026-04-26

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6d9fb55e6e3b"
down_revision = "9a0c3a6f1d21"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_invites",
        sa.Column("invite_id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role_to_grant", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column("accepted_by", sa.String(), sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("accepted_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("revoked_by", sa.String(), sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("revoke_reason", sa.String(), nullable=True),
        sa.Column("send_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_sent_at", sa.TIMESTAMP(), nullable=True),
    )
    op.create_index("ix_admin_invites_email", "admin_invites", ["email"])
    op.create_index("ix_admin_invites_token_hash", "admin_invites", ["token_hash"], unique=True)


def downgrade():
    op.drop_index("ix_admin_invites_token_hash", table_name="admin_invites")
    op.drop_index("ix_admin_invites_email", table_name="admin_invites")
    op.drop_table("admin_invites")

