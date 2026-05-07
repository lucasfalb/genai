"""system settings and tenant AI config consolidation

Revision ID: 20260507_0009
Revises: 20260507_0008
Create Date: 2026-05-07
"""
from alembic import op

revision = "20260507_0009"
down_revision = "20260507_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tenants
          ADD COLUMN IF NOT EXISTS ai_provider VARCHAR(80),
          ADD COLUMN IF NOT EXISTS ai_default_model VARCHAR(120),
          ADD COLUMN IF NOT EXISTS ai_api_key_encrypted TEXT,
          ADD COLUMN IF NOT EXISTS ai_enabled BOOLEAN NOT NULL DEFAULT false,
          ADD COLUMN IF NOT EXISTS ai_configured_at TIMESTAMPTZ,
          ADD COLUMN IF NOT EXISTS ai_configured_by UUID REFERENCES users(id)
        """
    )

    op.execute(
        """
        CREATE TABLE system_settings (
          id                    INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
          platform_name         TEXT NOT NULL DEFAULT 'GenAI',
          platform_public_url   TEXT,
          platform_logo_url     TEXT,
          maintenance_mode      BOOLEAN NOT NULL DEFAULT false,
          registration_enabled  BOOLEAN NOT NULL DEFAULT true,
          smtp_host             TEXT,
          smtp_port             INTEGER NOT NULL DEFAULT 587,
          smtp_secure           BOOLEAN NOT NULL DEFAULT false,
          smtp_user             TEXT,
          smtp_pass_encrypted   TEXT,
          smtp_from             TEXT,
          ai_provider           VARCHAR(80) NOT NULL DEFAULT 'openai',
          ai_default_model      VARCHAR(120) NOT NULL DEFAULT 'gpt-4.1-mini',
          ai_api_key_encrypted  TEXT,
          custom_settings       JSONB NOT NULL DEFAULT '{}',
          public_settings       JSONB NOT NULL DEFAULT '{}',
          updated_by            UUID REFERENCES users(id),
          created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        INSERT INTO system_settings (
          id,
          ai_provider,
          ai_default_model,
          ai_api_key_encrypted,
          updated_at
        )
        SELECT
          1,
          provider,
          default_model,
          api_key_encrypted,
          now()
        FROM platform_ai_configs
        WHERE is_active = true
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 1
        ON CONFLICT (id) DO UPDATE SET
          ai_provider = EXCLUDED.ai_provider,
          ai_default_model = EXCLUDED.ai_default_model,
          ai_api_key_encrypted = EXCLUDED.ai_api_key_encrypted,
          updated_at = now()
        """
    )
    op.execute("INSERT INTO system_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING")

    op.execute(
        """
        UPDATE tenants t
        SET
          ai_provider = c.provider,
          ai_default_model = c.default_model,
          ai_api_key_encrypted = c.api_key_encrypted,
          ai_enabled = c.is_active,
          ai_configured_at = c.updated_at
        FROM tenant_ai_configs c
        WHERE c.tenant_id = t.id
        """
    )

    op.execute("DROP TABLE IF EXISTS tenant_ai_configs")
    op.execute("DROP TABLE IF EXISTS platform_ai_configs")
    op.execute("DROP TABLE IF EXISTS llm_providers")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON system_settings TO genai_app")


def downgrade() -> None:
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
        CREATE TABLE platform_ai_configs (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider        VARCHAR(80)  NOT NULL DEFAULT 'openai',
            base_url        TEXT,
            api_key_encrypted TEXT       NOT NULL,
            default_model   VARCHAR(120) NOT NULL DEFAULT 'gpt-4.1-mini',
            is_active       BOOLEAN      NOT NULL DEFAULT true,
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE tenant_ai_configs (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            provider        VARCHAR(80)  NOT NULL DEFAULT 'openai',
            base_url        TEXT,
            api_key_encrypted TEXT       NOT NULL,
            default_model   VARCHAR(120),
            is_active       BOOLEAN      NOT NULL DEFAULT true,
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            UNIQUE (tenant_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO platform_ai_configs (provider, base_url, api_key_encrypted, default_model)
        SELECT ai_provider, NULL, ai_api_key_encrypted, ai_default_model
        FROM system_settings
        WHERE id = 1 AND ai_api_key_encrypted IS NOT NULL
        """
    )
    op.execute(
        """
        INSERT INTO tenant_ai_configs
          (tenant_id, provider, base_url, api_key_encrypted, default_model, is_active, updated_at)
        SELECT id, ai_provider, NULL, ai_api_key_encrypted, ai_default_model, ai_enabled, ai_configured_at
        FROM tenants
        WHERE ai_api_key_encrypted IS NOT NULL
        """
    )
    op.execute("DROP TABLE IF EXISTS system_settings")
    op.execute(
        """
        ALTER TABLE tenants
          DROP COLUMN IF EXISTS ai_configured_by,
          DROP COLUMN IF EXISTS ai_configured_at,
          DROP COLUMN IF EXISTS ai_enabled,
          DROP COLUMN IF EXISTS ai_api_key_encrypted,
          DROP COLUMN IF EXISTS ai_default_model,
          DROP COLUMN IF EXISTS ai_provider
        """
    )
