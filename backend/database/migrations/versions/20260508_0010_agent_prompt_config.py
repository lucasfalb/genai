"""agent prompt instruction blocks and guardrails

Revision ID: 20260508_0010
Revises: 20260507_0009
Create Date: 2026-05-08
"""
from alembic import op

revision = "20260508_0010"
down_revision = "20260507_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE agent_instances
          ADD COLUMN IF NOT EXISTS instruction_blocks JSONB NOT NULL DEFAULT '[]'::jsonb,
          ADD COLUMN IF NOT EXISTS guardrails JSONB NOT NULL DEFAULT '[]'::jsonb
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE agent_instances
          DROP COLUMN IF EXISTS guardrails,
          DROP COLUMN IF EXISTS instruction_blocks
        """
    )
