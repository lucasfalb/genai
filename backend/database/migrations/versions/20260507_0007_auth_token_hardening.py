"""auth token hardening

Revision ID: 20260507_0007
Revises: 20260507_0006
Create Date: 2026-05-07
"""
from alembic import op

revision = "20260507_0007"
down_revision = "20260507_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE auth_action_tokens ADD COLUMN tenant_id UUID REFERENCES tenants(id)")
    op.execute(
        """
        ALTER TABLE auth_action_tokens
        ADD CONSTRAINT chk_auth_action_tokens_type
        CHECK (token_type IN ('account_activation', 'password_reset', 'tenant_invitation'))
        """
    )
    op.execute(
        """
        ALTER TABLE email_events
        ADD CONSTRAINT chk_email_events_status
        CHECK (status IN ('pending', 'sent', 'failed'))
        """
    )
    op.execute("CREATE INDEX idx_auth_action_tokens_tenant ON auth_action_tokens(tenant_id, token_type)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_auth_action_tokens_tenant")
    op.execute("ALTER TABLE email_events DROP CONSTRAINT IF EXISTS chk_email_events_status")
    op.execute("ALTER TABLE auth_action_tokens DROP CONSTRAINT IF EXISTS chk_auth_action_tokens_type")
    op.execute("ALTER TABLE auth_action_tokens DROP COLUMN IF EXISTS tenant_id")
