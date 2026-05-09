from openai import AsyncOpenAI

from app.config import settings


class EmbedderError(RuntimeError):
    pass


class OpenAIEmbedder:
    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.openai_embedding_api_key or settings.openai_api_key
        self.model = model or settings.embedding_model
        if not self.api_key:
            raise EmbedderError("OpenAI embedding API key is not configured")
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]
