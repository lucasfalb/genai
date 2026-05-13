from __future__ import annotations

import psycopg

from app.config import settings


def psycopg_url() -> str:
    return settings.sync_database_url.replace("postgresql+psycopg://", "postgresql://")


def main() -> None:
    with psycopg.connect(psycopg_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tenants (slug, name)
                VALUES
                  ('demo-a', 'Demo Tenant A'),
                  ('demo-b', 'Demo Tenant B')
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                RETURNING id, slug
                """
            )
            tenants = {slug: tenant_id for tenant_id, slug in cursor.fetchall()}

            cursor.execute(
                """
                INSERT INTO users (email, name, status)
                VALUES ('demo-admin@example.com', 'Demo Admin', 'active')
                ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """
            )
            user_id = cursor.fetchone()[0]

            for tenant_id in tenants.values():
                cursor.execute(
                    """
                    INSERT INTO memberships (user_id, tenant_id, role, status)
                    VALUES (%s, %s, 'tenant_admin', 'active')
                    ON CONFLICT (user_id, tenant_id) DO UPDATE
                    SET role = EXCLUDED.role, status = EXCLUDED.status
                    """,
                    (user_id, tenant_id),
                )

            for slug, tenant_id in tenants.items():
                cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(tenant_id),))
                cursor.execute(
                    """
                    SELECT id
                    FROM agent_instances
                    WHERE tenant_id = %s AND name = %s
                    """,
                    (tenant_id, f"Demo Agent {slug[-1].upper()}"),
                )
                if cursor.fetchone() is None:
                    cursor.execute(
                        """
                        INSERT INTO agent_instances (tenant_id, name, core_prompt, created_by, status)
                        VALUES (%s, %s, %s, %s, 'active')
                        """,
                        (
                            tenant_id,
                            f"Demo Agent {slug[-1].upper()}",
                            f"You are the demo assistant for tenant {slug[-1].upper()}.",
                            user_id,
                        ),
                    )

            cursor.execute("RESET app.current_tenant_id")

    print("Stage 01 seed applied.")


if __name__ == "__main__":
    main()
