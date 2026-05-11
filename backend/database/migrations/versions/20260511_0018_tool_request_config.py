"""Stage tool-config: configurable HTTP request for web_fetch tools

Adds method, endpoint, headers_template, body_template, variables_schema
to tool_definitions so tools backed by the web_fetch executor declare
their HTTP shape and tenant-configurable variables.

Revision ID: 20260511_0018
Revises: 20260511_0017
Create Date: 2026-05-11
"""
from alembic import op

revision = "20260511_0018"
down_revision = "20260511_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tool_definitions
          ADD COLUMN IF NOT EXISTS method TEXT NOT NULL DEFAULT 'GET',
          ADD COLUMN IF NOT EXISTS endpoint TEXT,
          ADD COLUMN IF NOT EXISTS headers_template JSONB NOT NULL DEFAULT '{}'::jsonb,
          ADD COLUMN IF NOT EXISTS body_template TEXT,
          ADD COLUMN IF NOT EXISTS variables_schema JSONB NOT NULL DEFAULT '[]'::jsonb
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE tool_definitions
          DROP COLUMN IF EXISTS variables_schema,
          DROP COLUMN IF EXISTS body_template,
          DROP COLUMN IF EXISTS headers_template,
          DROP COLUMN IF EXISTS endpoint,
          DROP COLUMN IF EXISTS method
        """
    )
