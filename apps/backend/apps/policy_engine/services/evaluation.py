from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q

from apps.markets.models import Market, MarketStatus
from apps.paper_trading.models import PaperAccount, PaperPositionStatus, PaperPositionSide, PaperTradeType
from apps.paper_trading.services.portfolio import get_active_account
from apps.paper_trading.services.valuation import get_market_price
from apps.policy_engine.models import (
    ApprovalDecision,
    ApprovalDecisionType,
    PolicyRequestedBy,
    PolicySeverity,
    PolicyTriggeredFrom,
)
from apps.policy_engine.services.rules import PolicyRuleMatch, approval_required_rule, auto_approve_rule, hard_block_rule
from apps.risk_demo.models import TradeRiskAssessment, TradeRiskDecision
from apps.signals.models import MarketSignal, MarketSignalStatus

ZERO = Decimal('0')
ONE = Decimal('1')

BLOCKED_MARKET_STATES = {
    MarketStatus.CLOSED,
    MarketStatus.RESOLVED,
    MarketStatus.CANCELLED,
    MarketStatus.ARCHIVED,
}


@dataclass
class TradePolicyContext:
    market: Market
    paper_account: PaperAccount | None
    trade_type: str
    side: str
    quantity: Decimal
    requested_price: Decimal | None
    triggered_from: str
    requested_by: str
    risk_assessment: TradeRiskAssessment | None
    linked_signal: MarketSignal | None
    estimated_price: Decimal | None
    estimated_gross_amount: Decimal | None
    existing_market_value: Decimal
    existing_market_quantity: Decimal
    concentration_ratio: Decimal
    cash_ratio: Decimal
    metadata: dict


class PolicyEvaluationError(ValueError):
    pass


def quantize_quantity(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def quantize_money(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def quantize_confidence(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def clamp(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    return max(minimum, min(value, maximum))


def _get_requested_price(market: Market, side: str, requested_price) -> Decimal | None:
    if requested_price is not None:
        return Decimal(str(requested_price)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    try:
        return get_market_price(market=market, side=side)
    except Exception:
        return None


def build_trade_policy_context(
    *,
    market: Market,
    trade_type: str,
    side: str,
    quantity,
    requested_price=None,
    triggered_from: str = PolicyTriggeredFrom.MARKET_DETAIL,
    requested_by: str = PolicyRequestedBy.USER,
    risk_assessment: TradeRiskAssessment | None = None,
    metadata: dict | None = None,
) -> TradePolicyContext:
    trade_type = trade_type.upper()
    side = side.upper()
    if trade_type not in PaperTradeType.values:
        raise PolicyEvaluationError(f'Unsupported trade_type: {trade_type}')
    if side not in PaperPositionSide.values:
        raise PolicyEvaluationError(f'Unsupported side: {side}')
    if triggered_from not in PolicyTriggeredFrom.values:
        raise PolicyEvaluationError(f'Unsupported triggered_from: {triggered_from}')
    if requested_by not in PolicyRequestedBy.values:
        raise PolicyEvaluationError(f'Unsupported requested_by: {requested_by}')

    quantity = quantize_quantity(quantity)
    if quantity <= ZERO:
        raise PolicyEvaluationError('Quantity must be greater than zero.')

    metadata = metadata or {}
    paper_account = get_active_account()
    estimated_price = _get_requested_price(market, side, requested_price)
    estimated_gross_amount = quantize_money(quantity * estimated_price) if estimated_price is not None else None

    open_positions = paper_account.positions.filter(status=PaperPositionStatus.OPEN, quantity__gt=0)
    same_market_positions = list(open_positions.filter(market=market).select_related('market'))
    existing_market_value = quantize_money(sum((position.market_value for position in same_market_positions), ZERO)) or ZERO
    existing_market_quantity = quantize_quantity(sum((position.quantity for position in same_market_positions), ZERO))
    cash_balance = paper_account.cash_balance or ZERO
    equity = paper_account.equity or cash_balance
    cash_ratio = ZERO
    if estimated_gross_amount is not None and cash_balance > ZERO:
        cash_ratio = estimated_gross_amount / cash_balance
    concentration_ratio = ZERO
    if estimated_gross_amount is not None and equity > ZERO:
        concentration_ratio = (existing_market_value + estimated_gross_amount) / equity

    linked_signal = (
        MarketSignal.objects.filter(market=market, status__in=[MarketSignalStatus.ACTIVE, MarketSignalStatus.MONITOR])
        .order_by('-created_at', '-id')
        .first()
    )

    return TradePolicyContext(
        market=market,
        paper_account=paper_account,
        trade_type=trade_type,
        side=side,
        quantity=quantity,
        requested_price=Decimal(str(requested_price)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP) if requested_price is not None else None,
        triggered_from=triggered_from,
        requested_by=requested_by,
        risk_assessment=risk_assessment,
        linked_signal=linked_signal,
        estimated_price=estimated_price,
        estimated_gross_amount=estimated_gross_amount,
        existing_market_value=existing_market_value,
        existing_market_quantity=existing_market_quantity,
        concentration_ratio=concentration_ratio,
        cash_ratio=cash_ratio,
        metadata=metadata,
    )


def evaluate_trade_policy(
    *,
    market: Market,
    trade_type: str,
    side: str,
    quantity,
    requested_price=None,
    triggered_from: str = PolicyTriggeredFrom.MARKET_DETAIL,
    requested_by: str = PolicyRequestedBy.USER,
    risk_assessment: TradeRiskAssessment | None = None,
    metadata: dict | None = None,
) -> ApprovalDecision:
    context = build_trade_policy_context(
        market=market,
        trade_type=trade_type,
        side=side,
        quantity=quantity,
        requested_price=requested_price,
        triggered_from=triggered_from,
        requested_by=requested_by,
        risk_assessment=risk_assessment,
        metadata=metadata,
    )
    matched_rules = match_policy_rules(context)
    return persist_policy_decision(context=context, matched_rules=matched_rules)


def match_policy_rules(context: TradePolicyContext) -> list[PolicyRuleMatch]:
    matches: list[PolicyRuleMatch] = []
    market = context.market
    account = context.paper_account
    risk = context.risk_assessment
    signal = context.linked_signal

    if account is None:
        matches.append(
            hard_block_rule(
                code='NO_PAPER_ACCOUNT',
                title='Missing paper account',
                message='No active demo paper account is available, so the trade cannot enter the policy flow.',
                recommendation='Seed or reactivate the local demo paper account before evaluating new trade proposals.',
            )
        )
        return matches

    if not market.is_active:
        matches.append(
            hard_block_rule(
                code='MARKET_INACTIVE',
                title='Inactive market',
                message='This market is inactive in the local demo state, so policy blocks execution.',
                recommendation='Choose an active market or refresh the local demo market state.',
            )
        )

    if market.status in BLOCKED_MARKET_STATES or market.status == MarketStatus.PAUSED:
        matches.append(
            hard_block_rule(
                code='MARKET_NOT_OPERABLE',
                title='Market not operable',
                message=f'This market is {market.status} and is not eligible for paper execution.',
                recommendation='Pick a tradable market in OPEN status before continuing.',
            )
        )

    if context.estimated_price is None or context.estimated_gross_amount is None:
        matches.append(
            hard_block_rule(
                code='PRICE_UNAVAILABLE',
                title='Missing trade price',
                message='The policy engine could not estimate a valid demo execution price for this proposal.',
                recommendation='Refresh the market data and re-evaluate the trade before executing it.',
            )
        )

    if risk and risk.decision == TradeRiskDecision.BLOCK:
        matches.append(
            hard_block_rule(
                code='RISK_BLOCK',
                title='Risk guard block',
                message='The linked risk assessment already returned BLOCK, so policy cannot override it.',
                recommendation='Review the risk warnings and adjust the proposal before trying again.',
            )
        )

    if context.trade_type == PaperTradeType.BUY and context.cash_ratio >= Decimal('0.90'):
        matches.append(
            hard_block_rule(
                code='BUY_TOO_LARGE_FOR_CASH',
                title='Trade too large for cash',
                message='This proposal would consume nearly all available demo cash in a single step.',
                recommendation='Reduce quantity materially before requesting execution.',
            )
        )
    elif context.trade_type == PaperTradeType.BUY and context.cash_ratio >= Decimal('0.35'):
        matches.append(
            approval_required_rule(
                code='BUY_LARGE_FOR_CASH',
                title='Large cash usage',
                message='This proposal uses a large share of the current demo cash balance.',
                recommendation='Confirm manually if you still want to allocate this much cash to one trade.',
            )
        )

    if context.concentration_ratio >= Decimal('0.60') or context.existing_market_quantity >= Decimal('100.0000'):
        matches.append(
            hard_block_rule(
                code='MARKET_EXPOSURE_TOO_HIGH',
                title='Exposure too high',
                message='The account would become overly concentrated in this single market after execution.',
                recommendation='Reduce quantity or diversify into a different market first.',
            )
        )
    elif context.concentration_ratio >= Decimal('0.35') or context.existing_market_quantity >= Decimal('50.0000'):
        matches.append(
            approval_required_rule(
                code='MARKET_EXPOSURE_REVIEW',
                title='Existing exposure review',
                message='The account already has meaningful exposure in this market, so manual approval is required.',
                recommendation='Review current position size and confirm the portfolio concentration intentionally.',
            )
        )

    if risk is None:
        matches.append(
            approval_required_rule(
                code='RISK_CONTEXT_MISSING',
                title='Risk context missing',
                message='No linked risk assessment was provided, so policy requires manual review rather than auto-approval.',
                recommendation='Run the demo risk check first if you want a cleaner approval path.',
                severity=PolicySeverity.LOW,
                weight='0.45',
            )
        )
    elif risk.decision == TradeRiskDecision.CAUTION:
        matches.append(
            approval_required_rule(
                code='RISK_CAUTION_TRANSLATED',
                title='Risk caution translated to approval gate',
                message='The linked risk assessment returned CAUTION, so policy escalates the trade to manual approval.',
                recommendation='Review the risk warnings, then confirm explicitly if the demo trade is still desired.',
                severity=PolicySeverity.MEDIUM,
                weight='0.65',
            )
        )

    if signal and not signal.is_actionable and context.trade_type == PaperTradeType.BUY:
        matches.append(
            approval_required_rule(
                code='SIGNAL_NOT_ACTIONABLE',
                title='Signal is monitor-only',
                message='The latest demo signal for this market is not actionable, so policy does not auto-approve the trade.',
                recommendation='Wait for a stronger signal or confirm manually that this trade is still worth taking.',
                severity=PolicySeverity.LOW,
                weight='0.40',
            )
        )

    if context.triggered_from == PolicyTriggeredFrom.AUTOMATION and context.cash_ratio >= Decimal('0.15'):
        matches.append(
            approval_required_rule(
                code='AUTOMATION_REQUIRES_CONFIRMATION',
                title='Automation threshold crossed',
                message='Automation-originated proposals above the small-size threshold require a human confirmation step.',
                recommendation='Review the automation suggestion manually before allowing paper execution.',
                severity=PolicySeverity.MEDIUM,
                weight='0.60',
            )
        )

    if not matches:
        matches.append(
            auto_approve_rule(
                code='SMALL_TRADE_AUTO_APPROVE',
                title='Small trade within guardrails',
                message='This proposal is small, the market is operable, and no approval-only rule was triggered.',
                recommendation='You can execute the demo paper trade directly from the current flow.',
            )
        )

    return matches


def persist_policy_decision(*, context: TradePolicyContext, matched_rules: list[PolicyRuleMatch]) -> ApprovalDecision:
    decision = derive_final_decision(matched_rules)
    severity = derive_severity(matched_rules)
    summary = build_summary(decision, matched_rules)
    rationale = build_rationale(context, matched_rules, decision)
    recommendation = ' '.join(dict.fromkeys(rule.recommendation for rule in matched_rules if rule.recommendation)).strip()
    confidence = derive_confidence(matched_rules)

    return ApprovalDecision.objects.create(
        market=context.market,
        paper_account=context.paper_account,
        risk_assessment=context.risk_assessment,
        linked_signal=context.linked_signal,
        trade_type=context.trade_type,
        side=context.side,
        quantity=context.quantity,
        requested_price=context.requested_price,
        estimated_gross_amount=context.estimated_gross_amount,
        requested_by=context.requested_by,
        triggered_from=context.triggered_from,
        decision=decision,
        severity=severity,
        confidence=confidence,
        summary=summary,
        rationale=rationale,
        matched_rules=[
            {
                'code': rule.code,
                'title': rule.title,
                'outcome': rule.outcome,
                'severity': rule.severity,
                'message': rule.message,
                'recommendation': rule.recommendation,
            }
            for rule in matched_rules
        ],
        recommendation=recommendation,
        risk_decision=context.risk_assessment.decision if context.risk_assessment else None,
        metadata={
            'estimated_price': f'{context.estimated_price:.4f}' if context.estimated_price is not None else None,
            'estimated_gross_amount': f'{context.estimated_gross_amount:.2f}' if context.estimated_gross_amount is not None else None,
            'cash_ratio': f'{context.cash_ratio:.4f}',
            'concentration_ratio': f'{context.concentration_ratio:.4f}',
            'existing_market_value': f'{context.existing_market_value:.2f}',
            'existing_market_quantity': f'{context.existing_market_quantity:.4f}',
            'linked_signal_actionable': context.linked_signal.is_actionable if context.linked_signal else None,
            'linked_signal_status': context.linked_signal.status if context.linked_signal else None,
            **context.metadata,
        },
    )


def derive_final_decision(matched_rules: list[PolicyRuleMatch]) -> str:
    outcomes = {rule.outcome for rule in matched_rules}
    if ApprovalDecisionType.HARD_BLOCK in outcomes:
        return ApprovalDecisionType.HARD_BLOCK
    if ApprovalDecisionType.APPROVAL_REQUIRED in outcomes:
        return ApprovalDecisionType.APPROVAL_REQUIRED
    return ApprovalDecisionType.AUTO_APPROVE


def derive_severity(matched_rules: list[PolicyRuleMatch]) -> str:
    severities = {rule.severity for rule in matched_rules}
    if PolicySeverity.HIGH in severities:
        return PolicySeverity.HIGH
    if PolicySeverity.MEDIUM in severities:
        return PolicySeverity.MEDIUM
    return PolicySeverity.LOW


def derive_confidence(matched_rules: list[PolicyRuleMatch]) -> Decimal:
    if any(rule.outcome == ApprovalDecisionType.HARD_BLOCK for rule in matched_rules):
        base = Decimal('0.93')
    elif any(rule.outcome == ApprovalDecisionType.APPROVAL_REQUIRED for rule in matched_rules):
        base = Decimal('0.78')
    else:
        base = Decimal('0.88')
    adjustment = Decimal('0.03') * Decimal(max(len(matched_rules) - 1, 0))
    return quantize_confidence(clamp(base - adjustment, Decimal('0.45'), Decimal('0.95')))


def build_summary(decision: str, matched_rules: list[PolicyRuleMatch]) -> str:
    first_rule = matched_rules[0]
    if decision == ApprovalDecisionType.HARD_BLOCK:
        return f'Policy blocked this trade because {first_rule.title.lower()}.'
    if decision == ApprovalDecisionType.APPROVAL_REQUIRED:
        return f'Policy requires manual approval because {first_rule.title.lower()}.'
    return 'Policy auto-approved this trade because it remains within the current demo guardrails.'


def build_rationale(context: TradePolicyContext, matched_rules: list[PolicyRuleMatch], decision: str) -> str:
    rule_text = ' '.join(f'{rule.title}: {rule.message}' for rule in matched_rules)
    risk_part = (
        f'Linked risk decision is {context.risk_assessment.decision}. '
        if context.risk_assessment is not None
        else 'No linked risk decision was provided. '
    )
    signal_part = (
        f'Latest signal status is {context.linked_signal.status} and actionable={context.linked_signal.is_actionable}. '
        if context.linked_signal is not None
        else 'No recent signal was linked for this market. '
    )
    price_text = f'{context.estimated_price:.4f}' if context.estimated_price is not None else 'n/a'
    gross_text = f'{context.estimated_gross_amount:.2f}' if context.estimated_gross_amount is not None else 'n/a'
    return (
        f'Proposed {context.trade_type} {context.side} {context.quantity:.4f} on {context.market.title} '
        f'from {context.triggered_from} requested by {context.requested_by}. Estimated price {price_text} '
        f'and gross amount {gross_text} were compared against demo account cash, current market status, '
        f'and existing exposure. {risk_part}{signal_part}Final policy decision is {decision}. {rule_text}'
    )
