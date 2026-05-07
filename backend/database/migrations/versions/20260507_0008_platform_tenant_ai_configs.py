"""platform and tenant AI provider configs

Revision ID: 20260507_0008
Revises: 20260507_0007
Create Date: 2026-05-07
"""
from alembic import op

revision = "20260507_0008"
down_revision = "20260507_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_ai_configs")
    op.execute("DROP TABLE IF EXISTS platform_ai_configs")
