from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from engine.prompt_schema import PromptDensity, SystemPrompt

logger = logging.getLogger(__name__)

MAX_SYSTEM_TOKENS = 6000
WARNING_RATIO = 0.60
CRITICAL_RATIO = 0.80
WARNING_SCORE = 22
CRITICAL_SCORE = 35

_SENTENCE_SPLITTER = re.compile(r"[.!?;\n]+")
_WHITESPACE = re.compile(r"\s+")
_IMPERATIVE_PATTERNS = (
    re.compile(r"\b(always|never|must|must not|do not|don't|should|cannot|required|require)\b", re.I),
    re.compile(r"\b(sempre|nunca|deve|nao deve|não deve|nao|não|obrigatorio|obrigatório)\b", re.I),
)
_CONFLICT_PATTERNS = (
    (re.compile(r"\b(?:always|must|should)\s+(.+)", re.I), re.compile(r"\b(?:never|must not|do not|don't|cannot)\s+(.+)", re.I)),
    (re.compile(r"\b(?:sempre|deve)\s+(.+)", re.I), re.compile(r"\b(?:nunca|nao deve|não deve|nao|não)\s+(.+)", re.I)),
)


class PromptValidationError(Exception):
    """Raised when a composed system prompt is unsafe to cache or execute."""


@dataclass(frozen=True)
class CapabilityName:
    kind: str
    name: str


class InstructionDensityScorer:
    @staticmethod
    def score(
        *,
        capability_count: int,
        imperative_count: int,
        token_count: int,
        max_tokens: int = MAX_SYSTEM_TOKENS,
    ) -> PromptDensity:
        score_value = capability_count * 2 + imperative_count + token_count / 1000
        budget_ratio = token_count / max_tokens if max_tokens else 0
        level = _density_level(score=score_value, budget_ratio=budget_ratio, blocked=False)
        return PromptDensity(
            score=score_value,
            level=level,
            capability_count=capability_count,
            imperative_count=imperative_count,
            token_count=token_count,
            max_tokens=max_tokens,
            budget_ratio=round(budget_ratio, 4),
        )


class PromptConflictDetector:
    @staticmethod
    def duplicated_names(capabilities: list[CapabilityName]) -> dict[str, list[str]]:
        by_name: dict[str, list[str]] = {}
        for capability in capabilities:
            normalized = _normalize_name(capability.name)
            if not normalized:
                continue
            by_name.setdefault(normalized, []).append(capability.kind)
        return {name: kinds for name, kinds in by_name.items() if len(kinds) > 1}

    @staticmethod
    def explicit_instruction_conflicts(prompt_text: str) -> list[str]:
        sentences = _split_sentences(prompt_text)
        conflicts: list[str] = []
        for positive_pattern, negative_pattern in _CONFLICT_PATTERNS:
            positive = {_normalize_instruction(match.group(1)) for item in sentences if (match := positive_pattern.search(item))}
            negative = {_normalize_instruction(match.group(1)) for item in sentences if (match := negative_pattern.search(item))}
            for instruction in sorted((positive & negative) - {""}):
                conflicts.append(instruction)
        return conflicts


class PromptSanitizer:
    def validate(
        self,
        prompt: SystemPrompt | str,
        metadata: dict[str, Any] | None = None,
    ) -> SystemPrompt:
        system_prompt = _coerce_prompt(prompt)
        density = self.measure(system_prompt, metadata=metadata)

        if density.token_count > MAX_SYSTEM_TOKENS:
            raise PromptValidationError(
                f"System prompt exceeds {MAX_SYSTEM_TOKENS} tokens "
                f"({density.token_count} used). Reduce core_prompt or deactivate tools/skills."
            )

        capabilities = _extract_capabilities(metadata or {})
        duplicates = PromptConflictDetector.duplicated_names(capabilities)
        if duplicates:
            duplicate_list = ", ".join(
                f"{name} ({'/'.join(sorted(kinds))})"
                for name, kinds in sorted(duplicates.items())
            )
            raise PromptValidationError(f"Duplicate tool/skill/handoff names detected: {duplicate_list}")

        conflicts = PromptConflictDetector.explicit_instruction_conflicts(system_prompt.full)
        if conflicts:
            raise PromptValidationError(f"Conflicting prompt instructions detected: {', '.join(conflicts)}")

        self._emit_alert(density)
        return system_prompt.model_copy(update={"density": density})

    def measure(self, prompt: SystemPrompt | str, metadata: dict[str, Any] | None = None) -> PromptDensity:
        system_prompt = _coerce_prompt(prompt)
        capabilities = _extract_capabilities(metadata or {})
        token_count = self._count_tokens(system_prompt.full)
        return InstructionDensityScorer.score(
            capability_count=len(capabilities),
            imperative_count=_count_instruction_markers(system_prompt.full),
            token_count=token_count,
            max_tokens=MAX_SYSTEM_TOKENS,
        )

    def _count_tokens(self, text: str) -> int:
        try:
            import tiktoken

            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def _emit_alert(self, density: PromptDensity) -> None:
        if density.level not in {"warning", "critical"}:
            return
        logger.warning(
            "prompt_validation_alert",
            extra={
                "event": "prompt_validation_alert",
                "level": density.level,
                "code": "prompt_density_high" if density.level == "critical" else "prompt_density_warning",
                "token_count": density.token_count,
                "max_tokens": density.max_tokens,
                "budget_ratio": density.budget_ratio,
                "density": density.model_dump(),
            },
        )


def _coerce_prompt(prompt: SystemPrompt | str) -> SystemPrompt:
    if isinstance(prompt, SystemPrompt):
        return prompt
    return SystemPrompt(core=prompt, full=prompt)


def _extract_capabilities(metadata: dict[str, Any]) -> list[CapabilityName]:
    capabilities: list[CapabilityName] = []
    for skill in metadata.get("skills", []) or []:
        if name := _extract_callable_name(skill, schema_attrs=("tool_schema", "schema", "schema_")):
            capabilities.append(CapabilityName(kind="skill", name=name))
    for tool in metadata.get("tools", []) or []:
        if name := _extract_callable_name(tool, schema_attrs=("schema_", "schema", "tool_schema")):
            capabilities.append(CapabilityName(kind="tool", name=name))
    for link in metadata.get("linked_agents", []) or []:
        name = _get_value(link, "transfer_tool_name")
        if name:
            capabilities.append(CapabilityName(kind="handoff", name=str(name)))
    return capabilities


def _extract_callable_name(item: Any, *, schema_attrs: tuple[str, ...]) -> str:
    for attr in schema_attrs:
        schema = _get_value(item, attr)
        if isinstance(schema, dict) and schema.get("name"):
            return str(schema["name"])
    for attr in ("slug", "name"):
        value = _get_value(item, attr)
        if value:
            return str(value)
    return ""


def _get_value(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _count_instruction_markers(text: str) -> int:
    sentences = _split_sentences(text)
    explicit = sum(1 for item in sentences if any(pattern.search(item) for pattern in _IMPERATIVE_PATTERNS))
    return max(explicit, len(sentences))


def _split_sentences(text: str) -> list[str]:
    return [item.strip() for item in _SENTENCE_SPLITTER.split(text) if item.strip()]


def _density_level(*, score: float, budget_ratio: float, blocked: bool) -> str:
    if blocked:
        return "blocked"
    if score >= CRITICAL_SCORE or budget_ratio >= CRITICAL_RATIO:
        return "critical"
    if score >= WARNING_SCORE or budget_ratio >= WARNING_RATIO:
        return "warning"
    return "ok"


def _normalize_name(name: str) -> str:
    return _WHITESPACE.sub("_", name.strip().lower())


def _normalize_instruction(instruction: str) -> str:
    normalized = instruction.strip().lower()
    normalized = re.sub(r"[`*_\"']", "", normalized)
    normalized = re.sub(r"\b(the|a|an|o|a|os|as|um|uma)\b", "", normalized)
    normalized = _WHITESPACE.sub(" ", normalized)
    return normalized.strip(" .,:;-")
