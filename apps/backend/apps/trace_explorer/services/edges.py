from __future__ import annotations

from collections import defaultdict

from apps.trace_explorer.models import TraceEdge, TraceNode


RELATIONS_BY_STAGE = {
    ('RESEARCH', 'PREDICTION'): 'influenced_by',
    ('PREDICTION', 'RISK'): 'influenced_by',
    ('RISK', 'SIGNAL'): 'blocked_by',
    ('SIGNAL', 'PROPOSAL'): 'produced_by',
    ('PROPOSAL', 'ALLOCATION'): 'approved_by',
    ('ALLOCATION', 'EXECUTION'): 'executed_as',
    ('EXECUTION', 'VENUE'): 'mirrored_as',
    ('VENUE', 'INCIDENT'): 'degraded_by',
    ('PRECEDENT', 'PREDICTION'): 'influenced_by',
    ('PRECEDENT', 'RISK'): 'influenced_by',
    ('AGENT', 'AGENT'): 'handoff_to',
    ('MISSION', 'AGENT'): 'produced_by',
}


def build_edges(trace_root, nodes: list[TraceNode]) -> list[TraceEdge]:
    TraceEdge.objects.filter(trace_root=trace_root).delete()
    edges: list[TraceEdge] = []

    if len(nodes) < 2:
        return edges

    stage_bucket: dict[str, list[TraceNode]] = defaultdict(list)
    for node in nodes:
        stage_bucket[node.stage].append(node)

    for from_node, to_node in zip(nodes, nodes[1:]):
        relation = RELATIONS_BY_STAGE.get((from_node.stage, to_node.stage), 'derived_from')
        edges.append(
            TraceEdge.objects.create(
                trace_root=trace_root,
                from_node=from_node,
                to_node=to_node,
                relation=relation,
                summary=f'{to_node.node_type} {relation} {from_node.node_type}',
            )
        )

    if stage_bucket.get('PRECEDENT') and stage_bucket.get('PROPOSAL'):
        for precedent in stage_bucket['PRECEDENT'][:2]:
            edges.append(
                TraceEdge.objects.create(
                    trace_root=trace_root,
                    from_node=precedent,
                    to_node=stage_bucket['PROPOSAL'][0],
                    relation='influenced_by',
                    summary='Precedent context influenced proposal rationale',
                )
            )

    if stage_bucket.get('INCIDENT') and stage_bucket.get('EXECUTION'):
        for incident in stage_bucket['INCIDENT'][:2]:
            edges.append(
                TraceEdge.objects.create(
                    trace_root=trace_root,
                    from_node=incident,
                    to_node=stage_bucket['EXECUTION'][0],
                    relation='degraded_by',
                    summary='Incident context affected execution path',
                )
            )

    return edges
