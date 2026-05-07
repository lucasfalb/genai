from collections.abc import Iterator

import psycopg
import pytest
from psycopg import sql

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
    return settings.test_database_url.replace("postgresql+psycopg://", "postgresql://")


def admin_psycopg_url() -> str:
    return settings.sync_database_url.replace("postgresql+psycopg://", "postgresql://")


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
