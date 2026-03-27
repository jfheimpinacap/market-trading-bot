from __future__ import annotations

from apps.llm_local.services.embeddings import embed_text
from apps.memory_retrieval.models import MemoryDocument, MemoryQueryType, MemoryRetrievalRun, RetrievedPrecedent
from apps.memory_retrieval.services.embeddings import cosine_similarity


def _reason_for_match(doc: MemoryDocument, score: float) -> str:
    if score >= 0.84:
        sim = 'high similarity'
    elif score >= 0.74:
        sim = 'medium similarity'
    else:
        sim = 'low similarity'
    return f'{sim} with {doc.document_type} from {doc.source_app}'


def retrieve_precedents(*, query_text: str, query_type: str = MemoryQueryType.MANUAL, context_metadata: dict | None = None, limit: int = 8, min_similarity: float = 0.55) -> MemoryRetrievalRun:
    run = MemoryRetrievalRun.objects.create(
        query_text=query_text,
        query_type=query_type,
        context_metadata=context_metadata or {},
        result_count=0,
    )
    query_embedding = embed_text(query_text)
    candidates: list[tuple[float, MemoryDocument]] = []
    for doc in MemoryDocument.objects.exclude(embedding=[]):
        score = cosine_similarity(query_embedding, doc.embedding)
        if score >= min_similarity:
            candidates.append((score, doc))

    candidates.sort(key=lambda item: item[0], reverse=True)
    for rank, (score, doc) in enumerate(candidates[:limit], start=1):
        RetrievedPrecedent.objects.create(
            retrieval_run=run,
            memory_document=doc,
            similarity_score=score,
            rank=rank,
            short_reason=_reason_for_match(doc, score),
        )

    run.result_count = min(len(candidates), limit)
    run.metadata = {'min_similarity': min_similarity, 'candidate_count': len(candidates), 'limit': limit}
    run.save(update_fields=['result_count', 'metadata', 'updated_at'])
    return run
