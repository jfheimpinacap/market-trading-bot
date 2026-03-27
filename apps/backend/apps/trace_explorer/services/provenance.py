from __future__ import annotations

from apps.trace_explorer.models import TraceNode


def build_provenance_snapshot(root, nodes: list[TraceNode], edges: list) -> dict:
    stages = []
    influences = []
    blockers = []
    outcome = None
    incident_context = None
    evidence = []

    for node in nodes:
        if node.stage and node.stage not in stages:
            stages.append(node.stage)
        if node.stage in {'PRECEDENT', 'PROFILE', 'CERTIFICATION'}:
            influences.append({'type': node.node_type, 'status': node.status, 'title': node.title})
        if node.status in {'BLOCKED', 'REJECTED', 'FAILED', 'DEGRADED'}:
            blockers.append({'type': node.node_type, 'status': node.status, 'summary': node.summary})
        if node.stage in {'EXECUTION', 'VENUE'}:
            outcome = {'type': node.node_type, 'status': node.status, 'summary': node.summary}
        if node.stage in {'INCIDENT', 'DEGRADED'}:
            incident_context = {'type': node.node_type, 'status': node.status, 'summary': node.summary}
        if node.stage in {'PRECEDENT', 'INCIDENT', 'CERTIFICATION', 'PROFILE', 'VENUE'}:
            evidence.append({'type': node.node_type, 'title': node.title, 'status': node.status})

    return {
        'root': {'id': root.id, 'type': root.root_type, 'object_id': root.root_object_id, 'label': root.label, 'status': root.current_status},
        'current_status': root.current_status,
        'key_stages': stages,
        'key_influences': influences[:6],
        'blockers_or_guards': blockers[:6],
        'execution_outcome': outcome,
        'incident_or_degraded_context': incident_context,
        'latest_related_evidence': evidence[:8],
        'node_count': len(nodes),
        'edge_count': len(edges),
    }
