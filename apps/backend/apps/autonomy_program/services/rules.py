from __future__ import annotations

from collections import defaultdict

from apps.autonomy_campaign.models import AutonomyCampaign, AutonomyCampaignStatus
from apps.autonomy_program.models import CampaignConcurrencyRule, CampaignConcurrencyRuleType


DEFAULT_RULES = [
    {
        'rule_type': CampaignConcurrencyRuleType.MAX_ACTIVE_CAMPAIGNS,
        'scope': 'global',
        'config': {'max_active_campaigns': 2},
        'rationale': 'Limit blast radius by capping concurrent autonomy campaign execution.',
    },
    {
        'rule_type': CampaignConcurrencyRuleType.INCOMPATIBLE_DOMAINS,
        'scope': 'global',
        'config': {
            'pairs': [
                ['rollout_controls', 'bridge_validation_review'],
                ['incident_response', 'runbook_remediation'],
            ],
        },
        'rationale': 'Do not run campaigns together when domains are marked incompatible.',
    },
    {
        'rule_type': CampaignConcurrencyRuleType.BLOCK_IF_DEGRADED,
        'scope': 'global',
        'config': {'enabled': True},
        'rationale': 'Hold campaign changes during degraded posture.',
    },
    {
        'rule_type': CampaignConcurrencyRuleType.BLOCK_IF_UNDER_OBSERVATION,
        'scope': 'global',
        'config': {'enabled': True},
        'rationale': 'Prevent parallel changes while domain rollout observation is active.',
    },
    {
        'rule_type': CampaignConcurrencyRuleType.BLOCK_IF_CRITICAL_INCIDENT,
        'scope': 'global',
        'config': {'enabled': True},
        'rationale': 'Critical incidents freeze additional campaign movement until stabilized.',
    },
]


def ensure_default_rules() -> None:
    for payload in DEFAULT_RULES:
        CampaignConcurrencyRule.objects.get_or_create(
            rule_type=payload['rule_type'],
            scope=payload['scope'],
            defaults={
                'config': payload['config'],
                'rationale': payload['rationale'],
                'metadata': {},
            },
        )


def list_rules():
    ensure_default_rules()
    return CampaignConcurrencyRule.objects.order_by('created_at', 'id')


def evaluate_concurrency_conflicts(*, active_campaigns: list[AutonomyCampaign]) -> dict:
    ensure_default_rules()
    conflicts: list[dict] = []
    active_domains: dict[int, set[str]] = {}
    by_domain: dict[str, list[int]] = defaultdict(list)
    for campaign in active_campaigns:
        domains = {
            step.domain.slug
            for step in campaign.steps.all()
            if step.domain is not None and step.status in {'READY', 'RUNNING', 'WAITING_APPROVAL', 'OBSERVING'}
        }
        active_domains[campaign.id] = domains
        for domain in domains:
            by_domain[domain].append(campaign.id)

    max_rule = CampaignConcurrencyRule.objects.filter(rule_type=CampaignConcurrencyRuleType.MAX_ACTIVE_CAMPAIGNS).order_by('-created_at').first()
    max_active = int((max_rule.config or {}).get('max_active_campaigns', 2)) if max_rule else 2
    if len(active_campaigns) > max_active:
        conflicts.append(
            {
                'rule_type': CampaignConcurrencyRuleType.MAX_ACTIVE_CAMPAIGNS,
                'reason_code': 'MAX_ACTIVE_EXCEEDED',
                'details': {'max_active_campaigns': max_active, 'active_campaign_ids': [campaign.id for campaign in active_campaigns]},
            }
        )

    incompatible_rule = CampaignConcurrencyRule.objects.filter(rule_type=CampaignConcurrencyRuleType.INCOMPATIBLE_DOMAINS).order_by('-created_at').first()
    pairs = ((incompatible_rule.config or {}).get('pairs', []) if incompatible_rule else [])
    for left, right in pairs:
        left_campaigns = set(by_domain.get(left, []))
        right_campaigns = set(by_domain.get(right, []))
        if left_campaigns and right_campaigns:
            conflicts.append(
                {
                    'rule_type': CampaignConcurrencyRuleType.INCOMPATIBLE_DOMAINS,
                    'reason_code': 'INCOMPATIBLE_DOMAINS_ACTIVE',
                    'details': {
                        'pair': [left, right],
                        'campaign_ids': sorted(left_campaigns | right_campaigns),
                    },
                }
            )

    return {'max_active_campaigns': max_active, 'active_domains': active_domains, 'conflicts': conflicts}


def get_active_campaigns_queryset():
    return AutonomyCampaign.objects.filter(status__in=[AutonomyCampaignStatus.RUNNING, AutonomyCampaignStatus.BLOCKED, AutonomyCampaignStatus.PAUSED]).prefetch_related(
        'steps__domain', 'checkpoints'
    )
