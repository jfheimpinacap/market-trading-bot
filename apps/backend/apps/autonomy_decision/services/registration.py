from django.utils import timezone

from apps.autonomy_decision.models import GovernanceDecision, GovernanceDecisionStatus
from apps.autonomy_decision.services.status import DECISION_BY_PROPOSAL_TYPE, TARGET_BY_PROPOSAL_TYPE


def create_registered_decision(*, resolution, actor: str = 'operator-ui') -> GovernanceDecision:
    proposal = resolution.planning_proposal
    decision_type = DECISION_BY_PROPOSAL_TYPE[proposal.proposal_type]
    target_scope = TARGET_BY_PROPOSAL_TYPE[proposal.proposal_type]

    decision, _ = GovernanceDecision.objects.get_or_create(
        planning_proposal=proposal,
        target_scope=target_scope,
        defaults={
            'planning_resolution': resolution,
            'backlog_item': resolution.backlog_item,
            'advisory_artifact': resolution.advisory_artifact,
            'insight': resolution.insight,
            'campaign': resolution.campaign,
            'decision_type': decision_type,
            'decision_status': GovernanceDecisionStatus.REGISTERED,
            'priority_level': proposal.priority_level,
            'summary': proposal.summary,
            'rationale': f'Accepted planning proposal converted into formal decision package: {decision_type}.',
            'reason_codes': ['accepted_proposal_registered'],
            'blockers': [],
            'registered_by': actor,
            'registered_at': timezone.now(),
            'linked_target_artifact': proposal.linked_target_artifact,
            'metadata': {
                'manual_first': True,
                'auto_apply': False,
                'source': 'autonomy_decision.register',
            },
        },
    )

    if decision.decision_status != GovernanceDecisionStatus.ACKNOWLEDGED:
        decision.planning_resolution = resolution
        decision.backlog_item = resolution.backlog_item
        decision.advisory_artifact = resolution.advisory_artifact
        decision.insight = resolution.insight
        decision.campaign = resolution.campaign
        decision.decision_type = decision_type
        decision.target_scope = target_scope
        decision.decision_status = GovernanceDecisionStatus.REGISTERED
        decision.priority_level = proposal.priority_level
        decision.summary = proposal.summary
        decision.rationale = f'Accepted planning proposal converted into formal decision package: {decision_type}.'
        decision.reason_codes = ['accepted_proposal_registered']
        decision.blockers = []
        decision.registered_by = actor
        decision.registered_at = timezone.now()
        decision.linked_target_artifact = proposal.linked_target_artifact
        decision.metadata = {**(decision.metadata or {}), 'manual_first': True, 'auto_apply': False, 'source': 'autonomy_decision.register'}
        decision.save()

    return decision
