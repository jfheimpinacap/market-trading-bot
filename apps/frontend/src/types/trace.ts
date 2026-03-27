export type TraceRoot = {
  id: number;
  root_type: string;
  root_object_id: string;
  label: string;
  current_status: string;
  last_seen_at: string | null;
  metadata: Record<string, unknown>;
};

export type TraceNode = {
  id: number;
  node_type: string;
  stage: string;
  title: string;
  status: string;
  summary: string;
  ref_type: string;
  ref_id: string;
  happened_at: string | null;
  snapshot: Record<string, unknown>;
};

export type TraceEdge = {
  id: number;
  from_node: number;
  to_node: number;
  relation: string;
  summary: string;
};

export type TraceQueryRun = {
  id: number;
  root: number | null;
  root_type?: string;
  root_object_id?: string;
  query_type: string;
  status: string;
  partial: boolean;
  node_count: number;
  edge_count: number;
  summary: string;
  created_at: string;
};

export type ProvenanceSnapshot = {
  current_status: string;
  key_stages: string[];
  key_influences: Array<{ type: string; title: string; status: string }>;
  blockers_or_guards: Array<{ type: string; status: string; summary: string }>;
  execution_outcome: { type: string; status: string; summary: string } | null;
  incident_or_degraded_context: { type: string; status: string; summary: string } | null;
  latest_related_evidence: Array<{ type: string; title: string; status: string }>;
  node_count: number;
  edge_count: number;
};

export type TraceQueryResponse = {
  root: TraceRoot;
  nodes: TraceNode[];
  edges: TraceEdge[];
  snapshot: ProvenanceSnapshot;
  partial: boolean;
  query_run: TraceQueryRun;
};

export type TraceSummary = {
  total_roots: number;
  total_nodes: number;
  total_edges: number;
  roots_by_type: Array<{ root_type: string; count: number }>;
  latest_query_run: TraceQueryRun | null;
};
