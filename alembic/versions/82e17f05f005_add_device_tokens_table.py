"""add_device_tokens_table

Revision ID: 82e17f05f005
Revises: 12d789cdc69a
Create Date: 2026-03-29 03:47:07.508866

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '82e17f05f005'
down_revision = '12d789cdc69a'
branch_labels = None
depends_on = None


def upgrade():
    # Create device_tokens table
    op.create_table('device_tokens',
        sa.Column('token_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('fcm_token', sa.String(), nullable=False),
        sa.Column('device_info', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.session_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('token_id'),
        sa.UniqueConstraint('fcm_token')
    )
    
    # Create indexes
    op.create_index('ix_device_tokens_user_id', 'device_tokens', ['user_id'])
    op.create_index('ix_device_tokens_fcm_token', 'device_tokens', ['fcm_token'], unique=True)
    op.create_index('ix_device_tokens_session_id', 'device_tokens', ['session_id'])


def downgrade():
    op.drop_index('ix_device_tokens_session_id', table_name='device_tokens')
    op.drop_index('ix_device_tokens_fcm_token', table_name='device_tokens')
    op.drop_index('ix_device_tokens_user_id', table_name='device_tokens')
    op.drop_table('device_tokens')