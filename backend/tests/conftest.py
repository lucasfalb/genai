from collections.abc import Iterator

import psycopg
import pytest

from app.config import settings


def psycopg_url() -> str:
    return settings.test_database_url.replace("postgresql+psycopg://", "postgresql://")


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
