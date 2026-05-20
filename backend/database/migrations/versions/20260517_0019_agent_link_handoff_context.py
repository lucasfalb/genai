"""Add handoff context fields to agent links

Revision ID: 20260517_0019
Revises: 20260511_0018
Create Date: 2026-05-17
"""
from alembic import op

revision = "20260517_0019"
down_revision = "20260511_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE agent_links
          ADD COLUMN IF NOT EXISTS handoff_instructions TEXT,
          ADD COLUMN IF NOT EXISTS context_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
          ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_links_source_tool_name
          ON agent_links (tenant_id, source_instance_id, transfer_tool_name)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_agent_links_source_tool_name")
    op.execute(
        """
        ALTER TABLE agent_links
          DROP COLUMN IF EXISTS updated_at,
          DROP COLUMN IF EXISTS context_policy,
          DROP COLUMN IF EXISTS handoff_instructions
        """
    )
