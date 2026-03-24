import type { MouseEvent } from 'react';
import { navigate } from '../../lib/router';
import { formatDateTime, formatNumber } from '../markets/utils';
import { PolicyDecisionBadge } from '../policy/PolicyDecisionBadge';
import type { TradeProposal } from '../../types/proposals';
import {
  normalizeProposalConfidence,
  ProposalActionableBadge,
  ProposalApprovalBadge,
  ProposalDirectionBadge,
  ProposalStatusBadge,
} from './ProposalBadges';

type ProposalsTableProps = {
  proposals: TradeProposal[];
};

function handleClick(event: MouseEvent<HTMLAnchorElement>, path: string) {
  if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return;
  }

  event.preventDefault();
  navigate(path);
}

export function ProposalsTable({ proposals }: ProposalsTableProps) {
  return (
    <div className="markets-table-wrapper">
      <table className="markets-table signals-table">
        <thead>
          <tr>
            <th>Proposal</th>
            <th>Market</th>
            <th>Direction</th>
            <th>Suggested qty</th>
            <th>Score</th>
            <th>Confidence</th>
            <th>Risk</th>
            <th>Policy</th>
            <th>Approval</th>
            <th>Actionable</th>
            <th>Status</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {proposals.map((proposal) => (
            <tr key={proposal.id}>
              <td>
                <div className="signal-headline-cell">
                  <strong>{proposal.headline}</strong>
                  <span>{proposal.thesis}</span>
                </div>
              </td>
              <td>
                <a
                  href={`/markets/${proposal.market}`}
                  className="market-link"
                  onClick={(event) => handleClick(event, `/markets/${proposal.market}`)}
                >
                  <strong>{proposal.market_title}</strong>
                  <span>{proposal.market_slug}</span>
                </a>
              </td>
              <td><ProposalDirectionBadge direction={proposal.direction} /></td>
              <td>{proposal.suggested_quantity ? formatNumber(proposal.suggested_quantity) : '—'}</td>
              <td>{proposal.proposal_score}</td>
              <td>{normalizeProposalConfidence(proposal.confidence)}</td>
              <td>{proposal.risk_decision}</td>
              <td><PolicyDecisionBadge decision={proposal.policy_decision} /></td>
              <td><ProposalApprovalBadge approvalRequired={proposal.approval_required} /></td>
              <td><ProposalActionableBadge isActionable={proposal.is_actionable} /></td>
              <td><ProposalStatusBadge status={proposal.proposal_status} /></td>
              <td>{formatDateTime(proposal.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
