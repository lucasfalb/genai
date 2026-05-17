from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import settings


if settings.database_schema == "genai_test":
    engine_kwargs = {"pool_pre_ping": True, "poolclass": NullPool}
else:
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 1800,
    }
if settings.database_schema:
    engine_kwargs["connect_args"] = {
        "server_settings": {"search_path": settings.database_schema}
    }

engine = create_async_engine(settings.database_url, **engine_kwargs)


@dataclass(frozen=True)
class TenantContext:
    tenant_id: UUID
    user_id: UUID | None = None
    role: str | None = None


@asynccontextmanager
async def tenant_connection(context: TenantContext) -> AsyncIterator[AsyncConnection]:
    async with engine.begin() as connection:
        await connection.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(context.tenant_id)},
        )
        yield connection
