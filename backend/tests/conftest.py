from collections.abc import Iterator
import os
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy.engine import make_url

os.environ.setdefault("DATABASE_SCHEMA", "genai_test")
os.environ.setdefault("RAG_INDEXING_CONSUMER_ENABLED", "false")

from app.config import settings

PERSISTENT_TABLES = {"alembic_version", "email_templates"}
DEFAULT_EMAIL_TEMPLATE_SLUGS = {
    "account_activation",
    "tenant_invitation",
    "password_reset",
    "password_changed",
    "membership_assigned",
}


def psycopg_url() -> str:
    _assert_test_target(settings.test_database_url, "TEST_DATABASE_URL")
    return _as_psycopg_dsn(settings.test_database_url)


def admin_psycopg_url() -> str:
    test_url = make_url(settings.test_database_url)
    admin_url = make_url(settings.sync_database_url).set(database=test_url.database)
    dsn = admin_url.render_as_string(hide_password=False)
    _assert_test_target(dsn, "SYNC_DATABASE_URL/TEST_DATABASE_URL")
    return _as_psycopg_dsn(dsn)


@pytest.fixture(scope="session", autouse=True)
def prepare_test_schema() -> Iterator[None]:
    _assert_test_target(settings.test_database_url, "TEST_DATABASE_URL")
    schema = _test_schema()
    with psycopg.connect(admin_psycopg_url(), autocommit=True, connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

    alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location",
        str(Path(__file__).resolve().parents[1] / "database" / "migrations"),
    )
    command.upgrade(alembic_cfg, "head")
    yield


@pytest.fixture(scope="session")
def admin_connection(prepare_test_schema: None) -> Iterator[psycopg.Connection]:
    with psycopg.connect(
        admin_psycopg_url(),
        autocommit=True,
        connect_timeout=10,
    ) as connection:
        yield connection


@pytest.fixture(autouse=True)
def clean_database(admin_connection: psycopg.Connection) -> Iterator[None]:
    _cleanup_test_database(admin_connection)
    yield
    _cleanup_test_database(admin_connection)


@pytest.fixture()
def db_connection() -> Iterator[psycopg.Connection]:
    with psycopg.connect(
        psycopg_url(),
        autocommit=False,
        options=f"-csearch_path={_test_schema()}",
        connect_timeout=10,
    ) as connection:
        yield connection
        connection.rollback()


def api_data(response):
    body = response.json()
    assert body["status"] == "success"
    return body["data"]


def api_error(response):
    body = response.json()
    assert body["status"] == "error"
    return body["error"]


def _cleanup_test_database(connection: psycopg.Connection) -> None:
    _assert_test_target(settings.test_database_url, "TEST_DATABASE_URL")
    schema = _test_schema()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = %s
            """,
            (schema,),
        )
        tables = sorted(row[0] for row in cursor.fetchall() if row[0] not in PERSISTENT_TABLES)
        if tables:
            cursor.execute(
                sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
                    sql.SQL(", ").join(sql.Identifier(schema, table) for table in tables)
                )
            )
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name = 'email_templates'
            )
            """,
            (schema,),
        )
        if cursor.fetchone()[0]:
            cursor.execute(
                sql.SQL("DELETE FROM {} WHERE slug <> ALL(%s)").format(
                    sql.Identifier(schema, "email_templates")
                ),
                (list(DEFAULT_EMAIL_TEMPLATE_SLUGS),),
            )


def _as_psycopg_dsn(url: str) -> str:
    parsed = make_url(url)
    drivername = parsed.drivername.split("+", 1)[0]
    return parsed.set(drivername=drivername).render_as_string(hide_password=False)


def _test_schema() -> str:
    schema = settings.database_schema or ""
    if not schema:
        raise RuntimeError("DATABASE_SCHEMA must be set for tests.")
    return schema


def _assert_test_target(url: str, label: str) -> None:
    database = make_url(url).database or ""
    schema = os.environ.get("DATABASE_SCHEMA", "")
    if "test" not in database.lower() and "test" not in schema.lower():
        raise RuntimeError(
            f"Refusing to clean database '{database}' schema '{schema}' from {label}; "
            "database or schema name must contain 'test'."
        )


@pytest.fixture()
def seeded_core(db_connection: psycopg.Connection) -> dict[str, str]:
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO tenants (slug, name)
            VALUES ('tenant-a', 'Tenant A'), ('tenant-b', 'Tenant B')
            RETURNING id, slug
            """
        )
        tenants = {slug: str(tenant_id) for tenant_id, slug in cursor.fetchall()}

        cursor.execute(
            """
            INSERT INTO users (email, name, status)
            VALUES ('admin-a@example.com', 'Admin A', 'active')
            RETURNING id
            """
        )
        user_id = str(cursor.fetchone()[0])

        cursor.execute(
            """
            INSERT INTO memberships (user_id, tenant_id, role, status)
            VALUES (%s, %s, 'tenant_admin', 'active')
            """,
            (user_id, tenants["tenant-a"]),
        )

        instances = {}
        for slug in ("tenant-a", "tenant-b"):
            cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (tenants[slug],))
            cursor.execute(
                """
                INSERT INTO agent_instances (tenant_id, name, core_prompt, created_by, status)
                VALUES (%s, %s, %s, %s, 'active')
                RETURNING id
                """,
                (
                    tenants[slug],
                    f"Support {slug[-1].upper()}",
                    f"You are support {slug[-1].upper()}.",
                    user_id,
                ),
            )
            instances[tenants[slug]] = str(cursor.fetchone()[0])

        cursor.execute("RESET app.current_tenant_id")

    return {
        "tenant_a": tenants["tenant-a"],
        "tenant_b": tenants["tenant-b"],
        "user_id": user_id,
        "instance_a": instances[tenants["tenant-a"]],
        "instance_b": instances[tenants["tenant-b"]],
    }
