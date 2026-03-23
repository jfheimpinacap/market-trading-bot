import type { PaperAccount, PaperPortfolioSummary } from '../../types/paperTrading';
import { PnlBadge } from './PnlBadge';
import { formatPaperCurrency, formatTechnicalTimestamp } from './utils';

type PaperAccountPanelProps = {
  account: PaperAccount;
  summary: PaperPortfolioSummary | null;
};

export function PaperAccountPanel({ account, summary }: PaperAccountPanelProps) {
  return (
    <div className="paper-account-grid">
      <article className="paper-account-card">
        <div className="paper-account-card__header">
          <div>
            <p className="section-label">Active account</p>
            <h3>{account.name}</h3>
            <p>{account.notes || 'Local paper trading account seeded for portfolio inspection flows.'}</p>
          </div>
          <span className={`paper-badge ${account.is_active ? 'paper-badge--active' : 'paper-badge--inactive'}`}>
            {account.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>

        <dl className="dashboard-key-value-list">
          <div>
            <dt>Slug</dt>
            <dd>{account.slug}</dd>
          </div>
          <div>
            <dt>Currency</dt>
            <dd>{account.currency}</dd>
          </div>
          <div>
            <dt>Initial balance</dt>
            <dd>{formatPaperCurrency(account.initial_balance, account.currency)}</dd>
          </div>
          <div>
            <dt>Reserved balance</dt>
            <dd>{formatPaperCurrency(account.reserved_balance, account.currency)}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{formatTechnicalTimestamp(account.created_at)}</dd>
          </div>
          <div>
            <dt>Last updated</dt>
            <dd>{formatTechnicalTimestamp(account.updated_at)}</dd>
          </div>
        </dl>
      </article>

      <article className="paper-account-card">
        <div className="paper-account-card__header">
          <div>
            <p className="section-label">Backend summary</p>
            <h3>Portfolio diagnostics</h3>
            <p>Cross-check the active account against the summary endpoint used by this page.</p>
          </div>
        </div>

        <dl className="dashboard-key-value-list">
          <div>
            <dt>Open positions</dt>
            <dd>{summary?.open_positions_count ?? account.open_positions_count}</dd>
          </div>
          <div>
            <dt>Closed positions</dt>
            <dd>{summary?.closed_positions_count ?? '—'}</dd>
          </div>
          <div>
            <dt>Exposure rows</dt>
            <dd>{summary?.exposure_by_market.length ?? '—'}</dd>
          </div>
          <div>
            <dt>Recent trades in summary</dt>
            <dd>{summary?.recent_trades.length ?? '—'}</dd>
          </div>
          <div>
            <dt>Realized PnL</dt>
            <dd>
              <PnlBadge value={account.realized_pnl}>{formatPaperCurrency(account.realized_pnl, account.currency)}</PnlBadge>
            </dd>
          </div>
          <div>
            <dt>Total PnL</dt>
            <dd>
              <PnlBadge value={account.total_pnl}>{formatPaperCurrency(account.total_pnl, account.currency)}</PnlBadge>
            </dd>
          </div>
        </dl>
      </article>
    </div>
  );
}
