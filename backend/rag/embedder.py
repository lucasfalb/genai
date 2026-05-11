import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger("rag.embedder")


class EmbedderError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmbeddingResult:
    embeddings: list[list[float]]
    prompt_tokens: int = 0
    total_tokens: int = 0


class OpenAIEmbedder:
    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.openai_embedding_api_key or settings.openai_api_key
        self.model = model or settings.embedding_model
        if not self.api_key:
            raise EmbedderError("OpenAI embedding API key is not configured")
        self.client = AsyncOpenAI(api_key=self.api_key)
        logger.info("Embedder initialized | model=%s", self.model)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        result = await self.embed_texts_with_usage(texts)
        return result.embeddings

    async def embed_texts_with_usage(self, texts: list[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(embeddings=[])
        logger.debug("Calling embeddings API | texts=%d model=%s", len(texts), self.model)
        response = await self.client.embeddings.create(model=self.model, input=texts)
        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", 0) or 0)
        logger.debug(
            "Embeddings received | count=%d dim=%d prompt_tokens=%d",
            len(response.data), len(response.data[0].embedding), prompt_tokens,
        )
        return EmbeddingResult(
            embeddings=[item.embedding for item in response.data],
            prompt_tokens=prompt_tokens,
            total_tokens=total_tokens,
        )
