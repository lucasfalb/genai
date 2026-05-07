from typing import Literal

from pydantic import BaseModel, Field


class PromptDensity(BaseModel):
    score: float
    level: Literal["ok", "warning", "critical", "blocked"]
    capability_count: int
    imperative_count: int
    token_count: int
    max_tokens: int = 6000
    budget_ratio: float = 0


class SystemPrompt(BaseModel):
    core: str
    instruction_blocks: str = ""
    tool_instructions: str = ""
    guardrails: str = ""
    constraints: str = ""
    full: str
    density: PromptDensity | None = Field(default=None)
