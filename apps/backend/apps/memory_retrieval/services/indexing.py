from __future__ import annotations

from apps.memory_retrieval.models import MemoryDocument
from apps.memory_retrieval.services.documents import sync_documents
from apps.memory_retrieval.services.embeddings import ensure_document_embedding


def run_indexing(*, sources: list[str] | None = None, force_reembed: bool = False) -> dict:
    indexed_by_source = sync_documents(sources=sources)
    embedded_count = 0
    total_docs = MemoryDocument.objects.count()
    queryset = MemoryDocument.objects.order_by('-updated_at', '-id')
    for doc in queryset:
        had_embedding = bool(doc.embedding)
        ensure_document_embedding(doc, force=force_reembed)
        if force_reembed or not had_embedding:
            embedded_count += 1

    return {
        'indexed_by_source': indexed_by_source,
        'documents_total': total_docs,
        'embeddings_generated': embedded_count,
        'force_reembed': force_reembed,
    }
