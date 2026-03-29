# alembic/script.py.mako
"""add_image_url_to_notifications

Revision ID: 7ba1dc065c0b
Revises: 82e17f05f005
Create Date: 2026-03-29 04:30:43.774758

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7ba1dc065c0b'
down_revision = '82e17f05f005'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('notifications', sa.Column('image_url', sa.String(), nullable=True))

def downgrade():
    op.drop_column('notifications', 'image_url')