import type { MarketSystemSummary } from '../../types/markets';
import { formatNumber } from './utils';

type MarketsSummaryCardsProps = {
  summary: MarketSystemSummary;
};

const metrics = [
  { key: 'total_markets', label: 'Total markets', hint: 'Complete catalog available in demo mode.' },
  { key: 'active_markets', label: 'Active markets', hint: 'Markets currently flagged active by the backend.' },
  { key: 'resolved_markets', label: 'Resolved markets', hint: 'Terminal markets useful for state and detail testing.' },
  { key: 'total_providers', label: 'Providers', hint: 'Demo providers currently exposed to the UI.' },
  { key: 'total_snapshots', label: 'Snapshots', hint: 'Recent history available for market detail inspection.' },
] as const;

export function MarketsSummaryCards({ summary }: MarketsSummaryCardsProps) {
  return (
    <section className="markets-summary-grid">
      {metrics.map((metric) => (
        <article key={metric.key} className="panel markets-summary-card">
          <p className="section-label">Summary</p>
          <h3>{metric.label}</h3>
          <div className="markets-summary-card__value">{formatNumber(summary[metric.key])}</div>
          <p>{metric.hint}</p>
        </article>
      ))}
    </section>
  );
}
