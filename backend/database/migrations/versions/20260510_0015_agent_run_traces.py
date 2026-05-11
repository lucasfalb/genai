"""Stage 10: agent run traces (debug/observability)

Revision ID: 20260510_0015
Revises: 20260509_0014
Create Date: 2026-05-10
"""
from alembic import op

revision = "20260510_0015"
down_revision = "6ace8bb1b085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_run_traces (
            run_id        UUID PRIMARY KEY,
            tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            instance_id   UUID NOT NULL,
            session_id    UUID NOT NULL,
            channel       TEXT NOT NULL DEFAULT 'api',
            trace         JSONB NOT NULL,
            started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_run_traces_session "
        "ON agent_run_traces (tenant_id, session_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_run_traces_instance "
        "ON agent_run_traces (tenant_id, instance_id, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_agent_run_traces_instance")
    op.execute("DROP INDEX IF EXISTS idx_agent_run_traces_session")
    op.execute("DROP TABLE IF EXISTS agent_run_traces")
