"""RAG Stage 06: documents object storage metadata

Revision ID: 20260509_0013
Revises: 20260508_0012
Create Date: 2026-05-09
"""
from alembic import op


revision = "20260509_0013"
down_revision = "20260508_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_bucket TEXT")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_key TEXT")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_storage_key ON documents(storage_bucket, storage_key)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_documents_storage_key")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS storage_key")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS storage_bucket")
