from __future__ import annotations

from collections import Counter
from decimal import Decimal

from apps.autonomy_activation.models import ActivationRecommendation, ActivationRecommendationType


def generate_dispatch_recommendations(*, candidates: list[dict], activation_run=None) -> list[ActivationRecommendation]:
    rows: list[ActivationRecommendation] = []

    ready = [item for item in candidates if item['dispatch_readiness_status'] == 'READY_TO_DISPATCH']
    blocked = [item for item in candidates if item['dispatch_readiness_status'] == 'BLOCKED']
    expired = [item for item in candidates if item['dispatch_readiness_status'] == 'EXPIRED']
    waiting = [item for item in candidates if item['dispatch_readiness_status'] == 'WAITING']

    if ready:
        first = ready[0]
        rows.append(
            ActivationRecommendation.objects.create(
                activation_run=activation_run,
                recommendation_type=ActivationRecommendationType.DISPATCH_NOW,
                target_campaign=first['campaign'],
                rationale='Campaign is authorized and ready for manual dispatch.',
                reason_codes=['READY_TO_DISPATCH'],
                confidence=Decimal('0.9000'),
                blockers=[],
                impacted_domains=(first['campaign'].metadata or {}).get('domains', []),
            )
        )

    for item in waiting:
        rows.append(
            ActivationRecommendation.objects.create(
                activation_run=activation_run,
                recommendation_type=ActivationRecommendationType.WAIT_FOR_WINDOW,
                target_campaign=item['campaign'],
                rationale='Campaign authorization is valid but dispatch should wait for a safe start window.',
                reason_codes=item['metadata'].get('reason_codes', []),
                confidence=Decimal('0.8200'),
                blockers=item['blockers'],
                impacted_domains=(item['campaign'].metadata or {}).get('domains', []),
            )
        )

    for item in blocked:
        rows.append(
            ActivationRecommendation.objects.create(
                activation_run=activation_run,
                recommendation_type=ActivationRecommendationType.BLOCK_DISPATCH,
                target_campaign=item['campaign'],
                rationale='Dispatch blocked by governance checks at activation time.',
                reason_codes=item['metadata'].get('reason_codes', []),
                confidence=Decimal('0.9300'),
                blockers=item['blockers'],
                impacted_domains=(item['campaign'].metadata or {}).get('domains', []),
            )
        )

    for item in expired:
        rows.append(
            ActivationRecommendation.objects.create(
                activation_run=activation_run,
                recommendation_type=ActivationRecommendationType.EXPIRE_AUTHORIZATION,
                target_campaign=item['campaign'],
                rationale='Authorization can no longer be used and should remain expired until re-authorized.',
                reason_codes=item['metadata'].get('reason_codes', []),
                confidence=Decimal('0.9800'),
                blockers=item['blockers'],
                impacted_domains=(item['campaign'].metadata or {}).get('domains', []),
            )
        )

    if len(ready) > 1:
        rows.append(
            ActivationRecommendation.objects.create(
                activation_run=activation_run,
                recommendation_type=ActivationRecommendationType.REORDER_DISPATCH_PRIORITY,
                target_campaign=None,
                rationale='Multiple campaigns are ready; dispatch highest-priority campaign first.',
                reason_codes=['MULTIPLE_READY_CAMPAIGNS'],
                confidence=Decimal('0.7600'),
                blockers=[],
                impacted_domains=sorted(
                    {
                        domain
                        for item in ready
                        for domain in ((item['campaign'].metadata or {}).get('domains', []) or [])
                    }
                ),
            )
        )

    return rows


def summarize_recommendations(recommendations: list[ActivationRecommendation]) -> dict[str, int]:
    counts = Counter([row.recommendation_type for row in recommendations])
    return dict(counts)
