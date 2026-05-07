import psycopg
import pytest


EXPECTED_TABLES = {
    "tenants",
    "users",
    "memberships",
    "invitations",
    "system_settings",
    "skill_definitions",
    "tool_definitions",
    "audit_logs",
    "agent_instances",
    "agent_instance_skills",
    "agent_instance_tools",
    "agent_links",
    "tool_credentials",
    "collections",
    "documents",
    "document_permissions",
    "sessions",
    "messages",
    "agent_channel_configs",
}

TENANT_SCOPED_TABLES = {
    "agent_instances",
    "agent_instance_skills",
    "agent_instance_tools",
    "agent_links",
    "tool_credentials",
    "collections",
    "documents",
    "document_permissions",
    "sessions",
    "messages",
    "agent_channel_configs",
}


def test_stage_01_tables_exist(db_connection: psycopg.Connection) -> None:
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        )
        tables = {row[0] for row in cursor.fetchall()}

    assert EXPECTED_TABLES.issubset(tables)


def test_tenant_scoped_tables_have_rls_enabled(db_connection: psycopg.Connection) -> None:
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT relname
            FROM pg_class
            WHERE relname = ANY(%s)
              AND relrowsecurity = true
              AND relforcerowsecurity = true
            """,
            (list(TENANT_SCOPED_TABLES),),
        )
        rls_tables = {row[0] for row in cursor.fetchall()}

    assert TENANT_SCOPED_TABLES == rls_tables


def test_global_uniqueness_constraints(db_connection: psycopg.Connection) -> None:
    with db_connection.cursor() as cursor:
        cursor.execute("INSERT INTO tenants (slug, name) VALUES ('unique-tenant', 'Tenant')")

        with pytest.raises(psycopg.errors.UniqueViolation):
            cursor.execute("INSERT INTO tenants (slug, name) VALUES ('unique-tenant', 'Tenant Again')")
