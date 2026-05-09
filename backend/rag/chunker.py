import tiktoken


def chunk_text(
    text: str,
    *,
    chunk_tokens: int = 512,
    overlap_tokens: int = 64,
    encoding_name: str = "cl100k_base",
) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    if chunk_tokens <= 0:
        raise ValueError("chunk_tokens must be greater than zero")
    if overlap_tokens < 0 or overlap_tokens >= chunk_tokens:
        raise ValueError("overlap_tokens must be >= 0 and smaller than chunk_tokens")

    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(normalized)
    chunks: list[str] = []
    step = chunk_tokens - overlap_tokens
    for start in range(0, len(tokens), step):
        window = tokens[start : start + chunk_tokens]
        if not window:
            break
        chunk = encoding.decode(window).strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_tokens >= len(tokens):
            break
    return chunks
