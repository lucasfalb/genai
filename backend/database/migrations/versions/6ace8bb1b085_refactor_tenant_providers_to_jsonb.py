"""refactor_tenant_providers_to_jsonb

Revision ID: 6ace8bb1b085
Revises: 20260509_0014
Create Date: 2026-05-10 00:37:58.520874
"""
from alembic import op
import sqlalchemy as sa


revision = '6ace8bb1b085'
down_revision = '20260509_0014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new JSONB column for providers configuration
    op.execute(
        """
        ALTER TABLE tenants
          ADD COLUMN IF NOT EXISTS providers_config JSONB NOT NULL DEFAULT '{"providers": []}'
        """
    )

    # Migrate existing AI config to new format
    op.execute(
        """
        UPDATE tenants
        SET providers_config = jsonb_build_object(
          'providers', CASE
            WHEN ai_api_key_encrypted IS NOT NULL THEN
              jsonb_build_array(
                jsonb_build_object(
                  'name', ai_provider,
                  'api_key_encrypted', ai_api_key_encrypted,
                  'enabled', ai_enabled,
                  'configured_at', to_char(ai_configured_at, 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
                  'configured_by', ai_configured_by::text
                )
              )
            ELSE '[]'::jsonb
          END
        )
        WHERE ai_provider IS NOT NULL
        """
    )

    # Remove old AI columns
    op.execute(
        """
        ALTER TABLE tenants
          DROP COLUMN IF EXISTS ai_provider,
          DROP COLUMN IF EXISTS ai_default_model,
          DROP COLUMN IF EXISTS ai_api_key_encrypted,
          DROP COLUMN IF EXISTS ai_enabled,
          DROP COLUMN IF EXISTS ai_configured_at,
          DROP COLUMN IF EXISTS ai_configured_by
        """
    )


def downgrade() -> None:
    # Re-add old columns
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

    # Migrate back from JSONB (take first provider)
    op.execute(
        """
        UPDATE tenants
        SET
          ai_provider = (providers_config->'providers'->0->>'name'),
          ai_api_key_encrypted = (providers_config->'providers'->0->>'api_key_encrypted'),
          ai_enabled = COALESCE((providers_config->'providers'->0->>'enabled')::boolean, false),
          ai_configured_at = (providers_config->'providers'->0->>'configured_at')::timestamptz,
          ai_configured_by = (providers_config->'providers'->0->>'configured_by')::uuid
        WHERE jsonb_array_length(providers_config->'providers') > 0
        """
    )

    # Remove JSONB column
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS providers_config")
