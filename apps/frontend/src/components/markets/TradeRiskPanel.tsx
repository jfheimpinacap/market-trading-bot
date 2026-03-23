import type { TradeRiskAssessment } from '../../types/riskDemo';
import { formatPercent, titleize } from './utils';
import { RiskDecisionBadge } from './RiskDecisionBadge';

type TradeRiskPanelProps = {
  assessment: TradeRiskAssessment | null;
  isLoading: boolean;
  error: string | null;
  hasPaperAccount: boolean;
  isTradable: boolean;
};

function formatConfidence(value: string) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? formatPercent(numeric) : '—';
}

export function TradeRiskPanel({ assessment, isLoading, error, hasPaperAccount, isTradable }: TradeRiskPanelProps) {
  if (!hasPaperAccount) {
    return (
      <div className="trade-risk-panel trade-risk-panel--empty">
        <strong>Paper account not found.</strong>
        <p>Run <code>cd apps/backend && python manage.py seed_paper_account</code> and refresh the page before using the risk guard.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="trade-risk-panel trade-risk-panel--loading">
        <strong>Running demo risk check…</strong>
        <p>Comparing market status, paper cash, recent signals, concentration, spread, and activity heuristics.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="trade-risk-panel trade-risk-panel--error">
        <strong>Risk check failed.</strong>
        <p>{error}</p>
      </div>
    );
  }

  if (!assessment) {
    return (
      <div className="trade-risk-panel trade-risk-panel--empty">
        <strong>Trade guard ready.</strong>
        <p>
          {isTradable
            ? 'Run a demo risk check before executing this trade.'
            : 'This market is not operable right now. Run a demo risk check to see the exact block reason.'}
        </p>
      </div>
    );
  }

  return (
    <div className={`trade-risk-panel trade-risk-panel--${assessment.decision.toLowerCase()}`}>
      <div className="trade-risk-panel__header">
        <div>
          <p className="section-label">Risk demo / trade guard mock</p>
          <h4>Pre-trade assessment</h4>
        </div>
        <RiskDecisionBadge decision={assessment.decision} />
      </div>

      <div className="trade-risk-panel__metrics">
        <article className="trade-risk-metric-card">
          <span>Decision</span>
          <strong>{titleize(assessment.decision)}</strong>
        </article>
        <article className="trade-risk-metric-card">
          <span>Score</span>
          <strong>{assessment.score}/100</strong>
        </article>
        <article className="trade-risk-metric-card">
          <span>Confidence</span>
          <strong>{formatConfidence(assessment.confidence)}</strong>
        </article>
      </div>

      <div className="trade-risk-panel__body">
        <div>
          <strong>Summary</strong>
          <p>{assessment.summary}</p>
        </div>
        <div>
          <strong>Rationale</strong>
          <p>{assessment.rationale}</p>
        </div>
        {assessment.warnings.length > 0 ? (
          <div>
            <strong>Warnings</strong>
            <ul className="trade-risk-warnings-list">
              {assessment.warnings.map((warning) => (
                <li key={`${warning.code}-${warning.message}`}>
                  <span className={`trade-risk-warning-pill trade-risk-warning-pill--${warning.severity}`}>{titleize(warning.severity)}</span>
                  <div>
                    <span className="trade-risk-warning-code">{warning.code}</span>
                    <p>{warning.message}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {assessment.suggested_quantity ? (
          <p className="trade-risk-panel__note">
            Suggested smaller quantity: <strong>{assessment.suggested_quantity}</strong> contracts.
          </p>
        ) : null}
      </div>
    </div>
  );
}
