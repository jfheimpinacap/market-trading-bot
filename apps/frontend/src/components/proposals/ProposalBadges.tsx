import type { TradeProposal, TradeProposalDirection, TradeProposalStatus } from '../../types/proposals';
import { titleize } from '../markets/utils';

function normalizeDirectionLabel(direction: TradeProposalDirection) {
  if (direction === 'BUY_YES') {
    return 'Buy YES';
  }
  if (direction === 'BUY_NO') {
    return 'Buy NO';
  }
  return titleize(direction);
}

function getDirectionClass(direction: TradeProposalDirection) {
  if (direction === 'BUY_YES') {
    return 'signal-badge signal-badge--bullish';
  }
  if (direction === 'BUY_NO') {
    return 'signal-badge signal-badge--bearish';
  }
  return 'signal-badge signal-badge--muted';
}

function normalizeStatusLabel(status: TradeProposalStatus) {
  return titleize(status);
}

function getStatusClass(status: TradeProposalStatus) {
  const normalized = status.toLowerCase();
  if (normalized === 'active' || normalized === 'executed') {
    return 'signal-badge signal-badge--actionable';
  }
  if (normalized === 'stale' || normalized === 'superseded') {
    return 'signal-badge signal-badge--monitor';
  }
  if (normalized === 'rejected') {
    return 'signal-badge signal-badge--bearish';
  }
  return 'signal-badge signal-badge--muted';
}

function normalizeActionableLabel(isActionable: boolean) {
  return isActionable ? 'Actionable' : 'Not actionable';
}

function getActionableClass(isActionable: boolean) {
  return isActionable ? 'signal-badge signal-badge--actionable' : 'signal-badge signal-badge--muted';
}

export function ProposalDirectionBadge({ direction }: { direction: TradeProposalDirection }) {
  return <span className={getDirectionClass(direction)}>{normalizeDirectionLabel(direction)}</span>;
}

export function ProposalStatusBadge({ status }: { status: TradeProposalStatus }) {
  return <span className={getStatusClass(status)}>{normalizeStatusLabel(status)}</span>;
}

export function ProposalActionableBadge({ isActionable }: { isActionable: boolean }) {
  return <span className={getActionableClass(isActionable)}>{normalizeActionableLabel(isActionable)}</span>;
}

export function ProposalApprovalBadge({ approvalRequired }: { approvalRequired: boolean }) {
  return (
    <span className={approvalRequired ? 'signal-badge signal-badge--monitor' : 'signal-badge signal-badge--muted'}>
      {approvalRequired ? 'Approval required' : 'No approval'}
    </span>
  );
}

export function normalizeProposalConfidence(value: TradeProposal['confidence']) {
  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    return value;
  }

  return `${Math.round(numericValue * 100)}%`;
}
