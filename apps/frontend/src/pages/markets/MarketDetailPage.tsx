import { useCallback, useEffect, useMemo, useState } from 'react';
import { ContextLinksPanel } from '../../components/flow/ContextLinksPanel';
import { WorkflowStatusPanel } from '../../components/flow/WorkflowStatusPanel';
import { MarketTradePanel } from '../../components/markets/MarketTradePanel';
import { PageHeader } from '../../components/PageHeader';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { MarketActiveBadge } from '../../components/markets/MarketActiveBadge';
import { MarketProbabilityBadge } from '../../components/markets/MarketProbabilityBadge';
import { MarketHistoryChart } from '../../components/markets/MarketHistoryChart';
import { MarketRulesCard } from '../../components/markets/MarketRulesCard';
import { MarketSnapshotsTable } from '../../components/markets/MarketSnapshotsTable';
import { MarketStatusBadge } from '../../components/markets/MarketStatusBadge';
import { formatCompactCurrency, formatDateTime, formatNumber, titleize } from '../../components/markets/utils';
import { ReviewOutcomeBadge } from '../../components/postmortem/ReviewOutcomeBadge';
import { SectionCard } from '../../components/SectionCard';
import { LatestSignalsList } from '../../components/signals/LatestSignalsList';
import { useDemoFlowRefresh } from '../../hooks/useDemoFlowRefresh';
import { formatDecisionLabel, getLatestReviewForMarket, getLatestTradeForMarket, getOpenPositionsForMarket, publishDemoFlowRefresh } from '../../lib/demoFlow';
import { navigate, usePathname } from '../../lib/router';
import { getMarketDetail } from '../../services/markets';
import {
  createPaperTrade,
  getPaperAccount,
  getPaperPositions,
  getPaperSummary,
  getPaperTrades,
  revaluePaperPortfolio,
} from '../../services/paperTrading';
import { getTradeReviews } from '../../services/reviews';
import { getSignals } from '../../services/signals';
import type { ContextLinkItem, WorkflowStatusItem } from '../../types/demoFlow';
import type { MarketDetail } from '../../types/markets';
import type { CreatePaperTradePayload, PaperAccount, PaperPortfolioSummary, PaperPosition, PaperTrade, TradeExecutionState } from '../../types/paperTrading';
import type { TradeReview } from '../../types/reviews';
import type { MarketSignal } from '../../types/signals';

function getMarketIdFromPath(pathname: string) {
  const segments = pathname.split('/').filter(Boolean);
  return segments[1] ?? '';
}

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function MarketDetailPage() {
  const pathname = usePathname();
  const marketId = useMemo(() => getMarketIdFromPath(pathname), [pathname]);

  const [market, setMarket] = useState<MarketDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [marketSignals, setMarketSignals] = useState<MarketSignal[]>([]);
  const [signalsLoading, setSignalsLoading] = useState(true);
  const [signalsError, setSignalsError] = useState<string | null>(null);

  const [paperAccount, setPaperAccount] = useState<PaperAccount | null>(null);
  const [paperSummary, setPaperSummary] = useState<PaperPortfolioSummary | null>(null);
  const [paperPositions, setPaperPositions] = useState<PaperPosition[]>([]);
  const [paperTrades, setPaperTrades] = useState<PaperTrade[]>([]);
  const [marketReviews, setMarketReviews] = useState<TradeReview[]>([]);
  const [reviewsLoading, setReviewsLoading] = useState(true);
  const [reviewsError, setReviewsError] = useState<string | null>(null);
  const [paperLoading, setPaperLoading] = useState(true);
  const [paperError, setPaperError] = useState<string | null>(null);
  const [paperWarning, setPaperWarning] = useState<string | null>(null);
  const [isSubmittingTrade, setIsSubmittingTrade] = useState(false);
  const [tradeExecutionState, setTradeExecutionState] = useState<TradeExecutionState | null>(null);

  const loadMarketDetail = useCallback(async () => {
    if (!marketId) {
      setError('The market identifier is missing from the URL.');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await getMarketDetail(marketId);
      setMarket(response);
    } catch (loadError) {
      setError(getErrorMessage(loadError, 'Could not load market detail.'));
    } finally {
      setIsLoading(false);
    }
  }, [marketId]);

  const loadMarketSignals = useCallback(async () => {
    if (!marketId) {
      setSignalsError('The market identifier is missing from the URL.');
      setSignalsLoading(false);
      return;
    }

    setSignalsLoading(true);
    setSignalsError(null);

    try {
      const response = await getSignals({ market: marketId, ordering: '-created_at' });
      setMarketSignals(response.slice(0, 3));
    } catch (loadError) {
      setMarketSignals([]);
      setSignalsError(getErrorMessage(loadError, 'Could not load demo signals for this market.'));
    } finally {
      setSignalsLoading(false);
    }
  }, [marketId]);

  const loadMarketReviews = useCallback(async () => {
    if (!marketId) {
      setReviewsError('The market identifier is missing from the URL.');
      setReviewsLoading(false);
      return;
    }

    setReviewsLoading(true);
    setReviewsError(null);

    try {
      const response = await getTradeReviews({ market: marketId, ordering: '-reviewed_at' });
      setMarketReviews(response);
    } catch (loadError) {
      setMarketReviews([]);
      setReviewsError(getErrorMessage(loadError, 'Could not load trade reviews for this market.'));
    } finally {
      setReviewsLoading(false);
    }
  }, [marketId]);

  const loadPaperContext = useCallback(async () => {
    setPaperLoading(true);
    setPaperError(null);
    setPaperWarning(null);

    const [accountResult, summaryResult, positionsResult, tradesResult] = await Promise.allSettled([
      getPaperAccount(),
      getPaperSummary(),
      getPaperPositions(),
      getPaperTrades(),
    ]);

    const failures: string[] = [];

    if (accountResult.status === 'fulfilled') {
      setPaperAccount(accountResult.value);
    } else {
      setPaperAccount(null);
      failures.push(getErrorMessage(accountResult.reason, 'Could not load the active paper account.'));
    }

    if (summaryResult.status === 'fulfilled') {
      setPaperSummary(summaryResult.value);
    } else {
      setPaperSummary(null);
      failures.push(getErrorMessage(summaryResult.reason, 'Could not load the paper portfolio summary.'));
    }

    if (positionsResult.status === 'fulfilled') {
      setPaperPositions(positionsResult.value);
    } else {
      setPaperPositions([]);
      failures.push(getErrorMessage(positionsResult.reason, 'Could not load paper positions.'));
    }

    if (tradesResult.status === 'fulfilled') {
      setPaperTrades(tradesResult.value);
    } else {
      setPaperTrades([]);
      failures.push(getErrorMessage(tradesResult.reason, 'Could not load paper trades.'));
    }

    if (failures.length === 4) {
      setPaperError(failures[0]);
    } else if (failures.length > 0) {
      setPaperWarning(failures.join(' '));
    }

    setPaperLoading(false);
  }, []);

  const refreshPage = useCallback(async () => {
    if (!marketId) {
      setError('The market identifier is missing from the URL.');
      setIsLoading(false);
      setPaperLoading(false);
      return;
    }

    await Promise.all([
      loadMarketDetail(),
      loadMarketSignals(),
      loadPaperContext(),
      loadMarketReviews(),
    ]);
  }, [loadMarketDetail, loadMarketReviews, loadMarketSignals, loadPaperContext, marketId]);

  useEffect(() => {
    setTradeExecutionState(null);
    void refreshPage();
  }, [refreshPage]);

  useDemoFlowRefresh(refreshPage, Boolean(marketId));

  const handleTradeSubmit = useCallback(async (payload: CreatePaperTradePayload) => {
    setIsSubmittingTrade(true);
    setTradeExecutionState(null);

    try {
      const response = await createPaperTrade(payload);
      setTradeExecutionState({
        status: 'success',
        message: `${titleize(response.trade.trade_type)} ${response.trade.side} ${formatNumber(response.trade.quantity)} executed at ${Number(response.trade.price).toFixed(4)}. The paper account and portfolio context were refreshed from the backend.`,
        response,
      });
      setPaperAccount(response.account);
      await revaluePaperPortfolio();
      await Promise.all([loadPaperContext(), loadMarketReviews()]);
      publishDemoFlowRefresh('paper-trade-executed');
    } catch (submitError) {
      setTradeExecutionState({
        status: 'error',
        message: getErrorMessage(submitError, 'Failed to execute paper trade.'),
        response: null,
      });
    } finally {
      setIsSubmittingTrade(false);
    }
  }, [loadMarketReviews, loadPaperContext]);

  const openPositions = useMemo(() => (market ? getOpenPositionsForMarket(paperPositions, market.id) : []), [market, paperPositions]);
  const latestTrade = useMemo(() => (market ? getLatestTradeForMarket(paperTrades, market.id) : null), [market, paperTrades]);
  const latestReview = useMemo(() => (market ? getLatestReviewForMarket(marketReviews, market.id) : null), [market, marketReviews]);
  const latestDecision = useMemo(() => {
    const executionDecision = tradeExecutionState?.response?.trade.metadata?.risk_decision;
    if (typeof executionDecision === 'string') {
      return executionDecision;
    }

    return latestReview?.risk_decision_at_trade ?? null;
  }, [latestReview?.risk_decision_at_trade, tradeExecutionState?.response?.trade.metadata]);

  const workflowItems = useMemo<WorkflowStatusItem[]>(() => [
    {
      label: 'Signal status',
      value: marketSignals.length > 0 ? `${marketSignals.length} signal${marketSignals.length === 1 ? '' : 's'}` : 'No signals yet',
      helperText: marketSignals.length > 0 ? 'Recent demo signals are available directly above the trade panel.' : 'Generate demo signals to add more opportunity context to this market.',
      tone: marketSignals.some((signal) => signal.is_actionable) ? 'ready' : 'neutral',
      href: '/signals',
      linkLabel: 'Open signals board',
    },
    {
      label: 'Risk decision',
      value: formatDecisionLabel(latestDecision),
      helperText: latestDecision ? 'Latest captured risk posture for this market in the current demo flow.' : 'Run the risk check in the trade panel before executing a new paper trade.',
      tone: latestDecision === 'APPROVE' ? 'ready' : latestDecision === 'BLOCK' ? 'warning' : 'neutral',
    },
    {
      label: 'Open position',
      value: openPositions.length > 0 ? `${openPositions.length} active lot${openPositions.length === 1 ? '' : 's'}` : 'No open position',
      helperText: openPositions.length > 0 ? 'This market already affects the paper portfolio.' : 'A successful trade here will show up in Portfolio after execution and revalue.',
      tone: openPositions.length > 0 ? 'ready' : 'neutral',
      href: '/portfolio',
      linkLabel: 'Open portfolio',
    },
    {
      label: 'Latest review',
      value: latestReview ? titleize(latestReview.outcome) : 'No review yet',
      helperText: latestReview ? 'A post-mortem review already exists for a recent trade in this market.' : 'Generate trade reviews after executing trades to close the loop for this market.',
      tone: latestReview ? 'ready' : 'neutral',
      href: latestReview ? `/postmortem/${latestReview.id}` : '/postmortem',
      linkLabel: latestReview ? 'Open latest review' : 'Open review queue',
    },
  ], [latestDecision, latestReview, marketSignals, openPositions.length]);

  const contextLinks = useMemo<ContextLinkItem[]>(() => {
    const links: ContextLinkItem[] = [
      {
        title: 'Review portfolio impact',
        description: latestTrade ? `Latest trade #${latestTrade.id} already updated the portfolio context for this market.` : 'After executing a paper trade here, open Portfolio to inspect equity, PnL, and linked reviews.',
        href: '/portfolio',
        actionLabel: 'Go to portfolio',
        tone: 'primary',
      },
      {
        title: 'Inspect related signals',
        description: marketSignals.length > 0 ? 'Open the broader signals board to compare this market against the rest of the demo queue.' : 'Signals for this market are empty right now, so you may want to generate more demo signals first.',
        href: '/signals',
        actionLabel: 'Open signals',
        tone: 'secondary',
      },
    ];

    if (latestReview) {
      links.push({
        title: 'Open latest post-mortem',
        description: `Review #${latestReview.id} summarizes what happened after the most recent trade in this market.`,
        href: `/postmortem/${latestReview.id}`,
        actionLabel: 'View review',
        tone: 'neutral',
      });
    }

    return links;
  }, [latestReview, latestTrade, marketSignals.length]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Market detail"
        title={market?.title ?? 'Market detail'}
        description="Inspect current market state, verify recent signals, evaluate the demo risk decision, execute a paper trade, and continue into portfolio or post-mortem from one coherent workspace."
        actions={
          <button className="secondary-button" type="button" onClick={() => navigate('/markets')}>
            Back to markets
          </button>
        }
      />

      <DataStateWrapper
        isLoading={isLoading}
        isError={Boolean(error)}
        errorMessage={error ?? undefined}
        isEmpty={!isLoading && !error && !market}
        loadingTitle="Loading market detail"
        loadingDescription="Requesting the selected market, its rules, and recent snapshots from the local backend."
        errorTitle="Could not load market detail"
        emptyTitle="Market not found"
        emptyDescription="The selected market does not exist in the current local demo catalog."
        action={
          <button className="secondary-button" type="button" onClick={() => navigate('/markets')}>
            Return to markets
          </button>
        }
      >
        {market ? (
          <>
            <WorkflowStatusPanel
              title="Current demo workflow status"
              description="This compact summary keeps the operational story visible: opportunity, risk posture, position state, and whether a review already exists."
              items={workflowItems}
            />

            <section className="content-grid content-grid--two-columns">
              <SectionCard
                eyebrow="Overview"
                title="Market header"
                description="Primary identifiers and related event context for this contract."
                aside={
                  <div className="market-header-badges">
                    <MarketStatusBadge status={market.status} />
                    <MarketActiveBadge isActive={market.is_active} />
                  </div>
                }
              >
                <dl className="market-detail-list">
                  <div>
                    <dt>Provider</dt>
                    <dd>{market.provider.name}</dd>
                  </div>
                  <div>
                    <dt>Category</dt>
                    <dd>{market.category || '—'}</dd>
                  </div>
                  <div>
                    <dt>Related event</dt>
                    <dd>{market.event?.title ?? market.event_title ?? 'No related event'}</dd>
                  </div>
                  <div>
                    <dt>Ticker</dt>
                    <dd>{market.ticker || '—'}</dd>
                  </div>
                  <div>
                    <dt>Market type</dt>
                    <dd>{titleize(market.market_type)}</dd>
                  </div>
                  <div>
                    <dt>Outcome type</dt>
                    <dd>{titleize(market.outcome_type)}</dd>
                  </div>
                </dl>
              </SectionCard>

              <SectionCard eyebrow="Summary" title="Current market metrics" description="Latest values stored directly on the market row for quick inspection.">
                <div className="market-metric-grid">
                  <article className="market-metric-card">
                    <span>Current probability</span>
                    <strong><MarketProbabilityBadge value={market.current_market_probability} /></strong>
                  </article>
                  <article className="market-metric-card">
                    <span>Yes / No</span>
                    <strong>
                      {market.current_yes_price ? `${(Number(market.current_yes_price) * 100).toFixed(1)}%` : '—'} /{' '}
                      {market.current_no_price ? `${(Number(market.current_no_price) * 100).toFixed(1)}%` : '—'}
                    </strong>
                  </article>
                  <article className="market-metric-card">
                    <span>Liquidity</span>
                    <strong>{formatCompactCurrency(market.liquidity)}</strong>
                  </article>
                  <article className="market-metric-card">
                    <span>24h volume</span>
                    <strong>{formatCompactCurrency(market.volume_24h)}</strong>
                  </article>
                  <article className="market-metric-card">
                    <span>Total volume</span>
                    <strong>{formatCompactCurrency(market.volume_total)}</strong>
                  </article>
                  <article className="market-metric-card">
                    <span>Spread (bps)</span>
                    <strong>{formatNumber(market.spread_bps)}</strong>
                  </article>
                  <article className="market-metric-card">
                    <span>Resolution time</span>
                    <strong>{formatDateTime(market.resolution_time)}</strong>
                  </article>
                  <article className="market-metric-card">
                    <span>Latest snapshot</span>
                    <strong>{formatDateTime(market.latest_snapshot_at)}</strong>
                  </article>
                </div>
              </SectionCard>
            </section>

            <ContextLinksPanel
              eyebrow="Next actions"
              title="Continue the workflow from here"
              description="Market detail is now the operational hub of the demo flow, so these links keep the next module one click away."
              links={contextLinks}
            />

            <MarketHistoryChart snapshots={market.recent_snapshots} isLoading={isLoading} error={error} />

            <SectionCard
              eyebrow="Signals"
              title="Demo signals for this market"
              description="Recent local signals connect the market snapshot history above with the mock-agent opportunity layer and paper trading panel below."
              aside={<span className="muted-text">{marketSignals.filter((signal) => signal.is_actionable).length} actionable</span>}
            >
              <DataStateWrapper
                isLoading={signalsLoading}
                isError={Boolean(signalsError)}
                errorMessage={signalsError ?? undefined}
                isEmpty={!signalsLoading && !signalsError && marketSignals.length === 0}
                loadingTitle="Loading market signals"
                loadingDescription="Requesting the latest demo signals attached to this market."
                errorTitle="Could not load market signals"
                emptyTitle="No signals for this market yet"
                emptyDescription="Generate demo signals with `cd apps/backend && python manage.py generate_demo_signals`, then return here or open the broader Signals page."
                action={
                  <button className="secondary-button" type="button" onClick={() => navigate('/signals')}>
                    Open signals workspace
                  </button>
                }
              >
                <LatestSignalsList signals={marketSignals} emptyMessage="No recent demo signals for this market yet." />
              </DataStateWrapper>
            </SectionCard>

            <SectionCard
              eyebrow="Paper trading"
              title="Demo trade execution"
              description="Review the market context above, run the risk check, execute a local simulated trade, and then continue into portfolio or post-mortem with clear next steps."
            >
              <MarketTradePanel
                market={market}
                account={paperAccount}
                summary={paperSummary}
                positions={paperPositions}
                trades={paperTrades}
                isLoading={paperLoading}
                error={paperError}
                warning={paperWarning}
                isSubmitting={isSubmittingTrade}
                executionState={tradeExecutionState}
                onRetry={loadPaperContext}
                onSubmit={handleTradeSubmit}
              />
            </SectionCard>

            <section className="content-grid content-grid--two-columns">
              <SectionCard
                eyebrow="Workflow outcome"
                title="Position and review context"
                description="Small cross-module summary so the user can immediately understand what this market already changed in the portfolio and review loop."
              >
                <dl className="dashboard-key-value-list">
                  <div><dt>Open position status</dt><dd>{openPositions.length > 0 ? `${openPositions.length} open lot${openPositions.length === 1 ? '' : 's'}` : 'No open position'}</dd></div>
                  <div><dt>Latest trade</dt><dd>{latestTrade ? `Trade #${latestTrade.id} · ${titleize(latestTrade.trade_type)} ${latestTrade.side}` : 'No trade executed yet'}</dd></div>
                  <div><dt>Latest review</dt><dd>{latestReview ? <ReviewOutcomeBadge outcome={latestReview.outcome} status={latestReview.review_status} /> : 'No review yet'}</dd></div>
                  <div><dt>Review queue</dt><dd>{reviewsLoading ? 'Loading reviews…' : `${marketReviews.length} review${marketReviews.length === 1 ? '' : 's'} for this market`}</dd></div>
                </dl>
                {reviewsError ? <p className="paper-inline-notice">Review context unavailable: {reviewsError}</p> : null}
              </SectionCard>

              <MarketRulesCard shortRules={market.short_rules} rules={market.rules} />
            </section>

            <section className="content-grid content-grid--two-columns">
              <SectionCard eyebrow="Metadata" title="Useful backend metadata" description="Operational fields that help inspect provenance and resolution details.">
                <dl className="market-detail-list">
                  <div>
                    <dt>Resolution source</dt>
                    <dd>{market.resolution_source || '—'}</dd>
                  </div>
                  <div>
                    <dt>Open time</dt>
                    <dd>{formatDateTime(market.open_time)}</dd>
                  </div>
                  <div>
                    <dt>Close time</dt>
                    <dd>{formatDateTime(market.close_time)}</dd>
                  </div>
                  <div>
                    <dt>Snapshot count</dt>
                    <dd>{formatNumber(market.snapshot_count)}</dd>
                  </div>
                  <div>
                    <dt>Market URL</dt>
                    <dd>
                      {market.url ? (
                        <a href={market.url} target="_blank" rel="noreferrer" className="external-link">
                          Open source market page
                        </a>
                      ) : (
                        '—'
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt>Metadata</dt>
                    <dd className="market-json-preview">{JSON.stringify(market.metadata ?? {}, null, 2)}</dd>
                  </div>
                </dl>
              </SectionCard>

              <SectionCard
                eyebrow="Related reviews"
                title="Post-mortem links"
                description="If reviews already exist for this market, use them to understand what happened after recent trades and what the demo engine learned."
              >
                <DataStateWrapper
                  isLoading={reviewsLoading}
                  isError={Boolean(reviewsError)}
                  errorMessage={reviewsError ?? undefined}
                  isEmpty={!reviewsLoading && !reviewsError && marketReviews.length === 0}
                  loadingTitle="Loading market reviews"
                  loadingDescription="Requesting related trade reviews for this market."
                  errorTitle="Could not load market reviews"
                  emptyTitle="No reviews linked yet"
                  emptyDescription="Execute a paper trade, generate reviews with `cd apps/backend && python manage.py generate_trade_reviews`, and return here to close the loop."
                  action={
                    <button className="secondary-button" type="button" onClick={() => navigate('/postmortem')}>
                      Open review queue
                    </button>
                  }
                >
                  <div className="table-link-stack">
                    {marketReviews.slice(0, 3).map((review) => (
                      <a key={review.id} href={`/postmortem/${review.id}`} className="market-link" onClick={(event) => {
                        event.preventDefault();
                        navigate(`/postmortem/${review.id}`);
                      }}>
                        <strong><ReviewOutcomeBadge outcome={review.outcome} status={review.review_status} /></strong>
                        <span>Trade #{review.trade_id} · {review.recommendation || review.summary}</span>
                      </a>
                    ))}
                  </div>
                </DataStateWrapper>
              </SectionCard>
            </section>

            <SectionCard
              eyebrow="Recent snapshots"
              title="Backend market snapshots"
              description="Most recent time-series records returned by the market detail endpoint."
            >
              <MarketSnapshotsTable snapshots={market.recent_snapshots} />
            </SectionCard>
          </>
        ) : null}
      </DataStateWrapper>
    </div>
  );
}
