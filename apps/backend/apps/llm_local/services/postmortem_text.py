from __future__ import annotations

from apps.llm_local.clients import OllamaChatClient
from apps.llm_local.prompts.postmortem import POSTMORTEM_SYSTEM_PROMPT, build_postmortem_prompt
from apps.llm_local.schemas import PostmortemInsightResult
from apps.postmortem_demo.models import TradeReview


def _build_context(data: dict) -> tuple[str, str, str, str, int | None]:
    review_id = data.get('review_id')
    if review_id:
        review = TradeReview.objects.get(pk=review_id)
        return review.summary, review.rationale, review.lesson, review.recommendation, review.id

    return (
        data.get('summary', ''),
        data.get('rationale', ''),
        data.get('lesson', ''),
        data.get('recommendation', ''),
        None,
    )


def enrich_postmortem_summary(data: dict) -> dict:
    summary, rationale, lesson, recommendation, review_id = _build_context(data)
    prompt = build_postmortem_prompt(summary=summary, rationale=rationale, lesson=lesson, recommendation=recommendation)
    payload = OllamaChatClient().chat_json(
        system_prompt=POSTMORTEM_SYSTEM_PROMPT,
        user_prompt=prompt,
        schema_hint='PostmortemInsightResult',
    )
    result = PostmortemInsightResult.from_payload(payload)
    return {
        'review_id': review_id,
        'result': {
            'enriched_summary': result.enriched_summary,
            'lessons_learned': result.lessons_learned,
            'action_items': result.action_items,
        },
    }
