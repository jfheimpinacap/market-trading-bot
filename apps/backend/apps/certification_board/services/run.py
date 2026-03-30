from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.certification_board.models import (
    BaselineActivationCandidate,
    BaselineActivationRun,
    BaselineConfirmationCandidate,
    BaselineConfirmationRun,
    CertificationDecision,
    CertificationDecisionStatus,
    CertificationEvidencePack,
    CertificationRecommendation,
    PaperBaselineActivation,
    PaperBaselineConfirmation,
    PaperBaselineConfirmationStatus,
    RolloutCertificationRun,
)
from apps.certification_board.services.activation import get_or_create_paper_baseline_activation
from apps.certification_board.services.candidate_building import (
    build_baseline_activation_candidates,
    build_baseline_confirmation_candidates,
    build_rollout_certification_candidates,
)
from apps.certification_board.services.confirmation import get_or_create_confirmation
from apps.certification_board.services.decision import build_certification_decision
from apps.certification_board.services.evidence_pack import build_certification_evidence_pack
from apps.certification_board.services.recommendation import (
    build_baseline_activation_recommendation,
    build_baseline_confirmation_recommendation,
    build_certification_recommendation,
)


@transaction.atomic
def run_post_rollout_certification_review(*, actor: str = 'operator-ui', metadata: dict | None = None) -> dict:
    started_at = timezone.now()
    run = RolloutCertificationRun.objects.create(started_at=started_at, metadata={'actor': actor, **(metadata or {})})

    candidates = build_rollout_certification_candidates(
        review_run=run,
        rollout_execution_run_id=(metadata or {}).get('rollout_execution_run_id'),
    )

    evidence_packs: list[CertificationEvidencePack] = []
    decisions: list[CertificationDecision] = []
    recommendations: list[CertificationRecommendation] = []

    for candidate in candidates:
        evidence = build_certification_evidence_pack(candidate=candidate)
        decision = build_certification_decision(candidate=candidate, evidence_pack=evidence)
        recommendation = build_certification_recommendation(review_run=run, decision=decision)

        evidence_packs.append(evidence)
        decisions.append(decision)
        recommendations.append(recommendation)

    run.completed_at = timezone.now()
    run.candidate_count = len(candidates)
    run.certified_count = sum(
        1 for item in decisions if item.decision_status == CertificationDecisionStatus.CERTIFIED_FOR_PAPER_BASELINE
    )
    run.observation_count = sum(
        1 for item in decisions if item.decision_status == CertificationDecisionStatus.KEEP_UNDER_OBSERVATION
    )
    run.review_required_count = sum(
        1 for item in decisions if item.decision_status == CertificationDecisionStatus.REQUIRE_MANUAL_REVIEW
    )
    run.rollback_recommended_count = sum(
        1 for item in decisions if item.decision_status == CertificationDecisionStatus.RECOMMEND_ROLLBACK
    )
    run.rejected_count = sum(1 for item in decisions if item.decision_status == CertificationDecisionStatus.REJECT_CERTIFICATION)
    run.recommendation_summary = dict(Counter(item.recommendation_type for item in recommendations))
    run.save(
        update_fields=[
            'completed_at',
            'candidate_count',
            'certified_count',
            'observation_count',
            'review_required_count',
            'rollback_recommended_count',
            'rejected_count',
            'recommendation_summary',
            'updated_at',
        ]
    )

    return {
        'run': run,
        'candidates': candidates,
        'evidence_packs': evidence_packs,
        'decisions': decisions,
        'recommendations': recommendations,
    }


@transaction.atomic
def run_baseline_confirmation_review(*, actor: str = 'operator-ui', metadata: dict | None = None) -> dict:
    started_at = timezone.now()
    linked_certification_run = RolloutCertificationRun.objects.order_by('-started_at', '-id').first()
    run = BaselineConfirmationRun.objects.create(
        started_at=started_at,
        linked_certification_run=linked_certification_run,
        metadata={'actor': actor, **(metadata or {})},
    )

    candidates = build_baseline_confirmation_candidates(review_run=run)
    confirmations: list[PaperBaselineConfirmation] = [get_or_create_confirmation(candidate=item) for item in candidates]
    recommendations = [build_baseline_confirmation_recommendation(review_run=run, confirmation=item) for item in confirmations]

    run.completed_at = timezone.now()
    run.candidate_count = BaselineConfirmationCandidate.objects.filter(review_run=run).count()
    run.ready_to_confirm_count = BaselineConfirmationCandidate.objects.filter(review_run=run, ready_for_confirmation=True).count()
    run.blocked_count = BaselineConfirmationCandidate.objects.filter(
        review_run=run, ready_for_confirmation=False
    ).count()
    run.confirmed_count = PaperBaselineConfirmation.objects.filter(
        linked_candidate__review_run=run, confirmation_status=PaperBaselineConfirmationStatus.CONFIRMED
    ).count()
    run.rollback_ready_count = PaperBaselineConfirmation.objects.filter(
        linked_candidate__review_run=run,
        confirmation_status=PaperBaselineConfirmationStatus.ROLLBACK_AVAILABLE,
    ).count()
    run.recommendation_summary = dict(Counter(item.recommendation_type for item in recommendations))
    run.save(
        update_fields=[
            'completed_at',
            'candidate_count',
            'ready_to_confirm_count',
            'blocked_count',
            'confirmed_count',
            'rollback_ready_count',
            'recommendation_summary',
            'updated_at',
        ]
    )

    return {
        'run': run,
        'candidates': candidates,
        'confirmations': confirmations,
        'recommendations': recommendations,
    }


@transaction.atomic
def run_baseline_activation_review(*, actor: str = 'operator-ui', metadata: dict | None = None) -> dict:
    started_at = timezone.now()
    linked_confirmation_run = BaselineConfirmationRun.objects.order_by('-started_at', '-id').first()
    run = BaselineActivationRun.objects.create(
        started_at=started_at,
        linked_baseline_confirmation_run=linked_confirmation_run,
        metadata={'actor': actor, **(metadata or {})},
    )

    candidates = build_baseline_activation_candidates(review_run=run)
    activations: list[PaperBaselineActivation] = [get_or_create_paper_baseline_activation(candidate=item) for item in candidates]
    recommendations = [
        build_baseline_activation_recommendation(review_run=run, candidate=item, activation=activation)
        for item, activation in zip(candidates, activations)
    ]

    run.completed_at = timezone.now()
    run.candidate_count = BaselineActivationCandidate.objects.filter(review_run=run).count()
    run.ready_to_activate_count = BaselineActivationCandidate.objects.filter(review_run=run, ready_for_activation=True).count()
    run.blocked_count = BaselineActivationCandidate.objects.filter(review_run=run, ready_for_activation=False).count()
    run.activated_count = PaperBaselineActivation.objects.filter(
        linked_candidate__review_run=run, activation_status='ACTIVATED'
    ).count()
    run.rollback_ready_count = PaperBaselineActivation.objects.filter(
        linked_candidate__review_run=run, metadata__rollback_ready=True
    ).count()
    run.recommendation_summary = dict(Counter(item.recommendation_type for item in recommendations))
    run.save(
        update_fields=[
            'completed_at',
            'candidate_count',
            'ready_to_activate_count',
            'blocked_count',
            'activated_count',
            'rollback_ready_count',
            'recommendation_summary',
            'updated_at',
        ]
    )

    return {
        'run': run,
        'candidates': candidates,
        'activations': activations,
        'recommendations': recommendations,
    }
