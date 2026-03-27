from __future__ import annotations

from typing import Iterable

from apps.agents.models import AgentHandoff, AgentPipelineRun, AgentRun
from apps.allocation_engine.models import AllocationDecision
from apps.broker_bridge.models import BrokerOrderIntent
from apps.execution_simulator.models import PaperFill, PaperOrder
from apps.execution_venue.models import VenueOrderPayload, VenueOrderResponse
from apps.incident_commander.models import DegradedModeState, IncidentRecord
from apps.memory_retrieval.models import AgentPrecedentUse, MemoryRetrievalRun
from apps.mission_control.models import MissionControlCycle, MissionControlStep
from apps.prediction_agent.models import PredictionScore
from apps.profile_manager.models import ProfileDecision
from apps.proposal_engine.models import TradeProposal
from apps.research_agent.models import ResearchCandidate
from apps.risk_agent.models import RiskAssessment, RiskSizingDecision
from apps.runtime_governor.models import RuntimeModeState
from apps.signals.models import OpportunitySignal
from apps.trace_explorer.models import TraceNode
from apps.venue_account.models import VenueOrderSnapshot, VenueReconciliationIssue
from apps.certification_board.models import CertificationRun


def _create_node(trace_root, *, node_key: str, node_type: str, stage: str, title: str, status: str = '', summary: str = '', ref_type: str = '', ref_id: str = '', happened_at=None, snapshot: dict | None = None) -> TraceNode:
    defaults = {
        'node_type': node_type,
        'stage': stage,
        'title': title,
        'status': status,
        'summary': summary,
        'ref_type': ref_type,
        'ref_id': str(ref_id) if ref_id else '',
        'happened_at': happened_at,
        'snapshot': snapshot or {},
    }
    node, _ = TraceNode.objects.update_or_create(trace_root=trace_root, node_key=node_key, defaults=defaults)
    return node


def _iter_agent_records(context: dict) -> Iterable[AgentRun]:
    market_id = context.get('market_id')
    proposal_id = context.get('proposal_id')
    paper_order_id = context.get('paper_order_id')
    candidates = AgentRun.objects.select_related('agent_definition', 'pipeline_run').order_by('-started_at', '-id')[:200]
    for run in candidates:
        details = run.details or {}
        blob = str(details)
        if any(token and token in blob for token in [str(market_id) if market_id else '', str(proposal_id) if proposal_id else '', str(paper_order_id) if paper_order_id else '']):
            yield run


def collect_nodes(trace_root, context: dict) -> list[TraceNode]:
    nodes: list[TraceNode] = []
    market_id = context.get('market_id')
    proposal_id = context.get('proposal_id')
    paper_order_id = context.get('paper_order_id')
    incident_id = context.get('incident_id')
    mission_cycle_id = context.get('mission_cycle_id')

    if market_id:
        candidate = ResearchCandidate.objects.filter(market_id=market_id).order_by('-updated_at', '-id').first()
        if candidate:
            nodes.append(_create_node(trace_root, node_key=f'research_candidate:{candidate.id}', node_type='ResearchCandidate', stage='RESEARCH', title=f'Research candidate #{candidate.id}', status=candidate.sentiment_direction, summary=candidate.short_thesis, ref_type='research_candidate', ref_id=str(candidate.id), happened_at=candidate.updated_at, snapshot={'priority': str(candidate.priority), 'divergence_score': str(candidate.divergence_score)}))

        prediction = PredictionScore.objects.filter(market_id=market_id).order_by('-created_at', '-id').first()
        if prediction:
            nodes.append(_create_node(trace_root, node_key=f'prediction:{prediction.id}', node_type='PredictionScore', stage='PREDICTION', title=f'Prediction score #{prediction.id}', status=prediction.confidence_level, summary=prediction.rationale[:255], ref_type='prediction_score', ref_id=str(prediction.id), happened_at=prediction.created_at, snapshot={'edge': str(prediction.edge), 'system_probability': str(prediction.system_probability), 'market_probability': str(prediction.market_probability)}))

        signal = OpportunitySignal.objects.filter(market_id=market_id).order_by('-created_at', '-id').first()
        if signal:
            nodes.append(_create_node(trace_root, node_key=f'opportunity_signal:{signal.id}', node_type='OpportunitySignal', stage='SIGNAL', title=f'Opportunity signal #{signal.id}', status=signal.opportunity_status, summary=signal.rationale, ref_type='opportunity_signal', ref_id=str(signal.id), happened_at=signal.created_at, snapshot={'opportunity_score': str(signal.opportunity_score), 'edge': str(signal.edge), 'risk_level': signal.risk_level}))

    proposal = TradeProposal.objects.filter(pk=proposal_id).first() if proposal_id else TradeProposal.objects.filter(market_id=market_id).order_by('-created_at', '-id').first() if market_id else None
    if proposal:
        proposal_id = proposal.id
        context['proposal_id'] = proposal_id
        nodes.append(_create_node(trace_root, node_key=f'proposal:{proposal.id}', node_type='TradeProposal', stage='PROPOSAL', title=f'Proposal #{proposal.id}', status=proposal.proposal_status, summary=proposal.recommendation[:255], ref_type='proposal', ref_id=str(proposal.id), happened_at=proposal.created_at, snapshot={'direction': proposal.direction, 'risk_decision': proposal.risk_decision, 'policy_decision': proposal.policy_decision, 'suggested_quantity': str(proposal.suggested_quantity) if proposal.suggested_quantity is not None else None}))

        allocation = AllocationDecision.objects.filter(proposal_id=proposal.id).select_related('run').order_by('-created_at', '-id').first()
        if allocation:
            nodes.append(_create_node(trace_root, node_key=f'allocation:{allocation.id}', node_type='AllocationDecision', stage='ALLOCATION', title=f'Allocation decision #{allocation.id}', status=allocation.decision, summary=allocation.rationale[:255], ref_type='allocation_decision', ref_id=str(allocation.id), happened_at=allocation.created_at, snapshot={'allocated_quantity': str(allocation.final_allocated_quantity), 'allocation_run_id': allocation.run_id}))

    risk = RiskAssessment.objects.filter(proposal_id=proposal_id).order_by('-created_at', '-id').first() if proposal_id else RiskAssessment.objects.filter(market_id=market_id).order_by('-created_at', '-id').first() if market_id else None
    if risk:
        nodes.append(_create_node(trace_root, node_key=f'risk:{risk.id}', node_type='RiskAssessment', stage='RISK', title=f'Risk assessment #{risk.id}', status=risk.risk_level, summary=risk.narrative_risk_summary[:255], ref_type='risk_assessment', ref_id=str(risk.id), happened_at=risk.created_at, snapshot={'risk_score': str(risk.risk_score) if risk.risk_score is not None else None, 'assessment_status': risk.assessment_status}))
        sizing = RiskSizingDecision.objects.filter(risk_assessment_id=risk.id).order_by('-created_at', '-id').first()
        if sizing:
            nodes.append(_create_node(trace_root, node_key=f'sizing:{sizing.id}', node_type='RiskSizingDecision', stage='RISK', title=f'Sizing decision #{sizing.id}', status=sizing.sizing_mode, summary=sizing.sizing_rationale[:255], ref_type='risk_sizing_decision', ref_id=str(sizing.id), happened_at=sizing.created_at, snapshot={'adjusted_quantity': str(sizing.adjusted_quantity), 'base_quantity': str(sizing.base_quantity)}))

    order = PaperOrder.objects.filter(pk=paper_order_id).first() if paper_order_id else PaperOrder.objects.filter(market_id=market_id).order_by('-created_at', '-id').first() if market_id else None
    if order:
        context['paper_order_id'] = order.id
        nodes.append(_create_node(trace_root, node_key=f'paper_order:{order.id}', node_type='PaperOrder', stage='EXECUTION', title=f'Paper order #{order.id}', status=order.status, summary=f'{order.side} {order.requested_quantity}', ref_type='paper_order', ref_id=str(order.id), happened_at=order.created_at, snapshot={'order_type': order.order_type, 'requested_quantity': str(order.requested_quantity), 'remaining_quantity': str(order.remaining_quantity)}))

        fill = PaperFill.objects.filter(paper_order_id=order.id).order_by('-created_at', '-id').first()
        if fill:
            nodes.append(_create_node(trace_root, node_key=f'paper_fill:{fill.id}', node_type='PaperFill', stage='EXECUTION', title=f'Paper fill #{fill.id}', status=fill.fill_type.upper(), summary=f'{fill.fill_quantity} @ {fill.fill_price}', ref_type='paper_fill', ref_id=str(fill.id), happened_at=fill.created_at, snapshot={'fill_quantity': str(fill.fill_quantity), 'fill_price': str(fill.fill_price)}))

        intent = BrokerOrderIntent.objects.filter(related_paper_order_id=order.id).order_by('-created_at', '-id').first()
        if intent:
            nodes.append(_create_node(trace_root, node_key=f'broker_intent:{intent.id}', node_type='BrokerOrderIntent', stage='EXECUTION', title=f'Broker intent #{intent.id}', status=intent.status, summary=f'{intent.side} {intent.quantity}', ref_type='broker_order_intent', ref_id=str(intent.id), happened_at=intent.created_at, snapshot={'order_type': intent.order_type, 'market_ref': intent.market_ref, 'mapping_profile': intent.mapping_profile}))

            payload = VenueOrderPayload.objects.filter(intent_id=intent.id).order_by('-created_at', '-id').first()
            if payload:
                nodes.append(_create_node(trace_root, node_key=f'venue_payload:{payload.id}', node_type='VenueOrderPayload', stage='VENUE', title=f'Venue payload #{payload.id}', status=payload.venue_name, summary=f'{payload.side} {payload.quantity}', ref_type='venue_order_payload', ref_id=str(payload.id), happened_at=payload.created_at, snapshot={'external_market_id': payload.external_market_id, 'order_type': payload.order_type}))

            response = VenueOrderResponse.objects.filter(intent_id=intent.id).order_by('-created_at', '-id').first()
            if response:
                nodes.append(_create_node(trace_root, node_key=f'venue_response:{response.id}', node_type='VenueOrderResponse', stage='VENUE', title=f'Venue response #{response.id}', status=response.normalized_status, summary=(response.reason_codes or [''])[0], ref_type='venue_order_response', ref_id=str(response.id), happened_at=response.created_at, snapshot={'external_order_id': response.external_order_id, 'warnings': response.warnings}))

            venue_snapshot = VenueOrderSnapshot.objects.filter(source_intent_id=intent.id).order_by('-updated_at', '-id').first()
            if venue_snapshot:
                nodes.append(_create_node(trace_root, node_key=f'venue_snapshot:{venue_snapshot.id}', node_type='VenueOrderSnapshot', stage='VENUE', title=f'Venue order snapshot #{venue_snapshot.id}', status=venue_snapshot.status, summary=venue_snapshot.external_order_id, ref_type='venue_order_snapshot', ref_id=str(venue_snapshot.id), happened_at=venue_snapshot.updated_at, snapshot={'filled_quantity': str(venue_snapshot.filled_quantity), 'remaining_quantity': str(venue_snapshot.remaining_quantity)}))

    issue = VenueReconciliationIssue.objects.order_by('-created_at', '-id').first()
    if issue and ((paper_order_id and str(paper_order_id) in str(issue.source_refs)) or (market_id and str(market_id) in str(issue.source_refs))):
        nodes.append(_create_node(trace_root, node_key=f'venue_reconciliation_issue:{issue.id}', node_type='VenueReconciliationIssue', stage='VENUE', title=f'Venue reconciliation issue #{issue.id}', status=issue.severity, summary=issue.reason, ref_type='venue_reconciliation_issue', ref_id=str(issue.id), happened_at=issue.created_at, snapshot={'issue_type': issue.issue_type, 'source_refs': issue.source_refs}))

    if mission_cycle_id:
        cycle = MissionControlCycle.objects.filter(pk=mission_cycle_id).first()
        if cycle:
            nodes.append(_create_node(trace_root, node_key=f'mission_cycle:{cycle.id}', node_type='MissionControlCycle', stage='MISSION', title=f'Mission cycle #{cycle.cycle_number}', status=cycle.status, summary=cycle.summary, ref_type='mission_cycle', ref_id=str(cycle.id), happened_at=cycle.started_at, snapshot={'opportunities_built': cycle.opportunities_built, 'proposals_generated': cycle.proposals_generated, 'blocked_count': cycle.blocked_count}))
            for step in MissionControlStep.objects.filter(cycle_id=cycle.id).order_by('started_at', 'id')[:8]:
                nodes.append(_create_node(trace_root, node_key=f'mission_step:{step.id}', node_type='MissionControlStep', stage='MISSION', title=f'Mission step {step.step_type}', status=step.status, summary=step.summary, ref_type='mission_step', ref_id=str(step.id), happened_at=step.started_at, snapshot={'details': step.details}))

    precedent_uses = AgentPrecedentUse.objects.order_by('-created_at', '-id')[:80]
    for use in precedent_uses:
        if any([proposal_id and use.source_object_id == str(proposal_id), market_id and use.source_object_id == str(market_id), str(context.get('root_id')) == use.source_object_id]):
            nodes.append(_create_node(trace_root, node_key=f'precedent_use:{use.id}', node_type='AgentPrecedentUse', stage='PRECEDENT', title=f'Precedent use #{use.id}', status=use.influence_mode, summary=f'{use.agent_name} used {use.precedent_count} precedents', ref_type='agent_precedent_use', ref_id=str(use.id), happened_at=use.created_at, snapshot={'agent_name': use.agent_name, 'source_app': use.source_app, 'retrieval_run_id': use.retrieval_run_id}))
            retrieval = MemoryRetrievalRun.objects.filter(pk=use.retrieval_run_id).first()
            if retrieval:
                nodes.append(_create_node(trace_root, node_key=f'retrieval_run:{retrieval.id}', node_type='MemoryRetrievalRun', stage='PRECEDENT', title=f'Retrieval run #{retrieval.id}', status=retrieval.query_type, summary=retrieval.query_text[:255], ref_type='memory_retrieval_run', ref_id=str(retrieval.id), happened_at=retrieval.created_at, snapshot={'result_count': retrieval.result_count, 'context_metadata': retrieval.context_metadata}))

    incidents = IncidentRecord.objects.order_by('-last_seen_at', '-id')[:120]
    for incident in incidents:
        if incident_id and incident.id == int(incident_id):
            include = True
        else:
            include = (
                (proposal_id and incident.related_object_type == 'proposal' and incident.related_object_id == str(proposal_id))
                or (paper_order_id and incident.related_object_id == str(paper_order_id))
                or (market_id and incident.related_object_type == 'market' and incident.related_object_id == str(market_id))
            )
        if include:
            nodes.append(_create_node(trace_root, node_key=f'incident:{incident.id}', node_type='IncidentRecord', stage='INCIDENT', title=incident.title, status=incident.status, summary=incident.summary[:255], ref_type='incident', ref_id=str(incident.id), happened_at=incident.last_seen_at, snapshot={'severity': incident.severity, 'incident_type': incident.incident_type, 'source_app': incident.source_app}))

    degraded = DegradedModeState.objects.order_by('-updated_at', '-id').first()
    if degraded:
        nodes.append(_create_node(trace_root, node_key=f'degraded_state:{degraded.id}', node_type='DegradedModeState', stage='DEGRADED', title='Degraded mode state', status=degraded.state, summary=', '.join(degraded.reasons[:2]) if degraded.reasons else '', ref_type='degraded_mode_state', ref_id=str(degraded.id), happened_at=degraded.updated_at, snapshot={'mission_control_paused': degraded.mission_control_paused, 'auto_execution_enabled': degraded.auto_execution_enabled, 'disabled_actions': degraded.disabled_actions}))

    runtime = RuntimeModeState.objects.order_by('-effective_at', '-id').first()
    if runtime:
        nodes.append(_create_node(trace_root, node_key=f'runtime_state:{runtime.id}', node_type='RuntimeModeState', stage='RUNTIME', title='Runtime mode state', status=runtime.status, summary=runtime.rationale, ref_type='runtime_mode_state', ref_id=str(runtime.id), happened_at=runtime.effective_at, snapshot={'current_mode': runtime.current_mode, 'set_by': runtime.set_by}))

    profile_decision = ProfileDecision.objects.select_related('run').order_by('-created_at', '-id').first()
    if profile_decision:
        nodes.append(_create_node(trace_root, node_key=f'profile_decision:{profile_decision.id}', node_type='ProfileDecision', stage='PROFILE', title=f'Profile decision #{profile_decision.id}', status=profile_decision.decision_mode, summary=profile_decision.rationale[:255], ref_type='profile_decision', ref_id=str(profile_decision.id), happened_at=profile_decision.created_at, snapshot={'target_mission_control_profile': profile_decision.target_mission_control_profile, 'target_signal_profile': profile_decision.target_signal_profile, 'is_applied': profile_decision.is_applied}))

    cert_run = CertificationRun.objects.order_by('-created_at', '-id').first()
    if cert_run:
        nodes.append(_create_node(trace_root, node_key=f'certification_run:{cert_run.id}', node_type='CertificationRun', stage='CERTIFICATION', title=f'Certification run #{cert_run.id}', status=cert_run.certification_level, summary=cert_run.summary or cert_run.rationale[:255], ref_type='certification_run', ref_id=str(cert_run.id), happened_at=cert_run.created_at, snapshot={'recommendation_code': cert_run.recommendation_code, 'confidence': str(cert_run.confidence)}))

    for run in _iter_agent_records(context):
        nodes.append(_create_node(trace_root, node_key=f'agent_run:{run.id}', node_type='AgentRun', stage='AGENT', title=f'Agent run {run.agent_definition.slug}', status=run.status, summary=run.summary, ref_type='agent_run', ref_id=str(run.id), happened_at=run.started_at, snapshot={'pipeline_run_id': run.pipeline_run_id, 'triggered_from': run.triggered_from}))

        if run.pipeline_run_id:
            pipeline = AgentPipelineRun.objects.filter(pk=run.pipeline_run_id).first()
            if pipeline:
                nodes.append(_create_node(trace_root, node_key=f'pipeline_run:{pipeline.id}', node_type='AgentPipelineRun', stage='AGENT', title=f'Pipeline run {pipeline.pipeline_type}', status=pipeline.status, summary=pipeline.summary, ref_type='agent_pipeline_run', ref_id=str(pipeline.id), happened_at=pipeline.started_at, snapshot={'agents_run_count': pipeline.agents_run_count, 'handoffs_count': pipeline.handoffs_count}))
            for handoff in AgentHandoff.objects.filter(from_agent_run_id=run.id).select_related('to_agent_definition').order_by('-created_at', '-id')[:5]:
                nodes.append(_create_node(trace_root, node_key=f'agent_handoff:{handoff.id}', node_type='AgentHandoff', stage='AGENT', title=f'Handoff to {handoff.to_agent_definition.slug}', status=handoff.handoff_type, summary=handoff.payload_summary, ref_type='agent_handoff', ref_id=str(handoff.id), happened_at=handoff.created_at, snapshot={'pipeline_run_id': handoff.pipeline_run_id, 'payload_ref': handoff.payload_ref}))

    return sorted(nodes, key=lambda node: (node.happened_at is None, node.happened_at or node.created_at, node.id))
