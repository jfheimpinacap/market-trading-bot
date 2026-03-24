import type { MouseEvent } from 'react';
import type { MarketListItem } from '../../types/markets';
import { navigate } from '../../lib/router';
import { MarketActiveBadge } from './MarketActiveBadge';
import { MarketProbabilityBadge } from './MarketProbabilityBadge';
import { MarketProviderBadge } from './MarketProviderBadge';
import { MarketStatusBadge } from './MarketStatusBadge';
import { MarketSourceBadge } from './MarketSourceBadge';
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
            <th>Source</th>
            <th>Provider</th>
            <th>Paper mode</th>
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
              <td>
                <MarketSourceBadge sourceType={market.source_type} />
              </td>
              <td>
                <MarketProviderBadge providerName={market.provider.name} />
              </td>
              <td>
                {market.paper_tradable ? (
                  <span className="market-badge market-badge--open">Paper-tradable</span>
                ) : (
                  <div className="table-inline-stack">
                    <span className="market-badge market-badge--closed">Not paper-tradable</span>
                    {market.paper_tradable_reason ? <span className="muted-text">{market.paper_tradable_reason}</span> : null}
                  </div>
                )}
              </td>
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
