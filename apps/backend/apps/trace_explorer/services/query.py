from __future__ import annotations

from apps.trace_explorer.models import TraceQueryRun, TraceQueryRunStatus
from apps.trace_explorer.services.edges import build_edges
from apps.trace_explorer.services.nodes import collect_nodes
from apps.trace_explorer.services.provenance import build_provenance_snapshot
from apps.trace_explorer.services.roots import resolve_root


def run_trace_query(*, root_type: str, root_id: str, query_type: str = 'root_lookup', query_payload: dict | None = None) -> dict:
    payload = query_payload or {'root_type': root_type, 'root_id': str(root_id)}
    resolved = resolve_root(root_type=root_type, root_id=str(root_id))
    nodes = collect_nodes(resolved.root, resolved.context)
    edges = build_edges(resolved.root, nodes)
    partial = len(nodes) < 4

    if nodes:
        latest_happened = next((node.happened_at for node in reversed(nodes) if node.happened_at), None)
        if latest_happened:
            resolved.root.last_seen_at = latest_happened
            resolved.root.save(update_fields=['last_seen_at', 'updated_at'])

    status = TraceQueryRunStatus.PARTIAL if partial else TraceQueryRunStatus.SUCCESS
    query_run = TraceQueryRun.objects.create(
        root=resolved.root,
        query_type=query_type,
        query_payload=payload,
        status=status,
        partial=partial,
        node_count=len(nodes),
        edge_count=len(edges),
        summary='No trace data found for this object yet.' if len(nodes) == 0 else f'Built trace with {len(nodes)} nodes and {len(edges)} edges.',
    )

    snapshot = build_provenance_snapshot(resolved.root, nodes, edges)
    return {
        'root': resolved.root,
        'nodes': nodes,
        'edges': edges,
        'snapshot': snapshot,
        'partial': partial,
        'query_run': query_run,
    }
