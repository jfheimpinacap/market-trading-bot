import type { MarketSystemSummary } from '../../types/markets';
import { formatNumber } from './utils';

type MarketsSummaryCardsProps = {
  summary: MarketSystemSummary;
};

const metrics = [
  { key: 'total_markets', label: 'Mercados totales', hint: 'Cantidad total disponible para explorar.' },
  { key: 'active_markets', label: 'Mercados activos', hint: 'Mercados que hoy siguen abiertos o en curso.' },
  { key: 'resolved_markets', label: 'Mercados cerrados', hint: 'Mercados ya finalizados para referencia histórica.' },
  { key: 'total_providers', label: 'Proveedores', hint: 'Fuentes de datos visibles en esta vista.' },
  { key: 'total_snapshots', label: 'Actualizaciones guardadas', hint: 'Historial reciente para revisar cambios.' },
] as const;

export function MarketsSummaryCards({ summary }: MarketsSummaryCardsProps) {
  return (
    <section className="markets-summary-grid">
      {metrics.map((metric) => (
        <article key={metric.key} className="panel markets-summary-card">
          <p className="section-label">Resumen</p>
          <h3>{metric.label}</h3>
          <div className="markets-summary-card__value">{formatNumber(summary[metric.key])}</div>
          <p>{metric.hint}</p>
        </article>
      ))}
    </section>
  );
}
