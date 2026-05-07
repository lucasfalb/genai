"""actor audit versions

Revision ID: 20260507_0005
Revises: 20260507_0004
Create Date: 2026-05-07
"""
from alembic import op

revision = "20260507_0005"
down_revision = "20260507_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE audit_logs ADD COLUMN actor_type TEXT NOT NULL DEFAULT 'user'")
    op.execute("ALTER TABLE audit_logs ADD COLUMN actor_role TEXT")
    op.execute("CREATE INDEX idx_audit_logs_tenant_actor ON audit_logs(tenant_id, actor_type, created_at DESC)")

    op.execute(
        """
        CREATE TABLE resource_versions (
          id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id   UUID NOT NULL REFERENCES tenants(id),
          resource    TEXT NOT NULL,
          resource_id TEXT NOT NULL,
          version_no  BIGINT NOT NULL,
          action      TEXT NOT NULL,
          changed_by  UUID REFERENCES users(id),
          actor_type  TEXT NOT NULL DEFAULT 'user',
          actor_role  TEXT,
          snapshot    JSONB NOT NULL DEFAULT '{}',
          metadata    JSONB NOT NULL DEFAULT '{}',
          created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE(tenant_id, resource, resource_id, version_no)
        )
        """
    )
    op.execute("CREATE INDEX idx_resource_versions_resource ON resource_versions(tenant_id, resource, resource_id, version_no DESC)")
    op.execute("ALTER TABLE resource_versions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE resource_versions FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY resource_versions_tenant_isolation ON resource_versions
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON resource_versions TO genai_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS resource_versions")
    op.execute("DROP INDEX IF EXISTS idx_audit_logs_tenant_actor")
    op.execute("ALTER TABLE audit_logs DROP COLUMN IF EXISTS actor_role")
    op.execute("ALTER TABLE audit_logs DROP COLUMN IF EXISTS actor_type")
