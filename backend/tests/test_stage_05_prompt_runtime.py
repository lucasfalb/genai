import pytest

from engine.prompt_builder import PromptBuilder
from engine.prompt_sanitizer import MAX_SYSTEM_TOKENS, PromptSanitizer, PromptValidationError
from engine.prompt_schema import PromptDensity


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


def test_prompt_builder_with_instruction_blocks_and_guardrails():
    sp = PromptBuilder.assemble(
        core_prompt="Core.",
        instruction_blocks=[
            {
                "id": "late",
                "topic": "tone",
                "title": "Late",
                "content": "Use friendly tone.",
                "priority": 20,
                "is_enabled": True,
            },
            {
                "id": "early",
                "topic": "scope",
                "title": "Early",
                "content": "Answer only product questions.",
                "priority": 10,
                "is_enabled": True,
            },
        ],
        guardrails=[
            {
                "id": "safe",
                "category": "safety",
                "rule": "Never provide legal advice.",
                "severity": "blocking",
                "is_enabled": True,
            }
        ],
        skills=[],
        tools=[],
    )

    assert sp.full.index("Answer only product questions.") < sp.full.index("Use friendly tone.")
    assert "### Guardrails Customizados" in sp.full
    assert "[blocking] safety: Never provide legal advice." in sp.full


# ---------------------------------------------------------------------------
# PromptSanitizer
# ---------------------------------------------------------------------------

def test_prompt_sanitizer_valid_prompt():
    prompt = "You are a helpful assistant."
    validated = PromptSanitizer().validate(prompt)
    assert validated.density is not None
    assert isinstance(validated.density, PromptDensity)
    assert validated.density.level in ("ok", "warning", "critical")
    assert validated.density.token_count > 0
    assert validated.density.score > 0


def test_prompt_sanitizer_measure_returns_density():
    density = PromptSanitizer().measure("Hello world")
    assert isinstance(density, PromptDensity)
    assert density.token_count > 0


def test_prompt_sanitizer_rejects_oversized_prompt():
    oversized = "word " * (MAX_SYSTEM_TOKENS * 5)
    with pytest.raises(PromptValidationError, match="exceeds"):
        PromptSanitizer().validate(oversized)


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
