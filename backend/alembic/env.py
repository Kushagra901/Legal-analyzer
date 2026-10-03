"""
Alembic environment configuration script.
Configures database connectivity, model metadata inspection, and custom type rendering for migrations.
"""

from logging.config import fileConfig

import app.models.database_models  # Ensure all models are loaded
from alembic import context
from app.core.config import settings
from app.core.database import Base, engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set database URL dynamically from app settings/database configuration (escape % for configparser)
safe_db_url = settings.DATABASE_URL.replace("%", "%%")
config.set_main_option("sqlalchemy.url", safe_db_url)
target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    """
    Custom rendering for VectorType, GUID, and pgvector types in migration scripts.
    """
    if type_ == "type":
        if isinstance(obj, app.models.database_models.VectorType):
            autogen_context.imports.add("import app.models.database_models")
            return f"app.models.database_models.VectorType(dim={obj.dim})"
        if isinstance(obj, app.models.database_models.GUID):
            autogen_context.imports.add("import app.models.database_models")
            return "app.models.database_models.GUID()"
        if hasattr(obj, "__module__") and "pgvector" in str(obj.__module__):
            autogen_context.imports.add("import pgvector.sqlalchemy")
            dim = getattr(obj, "dim", 768)
            return f"pgvector.sqlalchemy.Vector(dim={dim})"
    return False


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
