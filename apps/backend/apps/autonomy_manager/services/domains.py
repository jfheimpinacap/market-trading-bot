from __future__ import annotations

from typing import TypedDict

from apps.autonomy_manager.models import AutonomyDomain, AutonomyEnvelope, AutonomyStage, AutonomyStageState


class DomainSeed(TypedDict):
    slug: str
    name: str
    description: str
    owner_app: str
    action_types: list[str]
    source_apps: list[str]
    envelope: dict


DOMAIN_SEEDS: list[DomainSeed] = [
    {
        'slug': 'incident_response',
        'name': 'Incident response',
        'description': 'Incident detection and remediation decisions across degraded contexts.',
        'owner_app': 'incident_commander',
        'action_types': ['open_incident', 'mitigate_incident', 'resolve_incident', 'apply_degraded_mode'],
        'source_apps': ['incident_commander', 'mission_control'],
        'envelope': {
            'max_auto_actions_per_cycle': 2,
            'approval_override_behavior': 'ALWAYS_REQUIRE_APPROVAL',
            'blocked_contexts': ['critical_incident_escalation'],
            'degraded_mode_handling': 'FREEZE_ON_CRITICAL',
            'certification_dependencies': ['incident_response_certified'],
            'runtime_dependencies': ['mission_control_heartbeat'],
        },
    },
    {
        'slug': 'runbook_remediation',
        'name': 'Runbook remediation',
        'description': 'Supervised runbook autopilot and checkpoint automation envelope.',
        'owner_app': 'runbook_engine',
        'action_types': ['runbook_step_execute', 'runbook_step_skip', 'runbook_checkpoint_continue'],
        'source_apps': ['runbook_engine', 'approval_center'],
        'envelope': {
            'max_auto_actions_per_cycle': 3,
            'approval_override_behavior': 'CHECKPOINT_APPROVAL_REQUIRED',
            'blocked_contexts': ['blocked_runbook', 'missing_runbook_approval'],
            'degraded_mode_handling': 'DOWNGRADE_TO_ASSISTED',
            'certification_dependencies': ['runbook_autopilot_certified'],
            'runtime_dependencies': ['runtime_governor_ok'],
        },
    },
    {
        'slug': 'certification_reviews',
        'name': 'Certification reviews',
        'description': 'Certification board recommendation and envelope governance.',
        'owner_app': 'certification_board',
        'action_types': ['run_certification_review', 'issue_certification_recommendation'],
        'source_apps': ['certification_board', 'go_live_gate'],
        'envelope': {
            'max_auto_actions_per_cycle': 1,
            'approval_override_behavior': 'REQUIRE_APPROVAL_FOR_UPGRADE',
            'blocked_contexts': ['remediation_required'],
            'degraded_mode_handling': 'MANUAL_ONLY_UNTIL_RECERTIFIED',
            'certification_dependencies': ['certification_evidence_fresh'],
            'runtime_dependencies': ['safety_guard_green'],
        },
    },
    {
        'slug': 'portfolio_governance_actions',
        'name': 'Portfolio governance actions',
        'description': 'Portfolio throttles, governance actions and exposure controls.',
        'owner_app': 'portfolio_governor',
        'action_types': ['pause_new_entries', 'throttle_entries', 'resume_entries'],
        'source_apps': ['portfolio_governor', 'position_manager'],
        'envelope': {
            'max_auto_actions_per_cycle': 2,
            'approval_override_behavior': 'REQUIRE_APPROVAL_ON_RELAX',
            'blocked_contexts': ['drawdown_alert', 'degraded_runtime'],
            'degraded_mode_handling': 'FORCE_CONSERVATIVE',
            'certification_dependencies': ['portfolio_governor_certified'],
            'runtime_dependencies': ['position_manager_online'],
        },
    },
    {
        'slug': 'profile_governance_actions',
        'name': 'Profile governance actions',
        'description': 'Profile/regime switching and policy profile governance.',
        'owner_app': 'profile_manager',
        'action_types': ['set_profile_regime', 'apply_profile_target'],
        'source_apps': ['profile_manager', 'mission_control'],
        'envelope': {
            'max_auto_actions_per_cycle': 1,
            'approval_override_behavior': 'REQUIRE_APPROVAL_FOR_AGGRESSIVE_PROFILE',
            'blocked_contexts': ['recertification_required'],
            'degraded_mode_handling': 'PIN_DEFENSIVE_PROFILE',
            'certification_dependencies': ['profile_manager_certified'],
            'runtime_dependencies': ['mission_control_running'],
        },
    },
    {
        'slug': 'venue_reconciliation',
        'name': 'Venue reconciliation',
        'description': 'Execution venue/account parity and reconciliation follow-up.',
        'owner_app': 'venue_account',
        'action_types': ['run_reconciliation', 'flag_parity_gap', 'resolve_parity_gap'],
        'source_apps': ['execution_venue', 'venue_account'],
        'envelope': {
            'max_auto_actions_per_cycle': 2,
            'approval_override_behavior': 'REQUIRE_APPROVAL_FOR_AUTO_RESOLVE',
            'blocked_contexts': ['high_parity_gap'],
            'degraded_mode_handling': 'FREEZE_AUTO_RESOLVE',
            'certification_dependencies': ['venue_connector_certified'],
            'runtime_dependencies': ['connector_lab_green'],
        },
    },
    {
        'slug': 'rollout_controls',
        'name': 'Rollout controls',
        'description': 'Policy rollout guardrails and rollback controls.',
        'owner_app': 'policy_rollout',
        'action_types': ['rollout_pause', 'rollout_resume', 'rollout_rollback'],
        'source_apps': ['policy_rollout', 'rollout_manager'],
        'envelope': {
            'max_auto_actions_per_cycle': 1,
            'approval_override_behavior': 'ALWAYS_REQUIRE_APPROVAL',
            'blocked_contexts': ['rollback_recommended', 'high_incident_rate'],
            'degraded_mode_handling': 'ROLLBACK_RECOMMENDED',
            'certification_dependencies': ['rollout_guard_certified'],
            'runtime_dependencies': ['runtime_rollout_enabled'],
        },
    },
    {
        'slug': 'bridge_validation_review',
        'name': 'Bridge validation review',
        'description': 'Broker bridge validation and connector readiness review.',
        'owner_app': 'broker_bridge',
        'action_types': ['validate_bridge_payload', 'reject_bridge_payload'],
        'source_apps': ['broker_bridge', 'connector_lab'],
        'envelope': {
            'max_auto_actions_per_cycle': 2,
            'approval_override_behavior': 'APPROVAL_ON_VALIDATION_FAIL',
            'blocked_contexts': ['connector_uncertified'],
            'degraded_mode_handling': 'ASSISTED_ONLY',
            'certification_dependencies': ['bridge_validation_certified'],
            'runtime_dependencies': ['execution_venue_parity_ok'],
        },
    },
]


def sync_domain_catalog() -> list[AutonomyDomain]:
    domains: list[AutonomyDomain] = []
    for seed in DOMAIN_SEEDS:
        domain, _ = AutonomyDomain.objects.update_or_create(
            slug=seed['slug'],
            defaults={
                'name': seed['name'],
                'description': seed['description'],
                'owner_app': seed['owner_app'],
                'action_types': seed['action_types'],
                'source_apps': seed['source_apps'],
            },
        )
        AutonomyEnvelope.objects.update_or_create(domain=domain, defaults=seed['envelope'])
        AutonomyStageState.objects.get_or_create(
            domain=domain,
            defaults={
                'current_stage': AutonomyStage.MANUAL,
                'effective_stage': AutonomyStage.MANUAL,
                'rationale': 'Initial manual-first domain baseline.',
                'linked_action_types': seed['action_types'],
                'metadata': {'seeded': True},
            },
        )
        domains.append(domain)
    return domains


def list_domains() -> list[AutonomyDomain]:
    sync_domain_catalog()
    return list(AutonomyDomain.objects.select_related('envelope', 'stage_state').order_by('slug'))
