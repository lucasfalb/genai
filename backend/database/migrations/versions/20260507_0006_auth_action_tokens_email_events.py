"""auth action tokens and email events

Revision ID: 20260507_0006
Revises: 20260507_0005
Create Date: 2026-05-07
"""
from alembic import op

revision = "20260507_0006"
down_revision = "20260507_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE auth_action_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id),
            token_hash TEXT UNIQUE NOT NULL,
            token_type TEXT NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            consumed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_auth_action_tokens_user_type ON auth_action_tokens(user_id, token_type, consumed_at)")
    op.execute("CREATE INDEX idx_auth_action_tokens_hash ON auth_action_tokens(token_hash) WHERE consumed_at IS NULL")

    op.execute(
        """
        CREATE TABLE email_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            template_id UUID NOT NULL REFERENCES email_templates(id),
            recipient_email TEXT NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INT NOT NULL DEFAULT 0,
            last_attempt_at TIMESTAMPTZ,
            sent_at TIMESTAMPTZ,
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_email_events_status ON email_events(status, created_at)")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON auth_action_tokens TO genai_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON email_events TO genai_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS email_events")
    op.execute("DROP TABLE IF EXISTS auth_action_tokens")
