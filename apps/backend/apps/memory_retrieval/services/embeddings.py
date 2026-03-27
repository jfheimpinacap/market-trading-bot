from __future__ import annotations

from math import sqrt

from django.conf import settings
from django.utils import timezone

from apps.llm_local.services.embeddings import embed_text
from apps.memory_retrieval.models import MemoryDocument


def get_embedding_model_name() -> str:
    return getattr(settings, 'OLLAMA_EMBED_MODEL', 'local-embedding-model')


def ensure_document_embedding(document: MemoryDocument, force: bool = False) -> MemoryDocument:
    model_name = get_embedding_model_name()
    if not force and document.embedding and document.embedding_model == model_name:
        return document
    vector = embed_text(document.text_content)
    document.embedding = vector
    document.embedding_model = model_name
    document.embedded_at = timezone.now()
    document.save(update_fields=['embedding', 'embedding_model', 'embedded_at', 'updated_at'])
    return document


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sqrt(sum(a * a for a in vec_a))
    norm_b = sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
