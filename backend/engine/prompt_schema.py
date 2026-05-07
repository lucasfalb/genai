from pydantic import BaseModel


class SystemPrompt(BaseModel):
    core: str
    tool_instructions: str = ""
    constraints: str = ""
    full: str


class PromptDensity(BaseModel):
    score: float
    level: str  # "low" | "medium" | "high" | "critical"
    capability_count: int
    imperative_count: int
    token_count: int
