from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncConnection

from app.responses import api_success
from app.schemas import (
    ApiResponse,
    MessageResponse,
    SkillDefinitionRequest,
    SkillDefinitionResponse,
    ToolDefinitionRequest,
    ToolDefinitionResponse,
)
from database.repositories.registry import RegistryRepository, SkillDefinitionRecord, ToolDefinitionRecord
from dependencies.auth import get_connection, require_superadmin


router = APIRouter(
    prefix="/superadmin/registry",
    tags=["superadmin-registry"],
    dependencies=[Depends(require_superadmin)],
)


@router.get(
    "/skills",
    response_model=ApiResponse[list[SkillDefinitionResponse]],
    summary="List global skill definitions",
    description="Lists every global skill definition available to the platform catalog. Only superadmin users can inspect this catalog.",
)
async def list_skill_definitions(
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[SkillDefinitionResponse]]:
    repository = RegistryRepository(connection)
    return api_success([_skill_response(item) for item in await repository.list_skills()])


@router.put(
    "/skills/{slug}",
    response_model=ApiResponse[SkillDefinitionResponse],
    summary="Upsert global skill definition",
    description="Creates or updates one global skill definition by slug, including prompt block, executor, schemas, and credential requirements.",
)
async def upsert_skill_definition(
    slug: str,
    payload: SkillDefinitionRequest,
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[SkillDefinitionResponse]:
    if payload.slug != slug:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Skill slug mismatch")
    repository = RegistryRepository(connection)
    return api_success(_skill_response(await repository.upsert_skill(**payload.model_dump())), message="Skill saved.")


@router.get(
    "/tools",
    response_model=ApiResponse[list[ToolDefinitionResponse]],
    summary="List global tool definitions",
    description="Lists every global utility tool definition available to the platform catalog. Only superadmin users can inspect this catalog.",
)
async def list_tool_definitions(
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[ToolDefinitionResponse]]:
    repository = RegistryRepository(connection)
    return api_success([_tool_response(item) for item in await repository.list_tools()])


@router.put(
    "/tools/{slug}",
    response_model=ApiResponse[ToolDefinitionResponse],
    summary="Upsert global tool definition",
    description="Creates or updates one global utility tool definition by slug, including prompt block, executor, schema, and builtin marker.",
)
async def upsert_tool_definition(
    slug: str,
    payload: ToolDefinitionRequest,
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[ToolDefinitionResponse]:
    if payload.slug != slug:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tool slug mismatch")
    repository = RegistryRepository(connection)
    return api_success(_tool_response(await repository.upsert_tool(**payload.model_dump(by_alias=True))), message="Tool saved.")


@router.delete(
    "/skills/{slug}",
    response_model=ApiResponse[MessageResponse],
    summary="Delete global skill definition",
    description="Permanently deletes a global skill definition by slug.",
)
async def delete_skill_definition(
    slug: str,
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    deleted = await RegistryRepository(connection).delete_skill(slug=slug)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Skill not found")
    return api_success(MessageResponse(message="Skill deleted."), message="Skill deleted.")


@router.delete(
    "/tools/{slug}",
    response_model=ApiResponse[MessageResponse],
    summary="Delete global tool definition",
    description="Permanently deletes a global tool definition by slug.",
)
async def delete_tool_definition(
    slug: str,
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    deleted = await RegistryRepository(connection).delete_tool(slug=slug)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tool not found")
    return api_success(MessageResponse(message="Tool deleted."), message="Tool deleted.")


def _skill_response(record: SkillDefinitionRecord) -> SkillDefinitionResponse:
    return SkillDefinitionResponse(**record.__dict__)


def _tool_response(record: ToolDefinitionRecord) -> ToolDefinitionResponse:
    return ToolDefinitionResponse(
        id=record.id,
        slug=record.slug,
        name=record.name,
        description=record.description,
        category=record.category,
        prompt_block=record.prompt_block,
        schema=record.schema,
        executor=record.executor,
        is_builtin=record.is_builtin,
    )
