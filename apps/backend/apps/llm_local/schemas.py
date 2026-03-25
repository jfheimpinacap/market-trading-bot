from __future__ import annotations

from dataclasses import dataclass, field

from apps.llm_local.errors import LlmResponseParseError


@dataclass
class ProposalThesisResult:
    thesis: str
    summary: str
    key_risks: list[str] = field(default_factory=list)
    confidence_note: str = ''

    @classmethod
    def from_payload(cls, payload: dict) -> 'ProposalThesisResult':
        thesis = str(payload.get('thesis', '')).strip()
        summary = str(payload.get('summary', '')).strip()
        confidence_note = str(payload.get('confidence_note', '')).strip()
        key_risks = [str(item).strip() for item in (payload.get('key_risks') or []) if str(item).strip()]
        if len(thesis) < 20 or len(summary) < 20 or len(confidence_note) < 10:
            raise LlmResponseParseError('Proposal thesis response missing required narrative detail.')
        return cls(thesis=thesis, summary=summary, key_risks=key_risks[:5], confidence_note=confidence_note)


@dataclass
class PostmortemInsightResult:
    enriched_summary: str
    lessons_learned: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict) -> 'PostmortemInsightResult':
        enriched_summary = str(payload.get('enriched_summary', '')).strip()
        lessons = [str(item).strip() for item in (payload.get('lessons_learned') or []) if str(item).strip()]
        action_items = [str(item).strip() for item in (payload.get('action_items') or []) if str(item).strip()]
        if len(enriched_summary) < 20:
            raise LlmResponseParseError('Postmortem summary response is too short.')
        return cls(enriched_summary=enriched_summary, lessons_learned=lessons[:5], action_items=action_items[:5])


@dataclass
class LearningNoteResult:
    note_title: str
    note_body: str
    tags: list[str] = field(default_factory=list)
    suggested_follow_up: str = ''

    @classmethod
    def from_payload(cls, payload: dict) -> 'LearningNoteResult':
        note_title = str(payload.get('note_title', '')).strip()
        note_body = str(payload.get('note_body', '')).strip()
        suggested_follow_up = str(payload.get('suggested_follow_up', '')).strip()
        tags = [str(item).strip() for item in (payload.get('tags') or []) if str(item).strip()]
        if len(note_title) < 5 or len(note_body) < 20 or len(suggested_follow_up) < 10:
            raise LlmResponseParseError('Learning note response missing required fields.')
        return cls(note_title=note_title, note_body=note_body, tags=tags[:8], suggested_follow_up=suggested_follow_up)


@dataclass
class ResearchSummaryResult:
    topic: str
    narrative_summary: str
    key_points: list[str] = field(default_factory=list)
    sentiment: str = 'neutral'

    @classmethod
    def from_payload(cls, payload: dict) -> 'ResearchSummaryResult':
        topic = str(payload.get('topic', '')).strip()
        narrative_summary = str(payload.get('narrative_summary', '')).strip()
        key_points = [str(item).strip() for item in (payload.get('key_points') or []) if str(item).strip()]
        sentiment = str(payload.get('sentiment', 'neutral')).strip() or 'neutral'
        if len(topic) < 3 or len(narrative_summary) < 20:
            raise LlmResponseParseError('Research summary missing required topic/body.')
        return cls(topic=topic, narrative_summary=narrative_summary, key_points=key_points[:8], sentiment=sentiment)
