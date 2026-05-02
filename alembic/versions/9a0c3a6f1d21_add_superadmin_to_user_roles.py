"""add superadmin to user_roles enum

Revision ID: 9a0c3a6f1d21
Revises: f4c2d9a8e1b0
Create Date: 2026-04-26

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "9a0c3a6f1d21"
down_revision = "f4c2d9a8e1b0"
branch_labels = None
depends_on = None


def upgrade():
    # Extend Postgres enum
    with op.get_context().autocommit_block():
        op.execute(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typname = 'user_roles'
                  AND e.enumlabel = 'superadmin'
              ) THEN
                ALTER TYPE user_roles ADD VALUE 'superadmin';
              END IF;
            END$$;
            """
        )


def downgrade():
    # Postgres enums cannot easily remove a value without type recreation.
    pass

