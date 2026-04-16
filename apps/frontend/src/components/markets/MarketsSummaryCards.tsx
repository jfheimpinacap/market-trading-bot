import type { MarketSystemSummary } from '../../types/markets';
import { formatNumber } from './utils';

type MarketsSummaryCardsProps = {
  summary: MarketSystemSummary;
};

const metrics = [
  { key: 'total_markets', label: 'Mercados totales' },
  { key: 'active_markets', label: 'Mercados activos' },
  { key: 'resolved_markets', label: 'Mercados cerrados' },
  { key: 'total_providers', label: 'Proveedores' },
  { key: 'total_snapshots', label: 'Actualizaciones' },
] as const;

export function MarketsSummaryCards({ summary }: MarketsSummaryCardsProps) {
  return (
    <section className="markets-summary-grid">
      {metrics.map((metric) => (
        <article key={metric.key} className="panel markets-summary-card">
          <h3>{metric.label}</h3>
          <div className="markets-summary-card__value">{formatNumber(summary[metric.key])}</div>
        </article>
      ))}
    </section>
  );
}
