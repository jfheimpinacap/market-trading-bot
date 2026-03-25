PROPOSAL_SYSTEM_PROMPT = """
You enrich trade proposal narratives for a local-first paper trading system.
You must NOT change operational decisions, risk decisions, policy decisions, or suggest real-money execution.
Return only JSON.
""".strip()


def build_proposal_prompt(*, market_title: str, headline: str, thesis: str, rationale: str) -> str:
    return f"""
Create an enriched proposal thesis.

Context:
- Market title: {market_title}
- Headline: {headline}
- Existing thesis: {thesis}
- Existing rationale: {rationale}

Respond as JSON with:
{{
  "thesis": "string >= 20 chars",
  "summary": "string >= 20 chars",
  "key_risks": ["string", "... up to 5"],
  "confidence_note": "string >= 10 chars"
}}
""".strip()
