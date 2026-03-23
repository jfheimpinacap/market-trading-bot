import type { MouseEvent } from 'react';
import { navigate } from '../../lib/router';
import type { MarketSignal } from '../../types/signals';
import { formatDateTime, formatPercent } from '../markets/utils';
import { SignalBadge } from './SignalBadges';

type SignalsTableProps = {
  signals: MarketSignal[];
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

export function SignalsTable({ signals }: SignalsTableProps) {
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
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((signal) => (
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
              <td><SignalBadge kind="actionable" value={signal.is_actionable ? 'actionable' : 'monitor only'} /></td>
              <td>{signal.score}</td>
              <td>{formatConfidence(signal.confidence)}</td>
              <td>{formatPercent(signal.edge_estimate)}</td>
              <td>{formatDateTime(signal.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
