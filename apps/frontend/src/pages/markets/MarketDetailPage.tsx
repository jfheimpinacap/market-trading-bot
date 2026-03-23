import { useCallback, useEffect, useMemo, useState } from 'react';
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
import { SectionCard } from '../../components/SectionCard';
import { LatestSignalsList } from '../../components/signals/LatestSignalsList';
import { navigate, usePathname } from '../../lib/router';
import { getMarketDetail } from '../../services/markets';
import { getSignals } from '../../services/signals';
import {
  createPaperTrade,
  getPaperAccount,
  getPaperPositions,
  getPaperSummary,
  getPaperTrades,
  revaluePaperPortfolio,
} from '../../services/paperTrading';
import type { MarketDetail } from '../../types/markets';
import type { MarketSignal } from '../../types/signals';
import type {
  CreatePaperTradePayload,
  PaperAccount,
  PaperPortfolioSummary,
  PaperPosition,
  PaperTrade,
  TradeExecutionState,
} from '../../types/paperTrading';

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

  useEffect(() => {
    let isMounted = true;

    async function loadPage() {
      if (!marketId) {
        setError('The market identifier is missing from the URL.');
        setIsLoading(false);
        setPaperLoading(false);
        return;
      }

      setTradeExecutionState(null);

      await Promise.all([
        (async () => {
          if (!isMounted) {
            return;
          }
          await loadMarketDetail();
        })(),
        (async () => {
          if (!isMounted) {
            return;
          }
          await loadPaperContext();
        })(),
        (async () => {
          if (!isMounted) {
            return;
          }
          await loadMarketSignals();
        })(),
      ]);
    }

    void loadPage();

    return () => {
      isMounted = false;
    };
  }, [loadMarketDetail, loadMarketSignals, loadPaperContext, marketId]);

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
      await loadPaperContext();
    } catch (submitError) {
      setTradeExecutionState({
        status: 'error',
        message: getErrorMessage(submitError, 'Failed to execute paper trade.'),
        response: null,
      });
    } finally {
      setIsSubmittingTrade(false);
    }
  }, [loadPaperContext]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Market detail"
        title={market?.title ?? 'Market detail'}
        description="Inspect current market state, execute demo paper trades, review account exposure, and verify recent backend snapshots from the local API."
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

            <MarketHistoryChart snapshots={market.recent_snapshots} isLoading={isLoading} error={error} />

            <SectionCard
              eyebrow="Signals"
              title="Demo signals for this market"
              description="Recent local signals connect the market snapshot history above with the mock-agent opportunity layer and paper trading panel below."
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
                emptyDescription="Generate demo signals with `cd apps/backend && python manage.py generate_demo_signals` to populate this section."
              >
                <LatestSignalsList signals={marketSignals} emptyMessage="No recent demo signals for this market yet." />
              </DataStateWrapper>
            </SectionCard>

            <SectionCard
              eyebrow="Paper trading"
              title="Demo trade execution"
              description="Review the historical snapshot trend above, then execute a local simulated buy or sell and refresh the market detail to compare how later snapshots evolve."
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
              <MarketRulesCard shortRules={market.short_rules} rules={market.rules} />

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
