"""Stage 10b: rebase default model literals to gpt-5-mini

Revision ID: 20260511_0016
Revises: 20260510_0015
Create Date: 2026-05-11
"""
from alembic import op

revision = "20260511_0016"
down_revision = "20260510_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE agent_instances ALTER COLUMN model SET DEFAULT 'gpt-5-mini'")
    op.execute("ALTER TABLE system_settings ALTER COLUMN ai_default_model SET DEFAULT 'gpt-5-mini'")
    op.execute(
        "DO $$ BEGIN "
        "  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'platform_ai_configs') THEN "
        "    EXECUTE 'ALTER TABLE platform_ai_configs ALTER COLUMN default_model SET DEFAULT ''gpt-5-mini'''; "
        "  END IF; "
        "  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tenant_ai_configs') THEN "
        "    EXECUTE 'ALTER TABLE tenant_ai_configs ALTER COLUMN default_model SET DEFAULT ''gpt-5-mini'''; "
        "  END IF; "
        "END $$;"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE agent_instances ALTER COLUMN model SET DEFAULT 'gpt-4.1-mini'")
    op.execute("ALTER TABLE system_settings ALTER COLUMN ai_default_model SET DEFAULT 'gpt-4.1-mini'")
    op.execute(
        "DO $$ BEGIN "
        "  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'platform_ai_configs') THEN "
        "    EXECUTE 'ALTER TABLE platform_ai_configs ALTER COLUMN default_model SET DEFAULT ''gpt-4.1-mini'''; "
        "  END IF; "
        "  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tenant_ai_configs') THEN "
        "    EXECUTE 'ALTER TABLE tenant_ai_configs ALTER COLUMN default_model SET DEFAULT ''gpt-4.1-mini'''; "
        "  END IF; "
        "END $$;"
    )
