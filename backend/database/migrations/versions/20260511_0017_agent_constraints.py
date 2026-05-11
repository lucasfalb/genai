"""Stage 10b: per-instance constraints column

Revision ID: 20260511_0017
Revises: 20260511_0016
Create Date: 2026-05-11
"""
from alembic import op

revision = "20260511_0017"
down_revision = "20260511_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE agent_instances "
        "ADD COLUMN IF NOT EXISTS constraints JSONB NOT NULL DEFAULT '[]'::jsonb"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE agent_instances DROP COLUMN IF EXISTS constraints")
