import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from models import Base

# 🔹 Cargar variables desde .env
from dotenv import load_dotenv
load_dotenv()

# 🔹 Construir DATABASE_URL desde variables
db_driver = os.getenv("DB_DRIVER")
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME")

DATABASE_URL = f"{db_driver}://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
# DATABASE_URL = f"{db_driver}://{db_user}:{db_pass}@{db_host}/{db_name}"

# Alembic config
config = context.config
if DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Logs
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLModel metadata para autogeneración
target_metadata = Base.metadata

def run_migrations_offline():
    """Generar el SQL de la migración sin ejecutar contra la base"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        import_module="sqlmodel",
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Ejecutar la migración directamente contra la base"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
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
