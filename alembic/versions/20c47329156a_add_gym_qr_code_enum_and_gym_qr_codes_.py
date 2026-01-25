# alembic/script.py.mako
"""add gym_qr_code enum and gym_qr_codes table

Revision ID: 20c47329156a
Revises: 583a5fff36d9
Create Date: 2026-01-23 16:33:31.772309

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20c47329156a'
down_revision = '583a5fff36d9'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE file_purposes ADD VALUE 'gym_qr_code';")

    op.create_table(
        'gym_qr_codes',
        sa.Column('qr_id', sa.String(), primary_key=True),
        sa.Column('gym_id', sa.String(), sa.ForeignKey('gyms.gym_id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('qr_nonce', sa.String(), nullable=False, unique=True),
        sa.Column('file_id', sa.String(), sa.ForeignKey('files.file_id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column('rotated_at', sa.TIMESTAMP(), nullable=True),
    )
    op.create_index('idx_gym_qr_nonce', 'gym_qr_codes', ['qr_nonce'], unique=True)





def downgrade():
    op.drop_index('idx_gym_qr_nonce', table_name='gym_qr_codes')
    op.drop_table('gym_qr_codes')
    
    pass