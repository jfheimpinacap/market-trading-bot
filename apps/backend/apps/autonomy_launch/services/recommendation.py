from apps.autonomy_launch.models import LaunchRecommendation, LaunchRecommendationType


def create_recommendations(*, launch_run, snapshots: list):
    recommendations = []
    ready = [snap for snap in snapshots if snap.readiness_status == 'READY_TO_START']
    if len(ready) > 1:
        ordered = sorted(ready, key=lambda snap: (-snap.readiness_score, -snap.id))
        recommendations.append(
            LaunchRecommendation.objects.create(
                launch_run=launch_run,
                recommendation_type=LaunchRecommendationType.REORDER_START_PRIORITY,
                rationale='Multiple campaigns are ready; reorder start sequence by readiness_score then recency.',
                reason_codes=['MULTIPLE_READY'],
                confidence='0.7800',
                blockers=[],
                impacted_domains=[],
                metadata={'ordered_campaign_ids': [snap.campaign_id for snap in ordered]},
            )
        )

    for snap in snapshots:
        reason_codes = (snap.metadata or {}).get('reason_codes', [])
        if snap.readiness_status == 'READY_TO_START':
            rec_type = LaunchRecommendationType.START_NOW
            rationale = 'Campaign is ready for explicit manual start authorization now.'
        elif 'WINDOW_NOT_OPEN' in reason_codes:
            rec_type = LaunchRecommendationType.WAIT_FOR_WINDOW
            rationale = 'Campaign remains admitted but should wait for an OPEN window.'
        elif any(code in reason_codes for code in ['PROGRAM_FROZEN', 'DOMAIN_CONFLICT', 'INCIDENT_IMPACT', 'ROLLOUT_PRESSURE']):
            rec_type = LaunchRecommendationType.BLOCK_START
            rationale = 'Campaign start should be blocked due to active safety conflicts.'
        elif snap.unresolved_approvals_count > 0 or 'PROGRAM_HIGH_RISK' in reason_codes:
            rec_type = LaunchRecommendationType.REQUIRE_APPROVAL_TO_START
            rationale = 'Campaign requires approval prior to start under current risk posture.'
        else:
            rec_type = LaunchRecommendationType.HOLD_START
            rationale = 'Campaign should remain on hold until blockers clear.'

        recommendations.append(
            LaunchRecommendation.objects.create(
                launch_run=launch_run,
                recommendation_type=rec_type,
                target_campaign=snap.campaign,
                rationale=rationale,
                reason_codes=reason_codes,
                confidence=f"{min(max(snap.readiness_score / 100, 0.2), 0.95):.4f}",
                blockers=snap.blockers,
                impacted_domains=(snap.metadata or {}).get('impacted_domains', []),
                metadata={'readiness_status': snap.readiness_status},
            )
        )
    return recommendations
