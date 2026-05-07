from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncConnection

from app.schemas import EmailTemplateRequest, EmailTemplateResponse
from database.repositories.email_templates import EmailTemplateRecord, EmailTemplateRepository
from dependencies.auth import get_connection, require_superadmin


router = APIRouter(
    prefix="/superadmin/email-templates",
    tags=["superadmin-email-templates"],
    dependencies=[Depends(require_superadmin)],
)


@router.get(
    "",
    response_model=list[EmailTemplateResponse],
    summary="List email templates",
    description="Lists global transactional email templates managed by superadmin users.",
)
async def list_email_templates(connection: AsyncConnection = Depends(get_connection)) -> list[EmailTemplateResponse]:
    repository = EmailTemplateRepository(connection)
    return [_to_response(item) for item in await repository.list_templates()]


@router.get(
    "/{slug}",
    response_model=EmailTemplateResponse,
    summary="Get email template",
    description="Returns one global transactional email template by slug for superadmin management.",
)
async def get_email_template(slug: str, connection: AsyncConnection = Depends(get_connection)) -> EmailTemplateResponse:
    repository = EmailTemplateRepository(connection)
    template = await repository.get_by_slug(slug)
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Email template not found")
    return _to_response(template)


@router.put(
    "/{slug}",
    response_model=EmailTemplateResponse,
    summary="Upsert email template",
    description="Creates or updates a global transactional email template. Only superadmin users can manage these templates.",
)
async def upsert_email_template(
    slug: str,
    payload: EmailTemplateRequest,
    connection: AsyncConnection = Depends(get_connection),
) -> EmailTemplateResponse:
    if payload.slug != slug:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Template slug mismatch")

    repository = EmailTemplateRepository(connection)
    template = await repository.upsert_template(**payload.model_dump())
    return _to_response(template)


def _to_response(template: EmailTemplateRecord) -> EmailTemplateResponse:
    return EmailTemplateResponse(
        id=template.id,
        slug=template.slug,
        name=template.name,
        description=template.description,
        subject_template=template.subject_template,
        body_template=template.body_template,
        body_format=template.body_format,
        variables_schema=template.variables_schema,
        is_active=template.is_active,
    )
