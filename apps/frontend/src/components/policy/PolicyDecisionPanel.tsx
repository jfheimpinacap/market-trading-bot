import type { TradeRiskAssessment } from '../../types/riskDemo';
import type { TradePolicyEvaluation } from '../../types/policy';
import { titleize } from '../markets/utils';
import { PolicyDecisionBadge } from './PolicyDecisionBadge';

type PolicyDecisionPanelProps = {
  evaluation: TradePolicyEvaluation | null;
  riskAssessment: TradeRiskAssessment | null;
  isLoading: boolean;
  error: string | null;
  hasPaperAccount: boolean;
  isTradable: boolean;
};

function getFixSuggestions(evaluation: TradePolicyEvaluation) {
  const suggestions = new Set<string>();
  for (const rule of evaluation.matched_rules) {
    if (/EXPOSURE|LARGE|CASH/i.test(rule.code)) {
      suggestions.add('Reduce quantity before trying again.');
    }
    if (/MARKET/i.test(rule.code)) {
      suggestions.add('Choose a tradable market with OPEN status.');
    }
    if (/RISK/i.test(rule.code)) {
      suggestions.add('Review the linked risk warnings and re-evaluate first.');
    }
    if (/SIGNAL/i.test(rule.code)) {
      suggestions.add('Wait for a stronger actionable signal or confirm manually.');
    }
  }
  if (suggestions.size === 0) {
    suggestions.add('Refresh the trade context and evaluate again.');
  }
  return Array.from(suggestions);
}

export function PolicyDecisionPanel({ evaluation, riskAssessment, isLoading, error, hasPaperAccount, isTradable }: PolicyDecisionPanelProps) {
  if (!hasPaperAccount) {
    return (
      <div className="policy-decision-panel policy-decision-panel--empty">
        <strong>Policy engine is waiting for a paper account.</strong>
        <p>Seed the demo account first so governance rules can evaluate cash, exposure, and execution eligibility.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="policy-decision-panel policy-decision-panel--loading">
        <strong>Evaluating policy rules…</strong>
        <p>Combining market operability, account exposure, risk posture, signal actionability, and governance thresholds.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="policy-decision-panel policy-decision-panel--error">
        <strong>Policy evaluation failed.</strong>
        <p>{error}</p>
      </div>
    );
  }

  if (!evaluation) {
    return (
      <div className="policy-decision-panel policy-decision-panel--empty">
        <strong>Policy engine ready.</strong>
        <p>
          {isTradable
            ? 'Run policy evaluation after the risk check to know whether this trade can auto-execute, needs manual confirmation, or is blocked.'
            : 'This market may already be non-operable. Evaluate policy to get the explicit governance decision.'}
        </p>
      </div>
    );
  }

  const suggestions = getFixSuggestions(evaluation);
  const requiresApproval = evaluation.decision === 'APPROVAL_REQUIRED';
  const isBlocked = evaluation.decision === 'HARD_BLOCK';

  return (
    <div className={`policy-decision-panel policy-decision-panel--${evaluation.decision.toLowerCase()}`}>
      <div className="policy-decision-panel__header">
        <div>
          <p className="section-label">Policy engine / approval rules demo</p>
          <h4>Operational approval decision</h4>
        </div>
        <PolicyDecisionBadge decision={evaluation.decision} />
      </div>

      <div className="policy-decision-panel__comparison-grid">
        <article className="policy-decision-metric-card">
          <span>Risk demo</span>
          <strong>{riskAssessment ? titleize(riskAssessment.decision) : 'Missing'}</strong>
        </article>
        <article className="policy-decision-metric-card">
          <span>Policy decision</span>
          <strong>{titleize(evaluation.decision)}</strong>
        </article>
        <article className="policy-decision-metric-card">
          <span>Severity</span>
          <strong>{titleize(evaluation.severity)}</strong>
        </article>
        <article className="policy-decision-metric-card">
          <span>Confidence</span>
          <strong>{evaluation.confidence ?? '—'}</strong>
        </article>
      </div>

      {requiresApproval ? (
        <div className="policy-decision-notice policy-decision-notice--approval">
          <strong>This trade requires manual approval.</strong>
          <p>The system allows it only with an explicit confirmation step from the user.</p>
        </div>
      ) : null}

      {isBlocked ? (
        <div className="policy-decision-notice policy-decision-notice--blocked">
          <strong>This trade is hard blocked.</strong>
          <p>The execute action stays disabled until the proposal or market context changes.</p>
        </div>
      ) : null}

      <div className="policy-decision-panel__body">
        <div>
          <strong>Summary</strong>
          <p>{evaluation.summary}</p>
        </div>
        <div>
          <strong>Rationale</strong>
          <p>{evaluation.rationale}</p>
        </div>
        <div>
          <strong>Matched rules</strong>
          <ul className="policy-rule-list">
            {evaluation.matched_rules.map((rule) => (
              <li key={`${rule.code}-${rule.title}`}>
                <div className="policy-rule-list__heading">
                  <span className={`policy-rule-pill policy-rule-pill--${rule.severity.toLowerCase()}`}>{titleize(rule.severity)}</span>
                  <strong>{rule.title}</strong>
                </div>
                <p>{rule.message}</p>
                {rule.recommendation ? <small>{rule.recommendation}</small> : null}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <strong>Recommendation</strong>
          <p>{evaluation.recommendation}</p>
        </div>
        {isBlocked ? (
          <div>
            <strong>Suggested fixes</strong>
            <ul className="policy-suggestion-list">
              {suggestions.map((suggestion) => (
                <li key={suggestion}>{suggestion}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}
