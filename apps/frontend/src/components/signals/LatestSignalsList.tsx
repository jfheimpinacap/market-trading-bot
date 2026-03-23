import type { MouseEvent } from 'react';
import { navigate } from '../../lib/router';
import type { MarketSignal } from '../../types/signals';
import { formatDateTime, formatPercent } from '../markets/utils';
import { SignalBadge } from './SignalBadges';

type LatestSignalsListProps = {
  signals: MarketSignal[];
  emptyMessage?: string;
};

function handleClick(event: MouseEvent<HTMLAnchorElement>, path: string) {
  if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return;
  }

  event.preventDefault();
  navigate(path);
}

export function LatestSignalsList({ signals, emptyMessage = 'No demo signals available yet.' }: LatestSignalsListProps) {
  if (signals.length === 0) {
    return <p className="muted-text">{emptyMessage}</p>;
  }

  return (
    <div className="signal-card-list">
      {signals.map((signal) => (
        <a
          key={signal.id}
          href={`/markets/${signal.market}`}
          className="signal-card"
          onClick={(event) => handleClick(event, `/markets/${signal.market}`)}
        >
          <div className="signal-card__header">
            <div>
              <h3>{signal.headline}</h3>
              <p>{signal.market_title}</p>
            </div>
            <SignalBadge kind="direction" value={signal.direction} />
          </div>
          <p className="signal-card__thesis">{signal.thesis}</p>
          <dl className="dashboard-key-value-list">
            <div>
              <dt>Agent</dt>
              <dd>{signal.agent?.name ?? 'Aggregate'}</dd>
            </div>
            <div>
              <dt>Score / confidence</dt>
              <dd>{signal.score} / {Math.round(Number(signal.confidence) * 100)}%</dd>
            </div>
            <div>
              <dt>Edge</dt>
              <dd>{formatPercent(signal.edge_estimate)}</dd>
            </div>
            <div>
              <dt>Created</dt>
              <dd>{formatDateTime(signal.created_at)}</dd>
            </div>
          </dl>
        </a>
      ))}
    </div>
  );
}
