import psycopg
import pytest


def set_tenant(cursor: psycopg.Cursor, tenant_id: str | None) -> None:
    if tenant_id is None:
        cursor.execute("RESET app.current_tenant_id")
        return
    cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (tenant_id,))


def test_rls_filters_agent_instances_by_current_tenant(
    db_connection: psycopg.Connection,
    seeded_core: dict[str, str],
) -> None:
    with db_connection.cursor() as cursor:
        set_tenant(cursor, seeded_core["tenant_a"])
        cursor.execute("SELECT id FROM agent_instances ORDER BY name")
        rows_for_a = [str(row[0]) for row in cursor.fetchall()]

        set_tenant(cursor, seeded_core["tenant_b"])
        cursor.execute("SELECT id FROM agent_instances ORDER BY name")
        rows_for_b = [str(row[0]) for row in cursor.fetchall()]

    assert rows_for_a == [seeded_core["instance_a"]]
    assert rows_for_b == [seeded_core["instance_b"]]


def test_rls_rejects_cross_tenant_insert(
    db_connection: psycopg.Connection,
    seeded_core: dict[str, str],
) -> None:
    with db_connection.cursor() as cursor:
        set_tenant(cursor, seeded_core["tenant_a"])

        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            cursor.execute(
                """
                INSERT INTO agent_instances (tenant_id, name, core_prompt, created_by)
                VALUES (%s, 'Bad Cross Tenant', 'Nope', %s)
                """,
                (seeded_core["tenant_b"], seeded_core["user_id"]),
            )


def test_messages_are_sequenced_per_session(
    db_connection: psycopg.Connection,
    seeded_core: dict[str, str],
) -> None:
    with db_connection.cursor() as cursor:
        set_tenant(cursor, seeded_core["tenant_a"])
        cursor.execute(
            """
            INSERT INTO sessions (tenant_id, instance_id, channel, user_ref)
            VALUES (%s, %s, 'api', 'user-1')
            RETURNING id
            """,
            (seeded_core["tenant_a"], seeded_core["instance_a"]),
        )
        session_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO messages (tenant_id, session_id, sequence_no, role, content)
            VALUES (%s, %s, 1, 'user', 'hello')
            """,
            (seeded_core["tenant_a"], session_id),
        )

        with pytest.raises(psycopg.errors.UniqueViolation):
            cursor.execute(
                """
                INSERT INTO messages (tenant_id, session_id, sequence_no, role, content)
                VALUES (%s, %s, 1, 'assistant', 'duplicate')
                """,
                (seeded_core["tenant_a"], session_id),
            )
