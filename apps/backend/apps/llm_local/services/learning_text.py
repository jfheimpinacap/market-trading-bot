from __future__ import annotations

from apps.learning_memory.models import LearningMemoryEntry
from apps.llm_local.clients import OllamaChatClient
from apps.llm_local.prompts.learning import LEARNING_SYSTEM_PROMPT, build_learning_prompt
from apps.llm_local.schemas import LearningNoteResult


def _build_context(data: dict) -> tuple[str, str, str, int | None]:
    memory_entry_id = data.get('memory_entry_id')
    if memory_entry_id:
        memory_entry = LearningMemoryEntry.objects.get(pk=memory_entry_id)
        return memory_entry.summary, memory_entry.rationale, memory_entry.outcome, memory_entry.id

    return data.get('summary', ''), data.get('rationale', ''), data.get('outcome', ''), None


def enrich_learning_note(data: dict) -> dict:
    summary, rationale, outcome, memory_entry_id = _build_context(data)
    prompt = build_learning_prompt(summary=summary, rationale=rationale, outcome=outcome)
    payload = OllamaChatClient().chat_json(
        system_prompt=LEARNING_SYSTEM_PROMPT,
        user_prompt=prompt,
        schema_hint='LearningNoteResult',
    )
    result = LearningNoteResult.from_payload(payload)
    return {
        'memory_entry_id': memory_entry_id,
        'result': {
            'note_title': result.note_title,
            'note_body': result.note_body,
            'tags': result.tags,
            'suggested_follow_up': result.suggested_follow_up,
        },
    }
