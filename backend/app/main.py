from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from api.v1.agent import router as agent_router
from api.v1.auth import router as auth_router
from api.v1.registry import router as registry_router
from api.v1.system_settings import router as system_settings_router
from api.v1.superadmin.admin import router as superadmin_admin_router
from api.v1.superadmin.email_templates import router as email_templates_router
from api.v1.superadmin.registry import router as superadmin_registry_router
from api.v1.superadmin.system_settings import router as superadmin_system_settings_router
from api.v1.tenant_invitations import public_router as tenant_invitations_public_router
from api.v1.tenant_invitations import tenant_router as tenant_invitations_router
from api.v1.tenant_agent_instances import router as tenant_agent_instances_router
from api.v1.tenant_ai_config import router as tenant_ai_config_router
from api.v1.tenant_collections import router as tenant_collections_router
from api.v1.tenant_members import router as tenant_members_router
from app.responses import api_success, http_exception_handler, validation_exception_handler
from app.schemas import ApiResponse


app = FastAPI(title="Agent Registry Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.include_router(agent_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(system_settings_router, prefix="/api/v1")
app.include_router(superadmin_admin_router, prefix="/api/v1")
app.include_router(email_templates_router, prefix="/api/v1")
app.include_router(superadmin_registry_router, prefix="/api/v1")
app.include_router(registry_router, prefix="/api/v1")
app.include_router(tenant_invitations_router, prefix="/api/v1")
app.include_router(tenant_invitations_public_router, prefix="/api/v1")
app.include_router(tenant_agent_instances_router, prefix="/api/v1")
app.include_router(tenant_ai_config_router, prefix="/api/v1")
app.include_router(tenant_collections_router, prefix="/api/v1")
app.include_router(tenant_members_router, prefix="/api/v1")
app.include_router(superadmin_system_settings_router, prefix="/api/v1")


@app.get(
    "/healthz",
    tags=["health"],
    response_model=ApiResponse[dict[str, str]],
    summary="Check service health",
    description="Returns a lightweight readiness response for local development, orchestration, and smoke tests.",
)
async def healthz() -> ApiResponse[dict[str, str]]:
    return api_success({"status": "ok"})
