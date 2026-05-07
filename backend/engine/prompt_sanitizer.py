MAX_SYSTEM_TOKENS = 6000


class PromptDensity:
    def __init__(self, total_tokens: int) -> None:
        self.total_tokens = total_tokens
        self.is_valid = total_tokens <= MAX_SYSTEM_TOKENS
        self.utilization = round(total_tokens / MAX_SYSTEM_TOKENS, 4)


class PromptSanitizer:
    def _count_tokens(self, text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            return len(text) // 4

    def measure(self, prompt: str) -> PromptDensity:
        return PromptDensity(total_tokens=self._count_tokens(prompt))

    def validate(self, prompt: str) -> PromptDensity:
        density = self.measure(prompt)
        if not density.is_valid:
            raise ValueError(
                f"System prompt exceeds {MAX_SYSTEM_TOKENS} tokens "
                f"({density.total_tokens} used). Reduce core_prompt or deactivate tools/skills."
            )
        return density
