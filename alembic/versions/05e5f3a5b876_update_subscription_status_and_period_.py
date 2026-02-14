# alembic/script.py.mako
"""update subscription status and period fields

Revision ID: 05e5f3a5b876
Revises: 43396528e32c
Create Date: 2026-02-14 13:31:54.713940

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '05e5f3a5b876'
down_revision = '43396528e32c'
branch_labels = None
depends_on = None



def upgrade():
    # 1. Create new enum type
    op.execute("""
        CREATE TYPE subscription_statuses_new AS ENUM (
            'pending',
            'active',
            'past_due',
            'cancelled'
        );
    """)

    # 2. Alter column to use new enum
    op.execute("""
        ALTER TABLE subscriptions
        ALTER COLUMN status DROP DEFAULT;
    """)

    op.execute("""
        ALTER TABLE subscriptions
        ALTER COLUMN status
        TYPE subscription_statuses_new
        USING status::text::subscription_statuses_new;
    """)

    # 3. Drop old enum
    op.execute("DROP TYPE subscription_statuses;")

    # 4. Rename new enum
    op.execute("ALTER TYPE subscription_statuses_new RENAME TO subscription_statuses;")

    # 5. Set new default
    op.execute("""
        ALTER TABLE subscriptions
        ALTER COLUMN status SET DEFAULT 'pending';
    """)

    # 6. Make period fields nullable
    op.alter_column("subscriptions", "current_period_start", nullable=True)
    op.alter_column("subscriptions", "current_period_end", nullable=True)



def downgrade():
    op.execute("""
        CREATE TYPE subscription_statuses_old AS ENUM (
            'trialing',
            'pending',
            'active',
            'past_due',
            'cancelled'
        );
    """)

    op.execute("ALTER TABLE subscriptions ALTER COLUMN status DROP DEFAULT;")

    op.execute("""
        ALTER TABLE subscriptions
        ALTER COLUMN status
        TYPE subscription_statuses_old
        USING status::text::subscription_statuses_old;
    """)

    op.execute("DROP TYPE subscription_statuses;")
    op.execute("ALTER TYPE subscription_statuses_old RENAME TO subscription_statuses;")

    op.execute("""
        ALTER TABLE subscriptions
        ALTER COLUMN status SET DEFAULT 'trialing';
    """)

    op.alter_column("subscriptions", "current_period_start", nullable=False)
    op.alter_column("subscriptions", "current_period_end", nullable=False)
