"""add_messaging_columns

Revision ID: 12d789cdc69a
Revises: d1c4c4f7b9aa
Create Date: 2026-03-23 06:13:53.550872

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '12d789cdc69a'
down_revision = 'd1c4c4f7b9aa'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to messages table
    op.add_column('messages', sa.Column('sender_type', sa.Enum('gym_user', 'gym_owner', 'dietician', 'admin', name='user_roles'), nullable=False))
    op.add_column('messages', sa.Column('receiver_type', sa.Enum('gym_user', 'gym_owner', 'dietician', 'admin', name='user_roles'), nullable=False))
    op.add_column('messages', sa.Column('file_id', sa.String(), nullable=True))
    
    # Drop old index and create new one
    op.drop_index(op.f('ix_messages_sender_receiver'), table_name='messages')
    op.create_index('ix_messages_conversation', 'messages', ['sender_id', 'receiver_id'], unique=False)
    
    # Add foreign key for file_id
    op.create_foreign_key(None, 'messages', 'files', ['file_id'], ['file_id'], ondelete='SET NULL')
    
    # Drop is_read column
    op.drop_column('messages', 'is_read')


def downgrade():
    # Add back is_read column
    op.add_column('messages', sa.Column('is_read', sa.BOOLEAN(), nullable=False, server_default=False))
    
    # Drop foreign key
    op.drop_constraint(None, 'messages', type_='foreignkey')
    
    # Drop new index and restore old one
    op.drop_index('ix_messages_conversation', table_name='messages')
    op.create_index(op.f('ix_messages_sender_receiver'), 'messages', ['sender_id', 'receiver_id'], unique=False)
    
    # Drop new columns
    op.drop_column('messages', 'file_id')
    op.drop_column('messages', 'receiver_type')
    op.drop_column('messages', 'sender_type')