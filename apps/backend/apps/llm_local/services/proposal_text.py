from __future__ import annotations

from apps.llm_local.clients import OllamaChatClient
from apps.llm_local.prompts.proposal import PROPOSAL_SYSTEM_PROMPT, build_proposal_prompt
from apps.llm_local.schemas import ProposalThesisResult
from apps.proposal_engine.models import TradeProposal


def _build_context(data: dict) -> tuple[str, str, str, str, int | None]:
    proposal_id = data.get('proposal_id')
    if proposal_id:
        proposal = TradeProposal.objects.select_related('market').get(pk=proposal_id)
        return proposal.market.title, proposal.headline, proposal.thesis, proposal.rationale, proposal.id

    return (
        data.get('market_title', 'Unknown market'),
        data.get('headline', ''),
        data.get('thesis', ''),
        data.get('rationale', ''),
        None,
    )


def enrich_proposal_thesis(data: dict) -> dict:
    market_title, headline, thesis, rationale, proposal_id = _build_context(data)
    prompt = build_proposal_prompt(market_title=market_title, headline=headline, thesis=thesis, rationale=rationale)
    payload = OllamaChatClient().chat_json(
        system_prompt=PROPOSAL_SYSTEM_PROMPT,
        user_prompt=prompt,
        schema_hint='ProposalThesisResult',
    )
    result = ProposalThesisResult.from_payload(payload)
    return {
        'proposal_id': proposal_id,
        'market_title': market_title,
        'result': {
            'thesis': result.thesis,
            'summary': result.summary,
            'key_risks': result.key_risks,
            'confidence_note': result.confidence_note,
        },
    }
