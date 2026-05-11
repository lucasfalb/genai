from types import SimpleNamespace

import pytest

import engine.llm_client as llm_client
from engine.base_graph import llm_node
from engine.llm_client import LLMProviderError


async def test_llm_node_populates_final_response(monkeypatch) -> None:
    calls = []

    class FakeCompletions:
        async def create(self, **kwargs):
            calls.append(kwargs)
            return _stream_content(["Hello ", "from LLM."])

    monkeypatch.setattr(llm_client, "_create_openai_client", lambda **_kwargs: _client(FakeCompletions()))

    result = await llm_node(
        {
            "ai_provider": "openai",
            "ai_api_key": "sk-test",
            "system_prompt": "You are helpful.",
            "messages": [{"role": "user", "content": "hello"}],
            "model": "gpt-test",
            "temperature": 0.1,
            "tool_schemas": [],
        }
    )

    assert result["final_response"] == "Hello from LLM."
    assert "token_usage" in result
    assert calls[0]["model"] == "gpt-test"
    assert calls[0]["messages"][0] == {"role": "system", "content": "You are helpful."}
    assert calls[0]["stream"] is True
    assert "tools" not in calls[0]


async def test_llm_node_populates_pending_tool_calls(monkeypatch) -> None:
    calls = []

    class FakeCompletions:
        async def create(self, **kwargs):
            calls.append(kwargs)
            return _stream_tool_call(call_id="call-1", name="search_docs", arguments='{"query": "billing"}')

    monkeypatch.setattr(llm_client, "_create_openai_client", lambda **_kwargs: _client(FakeCompletions()))

    result = await llm_node(
        {
            "ai_provider": "openai",
            "ai_api_key": "sk-test",
            "system_prompt": "Use tools when needed.",
            "messages": [{"role": "user", "content": "find billing docs"}],
            "model": "gpt-test",
            "temperature": 0.2,
            "tool_schemas": [{"name": "search_docs", "parameters": {"type": "object"}}],
        }
    )

    assert result["pending_tool_calls"] == [
        {"name": "search_docs", "arguments": {"query": "billing"}, "id": "call-1"}
    ]
    assert "token_usage" in result
    assert calls[0]["tool_choice"] == "auto"
    assert calls[0]["tools"][0]["function"]["name"] == "search_docs"


async def test_llm_node_rejects_invalid_tool_arguments(monkeypatch) -> None:
    class FakeCompletions:
        async def create(self, **_kwargs):
            return _stream_tool_call(call_id="call-1", name="search_docs", arguments="{bad-json}")

    monkeypatch.setattr(llm_client, "_create_openai_client", lambda **_kwargs: _client(FakeCompletions()))

    with pytest.raises(LLMProviderError, match="invalid tool arguments"):
        await llm_node(
            {
                "ai_provider": "openai",
                "ai_api_key": "sk-test",
                "system_prompt": "Use tools.",
                "messages": [{"role": "user", "content": "search"}],
                "tool_schemas": [{"name": "search_docs"}],
            }
        )


async def test_llm_node_rejects_unsupported_provider() -> None:
    with pytest.raises(LLMProviderError, match="Unsupported AI provider"):
        await llm_node(
            {
                "ai_provider": "cohere",
                "ai_api_key": "sk-test",
                "messages": [{"role": "user", "content": "hello"}],
            }
        )


def _client(completions):
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def _stream_content(pieces: list[str]):
    chunks = [
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=p, tool_calls=None))])
        for p in pieces
    ]
    return _async_iter(chunks)


def _stream_tool_call(*, call_id: str, name: str, arguments: str):
    tc = SimpleNamespace(
        index=0,
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )
    chunk = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=None, tool_calls=[tc]))]
    )
    return _async_iter([chunk])


def _async_iter(items: list):
    async def gen():
        for item in items:
            yield item
    return gen()
