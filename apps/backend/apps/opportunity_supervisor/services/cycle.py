from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.allocation_engine.services.allocation import evaluate_allocation
from apps.operator_queue.models import OperatorQueueItem, OperatorQueuePriority, OperatorQueueSource, OperatorQueueType
from apps.execution_simulator.services import create_order, run_execution_lifecycle
from apps.proposal_engine.services.proposal import generate_trade_proposal
from apps.runtime_governor.services import get_runtime_state
from apps.safety_guard.services.evaluation import get_safety_status
from apps.signals.models import OpportunityStatus
from apps.signals.services.fusion import run_signal_fusion
from apps.opportunity_supervisor.models import (
    OpportunityCycleItem,
    OpportunityCycleRun,
    OpportunityCycleStatus,
    OpportunityExecutionPath,
    OpportunityExecutionPlan,
)
from apps.opportunity_supervisor.services.execution_path import resolve_execution_path
from apps.opportunity_supervisor.services.profiles import get_profile
from apps.portfolio_governor.services import get_latest_throttle_decision, run_portfolio_governance


def _create_queue_item(*, item: OpportunityCycleItem, quantity: Decimal, explanation: str) -> OperatorQueueItem:
    return OperatorQueueItem.objects.create(
        source=OperatorQueueSource.ALLOCATION,
        queue_type=OperatorQueueType.APPROVAL_REQUIRED,
        related_market=item.market,
        related_proposal=item.proposal,
        priority=OperatorQueuePriority.HIGH if item.risk_context.get('risk_level') == 'HIGH' else OperatorQueuePriority.MEDIUM,
        headline=f'Opportunity cycle review for {item.market.title}',
        summary='Supervisor queued this proposal for operator approval before any paper execution.',
        rationale=explanation,
        suggested_action=item.proposal.suggested_trade_type if item.proposal else '',
        suggested_quantity=quantity,
        metadata={
            'origin': 'opportunity_supervisor',
            'cycle_run_id': item.run_id,
            'cycle_item_id': item.id,
            'paper_demo_only': True,
            'real_execution_enabled': False,
        },
    )


@transaction.atomic
def run_opportunity_cycle(*, profile_slug: str | None = None, triggered_by: str = 'manual_api') -> OpportunityCycleRun:
    profile = get_profile(profile_slug)
    runtime_state = get_runtime_state()
    safety = get_safety_status()

    cycle = OpportunityCycleRun.objects.create(
        status=OpportunityCycleStatus.RUNNING,
        profile_slug=profile.slug,
        started_at=timezone.now(),
        details={
            'triggered_by': triggered_by,
            'runtime_mode': runtime_state.current_mode,
            'runtime_status': runtime_state.status,
            'safety_status': safety['status'],
            'paper_demo_only': True,
            'real_execution_enabled': False,
        },
    )

    governance_run = run_portfolio_governance(triggered_by='opportunity_supervisor')
    throttle = governance_run.throttle_decision or get_latest_throttle_decision()

    fusion_run = run_signal_fusion(profile_slug=profile.fusion_profile_slug, triggered_by='opportunity_supervisor')
    opportunities = list(
        fusion_run.opportunities.select_related('market', 'proposal_gate').order_by('rank', 'id')
    )

    cycle.markets_scanned = fusion_run.markets_evaluated
    cycle.opportunities_built = len(opportunities)

    for opp in opportunities:
        gate = getattr(opp, 'proposal_gate', None)
        item = OpportunityCycleItem.objects.create(
            run=cycle,
            market=opp.market,
            source_provider=opp.provider_slug,
            research_context={
                'research_score': str(opp.research_score),
                'triage_score': str(opp.triage_score),
                'source_mix': opp.source_mix,
                'narrative_direction': opp.narrative_direction,
            },
            prediction_context={
                'edge': str(opp.edge),
                'confidence': str(opp.prediction_confidence),
                'system_probability': str(opp.prediction_system_probability) if opp.prediction_system_probability is not None else None,
                'market_probability': str(opp.prediction_market_probability) if opp.prediction_market_probability is not None else None,
            },
            risk_context={
                'risk_level': opp.risk_level,
                'adjusted_quantity': str(opp.adjusted_quantity) if opp.adjusted_quantity is not None else None,
            },
            signal_context={
                'opportunity_status': opp.opportunity_status,
                'opportunity_score': str(opp.opportunity_score),
                'rank': opp.rank,
                'proposal_gate': {
                    'should_generate_proposal': gate.should_generate_proposal if gate else False,
                    'proposal_priority': gate.proposal_priority if gate else 0,
                },
            },
            proposal_status='NOT_GENERATED',
            allocation_status='NOT_READY',
            execution_path=OpportunityExecutionPath.WATCH,
            rationale=opp.rationale,
            metadata={'opportunity_signal_id': opp.id},
        )

        proposal = None
        if (
            opp.opportunity_status == OpportunityStatus.PROPOSAL_READY
            and gate
            and gate.should_generate_proposal
            and gate.proposal_priority >= profile.min_gate_priority
        ):
            proposal = generate_trade_proposal(market=opp.market, triggered_from='opportunity_supervisor')
            item.proposal = proposal
            item.proposal_status = proposal.policy_decision
            cycle.proposals_generated += 1
        elif opp.opportunity_status == OpportunityStatus.BLOCKED:
            item.execution_path = OpportunityExecutionPath.BLOCKED
            item.proposal_status = 'BLOCKED'
            cycle.blocked_count += 1

        allocation_quantity = None
        allocation_status = 'NOT_READY'
        if proposal is not None:
            allocation_result = evaluate_allocation(proposals=[proposal], triggered_from='opportunity_supervisor', persist=False)
            decision = allocation_result['details'][0] if allocation_result['details'] else None
            if decision and decision['decision'] in {'SELECTED', 'REDUCED'}:
                allocation_quantity = decision['final_allocated_quantity']
                if throttle and throttle.recommended_max_size_multiplier is not None:
                    allocation_quantity = Decimal(str(allocation_quantity)) * Decimal(str(throttle.recommended_max_size_multiplier))
                allocation_status = decision['decision']
                cycle.allocation_ready_count += 1
            else:
                allocation_status = decision['decision'] if decision else 'SKIPPED'

        item.allocation_status = allocation_status
        item.allocation_quantity = allocation_quantity

        if proposal is None and item.execution_path != OpportunityExecutionPath.BLOCKED:
            item.execution_path = OpportunityExecutionPath.WATCH
            item.save(update_fields=['proposal', 'proposal_status', 'allocation_status', 'allocation_quantity', 'execution_path', 'updated_at'])
            continue

        blocked_reasons = list(fusion_run.metadata.get('blocked_reasons', []))
        path_decision = resolve_execution_path(
            policy_decision=proposal.policy_decision,
            runtime_mode=runtime_state.current_mode,
            safety_status=safety['status'],
            blocked_reasons=blocked_reasons,
            risk_level=opp.risk_level,
            has_allocation=bool(allocation_quantity and allocation_quantity > 0),
            portfolio_throttle_state=throttle.state if throttle else None,
            portfolio_size_multiplier=str(throttle.recommended_max_size_multiplier) if throttle else None,
        )

        queue_item = None
        executed_trade = None

        if path_decision.path == OpportunityExecutionPath.QUEUE and allocation_quantity:
            queue_item = _create_queue_item(item=item, quantity=allocation_quantity, explanation=path_decision.explanation)
            cycle.queued_count += 1
        elif path_decision.path == OpportunityExecutionPath.AUTO_EXECUTE_PAPER and allocation_quantity:
            order = create_order(
                market=proposal.market,
                side=f"{proposal.suggested_trade_type}_{proposal.suggested_side or 'YES'}",
                requested_quantity=allocation_quantity,
                created_from='opportunity_supervisor',
                paper_account=proposal.paper_account,
                metadata={'origin': 'opportunity_supervisor', 'cycle_run_id': cycle.id, 'cycle_item_id': item.id},
            )
            lifecycle_run = run_execution_lifecycle(
                open_only=True,
                metadata={'triggered_from': 'opportunity_supervisor', 'paper_order_id': order.id, 'cycle_run_id': cycle.id},
            )
            executed_trade = order.paper_account.trades.order_by('-executed_at', '-id').first()
            cycle.auto_executed_count += 1 if lifecycle_run.orders_filled or lifecycle_run.orders_partial else 0
        elif path_decision.path == OpportunityExecutionPath.BLOCKED:
            cycle.blocked_count += 1

        OpportunityExecutionPlan.objects.create(
            item=item,
            proposal=proposal,
            queue_item=queue_item,
            paper_trade=executed_trade,
            allocation_quantity=allocation_quantity,
            runtime_mode=runtime_state.current_mode,
            policy_decision=proposal.policy_decision,
            safety_status=safety['status'],
            queue_required=path_decision.queue_required,
            auto_execute_allowed=path_decision.auto_execute_allowed,
            final_recommended_action=path_decision.path,
            explanation=path_decision.explanation,
            metadata={
                'runtime_status': runtime_state.status,
                'portfolio_throttle_state': throttle.state if throttle else None,
                'paper_demo_only': True,
                'real_execution_enabled': False,
            },
        )

        item.execution_path = path_decision.path
        item.save(update_fields=['proposal', 'proposal_status', 'allocation_status', 'allocation_quantity', 'execution_path', 'updated_at'])

    cycle.status = OpportunityCycleStatus.COMPLETED
    cycle.finished_at = timezone.now()
    cycle.summary = (
        f'Cycle completed: opps={cycle.opportunities_built}, proposals={cycle.proposals_generated}, '
        f'alloc_ready={cycle.allocation_ready_count}, queue={cycle.queued_count}, auto={cycle.auto_executed_count}, blocked={cycle.blocked_count}.'
    )
    cycle.details = {
        **cycle.details,
        'fusion_run_id': fusion_run.id,
        'fusion_profile': fusion_run.profile_slug,
        'portfolio_governance_run_id': governance_run.id,
        'portfolio_throttle_state': throttle.state if throttle else None,
    }
    cycle.save()
    return cycle
