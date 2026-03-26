# Research Agent (MVP)

`research_agent` implements the first narrative scan/research block of the local-first stack:

1. Ingest configurable narrative sources (RSS + Reddit in this phase).
2. Deduplicate and persist narrative items.
3. Run structured analysis (local LLM via Ollama, with heuristic degradation fallback).
4. Link narrative items to real read-only markets using transparent heuristics.
5. Generate persisted research candidates/shortlist with narrative-vs-market relation flags.

## Scope in this MVP

- ✅ RSS/news feed ingestion.
- ✅ Reddit submissions ingestion (`hot/new/top`) from configured subreddits using public JSON listing reads.
- ✅ Structured analysis fields (`summary`, `sentiment`, `confidence`, `topics`, `entities`, relevance).
- ✅ Social narrative fields persisted in analysis metadata (`social_signal_strength`, `hype_risk`, `noise_risk`, market implication).
- ✅ Basic market linking and shortlist generation.
- ✅ RSS + Reddit fusion heuristics in shortlist (`source_mix`, conservative social weighting, convergence/divergence adjustments).
- ✅ Research scan run audit trace.
- ❌ No real money and no real execution.
- ❌ No X/Twitter scraping in this phase.
- ❌ No Reddit comment crawling or aggressive scraping.
- ❌ No vector DB/RAG system.
- ❌ LLM is never authoritative for risk/policy/safety.
