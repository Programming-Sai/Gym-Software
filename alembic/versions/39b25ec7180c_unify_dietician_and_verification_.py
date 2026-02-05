# alembic/script.py.mako
"""unify dietician and verification document types

Revision ID: 39b25ec7180c
Revises: b079f08eda57
Create Date: 2026-02-05 15:32:40.632460

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '39b25ec7180c'
down_revision = 'b079f08eda57'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Rename old enums
    op.execute("ALTER TYPE dietician_document_types RENAME TO old_dietician_document_types;")
    op.execute("ALTER TYPE verification_document_types RENAME TO old_verification_document_types;")

    # 2. Create new unified enum
    op.execute("""
        CREATE TYPE document_types AS ENUM (
            'business_license',
            'id',
            'certification',
            'proof_of_ownership',
            'gym_photos',
            'education',
            'other'
        );
    """)

    # 3. Alter columns to new enum, cast existing values to text first
    op.execute("""
        ALTER TABLE dietician_documents
        ALTER COLUMN document_type TYPE document_types
        USING document_type::text::document_types;
    """)
    op.execute("""
        ALTER TABLE verification_documents
        ALTER COLUMN document_type TYPE document_types
        USING document_type::text::document_types;
    """)

    # 4. Drop old enums
    op.execute("DROP TYPE old_dietician_document_types;")
    op.execute("DROP TYPE old_verification_document_types;")


def downgrade():
    # recreate old enums (minimal set)
    op.execute("CREATE TYPE dietician_document_types AS ENUM ('certification','id','education','other');")
    op.execute("CREATE TYPE verification_document_types AS ENUM ('business_license','id','certification','proof_of_ownership','gym_photos','other');")

    # revert columns
    op.execute("""
        ALTER TABLE dietician_documents
        ALTER COLUMN document_type TYPE dietician_document_types
        USING document_type::text::dietician_document_types;
    """)
    op.execute("""
        ALTER TABLE verification_documents
        ALTER COLUMN document_type TYPE verification_document_types
        USING document_type::text::verification_document_types;
    """)

    # drop unified enum
    op.execute("DROP TYPE document_types;")
