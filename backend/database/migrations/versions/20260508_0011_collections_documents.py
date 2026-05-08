"""RAG Stage 06: collections and documents tables

Revision ID: 20260508_0011
Revises: 20260508_0010
Create Date: 2026-05-08
"""
from alembic import op

revision = "20260508_0011"
down_revision = "20260508_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collections (
            id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id         UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            name              TEXT        NOT NULL,
            description       TEXT,
            indexing_status   TEXT        NOT NULL DEFAULT 'empty',
            indexing_progress FLOAT       NOT NULL DEFAULT 0,
            document_count    INTEGER     NOT NULL DEFAULT 0,
            indexed_count     INTEGER     NOT NULL DEFAULT 0,
            failed_count      INTEGER     NOT NULL DEFAULT 0,
            last_indexed_at   TIMESTAMPTZ,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("ALTER TABLE collections ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = 'collections' AND policyname = 'tenant_isolation'
            ) THEN
                CREATE POLICY tenant_isolation ON collections
                    USING      (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
            END IF;
        END $$
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id     UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            collection_id UUID        NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
            filename      TEXT        NOT NULL,
            source_type   TEXT        NOT NULL DEFAULT 'upload',
            status        TEXT        NOT NULL DEFAULT 'uploaded',
            chunk_count   INTEGER     NOT NULL DEFAULT 0,
            error_message TEXT,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            indexed_at    TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_collections_tenant_id ON collections(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_collection_id ON documents(collection_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_tenant_id ON documents(tenant_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS documents")
    op.execute("DROP TABLE IF EXISTS collections")
