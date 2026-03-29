from __future__ import annotations

from dataclasses import dataclass

from .candidates import InsightCandidate


@dataclass(slots=True)
class CampaignSynthesis:
    candidate: InsightCandidate
    domains: list[str]
    friction_score: int
    has_unresolved_followups: bool


def synthesize_campaign_evidence(candidates: list[InsightCandidate]) -> list[CampaignSynthesis]:
    synthesized: list[CampaignSynthesis] = []
    for candidate in candidates:
        if not candidate.lifecycle_closed:
            continue
        levels = {
            'LOW': 1,
            'MEDIUM': 2,
            'HIGH': 3,
        }
        friction_score = levels.get(candidate.approval_friction_level, 2) + levels.get(candidate.incident_pressure_level, 2) + levels.get(candidate.recovery_complexity_level, 2)
        domains = candidate.metadata.get('domains', []) if isinstance(candidate.metadata, dict) else []
        synthesized.append(
            CampaignSynthesis(
                candidate=candidate,
                domains=domains if isinstance(domains, list) else [],
                friction_score=friction_score,
                has_unresolved_followups=bool(candidate.metadata.get('unresolved_followups', 0)),
            )
        )
    return synthesized
