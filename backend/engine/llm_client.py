import json
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from engine.ai_provider import AIProviderNotConfigured


class LLMProviderError(RuntimeError):
    pass


DeltaCallback = Callable[[str], None] | Callable[[str], Awaitable[None]]


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class LLMCompletion:
    final_response: str | None = None
    pending_tool_calls: list[dict] | None = None
    usage: TokenUsage = TokenUsage()


_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"((?:api[_-]?key|token|secret)\s*[=:]\s*)[^\s,;]+", re.IGNORECASE),
)


PROVIDER_BASE_URLS: dict[str, str | None] = {
    "openai": None,
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "anthropic": "https://api.anthropic.com/v1/",
}


def _create_openai_client(*, api_key: str, base_url: str | None = None):
    from openai import AsyncOpenAI

    if base_url:
        return AsyncOpenAI(api_key=api_key, base_url=base_url)
    return AsyncOpenAI(api_key=api_key)


async def complete_chat(
    *,
    provider: str,
    api_key: str,
    model: str,
    temperature: float,
    messages: list[dict],
    tool_schemas: list[dict],
    on_delta: DeltaCallback | None = None,
) -> LLMCompletion:
    if not api_key:
        raise AIProviderNotConfigured("AI provider API key is not configured")

    provider_key = provider.lower() if isinstance(provider, str) else ""
    if provider_key not in PROVIDER_BASE_URLS:
        raise LLMProviderError(f"Unsupported AI provider: {provider}")
    base_url = PROVIDER_BASE_URLS[provider_key]

    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
        "stream": True,
    }
    if provider_key in {"openai", "google", "gemini"}:
        kwargs["stream_options"] = {"include_usage": True}
    if tool_schemas:
        kwargs["tools"] = [{"type": "function", "function": schema} for schema in tool_schemas]
        kwargs["tool_choice"] = "auto"

    try:
        client = _create_openai_client(api_key=api_key, base_url=base_url)
        stream = await client.chat.completions.create(**kwargs)
    except Exception as exc:
        detail = _format_provider_exception(exc)
        raise LLMProviderError(f"LLM provider request failed ({provider_key}): {detail}") from exc

    content_parts: list[str] = []
    tool_call_chunks: dict[int, dict[str, str]] = {}
    usage = TokenUsage()

    try:
        async for chunk in stream:
            chunk_usage = getattr(chunk, "usage", None)
            if chunk_usage is not None:
                usage = TokenUsage(
                    prompt_tokens=int(getattr(chunk_usage, "prompt_tokens", 0) or 0),
                    completion_tokens=int(getattr(chunk_usage, "completion_tokens", 0) or 0),
                    total_tokens=int(getattr(chunk_usage, "total_tokens", 0) or 0),
                )
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta is None:
                continue
            piece = getattr(delta, "content", None)
            if piece:
                content_parts.append(piece)
                if on_delta is not None:
                    result = on_delta(piece)
                    if hasattr(result, "__await__"):
                        await result
            tool_calls = getattr(delta, "tool_calls", None) or []
            for tc in tool_calls:
                idx = getattr(tc, "index", 0) or 0
                slot = tool_call_chunks.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                tc_id = getattr(tc, "id", None)
                if tc_id:
                    slot["id"] = tc_id
                fn = getattr(tc, "function", None)
                if fn is not None:
                    name = getattr(fn, "name", None)
                    if name:
                        slot["name"] += name
                    args = getattr(fn, "arguments", None)
                    if args:
                        slot["arguments"] += args
    except Exception as exc:
        raise LLMProviderError("LLM provider stream failed") from exc

    if tool_call_chunks:
        return LLMCompletion(
            pending_tool_calls=[
                {
                    "name": slot["name"],
                    "arguments": _parse_tool_arguments(slot["arguments"]),
                    "id": slot["id"] or None,
                }
                for slot in tool_call_chunks.values()
            ],
            usage=usage,
        )

    return LLMCompletion(final_response="".join(content_parts), usage=usage)


def _parse_tool_arguments(raw_arguments: str | None) -> dict:
    if not raw_arguments:
        return {}
    try:
        parsed = json.loads(raw_arguments)
    except json.JSONDecodeError as exc:
        raise LLMProviderError("LLM provider returned invalid tool arguments") from exc
    if not isinstance(parsed, dict):
        raise LLMProviderError("LLM provider returned non-object tool arguments")
    return parsed


def _format_provider_exception(exc: Exception) -> str:
    status_code = getattr(exc, "status_code", None)
    code = getattr(exc, "code", None)
    message = _extract_provider_message(exc)

    parts: list[str] = []
    if status_code:
        parts.append(f"HTTP {status_code}")
    if code:
        parts.append(str(code))
    if message:
        parts.append(message)

    detail = " - ".join(parts) if parts else str(exc) or exc.__class__.__name__
    return _sanitize_error_detail(detail)


def _extract_provider_message(exc: Exception) -> str:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message:
                return message
        message = body.get("message")
        if isinstance(message, str) and message:
            return message
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            payload = response.json()
        except Exception:
            payload = None
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = error.get("message")
                if isinstance(message, str) and message:
                    return message
            message = payload.get("message")
            if isinstance(message, str) and message:
                return message
    return str(exc)


def _sanitize_error_detail(detail: str, *, max_length: int = 500) -> str:
    sanitized = detail.replace("\n", " ").replace("\r", " ").strip()
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub(
            lambda match: f"{match.group(1)}[redacted]" if match.groups() else "[redacted]",
            sanitized,
        )
    if len(sanitized) > max_length:
        return sanitized[: max_length - 3] + "..."
    return sanitized or "Unknown provider error"
