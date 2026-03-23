import type { PolicyDecisionType } from '../../types/policy';

function getLabel(decision: PolicyDecisionType) {
  if (decision === 'AUTO_APPROVE') {
    return 'Auto approve';
  }
  if (decision === 'APPROVAL_REQUIRED') {
    return 'Approval required';
  }
  if (decision === 'HARD_BLOCK') {
    return 'Hard block';
  }
  return decision;
}

export function PolicyDecisionBadge({ decision }: { decision: PolicyDecisionType }) {
  return <span className={`policy-decision-badge policy-decision-badge--${decision.toLowerCase()}`}>{getLabel(decision)}</span>;
}
