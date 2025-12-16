# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your Base
from app.core.database import Base, DATABASE_URL

# Import ALL models so Alembic can detect them
# Don't use * import - import each module
import app.models.users
import app.models.auth
import app.models.gyms
import app.models.dieticians
import app.models.financials
import app.models.files
import app.models.notifications
import app.models.messages
import app.models.goals
import app.models.checkins
import app.models.ratings
import app.models.announcements
import app.models.relationships
import app.models.verifications

# Get Alembic config
config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)


# Set up logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata
target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()