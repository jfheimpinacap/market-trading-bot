from __future__ import annotations

from decimal import Decimal

from apps.autonomy_operations.models import OperationsRecommendation, OperationsRecommendationType


def build_recommendations(*, operations_run, snapshots, signals):
    recommendations = []
    needs_attention = 0

    for snapshot in snapshots:
        rtype = OperationsRecommendationType.CONTINUE_CAMPAIGN
        rationale = 'Campaign shows recent progress with no hard blockers.'
        reason_codes = ['ON_TRACK']
        confidence = Decimal('0.8200')

        if snapshot.runtime_status == 'WAITING_APPROVAL':
            rtype = OperationsRecommendationType.ESCALATE_TO_APPROVAL
            rationale = 'Campaign is waiting on approval/checkpoint resolution.'
            reason_codes = ['WAITING_APPROVAL']
            confidence = Decimal('0.9000')
            needs_attention += 1
        elif snapshot.runtime_status == 'BLOCKED':
            rtype = OperationsRecommendationType.PAUSE_CAMPAIGN
            rationale = 'Campaign is blocked and should remain paused pending blocker clearance.'
            reason_codes = ['BLOCKED_RUNTIME']
            confidence = Decimal('0.8600')
            needs_attention += 1
        elif snapshot.runtime_status == 'STALLED':
            rtype = OperationsRecommendationType.REVIEW_FOR_ABORT
            rationale = 'Campaign is stalled and should be reviewed for abort/resume decision.'
            reason_codes = ['STALLED_PROGRESS']
            confidence = Decimal('0.7800')
            needs_attention += 1
        elif snapshot.runtime_status == 'OBSERVING':
            rtype = OperationsRecommendationType.WAIT_FOR_CHECKPOINT
            rationale = 'Campaign is in rollout observation and should wait for checkpoint completion.'
            reason_codes = ['ROLLOUT_OBSERVATION']
            confidence = Decimal('0.8400')
        elif snapshot.runtime_status == 'CAUTION':
            rtype = OperationsRecommendationType.CLEAR_TO_CONTINUE
            rationale = 'Campaign can continue, but caution signals require closer operator watch.'
            reason_codes = ['CAUTION_RUNTIME']
            confidence = Decimal('0.7000')

        if snapshot.incident_impact > 1:
            rtype = OperationsRecommendationType.REVIEW_FOR_ABORT
            rationale = 'Critical incident pressure indicates campaign should be reviewed for abort risk.'
            reason_codes = ['INCIDENT_PRESSURE', 'REVIEW_ABORT']
            confidence = Decimal('0.9200')
            needs_attention += 1
        elif snapshot.incident_impact == 1 and rtype == OperationsRecommendationType.CONTINUE_CAMPAIGN:
            rtype = OperationsRecommendationType.PAUSE_CAMPAIGN
            rationale = 'Incident impact detected; pause and investigate before continuing.'
            reason_codes = ['INCIDENT_PRESSURE']
            confidence = Decimal('0.8100')
            needs_attention += 1

        recommendations.append(
            OperationsRecommendation.objects.create(
                operations_run=operations_run,
                recommendation_type=rtype,
                target_campaign=snapshot.campaign,
                rationale=rationale,
                reason_codes=reason_codes,
                confidence=confidence,
                blockers=snapshot.blockers,
                impacted_domains=(snapshot.metadata or {}).get('domains', []),
                metadata={'runtime_snapshot_id': snapshot.id},
            )
        )

    if needs_attention > 1:
        recommendations.append(
            OperationsRecommendation.objects.create(
                operations_run=operations_run,
                recommendation_type=OperationsRecommendationType.REORDER_OPERATOR_ATTENTION,
                rationale='Multiple active campaigns require intervention; reorder operator attention by severity.',
                reason_codes=['MULTI_CAMPAIGN_PRESSURE'],
                confidence=Decimal('0.8800'),
                blockers=[],
                impacted_domains=[],
                metadata={'attention_campaigns': needs_attention, 'signal_count': len(signals)},
            )
        )

    return recommendations
