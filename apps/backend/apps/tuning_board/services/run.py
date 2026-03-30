from collections import Counter

from django.utils import timezone

from apps.evaluation_lab.models import EffectivenessMetricStatus, EvaluationRuntimeRun
from apps.tuning_board.models import TuningImpactHypothesis, TuningReviewRun
from apps.tuning_board.services.bundling import build_bundles
from apps.tuning_board.services.evidence_scoring import score_evidence
from apps.tuning_board.services.proposal_derivation import derive_tuning_candidates
from apps.tuning_board.services.recommendation import build_recommendations


def run_tuning_review(*, evaluation_run: EvaluationRuntimeRun | None = None, metadata: dict | None = None) -> TuningReviewRun:
    linked_eval = evaluation_run or EvaluationRuntimeRun.objects.order_by('-started_at', '-id').first()
    run = TuningReviewRun.objects.create(
        started_at=timezone.now(),
        linked_evaluation_run=linked_eval,
        metadata={**(metadata or {}), 'manual_first': True, 'auto_apply': False, 'paper_only': True},
    )
    if linked_eval is None:
        run.completed_at = timezone.now()
        run.save(update_fields=['completed_at'])
        return run

    candidates = derive_tuning_candidates(linked_eval)
    scored = [score_evidence(candidate) for candidate in candidates]

    for payload in scored:
        proposal = run.proposals.create(
            proposal_type=payload['proposal_type'],
            target_scope=payload.get('target_scope', 'global'),
            target_component=payload['target_component'],
            target_value=payload.get('target_value', ''),
            current_value=payload.get('current_value'),
            proposed_value=payload.get('proposed_value'),
            proposal_status=payload['proposal_status'],
            evidence_strength_score=payload['evidence_strength_score'],
            priority_level=payload['priority_level'],
            rationale=payload['rationale'],
            reason_codes=payload.get('reason_codes', []),
            blockers=payload.get('blockers', []),
            linked_metrics=[payload['source_metric'].id] if payload.get('source_metric') else [],
            linked_recommendations=[payload['source_recommendation'].id] if payload.get('source_recommendation') else [],
            source_metric=payload.get('source_metric'),
            source_recommendation=payload.get('source_recommendation'),
            metadata={'source': 'evaluation_lab', 'manual_apply_required': True},
        )
        _create_hypothesis(proposal)

    build_bundles(run)
    build_recommendations(run)

    metrics = linked_eval.effectiveness_metrics.all()
    run.metrics_reviewed_count = metrics.count()
    run.poor_metric_count = metrics.filter(status=EffectivenessMetricStatus.POOR).count()
    run.drift_flag_count = linked_eval.drift_flag_count
    run.proposal_count = run.proposals.count()
    run.high_priority_proposal_count = run.proposals.filter(priority_level__in=['HIGH', 'CRITICAL']).count()
    run.recommendation_summary = dict(Counter(run.recommendations.values_list('recommendation_type', flat=True)))
    run.completed_at = timezone.now()
    run.save()

    return run


def build_tuning_summary() -> dict:
    latest = TuningReviewRun.objects.order_by('-started_at', '-id').first()
    if latest is None:
        return {
            'latest_run': None,
            'metrics_reviewed': 0,
            'proposals_generated': 0,
            'ready_for_review': 0,
            'need_more_data': 0,
            'bundled_proposals': 0,
            'critical_priority': 0,
        }

    proposals = latest.proposals.all()
    return {
        'latest_run': latest,
        'metrics_reviewed': latest.metrics_reviewed_count,
        'proposals_generated': proposals.count(),
        'ready_for_review': proposals.filter(proposal_status='READY_FOR_REVIEW').count(),
        'need_more_data': proposals.filter(proposal_status='WATCH').count(),
        'bundled_proposals': latest.bundles.count(),
        'critical_priority': proposals.filter(priority_level='CRITICAL').count(),
    }


def _create_hypothesis(proposal):
    mapping = {
        'calibration_bias_offset': ('improve_calibration', 'decrease', 'calibration_error'),
        'prediction_confidence_threshold': ('reduce_overconfidence', 'decrease', 'brier_score'),
        'prediction_edge_threshold': ('reduce_false_positives', 'decrease', 'edge_capture_rate'),
        'risk_gate_threshold': ('tighten_risk_gate', 'decrease', 'risk_approval_precision'),
        'shortlist_threshold': ('reduce_false_negatives', 'increase', 'shortlist_conversion_rate'),
        'learning_caution_weight': ('improve_watch_precision', 'stabilize', 'watchlist_hit_rate'),
    }
    hypothesis_type, direction, metric_type = mapping.get(
        proposal.proposal_type,
        ('improve_watch_precision', 'stabilize', proposal.source_metric.metric_type if proposal.source_metric else 'calibration_error'),
    )

    TuningImpactHypothesis.objects.create(
        proposal=proposal,
        hypothesis_type=hypothesis_type,
        expected_direction=direction,
        target_metric_type=metric_type,
        expected_effect_size=min(0.25, float(proposal.evidence_strength_score) * 0.3),
        rationale='Conservative impact hypothesis derived from proposal rationale and supporting metrics.',
        metadata={'manual_validation_required': True},
    )
