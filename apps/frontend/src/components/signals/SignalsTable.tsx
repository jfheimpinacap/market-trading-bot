import type { MouseEvent } from 'react';
import { navigate } from '../../lib/router';
import type { MarketSignal } from '../../types/signals';
import { formatActionableLabel } from '../../lib/demoFlow';
import { formatDateTime, formatPercent } from '../markets/utils';
import { ReviewOutcomeBadge } from '../postmortem/ReviewOutcomeBadge';
import { SignalBadge } from './SignalBadges';

type SignalWorkflowContext = {
  hasOpenPosition: boolean;
  latestTradeId?: number;
  latestReviewId?: number;
  latestReviewOutcome?: string;
  latestReviewStatus?: string;
};

type SignalsTableProps = {
  signals: MarketSignal[];
  workflowContextByMarket?: Record<number, SignalWorkflowContext>;
};

function handleClick(event: MouseEvent<HTMLAnchorElement>, path: string) {
  if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return;
  }

  event.preventDefault();
  navigate(path);
}

function formatConfidence(value: string) {
  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    return value;
  }
  return `${Math.round(numericValue * 100)}%`;
}

export function SignalsTable({ signals, workflowContextByMarket = {} }: SignalsTableProps) {
  return (
    <div className="markets-table-wrapper">
      <table className="markets-table signals-table">
        <thead>
          <tr>
            <th>Signal</th>
            <th>Market</th>
            <th>Agent</th>
            <th>Direction</th>
            <th>Status</th>
            <th>Actionable</th>
            <th>Score</th>
            <th>Confidence</th>
            <th>Edge</th>
            <th>Workflow</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((signal) => {
            const workflowContext = workflowContextByMarket[signal.market];
            const primaryPath = signal.is_actionable ? `/markets/${signal.market}` : `/markets/${signal.market}`;
            const primaryLabel = signal.is_actionable ? 'Evaluate trade' : 'Open market';

            return (
              <tr key={signal.id}>
                <td>
                  <div className="signal-headline-cell">
                    <strong>{signal.headline}</strong>
                    <span>{signal.thesis}</span>
                  </div>
                </td>
                <td>
                  <a href={`/markets/${signal.market}`} className="market-link" onClick={(event) => handleClick(event, `/markets/${signal.market}`)}>
                    <strong>{signal.market_title}</strong>
                    <span>{signal.market_provider_slug} · {signal.market_status}</span>
                  </a>
                </td>
                <td>{signal.agent?.name ?? 'Aggregate signal'}</td>
                <td><SignalBadge kind="direction" value={signal.direction} /></td>
                <td><SignalBadge kind="status" value={signal.status} /></td>
                <td><SignalBadge kind="actionable" value={formatActionableLabel(signal.is_actionable)} /></td>
                <td>{signal.score}</td>
                <td>{formatConfidence(signal.confidence)}</td>
                <td>{formatPercent(signal.edge_estimate)}</td>
                <td>
                  <div className="table-link-stack">
                    <a href={primaryPath} className="market-link" onClick={(event) => handleClick(event, primaryPath)}>
                      <strong>{primaryLabel}</strong>
                      <span>{workflowContext?.hasOpenPosition ? 'Open position already exists in this market.' : 'Inspect signal, risk, and execution context.'}</span>
                    </a>
                    {workflowContext?.hasOpenPosition ? (
                      <a href="/portfolio" className="market-link" onClick={(event) => handleClick(event, '/portfolio')}>
                        <strong>View portfolio</strong>
                        <span>Open position linked to this market.</span>
                      </a>
                    ) : null}
                    {workflowContext?.latestReviewId ? (
                      <a href={`/postmortem/${workflowContext.latestReviewId}`} className="market-link" onClick={(event) => handleClick(event, `/postmortem/${workflowContext.latestReviewId}`)}>
                        <strong>{workflowContext.latestReviewOutcome ? <ReviewOutcomeBadge outcome={workflowContext.latestReviewOutcome} status={workflowContext.latestReviewStatus} /> : 'Open review'}</strong>
                        <span>Latest review for this market.</span>
                      </a>
                    ) : null}
                  </div>
                </td>
                <td>{formatDateTime(signal.created_at)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
