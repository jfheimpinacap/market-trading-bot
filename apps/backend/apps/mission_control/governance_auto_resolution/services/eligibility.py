from __future__ import annotations

from dataclasses import dataclass

from apps.mission_control.models import (
    GovernanceAutoResolutionDecisionType,
    GovernanceReviewItem,
    GovernanceReviewSeverity,
    GovernanceReviewSourceType,
)

_HARD_BLOCK_TOKENS = ('INCIDENT', 'SAFETY', 'RUNTIME_PRESSURE', 'HARD_BLOCK', 'KILL_SWITCH', 'STOP_SESSION')
_CONFLICT_TOKENS = ('CONFLICT', 'CROSS_LAYER_CONFLICT')
_ADVISORY_TOKENS = ('ADVISORY', 'EXPECTED', 'INFO_ONLY', 'SAFE_TO_DISMISS')
_FOLLOWUP_TOKENS = ('FOLLOWUP', 'DEFER', 'MONITOR', 'OBSERVE')
_SAFE_RETRY_TOKENS = ('SAFE_RETRY', 'AUTO_SAFE_RETRY', 'RETRY_SAFE_APPLY')


@dataclass
class EligibilityDecision:
    decision_type: str
    auto_applicable: bool
    decision_summary: str
    reason_codes: list[str]
    metadata: dict


def _signals(item: GovernanceReviewItem) -> list[str]:
    values: list[str] = []
    values.extend(code.upper() for code in (item.reason_codes or []) if isinstance(code, str))
    values.extend(code.upper() for code in (item.blockers or []) if isinstance(code, str))
    values.extend(str(key).upper() for key in (item.metadata or {}).keys())
    values.extend(str(value).upper() for value in (item.metadata or {}).values() if isinstance(value, str))
    return values


def _has_any(values: list[str], tokens: tuple[str, ...]) -> bool:
    return any(token in value for token in tokens for value in values)


def evaluate_auto_resolution_eligibility(item: GovernanceReviewItem) -> EligibilityDecision:
    signals = _signals(item)

    if item.severity in {GovernanceReviewSeverity.HIGH, GovernanceReviewSeverity.CRITICAL}:
        return EligibilityDecision(
            decision_type=GovernanceAutoResolutionDecisionType.DO_NOT_AUTO_RESOLVE,
            auto_applicable=False,
            decision_summary='High/critical governance item is not eligible for auto-resolution.',
            reason_codes=['AUTO_BLOCK_HIGH_OR_CRITICAL'],
            metadata={'severity': item.severity},
        )

    if _has_any(signals, _HARD_BLOCK_TOKENS):
        return EligibilityDecision(
            decision_type=GovernanceAutoResolutionDecisionType.DO_NOT_AUTO_RESOLVE,
            auto_applicable=False,
            decision_summary='Incident/safety/runtime-pressure signals require manual resolution.',
            reason_codes=['AUTO_BLOCK_INCIDENT_OR_SAFETY_OR_RUNTIME_PRESSURE'],
            metadata={'signals': signals},
        )

    if _has_any(signals, _CONFLICT_TOKENS):
        return EligibilityDecision(
            decision_type=GovernanceAutoResolutionDecisionType.DO_NOT_AUTO_RESOLVE,
            auto_applicable=False,
            decision_summary='Cross-layer conflict markers require manual operator review.',
            reason_codes=['AUTO_BLOCK_LAYER_CONFLICT'],
            metadata={'signals': signals},
        )

    if item.source_type == GovernanceReviewSourceType.SESSION_RECOVERY and item.metadata.get('auto_applicable') and _has_any(signals, _SAFE_RETRY_TOKENS):
        return EligibilityDecision(
            decision_type=GovernanceAutoResolutionDecisionType.AUTO_RETRY_SAFE_APPLY,
            auto_applicable=True,
            decision_summary='Session recovery item has explicit safe-retry support and no hard blockers.',
            reason_codes=['AUTO_SAFE_RETRY_EXPLICIT'],
            metadata={'source_type': item.source_type},
        )

    advisory_low_risk = item.severity in {GovernanceReviewSeverity.INFO, GovernanceReviewSeverity.CAUTION} and not item.blockers
    if advisory_low_risk and _has_any(signals, _ADVISORY_TOKENS):
        return EligibilityDecision(
            decision_type=GovernanceAutoResolutionDecisionType.AUTO_DISMISS,
            auto_applicable=True,
            decision_summary='Advisory-only low-risk item with no real blockers is safe to auto-dismiss.',
            reason_codes=['AUTO_DISMISS_ADVISORY_LOW_RISK'],
            metadata={'source_type': item.source_type},
        )

    if item.severity in {GovernanceReviewSeverity.INFO, GovernanceReviewSeverity.CAUTION} and _has_any(signals, _FOLLOWUP_TOKENS):
        return EligibilityDecision(
            decision_type=GovernanceAutoResolutionDecisionType.AUTO_REQUIRE_FOLLOWUP,
            auto_applicable=True,
            decision_summary='Low-risk item is marked for deferred follow-up without unsafe apply.',
            reason_codes=['AUTO_REQUIRE_FOLLOWUP_LOW_RISK'],
            metadata={'source_type': item.source_type},
        )

    return EligibilityDecision(
        decision_type=GovernanceAutoResolutionDecisionType.DO_NOT_AUTO_RESOLVE,
        auto_applicable=False,
        decision_summary='No explicit low-risk auto-resolution path was found.',
        reason_codes=['AUTO_NO_EXPLICIT_SAFE_PATH'],
        metadata={'source_type': item.source_type},
    )
