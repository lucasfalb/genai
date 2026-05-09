from collections.abc import Iterator
import os

import psycopg
import pytest
from psycopg import sql
from sqlalchemy.engine import make_url

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://genai_app:genai_app@localhost:5432/genai_test",
)
os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql://genai_app:genai_app@localhost:5432/genai_test",
)
os.environ.setdefault(
    "SYNC_DATABASE_URL",
    "postgresql+psycopg://genai:genai@localhost:5432/genai_test",
)

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
    _assert_test_database(settings.test_database_url, "TEST_DATABASE_URL")
    return _as_psycopg_dsn(settings.test_database_url)


def admin_psycopg_url() -> str:
    test_url = make_url(settings.test_database_url)
    admin_url = make_url(settings.sync_database_url).set(database=test_url.database)
    dsn = admin_url.render_as_string(hide_password=False)
    _assert_test_database(dsn, "SYNC_DATABASE_URL/TEST_DATABASE_URL")
    return _as_psycopg_dsn(dsn)


@pytest.fixture(autouse=True)
def clean_database() -> Iterator[None]:
    _cleanup_test_database()
    yield
    _cleanup_test_database()


@pytest.fixture()
def db_connection() -> Iterator[psycopg.Connection]:
    with psycopg.connect(psycopg_url(), autocommit=False) as connection:
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


def _cleanup_test_database() -> None:
    _assert_test_database(settings.test_database_url, "TEST_DATABASE_URL")
    with psycopg.connect(admin_psycopg_url(), autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                """
            )
            tables = sorted(row[0] for row in cursor.fetchall() if row[0] not in PERSISTENT_TABLES)
            if tables:
                cursor.execute(
                    sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
                        sql.SQL(", ").join(sql.Identifier(table) for table in tables)
                    )
                )
            cursor.execute(
                "DELETE FROM email_templates WHERE slug <> ALL(%s)",
                (list(DEFAULT_EMAIL_TEMPLATE_SLUGS),),
            )


def _as_psycopg_dsn(url: str) -> str:
    parsed = make_url(url)
    drivername = parsed.drivername.split("+", 1)[0]
    return parsed.set(drivername=drivername).render_as_string(hide_password=False)


def _assert_test_database(url: str, label: str) -> None:
    database = make_url(url).database or ""
    if "test" not in database.lower():
        raise RuntimeError(
            f"Refusing to clean database '{database}' from {label}; test database name must contain 'test'."
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
