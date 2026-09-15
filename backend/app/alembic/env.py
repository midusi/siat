from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.models import Base

from app import config as app_config
DATABASE_URL = app_config.db_url()

# Alembic config
alembic_config = context.config
if DATABASE_URL:
    alembic_config.set_main_option(
        "sqlalchemy.url",
        DATABASE_URL.render_as_string(hide_password=False),
    )

# Logs
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    """Generar el SQL de la migración sin ejecutar contra la base"""
    url = alembic_config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Ejecutar la migración directamente contra la base"""
    connectable = engine_from_config(
        alembic_config.get_section(alembic_config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

# Seleccionar modo de ejecución
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
