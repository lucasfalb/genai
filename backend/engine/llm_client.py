import json
from dataclasses import dataclass
from typing import Any

from engine.ai_provider import AIProviderNotConfigured


class LLMProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMCompletion:
    final_response: str | None = None
    pending_tool_calls: list[dict] | None = None


def _create_openai_client(*, api_key: str):
    from openai import AsyncOpenAI

    return AsyncOpenAI(api_key=api_key)


async def complete_chat(
    *,
    provider: str,
    api_key: str,
    model: str,
    temperature: float,
    messages: list[dict],
    tool_schemas: list[dict],
) -> LLMCompletion:
    if not api_key:
        raise AIProviderNotConfigured("AI provider API key is not configured")

    if provider != "openai":
        raise LLMProviderError(f"Unsupported AI provider: {provider}")

    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
    }
    if tool_schemas:
        kwargs["tools"] = [{"type": "function", "function": schema} for schema in tool_schemas]
        kwargs["tool_choice"] = "auto"

    try:
        client = _create_openai_client(api_key=api_key)
        response = await client.chat.completions.create(**kwargs)
    except Exception as exc:
        raise LLMProviderError("LLM provider request failed") from exc

    choice = response.choices[0]
    if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
        return LLMCompletion(
            pending_tool_calls=[
                {
                    "name": tool_call.function.name,
                    "arguments": _parse_tool_arguments(tool_call.function.arguments),
                    "id": tool_call.id,
                }
                for tool_call in choice.message.tool_calls
            ]
        )

    return LLMCompletion(final_response=choice.message.content or "")


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
