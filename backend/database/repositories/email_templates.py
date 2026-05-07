from dataclasses import dataclass
import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class EmailTemplateRecord:
    id: UUID
    slug: str
    name: str
    description: str | None
    subject_template: str
    body_template: str
    body_format: str
    variables_schema: dict
    is_active: bool


class EmailTemplateRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def list_templates(self) -> list[EmailTemplateRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT id, slug, name, description, subject_template, body_template,
                       body_format, variables_schema, is_active
                FROM email_templates
                ORDER BY slug
                """
            )
        )
        return [_from_row(row) for row in result.fetchall()]

    async def get_by_slug(self, slug: str) -> EmailTemplateRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT id, slug, name, description, subject_template, body_template,
                       body_format, variables_schema, is_active
                FROM email_templates
                WHERE slug = :slug
                """
            ),
            {"slug": slug},
        )
        row = result.one_or_none()
        return None if row is None else _from_row(row)

    async def upsert_template(
        self,
        *,
        slug: str,
        name: str,
        subject_template: str,
        body_template: str,
        description: str | None = None,
        body_format: str = "html",
        variables_schema: dict | None = None,
        is_active: bool = True,
    ) -> EmailTemplateRecord:
        result = await self.connection.execute(
            text(
                """
                INSERT INTO email_templates
                  (slug, name, description, subject_template, body_template,
                   body_format, variables_schema, is_active)
                VALUES
                  (:slug, :name, :description, :subject_template, :body_template,
                   :body_format, CAST(:variables_schema AS jsonb), :is_active)
                ON CONFLICT (slug) DO UPDATE SET
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  subject_template = EXCLUDED.subject_template,
                  body_template = EXCLUDED.body_template,
                  body_format = EXCLUDED.body_format,
                  variables_schema = EXCLUDED.variables_schema,
                  is_active = EXCLUDED.is_active,
                  updated_at = now()
                RETURNING id, slug, name, description, subject_template, body_template,
                          body_format, variables_schema, is_active
                """
            ),
            {
                "slug": slug,
                "name": name,
                "description": description,
                "subject_template": subject_template,
                "body_template": body_template,
                "body_format": body_format,
                "variables_schema": json.dumps(variables_schema or {}),
                "is_active": is_active,
            },
        )
        return _from_row(result.one())


def _from_row(row) -> EmailTemplateRecord:
    return EmailTemplateRecord(
        id=row.id,
        slug=row.slug,
        name=row.name,
        description=row.description,
        subject_template=row.subject_template,
        body_template=row.body_template,
        body_format=row.body_format,
        variables_schema=row.variables_schema,
        is_active=row.is_active,
    )
