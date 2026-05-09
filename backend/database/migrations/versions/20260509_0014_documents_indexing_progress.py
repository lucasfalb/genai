"""RAG Stage 06: add indexing progress to documents

Revision ID: 20260509_0014
Revises: 20260509_0013
Create Date: 2026-05-09
"""
from alembic import op

revision = "20260509_0014"
down_revision = "20260509_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS progress FLOAT NOT NULL DEFAULT 0.0")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS total_chunks INTEGER NOT NULL DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS total_chunks")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS progress")
