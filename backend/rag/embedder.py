import logging

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger("rag.embedder")


class EmbedderError(RuntimeError):
    pass


class OpenAIEmbedder:
    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.openai_embedding_api_key or settings.openai_api_key
        self.model = model or settings.embedding_model
        if not self.api_key:
            raise EmbedderError("OpenAI embedding API key is not configured")
        self.client = AsyncOpenAI(api_key=self.api_key)
        logger.info("Embedder initialized | model=%s", self.model)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        logger.debug("Calling embeddings API | texts=%d model=%s", len(texts), self.model)
        response = await self.client.embeddings.create(model=self.model, input=texts)
        logger.debug("Embeddings received | count=%d dim=%d", len(response.data), len(response.data[0].embedding))
        return [item.embedding for item in response.data]
