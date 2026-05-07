import logging
from types import SimpleNamespace

import pytest

from engine.prompt_sanitizer import (
    CRITICAL_RATIO,
    MAX_SYSTEM_TOKENS,
    WARNING_RATIO,
    InstructionDensityScorer,
    PromptConflictDetector,
    PromptSanitizer,
    PromptValidationError,
)
from engine.prompt_schema import PromptDensity, SystemPrompt


class TestInstructionDensityScorer:
    def test_score_ok_level(self):
        density = InstructionDensityScorer.score(capability_count=1, imperative_count=2, token_count=100)

        assert density.level == "ok"
        assert density.score == pytest.approx(4.1)
        assert density.max_tokens == MAX_SYSTEM_TOKENS
        assert density.budget_ratio > 0

    def test_score_warning_level_from_score(self):
        density = InstructionDensityScorer.score(capability_count=6, imperative_count=6, token_count=4000)

        assert density.level == "warning"
        assert 22 <= density.score < 35

    def test_score_critical_level_from_score(self):
        density = InstructionDensityScorer.score(capability_count=10, imperative_count=10, token_count=5000)

        assert density.level == "critical"
        assert density.score >= 35

    def test_score_critical_level_from_budget(self):
        density = InstructionDensityScorer.score(capability_count=0, imperative_count=1, token_count=5000)

        assert density.level == "critical"
        assert density.budget_ratio >= CRITICAL_RATIO


class TestPromptConflictDetector:
    def test_duplicate_names_include_kind_context(self):
        duplicates = PromptConflictDetector.duplicated_names(
            [
                SimpleNamespace(kind="tool", name="handoff_billing"),
                SimpleNamespace(kind="handoff", name="handoff_billing"),
            ]
        )

        assert duplicates == {"handoff_billing": ["tool", "handoff"]}

    def test_explicit_instruction_conflicts(self):
        conflicts = PromptConflictDetector.explicit_instruction_conflicts(
            "Always use external search. Never use external search."
        )

        assert conflicts == ["use external search"]


class TestPromptSanitizer:
    def test_validate_returns_system_prompt_with_density(self):
        prompt = SystemPrompt(core="You are helpful.", full="You are helpful.")
        validated = PromptSanitizer().validate(prompt)

        assert isinstance(validated, SystemPrompt)
        assert isinstance(validated.density, PromptDensity)
        assert validated.full == prompt.full
        assert validated.density.level == "ok"

    def test_validate_accepts_string_for_measurement_compatibility(self):
        validated = PromptSanitizer().validate("You are a helpful agent.")

        assert isinstance(validated, SystemPrompt)
        assert validated.core == "You are a helpful agent."

    def test_measure_returns_density_without_validating_conflicts(self):
        density = PromptSanitizer().measure("Always answer. Never answer.")

        assert isinstance(density, PromptDensity)
        assert density.token_count > 0

    def test_exceeds_token_limit_raises_prompt_validation_error(self, monkeypatch):
        sanitizer = PromptSanitizer()
        monkeypatch.setattr(sanitizer, "_count_tokens", lambda _: MAX_SYSTEM_TOKENS + 1)

        with pytest.raises(PromptValidationError, match="exceeds"):
            sanitizer.validate(SystemPrompt(core="Core.", full="Core."))

    def test_duplicate_tool_names_raises(self):
        metadata = {
            "tools": [
                {"schema": {"name": "search_db"}, "slug": "search_db_v1"},
                {"schema": {"name": "search_db"}, "slug": "search_db_v2"},
            ],
        }

        with pytest.raises(PromptValidationError, match="search_db"):
            PromptSanitizer().validate(SystemPrompt(core="Core.", full="Core."), metadata=metadata)

    def test_duplicate_name_across_skill_tool_and_handoff_raises(self):
        metadata = {
            "skills": [{"tool_schema": {"name": "transfer_to_billing"}, "slug": "billing_skill"}],
            "tools": [{"schema": {"name": "lookup_order"}, "slug": "lookup_order"}],
            "linked_agents": [{"transfer_tool_name": "transfer_to_billing"}],
        }

        with pytest.raises(PromptValidationError, match="transfer_to_billing"):
            PromptSanitizer().validate(SystemPrompt(core="Core.", full="Core."), metadata=metadata)

    def test_explicit_prompt_instruction_conflict_raises(self):
        prompt = SystemPrompt(
            core="Always use external search. Never use external search.",
            full="Always use external search. Never use external search.",
        )

        with pytest.raises(PromptValidationError, match="Conflicting"):
            PromptSanitizer().validate(prompt)

    def test_density_counts_skills_tools_and_handoffs(self):
        prompt = SystemPrompt(
            core="Use tools. Answer clearly.",
            full="Use tools. Answer clearly.",
        )
        metadata = {
            "skills": [{"tool_schema": {"name": "skill_a"}}],
            "tools": [{"schema": {"name": "tool_a"}}],
            "linked_agents": [{"transfer_tool_name": "handoff_a"}],
        }

        validated = PromptSanitizer().validate(prompt, metadata=metadata)

        assert validated.density is not None
        assert validated.density.capability_count == 3


class TestPromptSanitizerLogging:
    def test_warning_log_is_structured(self, caplog, monkeypatch):
        sanitizer = PromptSanitizer()
        monkeypatch.setattr(sanitizer, "_count_tokens", lambda _: int(MAX_SYSTEM_TOKENS * (WARNING_RATIO + 0.01)))
        caplog.set_level(logging.WARNING)

        sanitizer.validate(SystemPrompt(core="Core.", full="Core."))

        record = caplog.records[0]
        assert record.event == "prompt_validation_alert"
        assert record.level == "warning"
        assert record.code == "prompt_density_warning"
        assert record.token_count > 0

    def test_critical_log_is_structured(self, caplog, monkeypatch):
        sanitizer = PromptSanitizer()
        monkeypatch.setattr(sanitizer, "_count_tokens", lambda _: int(MAX_SYSTEM_TOKENS * (CRITICAL_RATIO + 0.01)))
        caplog.set_level(logging.WARNING)

        sanitizer.validate(SystemPrompt(core="Core.", full="Core."))

        record = caplog.records[0]
        assert record.event == "prompt_validation_alert"
        assert record.level == "critical"
        assert record.code == "prompt_density_high"

    def test_ok_prompt_does_not_log(self, caplog):
        caplog.set_level(logging.WARNING)

        PromptSanitizer().validate(SystemPrompt(core="Short prompt.", full="Short prompt."))

        assert not caplog.records
