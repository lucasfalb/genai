"""RAG Stage 06: documents storage_path column

Revision ID: 20260508_0012
Revises: 20260508_0011
Create Date: 2026-05-08
"""
from alembic import op


revision = "20260508_0012"
down_revision = "20260508_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_path TEXT")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_type TEXT")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS size_bytes BIGINT")


def downgrade() -> None:
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS size_bytes")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS content_type")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS storage_path")
