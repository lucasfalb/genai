from fastapi import FastAPI

from api.v1.agent import router as agent_router
from api.v1.auth import router as auth_router
from api.v1.registry import router as registry_router
from api.v1.superadmin.email_templates import router as email_templates_router
from api.v1.superadmin.registry import router as superadmin_registry_router


app = FastAPI(title="Agent Registry Platform")
app.include_router(agent_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(email_templates_router, prefix="/api/v1")
app.include_router(superadmin_registry_router, prefix="/api/v1")
app.include_router(registry_router, prefix="/api/v1")


@app.get(
    "/healthz",
    tags=["health"],
    summary="Check service health",
    description="Returns a lightweight readiness response for local development, orchestration, and smoke tests.",
)
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
