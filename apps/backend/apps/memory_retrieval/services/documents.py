from __future__ import annotations

from apps.experiment_lab.models import ExperimentRun
from apps.learning_memory.models import LearningMemoryEntry
from apps.memory_retrieval.models import MemoryDocument, MemoryDocumentType
from apps.position_manager.models import PositionLifecycleDecision
from apps.postmortem_agents.models import PostmortemAgentReview, PostmortemBoardConclusion
from apps.postmortem_demo.models import TradeReview
from apps.replay_lab.models import ReplayRun


def _upsert_document(*, document_type: str, source_app: str, source_object_id: str, title: str, text_content: str, structured_summary: dict, tags: list[str], metadata: dict) -> tuple[MemoryDocument, bool]:
    return MemoryDocument.objects.update_or_create(
        document_type=document_type,
        source_app=source_app,
        source_object_id=source_object_id,
        defaults={
            'title': title,
            'text_content': text_content,
            'structured_summary': structured_summary,
            'tags': tags,
            'metadata': metadata,
        },
    )


def sync_learning_notes(limit: int = 200) -> int:
    total = 0
    for entry in LearningMemoryEntry.objects.select_related('market', 'provider').order_by('-created_at', '-id')[:limit]:
        _, _ = _upsert_document(
            document_type=MemoryDocumentType.LEARNING_NOTE,
            source_app='learning_memory',
            source_object_id=str(entry.id),
            title=f'Learning note #{entry.id}: {entry.summary[:80]}',
            text_content=f"{entry.summary}\nOutcome: {entry.outcome}\nRationale: {entry.rationale}",
            structured_summary={
                'memory_type': entry.memory_type,
                'outcome': entry.outcome,
                'score_delta': str(entry.score_delta),
                'confidence_delta': str(entry.confidence_delta),
            },
            tags=[entry.memory_type, entry.outcome],
            metadata={'provider': entry.provider.slug if entry.provider else None, 'market': entry.market.slug if entry.market else None},
        )
        total += 1
    return total


def sync_postmortem_conclusions(limit: int = 200) -> int:
    total = 0
    for conclusion in PostmortemBoardConclusion.objects.select_related('board_run__related_trade_review__market').order_by('-created_at', '-id')[:limit]:
        review = conclusion.board_run.related_trade_review
        _, _ = _upsert_document(
            document_type=MemoryDocumentType.POSTMORTEM_CONCLUSION,
            source_app='postmortem_board',
            source_object_id=str(conclusion.id),
            title=f'Postmortem conclusion #{conclusion.id}: {conclusion.primary_failure_mode}',
            text_content=f"Lesson: {conclusion.lesson_learned}\nPrimary failure mode: {conclusion.primary_failure_mode}",
            structured_summary={
                'severity': conclusion.severity,
                'primary_failure_mode': conclusion.primary_failure_mode,
                'secondary_failure_modes': conclusion.secondary_failure_modes,
                'recommended_adjustments': conclusion.recommended_adjustments,
            },
            tags=['postmortem', conclusion.severity, conclusion.primary_failure_mode],
            metadata={'review_id': review.id, 'market_slug': review.market.slug if review.market_id else None},
        )
        total += 1
    return total


def sync_postmortem_perspectives(limit: int = 400) -> int:
    total = 0
    for review in PostmortemAgentReview.objects.select_related('board_run').order_by('-created_at', '-id')[:limit]:
        _, _ = _upsert_document(
            document_type=MemoryDocumentType.POSTMORTEM_PERSPECTIVE,
            source_app='postmortem_board',
            source_object_id=str(review.id),
            title=f'Perspective {review.perspective_type} #{review.id}',
            text_content=f"Conclusion: {review.conclusion}\nFindings: {review.key_findings}",
            structured_summary={
                'status': review.status,
                'perspective_type': review.perspective_type,
                'recommended_actions': review.recommended_actions,
                'confidence': str(review.confidence),
            },
            tags=['postmortem', review.perspective_type, review.status.lower()],
            metadata={'board_run_id': review.board_run_id},
        )
        total += 1
    return total


def sync_trade_reviews(limit: int = 200) -> int:
    total = 0
    for review in TradeReview.objects.select_related('market').order_by('-reviewed_at', '-id')[:limit]:
        _, _ = _upsert_document(
            document_type=MemoryDocumentType.TRADE_REVIEW,
            source_app='postmortem_demo',
            source_object_id=str(review.id),
            title=f'Trade review #{review.id} {review.outcome}',
            text_content=f"Summary: {review.summary}\nLesson: {review.lesson}\nRecommendation: {review.recommendation}",
            structured_summary={'outcome': review.outcome, 'score': str(review.score), 'pnl_estimate': str(review.pnl_estimate)},
            tags=['trade_review', review.outcome.lower()],
            metadata={'market_slug': review.market.slug},
        )
        total += 1
    return total


def sync_replay_runs(limit: int = 120) -> int:
    total = 0
    for run in ReplayRun.objects.order_by('-created_at', '-id')[:limit]:
        _, _ = _upsert_document(
            document_type=MemoryDocumentType.REPLAY_SUMMARY,
            source_app='replay_lab',
            source_object_id=str(run.id),
            title=f'Replay #{run.id} {run.status}',
            text_content=f"Summary: {run.summary}\nProvider scope: {run.provider_scope}\nBlocked: {run.blocked_count}\nPNL: {run.total_pnl}",
            structured_summary={'status': run.status, 'source_scope': run.source_scope, 'blocked_count': run.blocked_count, 'total_pnl': str(run.total_pnl)},
            tags=['replay', run.status.lower(), run.source_scope],
            metadata={'markets_considered': run.markets_considered, 'trades_executed': run.trades_executed},
        )
        total += 1
    return total


def sync_experiment_runs(limit: int = 120) -> int:
    total = 0
    for run in ExperimentRun.objects.select_related('strategy_profile').order_by('-created_at', '-id')[:limit]:
        _, _ = _upsert_document(
            document_type=MemoryDocumentType.EXPERIMENT_RESULT,
            source_app='experiment_lab',
            source_object_id=str(run.id),
            title=f'Experiment #{run.id} {run.run_type}',
            text_content=f"Summary: {run.summary}\nProfile: {run.strategy_profile.slug}\nStatus: {run.status}",
            structured_summary={'run_type': run.run_type, 'status': run.status, 'normalized_metrics': run.normalized_metrics},
            tags=['experiment', run.run_type, run.status.lower(), run.strategy_profile.slug],
            metadata={'strategy_profile': run.strategy_profile.slug},
        )
        total += 1
    return total


def sync_lifecycle_decisions(limit: int = 240) -> int:
    total = 0
    for decision in PositionLifecycleDecision.objects.select_related('paper_position__market').order_by('-created_at', '-id')[:limit]:
        market_slug = decision.paper_position.market.slug if decision.paper_position_id and decision.paper_position.market_id else None
        _, _ = _upsert_document(
            document_type=MemoryDocumentType.LIFECYCLE_DECISION,
            source_app='position_manager',
            source_object_id=str(decision.id),
            title=f'Lifecycle decision #{decision.id} {decision.status}',
            text_content=f"Decision: {decision.status}\nRationale: {decision.rationale}\nReason codes: {decision.reason_codes}",
            structured_summary={'status': decision.status, 'decision_confidence': str(decision.decision_confidence), 'reason_codes': decision.reason_codes},
            tags=['lifecycle', decision.status.lower()],
            metadata={'market_slug': market_slug},
        )
        total += 1
    return total


def sync_documents(sources: list[str] | None = None) -> dict[str, int]:
    selected = set(sources or ['learning', 'postmortem', 'reviews', 'replay', 'experiments', 'lifecycle'])
    created: dict[str, int] = {}
    if 'learning' in selected:
        created['learning'] = sync_learning_notes()
    if 'postmortem' in selected:
        created['postmortem_conclusions'] = sync_postmortem_conclusions()
        created['postmortem_perspectives'] = sync_postmortem_perspectives()
    if 'reviews' in selected:
        created['trade_reviews'] = sync_trade_reviews()
    if 'replay' in selected:
        created['replay_runs'] = sync_replay_runs()
    if 'experiments' in selected:
        created['experiment_runs'] = sync_experiment_runs()
    if 'lifecycle' in selected:
        created['lifecycle_decisions'] = sync_lifecycle_decisions()
    return created
