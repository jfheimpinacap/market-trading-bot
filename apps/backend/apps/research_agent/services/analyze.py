from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.llm_local.clients import OllamaChatClient
from apps.llm_local.config import get_llm_local_settings
from apps.llm_local.errors import LlmLocalError
from apps.llm_local.services.embeddings import embed_text
from apps.research_agent.models import NarrativeAnalysis, NarrativeAnalysisStatus, NarrativeItem, NarrativeSentiment

SYSTEM_PROMPT = (
    'You are a narrative research extractor for prediction markets. Return strict JSON with keys: '
    'summary (string), sentiment (bullish|bearish|neutral|mixed|uncertain), confidence (0..1 number), '
    'entities (array of strings), topics (array of strings), market_relevance_score (0..1 number), '
    'social_signal_strength (0..1 number), hype_risk (0..1 number), noise_risk (0..1 number), market_implication (string).'
)


@dataclass
class AnalysisResult:
    analyzed: int = 0
    degraded: int = 0
    errors: list[str] | None = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def _heuristic_sentiment(text: str) -> str:
    text_lower = text.lower()
    bullish_words = ('surge', 'beat', 'growth', 'approval', 'win', 'up')
    bearish_words = ('drop', 'miss', 'decline', 'ban', 'loss', 'down')
    bullish_hits = sum(1 for token in bullish_words if token in text_lower)
    bearish_hits = sum(1 for token in bearish_words if token in text_lower)
    if bullish_hits > bearish_hits:
        return NarrativeSentiment.BULLISH
    if bearish_hits > bullish_hits:
        return NarrativeSentiment.BEARISH
    return NarrativeSentiment.NEUTRAL


def _normalize_payload(payload: dict, text: str) -> dict:
    sentiment = str(payload.get('sentiment') or NarrativeSentiment.UNCERTAIN).strip().lower()
    if sentiment not in NarrativeSentiment.values:
        sentiment = NarrativeSentiment.UNCERTAIN

    confidence = min(max(float(payload.get('confidence', 0.3)), 0.0), 1.0)
    relevance = min(max(float(payload.get('market_relevance_score', 0.25)), 0.0), 1.0)
    entities = [str(value).strip() for value in (payload.get('entities') or []) if str(value).strip()][:12]
    topics = [str(value).strip() for value in (payload.get('topics') or []) if str(value).strip()][:12]
    summary = str(payload.get('summary') or text[:220]).strip()
    implication = str(payload.get('market_implication') or '').strip()
    social_signal_strength = min(max(float(payload.get('social_signal_strength', 0.3)), 0.0), 1.0)
    hype_risk = min(max(float(payload.get('hype_risk', 0.25)), 0.0), 1.0)
    noise_risk = min(max(float(payload.get('noise_risk', 0.25)), 0.0), 1.0)
    return {
        'summary': summary,
        'sentiment': sentiment,
        'confidence': Decimal(f'{confidence:.4f}'),
        'entities': entities,
        'topics': topics,
        'market_relevance_score': Decimal(f'{relevance:.4f}'),
        'market_implication': implication,
        'social_signal_strength': Decimal(f'{social_signal_strength:.4f}'),
        'hype_risk': Decimal(f'{hype_risk:.4f}'),
        'noise_risk': Decimal(f'{noise_risk:.4f}'),
    }


def run_narrative_analysis(*, item_ids: list[int] | None = None) -> AnalysisResult:
    queryset = NarrativeItem.objects.order_by('-ingested_at')
    if item_ids:
        queryset = queryset.filter(id__in=item_ids)

    result = AnalysisResult()
    llm_settings = get_llm_local_settings()
    chat_client = OllamaChatClient()

    for item in queryset[:100]:
        if hasattr(item, 'analysis') and item.analysis.analysis_status == NarrativeAnalysisStatus.COMPLETE:
            continue

        text = (item.raw_text or item.snippet or item.title)[:6000]
        payload = {}
        status = NarrativeAnalysisStatus.COMPLETE
        error_note = ''

        if llm_settings.enabled:
            try:
                payload = chat_client.chat_json(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=(
                        'Extract structured narrative signals from this article for prediction market research.\n\n'
                        f'Title: {item.title}\nURL: {item.url}\nText:\n{text}'
                    ),
                    schema_hint='NarrativeAnalysis',
                )
            except LlmLocalError as exc:
                status = NarrativeAnalysisStatus.DEGRADED
                error_note = str(exc)
        else:
            status = NarrativeAnalysisStatus.DEGRADED
            error_note = 'LLM disabled by configuration.'

        if not payload:
            payload = {
                'summary': text[:220],
                'sentiment': _heuristic_sentiment(text),
                'confidence': 0.35,
                'entities': [],
                'topics': [],
                'market_relevance_score': 0.2,
                'social_signal_strength': 0.22,
                'hype_risk': 0.28,
                'noise_risk': 0.3,
            }

        normalized = _normalize_payload(payload, text)
        metadata = {
            'market_implication': normalized['market_implication'],
            'social_signal_strength': float(normalized['social_signal_strength']),
            'hype_risk': float(normalized['hype_risk']),
            'noise_risk': float(normalized['noise_risk']),
            'source_type': item.source.source_type,
        }
        if error_note:
            metadata['degraded_reason'] = error_note
            result.degraded += 1

        try:
            vector = embed_text(f"{item.title}\n{normalized['summary']}")
            metadata['summary_embedding'] = {'dim': len(vector), 'preview': vector[:8]}
        except Exception as exc:  # pragma: no cover - optional embedding path
            metadata['embedding_error'] = str(exc)

        NarrativeAnalysis.objects.update_or_create(
            narrative_item=item,
            defaults={
                'summary': normalized['summary'],
                'sentiment': normalized['sentiment'],
                'confidence': normalized['confidence'],
                'entities': normalized['entities'],
                'topics': normalized['topics'],
                'market_relevance_score': normalized['market_relevance_score'],
                'analysis_status': status,
                'model_name': llm_settings.chat_model if llm_settings.enabled else 'heuristic-fallback',
                'metadata': metadata,
            },
        )
        result.analyzed += 1

    return result
