POSTMORTEM_SYSTEM_PROMPT = """
You enrich post-mortem reviews for a controlled local demo trading system.
Do not invent executions, and do not override the base review outcome.
Return only JSON.
""".strip()


def build_postmortem_prompt(*, summary: str, rationale: str, lesson: str, recommendation: str) -> str:
    return f"""
Create an enriched post-mortem summary and lessons.

Context:
- Base summary: {summary}
- Base rationale: {rationale}
- Base lesson: {lesson}
- Base recommendation: {recommendation}

Respond as JSON with:
{{
  "enriched_summary": "string >= 20 chars",
  "lessons_learned": ["string", "... up to 5"],
  "action_items": ["string", "... up to 5"]
}}
""".strip()
