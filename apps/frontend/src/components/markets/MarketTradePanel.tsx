import { useEffect, useMemo, useState } from 'react';
import { navigate } from '../../lib/router';
import { evaluateTradePolicy } from '../../services/policy';
import { assessTrade } from '../../services/riskDemo';
import type { MarketDetail } from '../../types/markets';
import type { TradePolicyEvaluation } from '../../types/policy';
import type {
  CreatePaperTradePayload,
  PaperAccount,
  PaperPortfolioSummary,
  PaperPosition,
  PaperTrade,
  TradeExecutionState,
} from '../../types/paperTrading';
import type { TradeRiskAssessment } from '../../types/riskDemo';
import type { TradeProposal } from '../../types/proposals';
import { formatCompactCurrency, formatPercent, titleize } from './utils';
import { PaperStatusBadge } from '../paper-trading/PaperStatusBadge';
import { PnlBadge } from '../paper-trading/PnlBadge';
import { SideBadge } from '../paper-trading/SideBadge';
import {
  formatPaperCurrency,
  formatQuantity,
  formatTechnicalTimestamp,
} from '../paper-trading/utils';
import { PolicyDecisionPanel } from '../policy/PolicyDecisionPanel';
import { TradeRiskPanel } from './TradeRiskPanel';

const SIDE_OPTIONS: Array<CreatePaperTradePayload['side']> = ['YES', 'NO'];
const TRADE_TYPE_OPTIONS: Array<CreatePaperTradePayload['trade_type']> = ['BUY', 'SELL'];

type MarketTradePanelProps = {
  market: MarketDetail;
  account: PaperAccount | null;
  summary: PaperPortfolioSummary | null;
  positions: PaperPosition[];
  trades: PaperTrade[];
  isLoading: boolean;
  error: string | null;
  warning: string | null;
  isSubmitting: boolean;
  executionState: TradeExecutionState | null;
  proposal?: TradeProposal | null;
  proposalPrefillVersion?: number;
  onRetry: () => Promise<void> | void;
  onSubmit: (payload: CreatePaperTradePayload) => Promise<void>;
};

function getSidePrice(market: MarketDetail, side: CreatePaperTradePayload['side']) {
  if (side === 'YES') {
    if (market.current_yes_price !== null && market.current_yes_price !== undefined) {
      return Number(market.current_yes_price);
    }

    if (market.current_market_probability !== null && market.current_market_probability !== undefined) {
      return Number(market.current_market_probability);
    }

    return null;
  }

  if (market.current_no_price !== null && market.current_no_price !== undefined) {
    return Number(market.current_no_price);
  }

  if (market.current_market_probability !== null && market.current_market_probability !== undefined) {
    return 1 - Number(market.current_market_probability);
  }

  return null;
}

function formatTradeError(message: string) {
  if (/Insufficient paper cash balance/i.test(message)) {
    return 'Insufficient paper balance for this demo trade.';
  }

  if (/not available for paper trading/i.test(message)) {
    return 'This market is not currently tradable in paper mode.';
  }

  if (/Insufficient paper position quantity/i.test(message)) {
    return 'You do not have enough paper position quantity to execute this sell.';
  }

  return message || 'Failed to execute paper trade.';
}

function buildAssessmentKey(payload: Pick<CreatePaperTradePayload, 'trade_type' | 'side' | 'quantity'>) {
  return `${payload.trade_type}:${payload.side}:${payload.quantity.trim()}`;
}

export function MarketTradePanel({
  market,
  account,
  summary,
  positions,
  trades,
  isLoading,
  error,
  warning,
  isSubmitting,
  executionState,
  proposal,
  proposalPrefillVersion,
  onRetry,
  onSubmit,
}: MarketTradePanelProps) {
  const [tradeType, setTradeType] = useState<CreatePaperTradePayload['trade_type']>('BUY');
  const [side, setSide] = useState<CreatePaperTradePayload['side']>('YES');
  const [quantity, setQuantity] = useState('');
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [riskAssessment, setRiskAssessment] = useState<TradeRiskAssessment | null>(null);
  const [riskError, setRiskError] = useState<string | null>(null);
  const [isEvaluatingRisk, setIsEvaluatingRisk] = useState(false);
  const [policyEvaluation, setPolicyEvaluation] = useState<TradePolicyEvaluation | null>(null);
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [isEvaluatingPolicy, setIsEvaluatingPolicy] = useState(false);
  const [lastAssessmentKey, setLastAssessmentKey] = useState<string | null>(null);

  const isTradable = market.is_active && market.status.toLowerCase() === 'open';
  const marketPositions = useMemo(
    () => positions.filter((position) => position.market === market.id),
    [market.id, positions],
  );
  const positionForSelectedSide = useMemo(
    () => marketPositions.find((position) => position.side === side),
    [marketPositions, side],
  );
  const marketTrades = useMemo(
    () => trades.filter((trade) => trade.market === market.id).slice(0, 3),
    [market.id, trades],
  );
  const currentPrice = useMemo(() => getSidePrice(market, side), [market, side]);
  const yesPrice = useMemo(() => getSidePrice(market, 'YES'), [market]);
  const noPrice = useMemo(() => getSidePrice(market, 'NO'), [market]);
  const numericQuantity = Number(quantity);
  const availableSellQuantity = Number(positionForSelectedSide?.quantity ?? '0');
  const estimatedGrossAmount = currentPrice !== null && Number.isFinite(numericQuantity) && numericQuantity > 0
    ? numericQuantity * currentPrice
    : null;
  const currentAssessmentKey = useMemo(
    () => buildAssessmentKey({ trade_type: tradeType, side, quantity }),
    [tradeType, side, quantity],
  );
  const hasFreshPolicyEvaluation = policyEvaluation && lastAssessmentKey === currentAssessmentKey;
  const canExecuteTrade = Boolean(
    account
      && hasFreshPolicyEvaluation
      && policyEvaluation.decision !== 'HARD_BLOCK'
      && !isLoading
      && !error,
  );
  const requiresManualApproval = policyEvaluation?.decision === 'APPROVAL_REQUIRED';

  useEffect(() => {
    if (executionState?.status === 'success') {
      setQuantity('');
      setValidationMessage(null);
      setRiskAssessment(null);
      setRiskError(null);
      setPolicyEvaluation(null);
      setPolicyError(null);
      setLastAssessmentKey(null);
    }
  }, [executionState?.status, executionState?.response?.trade.id]);

  useEffect(() => {
    setRiskAssessment(null);
    setRiskError(null);
    setPolicyEvaluation(null);
    setPolicyError(null);
    setLastAssessmentKey(null);
  }, [market.id, tradeType, side, quantity]);

  useEffect(() => {
    if (!proposal || !proposalPrefillVersion) {
      return;
    }

    if (proposal.suggested_trade_type === 'BUY' || proposal.suggested_trade_type === 'SELL') {
      setTradeType(proposal.suggested_trade_type);
    }

    if (proposal.suggested_side === 'YES' || proposal.suggested_side === 'NO') {
      setSide(proposal.suggested_side);
    }

    setQuantity(proposal.suggested_quantity ?? '');
    setValidationMessage(null);
  }, [proposal, proposalPrefillVersion]);

  function applyProposalSuggestion() {
    if (!proposal || proposal.suggested_trade_type === 'HOLD' || !proposal.suggested_side || !proposal.suggested_quantity) {
      setValidationMessage('No actionable proposal suggestion available to preload.');
      return;
    }

    setTradeType(proposal.suggested_trade_type === 'SELL' ? 'SELL' : 'BUY');
    setSide(proposal.suggested_side);
    setQuantity(proposal.suggested_quantity);
    setValidationMessage(null);
  }

  function validateForm(options?: { requireTradable?: boolean }) {
    const requireTradable = options?.requireTradable ?? false;

    if (!market.id) {
      return 'The selected market is missing and the demo trade cannot be sent.';
    }

    if (!tradeType || !side) {
      return 'Choose a paper trade action before submitting.';
    }

    if (requireTradable && !isTradable) {
      return 'This market is not currently tradable in paper mode.';
    }

    if (!quantity.trim()) {
      return 'Enter a quantity greater than 0.';
    }

    if (!Number.isFinite(numericQuantity) || numericQuantity <= 0) {
      return 'Quantity must be greater than 0.';
    }

    if (tradeType === 'SELL' && numericQuantity > availableSellQuantity) {
      return `You only have ${formatQuantity(positionForSelectedSide?.quantity ?? '0')} ${side} contracts available to sell in this market.`;
    }

    return null;
  }

  async function handleEvaluateTrade() {
    const message = validateForm();
    if (message) {
      setValidationMessage(message);
      return;
    }

    setValidationMessage(null);
    setRiskError(null);
    setIsEvaluatingRisk(true);

    try {
      const response = await assessTrade({
        market_id: market.id,
        trade_type: tradeType,
        side,
        quantity: quantity.trim(),
        requested_price: currentPrice !== null ? currentPrice.toFixed(4) : null,
        metadata: {
          source: 'market-detail-risk-panel',
          market_slug: market.slug,
        },
      });
      setRiskAssessment(response.assessment);
      setPolicyEvaluation(null);
      setPolicyError(null);
      setLastAssessmentKey(buildAssessmentKey({ trade_type: tradeType, side, quantity }));
    } catch (assessmentError) {
      setRiskAssessment(null);
      setPolicyEvaluation(null);
      setRiskError(assessmentError instanceof Error ? assessmentError.message : 'Could not evaluate trade risk.');
    } finally {
      setIsEvaluatingRisk(false);
    }
  }

  async function handleEvaluatePolicy() {
    const message = validateForm();
    if (message) {
      setValidationMessage(message);
      return;
    }

    setValidationMessage(null);
    setPolicyError(null);
    setIsEvaluatingPolicy(true);

    try {
      const evaluation = await evaluateTradePolicy({
        market_id: market.id,
        trade_type: tradeType,
        side,
        quantity: quantity.trim(),
        requested_price: currentPrice !== null ? currentPrice.toFixed(4) : null,
        triggered_from: 'market_detail',
        requested_by: 'user',
        risk_assessment_id: riskAssessment?.id ?? null,
        metadata: {
          source: 'market-detail-policy-panel',
          market_slug: market.slug,
        },
      });
      setPolicyEvaluation(evaluation);
      setLastAssessmentKey(buildAssessmentKey({ trade_type: tradeType, side, quantity }));
    } catch (evaluationError) {
      setPolicyEvaluation(null);
      setPolicyError(evaluationError instanceof Error ? evaluationError.message : 'Could not evaluate trade policy.');
    } finally {
      setIsEvaluatingPolicy(false);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const message = validateForm({ requireTradable: true });
    if (message) {
      setValidationMessage(message);
      return;
    }

    if (!hasFreshPolicyEvaluation) {
      setValidationMessage('Run a fresh policy evaluation before executing this trade.');
      return;
    }

    if (policyEvaluation.decision === 'HARD_BLOCK') {
      setValidationMessage('This trade is hard blocked by policy and cannot be executed from this panel.');
      return;
    }

    setValidationMessage(null);
    await onSubmit({
      market_id: market.id,
      trade_type: tradeType,
      side,
      quantity: quantity.trim(),
      metadata: {
        source: 'market-detail-panel',
        market_slug: market.slug,
        risk_assessment_id: riskAssessment?.id ?? null,
        risk_decision: riskAssessment?.decision ?? null,
        policy_decision_id: policyEvaluation.id,
        policy_decision: policyEvaluation.decision,
        policy_summary: policyEvaluation.summary,
        policy_triggered_from: policyEvaluation.triggered_from,
      },
    });
  }

  const executionMessage = executionState?.status === 'error'
    ? formatTradeError(executionState.message)
    : executionState?.message;

  return (
    <div className="market-trade-panel">
      <div className="market-trade-panel__hero">
        <div>
          <p className="section-label">Simulated execution only</p>
          <h3>Paper trade this market</h3>
          <p>
            Paper trades are simulated and do not use real money. The backend remains the source of truth for the executed price,
            position changes, and resulting account balances.
          </p>
        </div>
        <div className="market-trade-panel__status">
          <PaperStatusBadge value={isTradable ? 'OPEN' : titleize(market.status)} />
          <span className="muted-text">{isTradable ? 'Demo trading enabled' : 'Paper trading blocked by market status'}</span>
        </div>
      </div>

      <div className="market-trade-price-grid">
        <article className="market-trade-price-card">
          <span>YES current price</span>
          <strong>{formatPaperCurrency(yesPrice, account?.currency ?? 'USD')}</strong>
          <small>Latest market detail value used only as an estimate before execution.</small>
        </article>
        <article className="market-trade-price-card">
          <span>NO current price</span>
          <strong>{formatPaperCurrency(noPrice, account?.currency ?? 'USD')}</strong>
          <small>The backend will confirm the final simulated fill price when the trade is executed.</small>
        </article>
        <article className="market-trade-price-card">
          <span>Current probability</span>
          <strong>{formatPercent(market.current_market_probability)}</strong>
          <small>Helpful context for demo YES/NO positioning decisions.</small>
        </article>
      </div>

      {isLoading ? (
        <div className="market-trade-notice market-trade-notice--info">
          Loading paper account context, open positions, and recent trade history for this market.
        </div>
      ) : null}

      {error ? (
        <div className="market-trade-notice market-trade-notice--error">
          <div>
            <strong>Could not load paper trading context.</strong>
            <p>
              {error} If the backend is starting from scratch, run <code>cd apps/backend && python manage.py seed_paper_account</code>{' '}
              and retry.
            </p>
          </div>
          <button className="secondary-button" type="button" onClick={() => void onRetry()}>
            Retry paper data
          </button>
        </div>
      ) : null}

      {warning && !error ? (
        <div className="market-trade-notice market-trade-notice--warning">
          <strong>Partial data warning.</strong>
          <p>{warning}</p>
        </div>
      ) : null}

      <div className="market-trade-layout">
        <form className="market-trade-form" onSubmit={handleSubmit}>
          <div className="market-trade-form__group">
            <span className="market-trade-form__label">Trade type</span>
            <div className="trade-toggle-group" role="group" aria-label="Trade type">
              {TRADE_TYPE_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  className={`trade-toggle-button ${tradeType === option ? 'trade-toggle-button--active' : ''}`}
                  onClick={() => setTradeType(option)}
                  disabled={isSubmitting || isEvaluatingRisk || isEvaluatingPolicy}
                >
                  {titleize(option)}
                </button>
              ))}
            </div>
          </div>

          <div className="market-trade-form__group">
            <span className="market-trade-form__label">Side</span>
            <div className="trade-toggle-group" role="group" aria-label="Trade side">
              {SIDE_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  className={`trade-toggle-button ${side === option ? 'trade-toggle-button--active' : ''}`}
                  onClick={() => setSide(option)}
                  disabled={isSubmitting || isEvaluatingRisk || isEvaluatingPolicy}
                >
                  {tradeType === 'BUY' ? 'Buy' : 'Sell'} {option}
                </button>
              ))}
            </div>
          </div>

          <label className="field-group" htmlFor="paper-trade-quantity">
            <span>Quantity</span>
            <input
              id="paper-trade-quantity"
              className="text-input"
              type="number"
              min="0.0001"
              step="0.0001"
              inputMode="decimal"
              placeholder="e.g. 10"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              disabled={isSubmitting || isEvaluatingRisk || isEvaluatingPolicy}
            />
          </label>

          <div className="market-trade-estimate-grid">
            <article className="market-trade-estimate-card">
              <span>Estimated unit price</span>
              <strong>{formatPaperCurrency(currentPrice, account?.currency ?? 'USD')}</strong>
            </article>
            <article className="market-trade-estimate-card">
              <span>Estimated gross amount</span>
              <strong>{formatPaperCurrency(estimatedGrossAmount, account?.currency ?? 'USD')}</strong>
            </article>
            <article className="market-trade-estimate-card">
              <span>Available to sell</span>
              <strong>{formatQuantity(positionForSelectedSide?.quantity ?? '0')}</strong>
            </article>
          </div>

          <div className="market-trade-flow-card">
            <div className="market-trade-flow-card__header">
              <div>
                <p className="section-label">Approval flow</p>
                <h4>Risk analysis → policy governance → execution</h4>
              </div>
              <span className="muted-text">Didactic local-first flow</span>
            </div>
            <ol className="market-trade-flow-list">
              <li>
                <strong>Evaluate risk</strong>
                <span>Run the analytical trade guard and capture the current demo risk posture.</span>
              </li>
              <li>
                <strong>Evaluate policy</strong>
                <span>Translate risk plus market, account, and signal context into an operational approval decision.</span>
              </li>
              <li>
                <strong>Execute paper trade</strong>
                <span>
                  Auto-approve enables direct execution, approval-required needs explicit confirmation, and hard block keeps execution disabled.
                </span>
              </li>
            </ol>
          </div>

          <TradeRiskPanel
            assessment={riskAssessment}
            isLoading={isEvaluatingRisk}
            error={riskError}
            hasPaperAccount={Boolean(account)}
            isTradable={isTradable}
          />

          <PolicyDecisionPanel
            evaluation={policyEvaluation}
            riskAssessment={riskAssessment}
            isLoading={isEvaluatingPolicy}
            error={policyError}
            hasPaperAccount={Boolean(account)}
            isTradable={isTradable}
          />

          {validationMessage ? <p className="market-trade-feedback market-trade-feedback--error">{validationMessage}</p> : null}

          <div className="market-trade-form__actions">
            <button className="secondary-button" type="button" onClick={() => void onRetry()} disabled={isSubmitting || isEvaluatingRisk || isEvaluatingPolicy}>
              Refresh paper context
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => applyProposalSuggestion()}
              disabled={isSubmitting || isEvaluatingRisk || isEvaluatingPolicy || !proposal}
            >
              Use proposal suggestion
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => void handleEvaluateTrade()}
              disabled={isSubmitting || isEvaluatingRisk || isEvaluatingPolicy || Boolean(error) || isLoading || !account}
            >
              {isEvaluatingRisk ? 'Evaluating risk…' : 'Evaluate risk'}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => void handleEvaluatePolicy()}
              disabled={isSubmitting || isEvaluatingRisk || isEvaluatingPolicy || Boolean(error) || isLoading || !account}
            >
              {isEvaluatingPolicy ? 'Evaluating policy…' : 'Evaluate policy'}
            </button>
            {hasFreshPolicyEvaluation ? (
              <button
                className={requiresManualApproval ? 'primary-button' : 'primary-button'}
                type="submit"
                disabled={isSubmitting || !canExecuteTrade}
              >
                {isSubmitting
                  ? 'Submitting demo trade…'
                  : requiresManualApproval
                    ? `Confirm and execute ${tradeType} ${side}`
                    : `Execute ${tradeType} ${side}`}
              </button>
            ) : null}
          </div>

          <p className="muted-text market-trade-form__hint">
            Flow for this stage: evaluate with <code>POST /api/risk/assess-trade/</code>, convert to governance with{' '}
            <code>POST /api/policy/evaluate-trade/</code>, then execute through <code>POST /api/paper/trades/</code> when allowed.
          </p>
        </form>

        <div className="market-trade-context">
          <div className="market-trade-context__grid">
            <article className="market-trade-context-card">
              <span>Paper cash available</span>
              <strong>{formatPaperCurrency(account?.cash_balance, account?.currency ?? 'USD')}</strong>
              <small>Ready buying power in the active demo account.</small>
            </article>
            <article className="market-trade-context-card">
              <span>Paper equity</span>
              <strong>{formatPaperCurrency(account?.equity, account?.currency ?? 'USD')}</strong>
              <small>Total demo account value after the latest backend revaluation.</small>
            </article>
            <article className="market-trade-context-card">
              <span>Open paper positions</span>
              <strong>{summary?.open_positions_count ?? account?.open_positions_count ?? '—'}</strong>
              <small>Current portfolio-wide open positions across markets.</small>
            </article>
            <article className="market-trade-context-card">
              <span>Market liquidity</span>
              <strong>{formatCompactCurrency(market.liquidity)}</strong>
              <small>Read-only market context for the current contract.</small>
            </article>
          </div>

          <div className="market-position-summary">
            <div className="market-position-summary__header">
              <div>
                <p className="section-label">Your paper position in this market</p>
                <h4>Current exposure</h4>
              </div>
            </div>

            {marketPositions.length === 0 ? (
              <div className="market-trade-empty-state">
                No paper position exists in this market yet. Submit a demo BUY to create your first simulated exposure here.
              </div>
            ) : (
              <div className="market-position-summary__grid">
                {marketPositions.map((position) => (
                  <article key={position.id} className="market-position-card">
                    <div className="market-position-card__header">
                      <SideBadge side={position.side} />
                      <PaperStatusBadge value={position.status} />
                    </div>
                    <dl className="dashboard-key-value-list market-position-card__details">
                      <div>
                        <dt>Quantity</dt>
                        <dd>{formatQuantity(position.quantity)}</dd>
                      </div>
                      <div>
                        <dt>Average entry</dt>
                        <dd>{formatPaperCurrency(position.average_entry_price, account?.currency ?? 'USD')}</dd>
                      </div>
                      <div>
                        <dt>Current mark</dt>
                        <dd>{formatPaperCurrency(position.current_mark_price, account?.currency ?? 'USD')}</dd>
                      </div>
                      <div>
                        <dt>Market value</dt>
                        <dd>{formatPaperCurrency(position.market_value, account?.currency ?? 'USD')}</dd>
                      </div>
                      <div>
                        <dt>Unrealized PnL</dt>
                        <dd>
                          <PnlBadge value={position.unrealized_pnl}>
                            {formatPaperCurrency(position.unrealized_pnl, account?.currency ?? 'USD')}
                          </PnlBadge>
                        </dd>
                      </div>
                      <div>
                        <dt>Last marked</dt>
                        <dd>{formatTechnicalTimestamp(position.last_marked_at ?? position.updated_at)}</dd>
                      </div>
                    </dl>
                  </article>
                ))}
              </div>
            )}
          </div>

          <div className="market-trade-recent-list">
            <div className="market-position-summary__header">
              <div>
                <p className="section-label">Recent paper trades in this market</p>
                <h4>Latest executions</h4>
              </div>
            </div>
            {marketTrades.length === 0 ? (
              <div className="market-trade-empty-state">
                No paper trades have been executed for this market yet from the active demo account.
              </div>
            ) : (
              <div className="market-trade-recent-items">
                {marketTrades.map((trade) => (
                  <article key={trade.id} className="market-trade-recent-item">
                    <div className="market-trade-recent-item__header">
                      <strong>{titleize(trade.trade_type)} {trade.side}</strong>
                      <PaperStatusBadge value={trade.status} />
                    </div>
                    <dl className="dashboard-key-value-list">
                      <div>
                        <dt>Quantity</dt>
                        <dd>{formatQuantity(trade.quantity)}</dd>
                      </div>
                      <div>
                        <dt>Price</dt>
                        <dd>{formatPaperCurrency(trade.price, account?.currency ?? 'USD')}</dd>
                      </div>
                      <div>
                        <dt>Gross amount</dt>
                        <dd>{formatPaperCurrency(trade.gross_amount, account?.currency ?? 'USD')}</dd>
                      </div>
                      <div>
                        <dt>Executed</dt>
                        <dd>{formatTechnicalTimestamp(trade.executed_at)}</dd>
                      </div>
                    </dl>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {executionState ? (
        <div className={`market-trade-result market-trade-result--${executionState.status}`}>
          <div>
            <strong>{executionState.status === 'success' ? 'Trade executed successfully.' : 'Paper trade failed.'}</strong>
            <p>{executionMessage}</p>
            {executionState.response ? (
              <p className="muted-text">
                Latest execution: {titleize(executionState.response.trade.trade_type)} {executionState.response.trade.side}{' '}
                {formatQuantity(executionState.response.trade.quantity)} @{' '}
                {formatPaperCurrency(executionState.response.trade.price, executionState.response.account.currency)}.
              </p>
            ) : null}
          </div>
          {executionState.status === 'success' ? (
            <button className="secondary-button" type="button" onClick={() => navigate('/portfolio')}>
              View updated portfolio
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
