# Research Agent (MVP)

`research_agent` implements the first narrative scan/research block of the local-first stack:

1. Ingest configurable narrative sources (RSS + Reddit + optional X/Twitter adapter).
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
- ✅ RSS + Reddit + Twitter multi-source fusion heuristics in shortlist (`source_mix`, conservative social weighting, convergence/divergence adjustments).
- ✅ X/Twitter adapter with auditable modes (`metadata.manual_items` or configurable `metadata.endpoint_url` fetch).
- ✅ Multi-source social normalization (`social_signal_strength`, `hype_risk`, `noise_risk`, cross-source agreement/divergence).
- ✅ Research scan run audit trace.
- ❌ No real money and no real execution.
- ❌ No aggressive X/Twitter scraping or thread/comment crawling.
- ❌ No Reddit comment crawling or aggressive scraping.
- ❌ No vector DB/RAG system.
- ❌ LLM is never authoritative for risk/policy/safety.

## Universe scanner / market triage board (new)

This module now formalizes the second research block: scan broad market universe, triage, and surface worth-pursuing markets.

### New persisted entities
- `MarketUniverseScanRun`: explicit run envelope with counters and top exclusion reasons.
- `MarketTriageDecision`: per-market score/status/reasons/flags.
- `PursuitCandidate`: formal board output (`shortlisted` or `watch`) for downstream prediction/risk.

### Services
- `services/market_triage.py`: profile thresholds + auditable triage scoring.
- `services/universe_scan.py`: run orchestration + persistence + triage-to-prediction handoff.
- `services/pursuit_board.py`: board summary + candidate retrieval.

### API surface
- `POST /api/research/run-universe-scan/`
- `GET /api/research/universe-scans/`
- `GET /api/research/universe-scans/<id>/`
- `GET /api/research/pursuit-candidates/`
- `GET /api/research/board-summary/`
- `POST /api/research/run-triage-to-prediction/`

### Operational boundaries
- narrative is contextual boost/caution, not a mandatory hard gate
- no real-money flow
- no real execution path
- no opaque optimizer/planner
