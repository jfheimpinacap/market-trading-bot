from __future__ import annotations

from dataclasses import dataclass

from apps.execution_simulator.models import PaperOrder
from apps.incident_commander.models import IncidentRecord
from apps.markets.models import Market
from apps.mission_control.models import MissionControlCycle
from apps.opportunity_supervisor.models import OpportunityCycleItem
from apps.proposal_engine.models import TradeProposal
from apps.trace_explorer.models import TraceRoot
from apps.venue_account.models import VenueOrderSnapshot


@dataclass
class ResolvedRoot:
    root: TraceRoot
    context: dict


SUPPORTED_ROOT_TYPES = {
    'market',
    'opportunity',
    'proposal',
    'paper_order',
    'venue_order_snapshot',
    'incident',
    'mission_cycle',
}


def _label_and_status(root_type: str, root_id: str) -> tuple[str, str, dict]:
    metadata: dict = {}
    if root_type == 'market':
        market = Market.objects.filter(pk=root_id).first()
        if market:
            return market.title, market.status, {'market_id': market.id}
    elif root_type == 'opportunity':
        opportunity = OpportunityCycleItem.objects.select_related('market').filter(pk=root_id).first()
        if opportunity:
            return f'Opportunity item {opportunity.id}', opportunity.execution_path, {'market_id': opportunity.market_id, 'opportunity_id': opportunity.id, 'proposal_id': opportunity.proposal_id}
    elif root_type == 'proposal':
        proposal = TradeProposal.objects.select_related('market').filter(pk=root_id).first()
        if proposal:
            return f'Proposal {proposal.id}', proposal.proposal_status, {'market_id': proposal.market_id, 'proposal_id': proposal.id}
    elif root_type == 'paper_order':
        order = PaperOrder.objects.select_related('market').filter(pk=root_id).first()
        if order:
            return f'Paper order {order.id}', order.status, {'market_id': order.market_id, 'paper_order_id': order.id}
    elif root_type == 'venue_order_snapshot':
        snapshot = VenueOrderSnapshot.objects.filter(pk=root_id).first()
        if snapshot:
            return f'Venue snapshot {snapshot.external_order_id}', snapshot.status, {
                'venue_order_snapshot_id': snapshot.id,
                'paper_order_id': snapshot.source_paper_order_id,
                'broker_intent_id': snapshot.source_intent_id,
            }
    elif root_type == 'incident':
        incident = IncidentRecord.objects.filter(pk=root_id).first()
        if incident:
            return incident.title, incident.status, {'incident_id': incident.id, 'related_object_type': incident.related_object_type, 'related_object_id': incident.related_object_id}
    elif root_type == 'mission_cycle':
        cycle = MissionControlCycle.objects.filter(pk=root_id).first()
        if cycle:
            return f'Mission cycle {cycle.cycle_number}', cycle.status, {'mission_cycle_id': cycle.id}
    return f'{root_type}:{root_id}', '', metadata


def resolve_root(root_type: str, root_id: str) -> ResolvedRoot:
    normalized_type = root_type.strip().lower()
    if normalized_type not in SUPPORTED_ROOT_TYPES:
        raise ValueError(f'Unsupported root_type: {root_type}')

    label, status, metadata = _label_and_status(normalized_type, root_id)
    root, _ = TraceRoot.objects.get_or_create(
        root_type=normalized_type,
        root_object_id=str(root_id),
        defaults={
            'label': label,
            'current_status': status,
            'metadata': metadata,
        },
    )
    changed = False
    if label and root.label != label:
        root.label = label
        changed = True
    if status and root.current_status != status:
        root.current_status = status
        changed = True
    if metadata:
        merged = {**root.metadata, **metadata}
        if merged != root.metadata:
            root.metadata = merged
            changed = True
    if changed:
        root.save(update_fields=['label', 'current_status', 'metadata', 'updated_at'])

    context = {'root_type': normalized_type, 'root_id': str(root_id), **root.metadata}
    return ResolvedRoot(root=root, context=context)
