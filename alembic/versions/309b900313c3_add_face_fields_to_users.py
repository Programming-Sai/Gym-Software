# alembic/script.py.mako
"""add face fields to users

Revision ID: 309b900313c3
Revises: a27255485bc3
Create Date: 2026-01-24 19:19:00.529901

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '309b900313c3'
down_revision = 'a27255485bc3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("face_file_id", sa.String(), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("face_registered_at", sa.TIMESTAMP(), nullable=True)
    )

    op.create_foreign_key(
        "fk_users_face_file",
        "users",
        "files",
        ["face_file_id"],
        ["file_id"],
        ondelete="SET NULL"
    )


def downgrade():
    op.drop_constraint("fk_users_face_file", "users", type_="foreignkey")
    op.drop_column("users", "face_registered_at")
    op.drop_column("users", "face_file_id")
