from __future__ import annotations

from collections import Counter

from django.db import transaction
from django.utils import timezone

from apps.certification_board.models import (
    CertificationDecision,
    CertificationDecisionStatus,
    CertificationEvidencePack,
    CertificationRecommendation,
    RolloutCertificationRun,
)
from apps.certification_board.services.candidate_building import build_rollout_certification_candidates
from apps.certification_board.services.decision import build_certification_decision
from apps.certification_board.services.evidence_pack import build_certification_evidence_pack
from apps.certification_board.services.recommendation import build_certification_recommendation


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
