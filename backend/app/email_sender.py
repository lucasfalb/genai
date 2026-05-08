import asyncio
import logging
import re
import smtplib
from email.utils import formataddr, parseaddr
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncConnection

from app.config import settings

logger = logging.getLogger(__name__)

_DOUBLE_BRACE_VAR_RE = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")
_SINGLE_BRACE_VAR_RE = re.compile(r"(?<!{){\s*([A-Za-z_][A-Za-z0-9_]*)\s*}(?!})")


def _smtp_send(*, to: str, subject: str, body: str, body_format: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = _from_header()
    msg["To"] = to
    msg.attach(MIMEText(body, "html" if body_format == "html" else "plain"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:  # type: ignore[arg-type]
        server.ehlo()
        if not settings.smtp_secure:
            server.starttls()
            server.ehlo()
        server.login(settings.smtp_user, settings.smtp_pass)  # type: ignore[arg-type]
        server.sendmail(settings.smtp_user, to, msg.as_string())


def _from_header() -> str:
    if not settings.smtp_from:
        return settings.smtp_user or ""
    display_name, address = parseaddr(settings.smtp_from)
    if settings.smtp_user and address.lower() != settings.smtp_user.lower():
        return formataddr((display_name or address or "GENAI", settings.smtp_user))
    return settings.smtp_from


async def dispatch_email(
    *,
    event_id: UUID,
    recipient_email: str,
    subject_template: str,
    body_template: str,
    body_format: str,
    payload: dict,
    connection: AsyncConnection,
) -> None:
    from database.repositories.auth_tokens import EmailEventRepository

    if not settings.smtp_host or not settings.smtp_pass:
        logger.warning(
            "SMTP not configured — email event %s queued but not sent (set SMTP_HOST and SMTP_PASS)",
            event_id,
        )
        return

    try:
        subject = _render_email_template(subject_template, payload)
        body = _render_email_template(body_template, payload)
    except KeyError as exc:
        err = f"Template rendering failed: missing key {exc}"
        logger.error("Email event %s — %s", event_id, err)
        await EmailEventRepository(connection).mark_failed(event_id=event_id, error_message=err)
        return

    try:
        await asyncio.to_thread(
            _smtp_send,
            to=recipient_email,
            subject=subject,
            body=body,
            body_format=body_format,
        )
        await EmailEventRepository(connection).mark_sent(event_id=event_id)
        logger.info("Email sent: event=%s recipient=%s", event_id, recipient_email)
    except Exception as exc:
        err = str(exc)[:500]
        await EmailEventRepository(connection).mark_failed(event_id=event_id, error_message=err)
        logger.error("Email send failed: event=%s error=%s", event_id, err)


def _render_email_template(template: str, payload: dict) -> str:
    """Render managed email templates using {{ variable }} placeholders.

    The single-brace form is kept as a compatibility path for templates that
    may already have been saved after Python's format escaping converted
    `{{ variable }}` into `{ variable }`.
    """

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in payload:
            raise KeyError(key)
        return str(payload[key])

    rendered = _DOUBLE_BRACE_VAR_RE.sub(replace, template)
    return _SINGLE_BRACE_VAR_RE.sub(replace, rendered)
