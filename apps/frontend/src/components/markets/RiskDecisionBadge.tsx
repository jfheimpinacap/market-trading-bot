import type { TradeRiskDecision } from '../../types/riskDemo';
import { titleize } from './utils';

type RiskDecisionBadgeProps = {
  decision: TradeRiskDecision;
};

export function RiskDecisionBadge({ decision }: RiskDecisionBadgeProps) {
  return <span className={`risk-decision-badge risk-decision-badge--${decision.toLowerCase()}`}>{titleize(decision)}</span>;
}
