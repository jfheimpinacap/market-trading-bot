from __future__ import annotations

from collections import Counter

from django.db import transaction

from apps.autonomy_disposition.models import CampaignDisposition, DispositionRecommendation, DispositionRun
from apps.autonomy_disposition.services.candidates import build_disposition_candidates
from apps.autonomy_disposition.services.readiness import evaluate_disposition_readiness
from apps.autonomy_disposition.services.recommendation import build_disposition_recommendation_payload, create_recommendation


@transaction.atomic
def run_disposition_review(*, actor: str = 'operator-ui'):
    contexts = build_disposition_candidates()
    dispositions: list[CampaignDisposition] = []

    for context in contexts:
        readiness = evaluate_disposition_readiness(context)
        recommendation = build_disposition_recommendation_payload(context=context, readiness=readiness)
        dispositions.append(
            CampaignDisposition.objects.create(
                campaign=context.campaign,
                disposition_type=recommendation['disposition_type'],
                disposition_status='APPROVAL_REQUIRED' if recommendation['requires_approval'] else 'READY',
                rationale=recommendation['rationale'],
                reason_codes=recommendation['reason_codes'],
                blockers=recommendation['blockers'],
                requires_approval=recommendation['requires_approval'],
                campaign_state_before=context.campaign.status,
                campaign_state_after=context.campaign.status,
                metadata={
                    'actor': actor,
                    'disposition_readiness': readiness['disposition_readiness'],
                    'closure_risk_level': readiness['closure_risk_level'],
                    'recovery_status': context.recovery_snapshot.recovery_status if context.recovery_snapshot else None,
                    'last_intervention_outcome': context.last_intervention_outcome.outcome_type if context.last_intervention_outcome else None,
                    'last_runtime_status': context.last_runtime_snapshot.runtime_status if context.last_runtime_snapshot else None,
                    'pending_approvals_count': context.pending_approvals_count,
                    'pending_checkpoints_count': context.pending_checkpoints_count,
                    'unresolved_incident_pressure': context.unresolved_incident_pressure,
                },
            )
        )

    readiness_counter = Counter(item.metadata.get('disposition_readiness') for item in dispositions)
    run = DispositionRun.objects.create(
        candidate_count=len(dispositions),
        ready_to_close_count=readiness_counter.get('READY_TO_CLOSE', 0),
        ready_to_abort_count=readiness_counter.get('READY_TO_ABORT', 0),
        ready_to_retire_count=readiness_counter.get('READY_TO_RETIRE', 0),
        require_more_review_count=readiness_counter.get('REQUIRE_MORE_REVIEW', 0),
        keep_open_count=readiness_counter.get('KEEP_OPEN', 0),
        approval_required_count=sum(1 for item in dispositions if item.requires_approval),
        recommendation_summary={},
        metadata={'actor': actor},
    )

    recommendations = [
        create_recommendation(
            run=run,
            context=context,
            recommendation=build_disposition_recommendation_payload(context=context, readiness=evaluate_disposition_readiness(context)),
            actor=actor,
        )
        for context in contexts
    ]

    prioritized = [item for item in dispositions if item.metadata.get('disposition_readiness') in {'READY_TO_ABORT', 'READY_TO_RETIRE', 'READY_TO_CLOSE'}]
    if len(prioritized) > 1:
        recommendations.append(
            DispositionRecommendation.objects.create(
                disposition_run=run,
                recommendation_type='REORDER_DISPOSITION_PRIORITY',
                rationale='Multiple campaigns are ready for final disposition; process by risk and blockers first.',
                reason_codes=['multiple_ready_dispositions', 'manual_priority_order'],
                confidence=0.8,
                blockers=[],
                impacted_domains=[],
                metadata={'actor': actor, 'priority_campaign_ids': [item.campaign_id for item in prioritized]},
            )
        )

    recommendation_counter = Counter(item.recommendation_type for item in recommendations)
    run.recommendation_summary = dict(recommendation_counter)
    run.save(update_fields=['recommendation_summary', 'updated_at'])

    return {'run': run, 'dispositions': dispositions, 'recommendations': recommendations}
