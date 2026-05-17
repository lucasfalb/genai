from logging.config import fileConfig
import re

from alembic import context
from sqlalchemy import create_engine, engine_from_config, pool, text

from app.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.sync_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None

SCHEMA_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _schema_name() -> str | None:
    schema = settings.database_schema
    if not schema:
        return None
    if not SCHEMA_NAME_PATTERN.fullmatch(schema):
        raise RuntimeError(f"Invalid DATABASE_SCHEMA value: {schema!r}")
    return schema


def run_migrations_offline() -> None:
    context.configure(
        url=settings.sync_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    schema = _schema_name()
    if schema:
        admin_connectable = create_engine(settings.sync_database_url, poolclass=pool.NullPool)
        with admin_connectable.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        admin_connectable.dispose()

        connectable = create_engine(
            settings.sync_database_url,
            poolclass=pool.NullPool,
            connect_args={"options": f"-csearch_path={schema}"},
        )
    else:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        if schema:
            connection.dialect.default_schema_name = schema
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=schema,
        )

        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
