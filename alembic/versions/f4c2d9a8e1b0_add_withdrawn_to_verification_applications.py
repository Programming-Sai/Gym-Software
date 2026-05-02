"""add withdrawn status to verification applications

Revision ID: f4c2d9a8e1b0
Revises: e3a1c1f7a5b2
Create Date: 2026-04-26

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f4c2d9a8e1b0"
down_revision = "e3a1c1f7a5b2"
branch_labels = None
depends_on = None


def upgrade():
    # 1) Extend enum (Postgres enum alteration can require autocommit)
    with op.get_context().autocommit_block():
        op.execute(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = 'verification_statuses'
                  AND e.enumlabel = 'withdrawn'
              ) THEN
                ALTER TYPE verification_statuses ADD VALUE 'withdrawn';
              END IF;
            END$$;
            """
        )

    # 2) Add withdrawal fields
    op.add_column("verification_applications", sa.Column("withdrawn_at", sa.TIMESTAMP(), nullable=True))
    op.add_column("verification_applications", sa.Column("withdrawn_reason", sa.Text(), nullable=True))
    op.add_column(
        "verification_applications",
        sa.Column(
            "withdrawn_by",
            sa.String(),
            sa.ForeignKey("users.user_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("verification_applications", "withdrawn_by")
    op.drop_column("verification_applications", "withdrawn_reason")
    op.drop_column("verification_applications", "withdrawn_at")

