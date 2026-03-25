from apps.readiness_lab.models import ReadinessProfile

BASE_READINESS_PROFILES = [
    {
        'name': 'Conservative readiness',
        'slug': 'readiness-conservative',
        'description': 'Promotion gate profile with strict safety and conservative stability thresholds.',
        'profile_type': 'conservative',
        'config': {
            'minimum_replay_runs': 3,
            'minimum_live_paper_runs': 3,
            'minimum_favorable_review_rate': 0.60,
            'maximum_block_rate': 0.25,
            'maximum_safety_event_rate': 0.20,
            'maximum_hard_stop_count': 0,
            'maximum_drawdown': 200,
            'minimum_stability_window': 5,
            'maximum_operator_intervention_rate': 0.45,
            'minimum_real_market_ops_coverage': 0.20,
            'minimum_experiment_comparison_consistency': 0.40,
        },
    },
    {
        'name': 'Balanced readiness',
        'slug': 'readiness-balanced',
        'description': 'General-purpose readiness profile for incremental autonomy in paper/demo mode.',
        'profile_type': 'balanced',
        'config': {
            'minimum_replay_runs': 2,
            'minimum_live_paper_runs': 2,
            'minimum_favorable_review_rate': 0.50,
            'maximum_block_rate': 0.35,
            'maximum_safety_event_rate': 0.30,
            'maximum_hard_stop_count': 1,
            'maximum_drawdown': 350,
            'minimum_stability_window': 3,
            'maximum_operator_intervention_rate': 0.60,
            'minimum_real_market_ops_coverage': 0.10,
            'minimum_experiment_comparison_consistency': 0.25,
        },
    },
    {
        'name': 'Strict readiness',
        'slug': 'readiness-strict',
        'description': 'Harder gate profile for stronger consistency before any higher-stakes phase.',
        'profile_type': 'strict',
        'config': {
            'minimum_replay_runs': 5,
            'minimum_live_paper_runs': 5,
            'minimum_favorable_review_rate': 0.70,
            'maximum_block_rate': 0.20,
            'maximum_safety_event_rate': 0.15,
            'maximum_hard_stop_count': 0,
            'maximum_drawdown': 150,
            'minimum_stability_window': 8,
            'maximum_operator_intervention_rate': 0.35,
            'minimum_real_market_ops_coverage': 0.35,
            'minimum_experiment_comparison_consistency': 0.55,
        },
    },
]


def seed_readiness_profiles() -> dict:
    created = 0
    updated = 0
    for payload in BASE_READINESS_PROFILES:
        _, was_created = ReadinessProfile.objects.update_or_create(
            slug=payload['slug'],
            defaults=payload,
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return {'created': created, 'updated': updated, 'total': ReadinessProfile.objects.count()}
