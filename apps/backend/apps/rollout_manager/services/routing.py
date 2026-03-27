from __future__ import annotations

import hashlib

from django.db.models import F

from apps.rollout_manager.models import StackRolloutMode, StackRolloutRun, StackRolloutRunStatus


class RoutingDecision:
    def __init__(self, *, route: str, is_canary: bool, bucket: int, reason: str):
        self.route = route
        self.is_canary = is_canary
        self.bucket = bucket
        self.reason = reason



def route_opportunity(*, run: StackRolloutRun | None, market_id: int, profile_slug: str = '') -> RoutingDecision:
    if run is None or run.status != StackRolloutRunStatus.RUNNING:
        return RoutingDecision(route='CHAMPION', is_canary=False, bucket=-1, reason='No active rollout run.')

    plan = run.plan
    if plan.profile_scope and plan.profile_scope != profile_slug:
        return RoutingDecision(route='CHAMPION', is_canary=False, bucket=-1, reason='Profile out of rollout scope.')

    if plan.mode == StackRolloutMode.SHADOW_ONLY:
        return RoutingDecision(route='SHADOW_ONLY', is_canary=False, bucket=-1, reason='Shadow-only mode; candidate observed only.')

    key = f'{run.id}:{market_id}:{plan.profile_scope or "global"}:{plan.sampling_rule}'
    bucket = int(hashlib.sha256(key.encode('utf-8')).hexdigest()[:8], 16) % 100
    is_canary = bucket < int(plan.canary_percentage)
    return RoutingDecision(
        route='CANARY' if is_canary else 'CHAMPION',
        is_canary=is_canary,
        bucket=bucket,
        reason='Deterministic hash routing by market id.',
    )


def record_routing_decision(*, run: StackRolloutRun, decision: RoutingDecision) -> None:
    updates = {
        'routed_opportunities_count': F('routed_opportunities_count') + 1,
    }
    if decision.route == 'CANARY':
        updates['canary_count'] = F('canary_count') + 1
        updates['challenger_count'] = F('challenger_count') + 1
    else:
        updates['champion_count'] = F('champion_count') + 1
    StackRolloutRun.objects.filter(pk=run.id).update(**updates)
