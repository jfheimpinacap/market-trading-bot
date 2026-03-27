from __future__ import annotations

from statistics import mean

from apps.memory_retrieval.models import MemoryRetrievalRun


def build_precedent_summary(run: MemoryRetrievalRun) -> dict:
    precedents = list(run.precedents.select_related('memory_document').order_by('rank'))
    by_type: dict[str, int] = {}
    caution_signals: list[str] = []
    failure_modes: list[str] = []
    lessons: list[str] = []
    scores = []

    for precedent in precedents:
        doc = precedent.memory_document
        by_type[doc.document_type] = by_type.get(doc.document_type, 0) + 1
        scores.append(precedent.similarity_score)
        if any(tag in {'negative', 'unfavorable', 'blocked', 'failed'} for tag in doc.tags):
            caution_signals.append(doc.title)
        failure = doc.structured_summary.get('primary_failure_mode')
        if isinstance(failure, str) and failure:
            failure_modes.append(failure)
        lesson = doc.structured_summary.get('lesson') or doc.structured_summary.get('lesson_learned')
        if isinstance(lesson, str) and lesson:
            lessons.append(lesson)

    return {
        'retrieval_run_id': run.id,
        'query_text': run.query_text,
        'query_type': run.query_type,
        'matches': len(precedents),
        'average_similarity': round(mean(scores), 4) if scores else None,
        'most_similar_cases': [
            {
                'rank': item.rank,
                'title': item.memory_document.title,
                'document_type': item.memory_document.document_type,
                'similarity_score': item.similarity_score,
            }
            for item in precedents[:3]
        ],
        'by_document_type': by_type,
        'prior_caution_signals': caution_signals[:5],
        'prior_failure_modes': failure_modes[:5],
        'lessons_learned': lessons[:5],
    }
