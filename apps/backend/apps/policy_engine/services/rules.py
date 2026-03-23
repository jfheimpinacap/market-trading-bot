from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.policy_engine.models import ApprovalDecisionType, PolicySeverity


@dataclass
class PolicyRuleMatch:
    code: str
    title: str
    outcome: str
    severity: str
    message: str
    recommendation: str
    weight: Decimal = Decimal('0')


def hard_block_rule(*, code: str, title: str, message: str, recommendation: str, weight: str | Decimal = '1.00') -> PolicyRuleMatch:
    return PolicyRuleMatch(
        code=code,
        title=title,
        outcome=ApprovalDecisionType.HARD_BLOCK,
        severity=PolicySeverity.HIGH,
        message=message,
        recommendation=recommendation,
        weight=Decimal(str(weight)),
    )


def approval_required_rule(
    *,
    code: str,
    title: str,
    message: str,
    recommendation: str,
    severity: str = PolicySeverity.MEDIUM,
    weight: str | Decimal = '0.55',
) -> PolicyRuleMatch:
    return PolicyRuleMatch(
        code=code,
        title=title,
        outcome=ApprovalDecisionType.APPROVAL_REQUIRED,
        severity=severity,
        message=message,
        recommendation=recommendation,
        weight=Decimal(str(weight)),
    )


def auto_approve_rule(*, code: str, title: str, message: str, recommendation: str, weight: str | Decimal = '0.85') -> PolicyRuleMatch:
    return PolicyRuleMatch(
        code=code,
        title=title,
        outcome=ApprovalDecisionType.AUTO_APPROVE,
        severity=PolicySeverity.LOW,
        message=message,
        recommendation=recommendation,
        weight=Decimal(str(weight)),
    )
