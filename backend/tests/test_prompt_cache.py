"""Tests for prompt_schema models and PromptCache interface (TASK-036)."""
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from engine.prompt_schema import PromptDensity, SystemPrompt


# ---------------------------------------------------------------------------
# SystemPrompt — round-trip serialization
# ---------------------------------------------------------------------------

def test_system_prompt_round_trip():
    sp = SystemPrompt(
        core="You are an assistant.",
        tool_instructions="Use the search tool.",
        constraints="Always respond in the user's language.",
        full="You are an assistant.\n\nUse the search tool.\n\nAlways respond in the user's language.",
    )
    serialized = sp.model_dump_json()
    recovered = SystemPrompt.model_validate_json(serialized)
    assert recovered == sp


def test_system_prompt_defaults():
    sp = SystemPrompt(core="Core.", full="Core.")
    assert sp.tool_instructions == ""
    assert sp.constraints == ""


def test_system_prompt_equality():
    a = SystemPrompt(core="x", full="x")
    b = SystemPrompt(core="x", full="x")
    assert a == b


# ---------------------------------------------------------------------------
# PromptDensity — round-trip serialization
# ---------------------------------------------------------------------------

def test_prompt_density_round_trip():
    pd = PromptDensity(
        score=22.72,
        level="warning",
        capability_count=3,
        imperative_count=5,
        token_count=850,
        max_tokens=6000,
        budget_ratio=0.1417,
    )
    recovered = PromptDensity.model_validate_json(pd.model_dump_json())
    assert recovered == pd


def test_prompt_density_levels():
    for level in ("ok", "warning", "critical", "blocked"):
        pd = PromptDensity(score=0.5, level=level, capability_count=0, imperative_count=0, token_count=100)
        assert pd.level == level


# ---------------------------------------------------------------------------
# PromptCache — key format
# ---------------------------------------------------------------------------

def test_prompt_cache_key_format():
    from engine.prompt_cache import PromptCache

    tenant_id = UUID("00000000-0000-0000-0000-000000000001")
    instance_id = UUID("00000000-0000-0000-0000-000000000002")
    key = PromptCache._key(tenant_id, instance_id)
    assert key == f"tenant:{tenant_id}:instance:{instance_id}:system_prompt"


# ---------------------------------------------------------------------------
# PromptCache — invalidate removes key
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prompt_cache_invalidate_calls_delete():
    from engine.prompt_cache import PromptCache

    tenant_id = UUID("00000000-0000-0000-0000-000000000001")
    instance_id = UUID("00000000-0000-0000-0000-000000000002")
    expected_key = PromptCache._key(tenant_id, instance_id)

    mock_redis = AsyncMock()
    with patch("engine.prompt_cache.redis_client", mock_redis):
        cache = PromptCache(connection=None)
        await cache.invalidate(tenant_id=tenant_id, instance_id=instance_id)

    mock_redis.delete.assert_awaited_once_with(expected_key)


# ---------------------------------------------------------------------------
# PromptCache — set stores JSON with TTL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prompt_cache_set_stores_json():
    from engine.prompt_cache import PromptCache

    tenant_id = UUID("00000000-0000-0000-0000-000000000001")
    instance_id = UUID("00000000-0000-0000-0000-000000000002")
    sp = SystemPrompt(core="Core.", full="Core.")

    mock_redis = AsyncMock()
    with patch("engine.prompt_cache.redis_client", mock_redis):
        cache = PromptCache(connection=None)
        await cache.set(tenant_id=tenant_id, instance_id=instance_id, prompt=sp)

    key = PromptCache._key(tenant_id, instance_id)
    mock_redis.setex.assert_awaited_once_with(key, 600, sp.model_dump_json())
