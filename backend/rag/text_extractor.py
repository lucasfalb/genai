from io import BytesIO
from pathlib import PurePath

from docx import Document
from pypdf import PdfReader


class TextExtractionError(RuntimeError):
    pass


def extract_text(*, filename: str, content_type: str | None, data: bytes) -> str:
    suffix = PurePath(filename).suffix.lower()
    try:
        if content_type == "application/pdf" or suffix == ".pdf":
            return _extract_pdf(data)
        if (
            content_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            or suffix == ".docx"
        ):
            return _extract_docx(data)
        if content_type in {"text/plain", "text/markdown"} or suffix in {".txt", ".md"}:
            return _extract_text(data)
    except Exception as exc:
        raise TextExtractionError(f"Failed to extract text from {filename}") from exc
    raise TextExtractionError(f"Unsupported document type for {filename}")


def _extract_pdf(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _extract_docx(data: bytes) -> str:
    document = Document(BytesIO(data))
    return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()


def _extract_text(data: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    raise TextExtractionError("Unable to decode text document")
