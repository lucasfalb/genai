import pytest

from engine.prompt_builder import PromptBuilder
from engine.prompt_sanitizer import MAX_SYSTEM_TOKENS, PromptDensity, PromptSanitizer


# ---------------------------------------------------------------------------
# PromptBuilder
# ---------------------------------------------------------------------------

class FakeSkill:
    def __init__(self, prompt_block: str) -> None:
        self.prompt_block = prompt_block


class FakeTool:
    def __init__(self, prompt_block: str) -> None:
        self.prompt_block = prompt_block


def test_prompt_builder_core_only():
    sp = PromptBuilder.assemble(core_prompt="You are a helpful bot.", skills=[], tools=[])
    assert sp.full.startswith("You are a helpful bot.")
    assert "### Restrições" in sp.full
    assert "### Habilidades" not in sp.full
    assert "### Ferramentas" not in sp.full


def test_prompt_builder_with_skills():
    skills = [FakeSkill("Skill one block"), FakeSkill("Skill two block")]
    sp = PromptBuilder.assemble(core_prompt="Core.", skills=skills, tools=[])
    assert "### Habilidades Disponíveis" in sp.full
    assert "Skill one block" in sp.full
    assert "Skill two block" in sp.full


def test_prompt_builder_with_tools():
    tools = [FakeTool("Tool A block")]
    sp = PromptBuilder.assemble(core_prompt="Core.", skills=[], tools=tools)
    assert "### Ferramentas Disponíveis" in sp.full
    assert "Tool A block" in sp.full


def test_prompt_builder_sandwich_order():
    skills = [FakeSkill("SKILL_BLOCK")]
    tools = [FakeTool("TOOL_BLOCK")]
    sp = PromptBuilder.assemble(core_prompt="CORE", skills=skills, tools=tools)
    core_pos = sp.full.index("CORE")
    skill_pos = sp.full.index("SKILL_BLOCK")
    tool_pos = sp.full.index("TOOL_BLOCK")
    constraint_pos = sp.full.index("### Restrições")
    assert core_pos < skill_pos < tool_pos < constraint_pos


def test_prompt_builder_strips_whitespace():
    sp = PromptBuilder.assemble(core_prompt="  Core.  ", skills=[], tools=[])
    assert sp.full.startswith("Core.")


# ---------------------------------------------------------------------------
# PromptSanitizer
# ---------------------------------------------------------------------------

def test_prompt_sanitizer_valid_prompt():
    prompt = "You are a helpful assistant."
    density = PromptSanitizer().validate(prompt)
    assert isinstance(density, PromptDensity)
    assert density.is_valid
    assert density.total_tokens > 0
    assert density.utilization < 1.0


def test_prompt_sanitizer_measure_returns_density():
    density = PromptSanitizer().measure("Hello world")
    assert isinstance(density, PromptDensity)
    assert density.total_tokens > 0


def test_prompt_sanitizer_rejects_oversized_prompt():
    oversized = "word " * (MAX_SYSTEM_TOKENS * 5)
    with pytest.raises(ValueError, match="exceeds"):
        PromptSanitizer().validate(oversized)


def test_prompt_density_utilization_range():
    density = PromptDensity(total_tokens=3000)
    assert density.is_valid
    assert 0.0 < density.utilization < 1.0


def test_prompt_density_invalid_at_limit():
    density = PromptDensity(total_tokens=MAX_SYSTEM_TOKENS + 1)
    assert not density.is_valid


# ---------------------------------------------------------------------------
# PromptCache key format
# ---------------------------------------------------------------------------

def test_prompt_cache_key_format():
    from uuid import UUID
    from engine.prompt_cache import PromptCache

    tenant_id = UUID("00000000-0000-0000-0000-000000000001")
    instance_id = UUID("00000000-0000-0000-0000-000000000002")
    key = PromptCache._key(tenant_id, instance_id)
    assert key == f"tenant:{tenant_id}:instance:{instance_id}:system_prompt"
