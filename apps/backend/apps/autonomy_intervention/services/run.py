from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from apps.autonomy_campaign.models import AutonomyCampaign
from apps.autonomy_intervention.models import CampaignInterventionAction, CampaignInterventionRequest, InterventionRun
from apps.autonomy_intervention.services.intake import create_request
from apps.autonomy_intervention.services.recommendation_bridge import recommendation_to_requested_action
from apps.autonomy_operations.models import CampaignAttentionSignal, CampaignAttentionSignalStatus, OperationsRecommendation


def run_intervention_review(*, actor: str = 'operator-ui') -> dict:
    created_requests = []
    recommendations = OperationsRecommendation.objects.select_related('target_campaign').order_by('-created_at', '-id')[:100]
    for recommendation in recommendations:
        if not recommendation.target_campaign:
            continue
        action = recommendation_to_requested_action(recommendation.recommendation_type)
        if not action:
            continue
        if CampaignInterventionRequest.objects.filter(
            campaign=recommendation.target_campaign,
            requested_action=action,
            request_status__in=['OPEN', 'READY', 'APPROVAL_REQUIRED', 'BLOCKED'],
        ).exists():
            continue
        created_requests.append(
            create_request(
                campaign=recommendation.target_campaign,
                source_type='operations_recommendation',
                requested_action=action,
                severity='HIGH' if recommendation.recommendation_type in {'PAUSE_CAMPAIGN', 'REVIEW_FOR_ABORT'} else 'MEDIUM',
                rationale=recommendation.rationale,
                reason_codes=recommendation.reason_codes,
                blockers=recommendation.blockers,
                linked_recommendation_id=recommendation.id,
                requested_by=actor,
                metadata={'generated_by': 'run_intervention_review'},
            )
        )

    summary = build_intervention_summary()
    run = InterventionRun.objects.create(
        active_campaign_count=summary['active_campaign_count'],
        open_request_count=summary['open_request_count'],
        approval_required_count=summary['approval_required_count'],
        ready_request_count=summary['ready_request_count'],
        blocked_request_count=summary['blocked_request_count'],
        executed_recent_count=summary['executed_recent_count'],
        recommendation_summary=summary['recommendation_summary'],
        metadata={'created_request_ids': [r.id for r in created_requests]},
    )
    return {'run': run, 'created_requests': created_requests}


def build_intervention_summary() -> dict:
    active_campaign_count = AutonomyCampaign.objects.filter(status__in=['RUNNING', 'PAUSED', 'BLOCKED']).count()
    request_counts = CampaignInterventionRequest.objects.values('request_status').annotate(total=Count('id'))
    by_status = {item['request_status']: item['total'] for item in request_counts}
    recent_cutoff = timezone.now() - timedelta(hours=24)
    executed_recent_count = CampaignInterventionAction.objects.filter(action_status='EXECUTED', created_at__gte=recent_cutoff).count()

    recommendation_summary = {
        item['recommendation_type']: item['total']
        for item in OperationsRecommendation.objects.values('recommendation_type').annotate(total=Count('id'))
    }

    campaigns_needing_intervention = CampaignInterventionRequest.objects.filter(request_status__in=['OPEN', 'READY', 'APPROVAL_REQUIRED', 'BLOCKED']).values('campaign_id').distinct().count()
    open_signals = CampaignAttentionSignal.objects.filter(status=CampaignAttentionSignalStatus.OPEN).count()

    return {
        'active_campaign_count': active_campaign_count,
        'open_request_count': by_status.get('OPEN', 0),
        'approval_required_count': by_status.get('APPROVAL_REQUIRED', 0),
        'ready_request_count': by_status.get('READY', 0),
        'blocked_request_count': by_status.get('BLOCKED', 0),
        'executed_recent_count': executed_recent_count,
        'recommendation_summary': recommendation_summary,
        'campaigns_needing_intervention': campaigns_needing_intervention,
        'open_attention_signal_count': open_signals,
    }
