"""refresh tokens

Revision ID: 20260507_0003
Revises: 20260507_0002
Create Date: 2026-05-07
"""
from alembic import op

revision = "20260507_0003"
down_revision = "20260507_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE refresh_tokens (
          id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id     UUID NOT NULL REFERENCES users(id),
          token_hash  TEXT UNIQUE NOT NULL,
          expires_at  TIMESTAMPTZ NOT NULL,
          revoked_at  TIMESTAMPTZ,
          created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_refresh_tokens_user_active ON refresh_tokens(user_id, expires_at) WHERE revoked_at IS NULL")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON refresh_tokens TO genai_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
