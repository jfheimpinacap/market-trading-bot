import type { MouseEvent } from 'react';
import type { MarketListItem } from '../../types/markets';
import { navigate } from '../../lib/router';
import { MarketActiveBadge } from './MarketActiveBadge';
import { MarketProbabilityBadge } from './MarketProbabilityBadge';
import { MarketStatusBadge } from './MarketStatusBadge';
import { formatCompactCurrency, formatDateTime } from './utils';

type MarketsTableProps = {
  markets: MarketListItem[];
};

export function MarketsTable({ markets }: MarketsTableProps) {
  function handleMarketClick(event: MouseEvent<HTMLAnchorElement>, marketId: number) {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }

    event.preventDefault();
    navigate(`/markets/${marketId}`);
  }

  return (
    <div className="markets-table-wrapper">
      <table className="markets-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Provider</th>
            <th>Category</th>
            <th>Status</th>
            <th>Probability</th>
            <th>Liquidity</th>
            <th>24h volume</th>
            <th>Resolution time</th>
            <th>Activity</th>
          </tr>
        </thead>
        <tbody>
          {markets.map((market) => (
            <tr key={market.id}>
              <td>
                <a href={`/markets/${market.id}`} className="market-link" onClick={(event) => handleMarketClick(event, market.id)}>
                  <strong>{market.title}</strong>
                  <span>{market.event_title ?? 'Standalone market'}</span>
                </a>
              </td>
              <td>{market.provider.name}</td>
              <td>{market.category || '—'}</td>
              <td>
                <MarketStatusBadge status={market.status} />
              </td>
              <td>
                <MarketProbabilityBadge value={market.current_market_probability} />
              </td>
              <td>{formatCompactCurrency(market.liquidity)}</td>
              <td>{formatCompactCurrency(market.volume_24h)}</td>
              <td>{formatDateTime(market.resolution_time)}</td>
              <td>
                <MarketActiveBadge isActive={market.is_active} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
