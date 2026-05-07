"""stage 01 core db

Revision ID: 20260507_0001
Revises:
Create Date: 2026-05-07
"""
from alembic import op

revision = "20260507_0001"
down_revision = None
branch_labels = None
depends_on = None


TENANT_SCOPED_TABLES = (
    "agent_instances",
    "agent_instance_skills",
    "agent_instance_tools",
    "agent_links",
    "tool_credentials",
    "collections",
    "documents",
    "document_permissions",
    "agent_channel_configs",
    "sessions",
    "messages",
)


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.execute(
        """
        CREATE TABLE tenants (
          id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          slug        TEXT UNIQUE NOT NULL,
          name        TEXT NOT NULL,
          plan        TEXT NOT NULL DEFAULT 'starter',
          status      TEXT NOT NULL DEFAULT 'active',
          settings    JSONB NOT NULL DEFAULT '{}',
          created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE users (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          email           TEXT UNIQUE NOT NULL,
          name            TEXT,
          avatar_url      TEXT,
          password_hash   TEXT,
          is_superadmin   BOOLEAN NOT NULL DEFAULT false,
          status          TEXT NOT NULL DEFAULT 'pending',
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE memberships (
          id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id     UUID NOT NULL REFERENCES users(id),
          tenant_id   UUID NOT NULL REFERENCES tenants(id),
          role        TEXT NOT NULL,
          status      TEXT NOT NULL DEFAULT 'pending',
          invited_by  UUID REFERENCES users(id),
          created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE(user_id, tenant_id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE invitations (
          id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id   UUID NOT NULL REFERENCES tenants(id),
          email       TEXT NOT NULL,
          role        TEXT NOT NULL,
          token_hash  TEXT UNIQUE NOT NULL,
          status      TEXT NOT NULL DEFAULT 'pending',
          invited_by  UUID REFERENCES users(id),
          expires_at  TIMESTAMPTZ NOT NULL,
          accepted_at TIMESTAMPTZ,
          created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE(tenant_id, email)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE llm_providers (
          id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name        TEXT NOT NULL,
          slug        TEXT UNIQUE NOT NULL,
          config      JSONB NOT NULL DEFAULT '{}',
          is_active   BOOLEAN NOT NULL DEFAULT true,
          created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE skill_definitions (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name            TEXT NOT NULL,
          slug            TEXT UNIQUE NOT NULL,
          description     TEXT,
          category        TEXT,
          prompt_block    TEXT NOT NULL,
          tool_schema     JSONB NOT NULL,
          executor        TEXT NOT NULL,
          input_schema    JSONB NOT NULL,
          output_schema   JSONB NOT NULL,
          requires_credential BOOLEAN NOT NULL DEFAULT false,
          credential_schema   JSONB,
          is_active       BOOLEAN NOT NULL DEFAULT true,
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE tool_definitions (
          id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name        TEXT NOT NULL,
          slug        TEXT UNIQUE NOT NULL,
          description TEXT,
          category    TEXT,
          prompt_block TEXT NOT NULL,
          schema      JSONB NOT NULL,
          executor    TEXT NOT NULL,
          is_builtin  BOOLEAN NOT NULL DEFAULT false,
          created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE agent_instances (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id       UUID NOT NULL REFERENCES tenants(id),
          name            TEXT NOT NULL,
          description     TEXT,
          core_prompt     TEXT NOT NULL,
          model           TEXT NOT NULL DEFAULT 'gpt-4.1-mini',
          temperature     FLOAT NOT NULL DEFAULT 0.2,
          status          TEXT NOT NULL DEFAULT 'inactive',
          rag_scope       JSONB NOT NULL DEFAULT '[]',
          created_by      UUID NOT NULL REFERENCES users(id),
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE agent_instance_skills (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id       UUID NOT NULL REFERENCES tenants(id),
          instance_id     UUID NOT NULL REFERENCES agent_instances(id),
          skill_id        UUID NOT NULL REFERENCES skill_definitions(id),
          is_enabled      BOOLEAN NOT NULL DEFAULT true,
          config          JSONB NOT NULL DEFAULT '{}',
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE(instance_id, skill_id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE agent_instance_tools (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id       UUID NOT NULL REFERENCES tenants(id),
          instance_id     UUID NOT NULL REFERENCES agent_instances(id),
          tool_id         UUID NOT NULL REFERENCES tool_definitions(id),
          is_enabled      BOOLEAN NOT NULL DEFAULT true,
          config          JSONB NOT NULL DEFAULT '{}',
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE(instance_id, tool_id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE agent_links (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id       UUID NOT NULL REFERENCES tenants(id),
          source_instance_id UUID NOT NULL REFERENCES agent_instances(id),
          target_instance_id UUID NOT NULL REFERENCES agent_instances(id),
          transfer_tool_name TEXT NOT NULL,
          trigger_description TEXT NOT NULL,
          transfer_mode   TEXT NOT NULL DEFAULT 'llm_decision',
          is_enabled      BOOLEAN NOT NULL DEFAULT true,
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE(source_instance_id, target_instance_id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE tool_credentials (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id       UUID NOT NULL REFERENCES tenants(id),
          skill_id        UUID NOT NULL REFERENCES skill_definitions(id),
          credential_data JSONB NOT NULL DEFAULT '{}',
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE(tenant_id, skill_id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE collections (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id       UUID NOT NULL REFERENCES tenants(id),
          name            TEXT NOT NULL,
          description     TEXT,
          indexing_status TEXT NOT NULL DEFAULT 'empty',
          indexing_progress FLOAT NOT NULL DEFAULT 0,
          document_count  INTEGER NOT NULL DEFAULT 0,
          indexed_count   INTEGER NOT NULL DEFAULT 0,
          failed_count    INTEGER NOT NULL DEFAULT 0,
          last_indexed_at TIMESTAMPTZ,
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE documents (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id       UUID NOT NULL REFERENCES tenants(id),
          collection_id   UUID NOT NULL REFERENCES collections(id),
          filename        TEXT NOT NULL,
          source_type     TEXT NOT NULL,
          status          TEXT NOT NULL DEFAULT 'uploaded',
          chunk_count     INTEGER NOT NULL DEFAULT 0,
          error_message   TEXT,
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          indexed_at      TIMESTAMPTZ
        )
        """
    )

    op.execute(
        """
        CREATE TABLE document_permissions (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id       UUID NOT NULL REFERENCES tenants(id),
          document_id     UUID NOT NULL REFERENCES documents(id),
          subject_type    TEXT NOT NULL,
          subject_id      UUID NOT NULL,
          permission      TEXT NOT NULL DEFAULT 'read',
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE(document_id, subject_type, subject_id, permission)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE agent_channel_configs (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id       UUID NOT NULL REFERENCES tenants(id),
          instance_id     UUID NOT NULL REFERENCES agent_instances(id),
          channel         TEXT NOT NULL,
          config          JSONB NOT NULL DEFAULT '{}',
          outbound_sync_config JSONB NOT NULL DEFAULT '{}',
          is_active       BOOLEAN NOT NULL DEFAULT false,
          api_key         TEXT,
          allowed_origins TEXT[],
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE(tenant_id, instance_id, channel)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE sessions (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id       UUID NOT NULL REFERENCES tenants(id),
          instance_id     UUID NOT NULL REFERENCES agent_instances(id),
          channel         TEXT NOT NULL,
          user_ref        TEXT,
          metadata        JSONB NOT NULL DEFAULT '{}',
          started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          last_message_at TIMESTAMPTZ
        )
        """
    )

    op.execute(
        """
        CREATE TABLE messages (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id       UUID NOT NULL REFERENCES tenants(id),
          session_id      UUID NOT NULL REFERENCES sessions(id),
          sequence_no     BIGINT NOT NULL,
          role            TEXT NOT NULL,
          content         TEXT NOT NULL,
          metadata        JSONB NOT NULL DEFAULT '{}',
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE(session_id, sequence_no)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE audit_logs (
          id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id   UUID REFERENCES tenants(id),
          user_id     UUID REFERENCES users(id),
          action      TEXT NOT NULL,
          resource    TEXT NOT NULL,
          resource_id TEXT,
          metadata    JSONB NOT NULL DEFAULT '{}',
          created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute("CREATE INDEX idx_agent_instances_tenant ON agent_instances(tenant_id)")
    op.execute("CREATE INDEX idx_agent_instance_skills_instance ON agent_instance_skills(instance_id, is_enabled)")
    op.execute("CREATE INDEX idx_agent_instance_tools_instance ON agent_instance_tools(instance_id, is_enabled)")
    op.execute("CREATE INDEX idx_agent_links_source ON agent_links(source_instance_id, is_enabled)")
    op.execute("CREATE INDEX idx_collections_tenant_status ON collections(tenant_id, indexing_status)")
    op.execute("CREATE INDEX idx_documents_collection_status ON documents(collection_id, status)")
    op.execute("CREATE INDEX idx_sessions_tenant_instance ON sessions(tenant_id, instance_id, started_at DESC)")
    op.execute("CREATE INDEX idx_messages_session ON messages(session_id, created_at)")
    op.execute("CREATE INDEX idx_invitations_tenant_status ON invitations(tenant_id, status)")
    op.execute("CREATE INDEX idx_audit_logs_tenant_created ON audit_logs(tenant_id, created_at DESC)")

    for table in TENANT_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
            """
        )


def downgrade() -> None:
    for table in reversed(TENANT_SCOPED_TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")

    op.execute("DROP TABLE IF EXISTS audit_logs")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS sessions")
    op.execute("DROP TABLE IF EXISTS agent_channel_configs")
    op.execute("DROP TABLE IF EXISTS document_permissions")
    op.execute("DROP TABLE IF EXISTS documents")
    op.execute("DROP TABLE IF EXISTS collections")
    op.execute("DROP TABLE IF EXISTS tool_credentials")
    op.execute("DROP TABLE IF EXISTS agent_links")
    op.execute("DROP TABLE IF EXISTS agent_instance_tools")
    op.execute("DROP TABLE IF EXISTS agent_instance_skills")
    op.execute("DROP TABLE IF EXISTS agent_instances")
    op.execute("DROP TABLE IF EXISTS tool_definitions")
    op.execute("DROP TABLE IF EXISTS skill_definitions")
    op.execute("DROP TABLE IF EXISTS llm_providers")
    op.execute("DROP TABLE IF EXISTS invitations")
    op.execute("DROP TABLE IF EXISTS memberships")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS tenants")
