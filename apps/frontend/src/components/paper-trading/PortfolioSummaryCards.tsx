import type { PaperAccount, PaperPortfolioSummary } from '../../types/paperTrading';
import { PnlBadge } from './PnlBadge';
import { formatPaperCurrency } from './utils';

type PortfolioSummaryCardsProps = {
  account: PaperAccount;
  summary: PaperPortfolioSummary | null;
  totalTrades: number;
};

type SummaryMetric = {
  label: string;
  value: string;
  helperText: string;
  emphasis?: 'pnl';
  rawValue?: string;
};

export function PortfolioSummaryCards({ account, summary, totalTrades }: PortfolioSummaryCardsProps) {
  const metrics: SummaryMetric[] = [
    {
      label: 'Cash',
      value: formatPaperCurrency(account.cash_balance, account.currency),
      helperText: 'Available virtual cash balance in the active demo account.',
    },
    {
      label: 'Equity',
      value: formatPaperCurrency(account.equity, account.currency),
      helperText: 'Cash plus marked value of current open positions.',
    },
    {
      label: 'Realized PnL',
      value: formatPaperCurrency(account.realized_pnl, account.currency),
      helperText: 'PnL from closed paper trades already booked by the backend.',
      emphasis: 'pnl',
      rawValue: account.realized_pnl,
    },
    {
      label: 'Unrealized PnL',
      value: formatPaperCurrency(account.unrealized_pnl, account.currency),
      helperText: 'Mark-to-market PnL across currently open demo positions.',
      emphasis: 'pnl',
      rawValue: account.unrealized_pnl,
    },
    {
      label: 'Total PnL',
      value: formatPaperCurrency(account.total_pnl, account.currency),
      helperText: 'Combined realized and unrealized performance of the portfolio.',
      emphasis: 'pnl',
      rawValue: account.total_pnl,
    },
    {
      label: 'Open positions',
      value: String(summary?.open_positions_count ?? account.open_positions_count ?? 0),
      helperText: 'Count of open paper positions reported by the backend.',
    },
    {
      label: 'Total trades',
      value: String(totalTrades),
      helperText: 'Recent execution history available from GET /api/paper/trades/.',
    },
  ];

  return (
    <section className="paper-summary-grid">
      {metrics.map((metric) => (
        <article key={metric.label} className="panel paper-summary-card">
          <div className="paper-summary-card__header">
            <span>{metric.label}</span>
            {metric.emphasis === 'pnl' ? <PnlBadge value={metric.rawValue}>{metric.value}</PnlBadge> : null}
          </div>
          <strong className="paper-summary-card__value">{metric.value}</strong>
          <details className="paper-summary-card__details">
            <summary>Detalle</summary>
            <p>{metric.helperText}</p>
          </details>
        </article>
      ))}
    </section>
  );
}
