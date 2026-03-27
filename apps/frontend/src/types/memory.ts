export type MemoryDocument = {
  id: number;
  document_type: string;
  source_app: string;
  source_object_id: string;
  title: string;
  text_content: string;
  structured_summary: Record<string, unknown>;
  tags: string[];
  metadata: Record<string, unknown>;
  embedding_model: string;
  embedded_at: string | null;
  created_at: string;
  updated_at: string;
};

export type RetrievedPrecedent = {
  id: number;
  retrieval_run: number;
  memory_document: MemoryDocument;
  similarity_score: number;
  rank: number;
  short_reason: string;
  created_at: string;
  updated_at: string;
};

export type MemoryRetrievalRun = {
  id: number;
  query_text: string;
  query_type: string;
  context_metadata: Record<string, unknown>;
  result_count: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  precedents: RetrievedPrecedent[];
};

export type MemorySummary = {
  documents_indexed: number;
  retrieval_runs: number;
  document_types: Record<string, number>;
  source_apps: Record<string, number>;
  last_indexed_document_at: string | null;
  last_retrieval_run: MemoryRetrievalRun | null;
};

export type MemoryPrecedentSummary = {
  retrieval_run_id: number;
  query_text: string;
  query_type: string;
  matches: number;
  average_similarity: number | null;
  most_similar_cases: Array<{ rank: number; title: string; document_type: string; similarity_score: number }>;
  by_document_type: Record<string, number>;
  prior_caution_signals: string[];
  prior_failure_modes: string[];
  lessons_learned: string[];
};

export type MemoryRunResponse = {
  run: MemoryRetrievalRun;
  summary: MemoryPrecedentSummary;
};
