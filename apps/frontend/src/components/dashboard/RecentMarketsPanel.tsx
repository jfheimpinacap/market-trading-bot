import type { MouseEvent } from 'react';
import { navigate } from '../../lib/router';
import type { RecentMarketItem } from '../../types/dashboard';
import { StatusBadge } from './StatusBadge';

type RecentMarketsPanelProps = {
  markets: RecentMarketItem[];
};

function formatProbability(value: string | null) {
  if (!value) {
    return 'No probability';
  }

  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    return value;
  }

  return `${Math.round(numericValue * 100)}% implied probability`;
}

function formatUpdatedAt(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

export function RecentMarketsPanel({ markets }: RecentMarketsPanelProps) {
  function handleClick(event: MouseEvent<HTMLAnchorElement>, path: string) {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }

    event.preventDefault();
    navigate(path);
  }

  return (
    <div className="dashboard-recent-list">
      {markets.map((market) => (
        <a
          key={market.id}
          className="dashboard-recent-list__item"
          href={`/markets/${market.id}`}
          onClick={(event) => handleClick(event, `/markets/${market.id}`)}
        >
          <div className="dashboard-recent-list__header">
            <div>
              <h3>{market.title}</h3>
              <p>{market.eventTitle ?? market.providerName}</p>
            </div>
            <StatusBadge tone="neutral">{market.status}</StatusBadge>
          </div>
          <dl className="dashboard-recent-list__meta">
            <div>
              <dt>Provider</dt>
              <dd>{market.providerName}</dd>
            </div>
            <div>
              <dt>Signal</dt>
              <dd>{formatProbability(market.probability)}</dd>
            </div>
            <div>
              <dt>Updated</dt>
              <dd>{formatUpdatedAt(market.updatedAt)}</dd>
            </div>
          </dl>
        </a>
      ))}
    </div>
  );
}
