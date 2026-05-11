import json
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
    if provider_key == "openai":
        kwargs["stream_options"] = {"include_usage": True}
    if tool_schemas:
        kwargs["tools"] = [{"type": "function", "function": schema} for schema in tool_schemas]
        kwargs["tool_choice"] = "auto"

    try:
        client = _create_openai_client(api_key=api_key, base_url=base_url)
        stream = await client.chat.completions.create(**kwargs)
    except Exception as exc:
        raise LLMProviderError(f"LLM provider request failed ({provider_key})") from exc

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
