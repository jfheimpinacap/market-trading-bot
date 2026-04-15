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
            <th className="markets-table__title-col">Mercado</th>
            <th className="markets-table__short-col">Fuente</th>
            <th className="markets-table__short-col">Proveedor</th>
            <th className="markets-table__paper-col">Estado paper</th>
            <th className="markets-table__short-col">Categoría</th>
            <th className="markets-table__short-col">Estado</th>
            <th className="markets-table__short-col">Probabilidad</th>
            <th className="markets-table__number-col">Liquidez</th>
            <th className="markets-table__number-col">Volumen 24h</th>
            <th className="markets-table__number-col">Cierre estimado</th>
            <th className="markets-table__short-col">Actividad</th>
          </tr>
        </thead>
        <tbody>
          {markets.map((market) => (
            <tr key={market.id}>
              <td className="markets-table__title-col">
                <a href={`/markets/${market.id}`} className="market-link" onClick={(event) => handleMarketClick(event, market.id)}>
                  <strong>{market.title}</strong>
                  <span>{market.event_title ?? 'Mercado independiente'}</span>
                </a>
              </td>
              <td className="markets-table__short-col">
                <MarketSourceBadge sourceType={market.source_type} />
              </td>
              <td className="markets-table__short-col">
                <MarketProviderBadge providerName={market.provider.name} />
              </td>
              <td className="markets-table__paper-col">
                {market.paper_tradable ? (
                  <span className="market-badge market-badge--open">Apto para paper</span>
                ) : (
                  <div className="table-inline-stack">
                    <span className="market-badge market-badge--closed">No apto para paper</span>
                    {market.paper_tradable_reason ? <span className="muted-text">{market.paper_tradable_reason}</span> : null}
                  </div>
                )}
              </td>
              <td className="markets-table__short-col">{market.category || '—'}</td>
              <td className="markets-table__short-col">
                <MarketStatusBadge status={market.status} />
              </td>
              <td className="markets-table__short-col">
                <MarketProbabilityBadge value={market.current_market_probability} />
              </td>
              <td className="markets-table__number-col">{formatCompactCurrency(market.liquidity)}</td>
              <td className="markets-table__number-col">{formatCompactCurrency(market.volume_24h)}</td>
              <td className="markets-table__number-col">{formatDateTime(market.resolution_time)}</td>
              <td className="markets-table__short-col">
                <MarketActiveBadge isActive={market.is_active} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
