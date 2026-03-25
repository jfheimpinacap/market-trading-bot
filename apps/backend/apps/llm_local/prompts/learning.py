LEARNING_SYSTEM_PROMPT = """
You create concise learning notes for a local-first paper-trading memory system.
Do not suggest real-money execution.
Return only JSON.
""".strip()


def build_learning_prompt(*, summary: str, rationale: str, outcome: str) -> str:
    return f"""
Create an enriched learning note.

Context:
- Summary: {summary}
- Rationale: {rationale}
- Outcome: {outcome}

Respond as JSON with:
{{
  "note_title": "string >= 5 chars",
  "note_body": "string >= 20 chars",
  "tags": ["string", "... up to 8"],
  "suggested_follow_up": "string >= 10 chars"
}}
""".strip()
