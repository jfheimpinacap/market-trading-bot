from apps.llm_local.clients import OllamaEmbeddingClient


def embed_text(text: str) -> list[float]:
    return OllamaEmbeddingClient().embed_text(text)


def embed_text_batch(texts: list[str]) -> list[list[float]]:
    return OllamaEmbeddingClient().embed_batch(texts)
