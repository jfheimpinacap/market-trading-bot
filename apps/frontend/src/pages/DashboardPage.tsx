import { useCallback, useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusCard } from '../components/StatusCard';
import { DashboardStatGrid } from '../components/dashboard/DashboardStatGrid';
import { ModuleStatusList } from '../components/dashboard/ModuleStatusList';
import { QuickLinksPanel } from '../components/dashboard/QuickLinksPanel';
import { RecentMarketsPanel } from '../components/dashboard/RecentMarketsPanel';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { WorkflowStatusPanel } from '../components/flow/WorkflowStatusPanel';
import { LatestSignalsList } from '../components/signals/LatestSignalsList';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { useSystemHealth } from '../app/SystemHealthProvider';
import { API_BASE_URL, PROJECT_NAME } from '../lib/config';
import { dashboardModules, dashboardQuickLinks, localEnvironmentHighlights, nextProjectSteps } from '../lib/dashboard';
import { navigate } from '../lib/router';
import { useDemoFlowRefresh } from '../hooks/useDemoFlowRefresh';
import { getMarketSystemSummary, getMarkets } from '../services/markets';
import { getPaperSummary } from '../services/paperTrading';
import { getReviewsSummary } from '../services/reviews';
import { getSignals, getSignalsSummary } from '../services/signals';
import { getTradeProposals } from '../services/proposals';
import type { MarketListItem, MarketSystemSummary } from '../types/markets';
import type { DashboardStatCard, RecentMarketItem } from '../types/dashboard';
import type { PaperPortfolioSummary } from '../types/paperTrading';
import type { TradeReviewSummary } from '../types/reviews';
import type { MarketSignal, SignalSummary } from '../types/signals';
import type { TradeProposal } from '../types/proposals';
import type { WorkflowStatusItem } from '../types/demoFlow';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function formatBooleanFlag(value: boolean | undefined) {
  return value ? 'Configured' : 'Not configured';
}

function formatCatalogSeeded(summary: MarketSystemSummary | null) {
  if (!summary) {
    return 'Checking demo catalog';
  }

  return summary.total_markets > 0 ? 'Seeded demo catalog detected' : 'No demo markets found yet';
}

function buildStats(summary: MarketSystemSummary): DashboardStatCard[] {
  return [
    {
      label: 'Providers',
      value: String(summary.total_providers),
      helperText: 'Registered market data providers in the local demo dataset.',
    },
    {
      label: 'Events',
      value: String(summary.total_events),
      helperText: 'Underlying events currently exposed by the read-only API.',
    },
    {
      label: 'Markets',
      value: String(summary.total_markets),
      helperText: 'Contracts available to inspect from the seeded backend catalog.',
    },
    {
      label: 'Active markets',
      value: String(summary.active_markets),
      helperText: 'Contracts that still appear open or active in the local dataset.',
    },
    {
      label: 'Resolved markets',
      value: String(summary.resolved_markets),
      helperText: 'Contracts already settled in the demo catalog.',
    },
    {
      label: 'Snapshots',
      value: String(summary.total_snapshots),
      helperText: 'Historical rows available for quick inspection in market detail views.',
    },
  ];
}

function mapRecentMarkets(markets: MarketListItem[]): RecentMarketItem[] {
  return [...markets]
    .sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime())
    .slice(0, 5)
    .map((market) => ({
      id: market.id,
      title: market.title,
      providerName: market.provider.name,
      eventTitle: market.event_title,
      status: market.status,
      probability: market.current_market_probability,
      updatedAt: market.updated_at,
    }));
}

export function DashboardPage() {
  const health = useSystemHealth();
  const [summary, setSummary] = useState<MarketSystemSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [recentMarkets, setRecentMarkets] = useState<RecentMarketItem[]>([]);
  const [recentMarketsLoading, setRecentMarketsLoading] = useState(true);
  const [recentMarketsError, setRecentMarketsError] = useState<string | null>(null);
  const [signalsSummary, setSignalsSummary] = useState<SignalSummary | null>(null);
  const [latestSignals, setLatestSignals] = useState<MarketSignal[]>([]);
  const [signalsLoading, setSignalsLoading] = useState(true);
  const [signalsError, setSignalsError] = useState<string | null>(null);
  const [reviewsSummary, setReviewsSummary] = useState<TradeReviewSummary | null>(null);
  const [reviewsLoading, setReviewsLoading] = useState(true);
  const [reviewsError, setReviewsError] = useState<string | null>(null);
  const [paperSummary, setPaperSummary] = useState<PaperPortfolioSummary | null>(null);
  const [paperSummaryLoading, setPaperSummaryLoading] = useState(true);
  const [paperSummaryError, setPaperSummaryError] = useState<string | null>(null);
  const [proposals, setProposals] = useState<TradeProposal[]>([]);
  const [proposalsLoading, setProposalsLoading] = useState(true);
  const [proposalsError, setProposalsError] = useState<string | null>(null);
  const [realMarketCount, setRealMarketCount] = useState(0);
  const [realPaperTradableCount, setRealPaperTradableCount] = useState(0);
  const [realProviders, setRealProviders] = useState<string[]>([]);
  const [realContextLoading, setRealContextLoading] = useState(true);
  const [realContextError, setRealContextError] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    setSummaryLoading(true);
    setSummaryError(null);

    try {
      const response = await getMarketSystemSummary();
      setSummary(response);
    } catch (error) {
      setSummaryError(getErrorMessage(error, 'Could not load market system summary.'));
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  const loadRecentMarkets = useCallback(async () => {
    setRecentMarketsLoading(true);
    setRecentMarketsError(null);

    try {
      const response = await getMarkets();
      setRecentMarkets(mapRecentMarkets(response));
    } catch (error) {
      setRecentMarketsError(getErrorMessage(error, 'Could not load recent markets from the local catalog.'));
    } finally {
      setRecentMarketsLoading(false);
    }
  }, []);

  const loadRealContext = useCallback(async () => {
    setRealContextLoading(true);
    setRealContextError(null);

    try {
      const response = await getMarkets({ source_type: 'real_read_only' });
      setRealMarketCount(response.length);
      setRealPaperTradableCount(response.filter((market) => market.paper_tradable).length);
      setRealProviders(Array.from(new Set(response.map((market) => market.provider.name))).sort((left, right) => left.localeCompare(right)));
    } catch (error) {
      setRealMarketCount(0);
      setRealPaperTradableCount(0);
      setRealProviders([]);
      setRealContextError(getErrorMessage(error, 'Could not load real read-only market context.'));
    } finally {
      setRealContextLoading(false);
    }
  }, []);

  const loadSignalsContext = useCallback(async () => {
    setSignalsLoading(true);
    setSignalsError(null);

    try {
      const [summaryResponse, latestSignalsResponse] = await Promise.all([
        getSignalsSummary(),
        getSignals({ ordering: '-created_at' }),
      ]);
      setSignalsSummary(summaryResponse);
      setLatestSignals(latestSignalsResponse.slice(0, 3));
    } catch (error) {
      setSignalsError(getErrorMessage(error, 'Could not load demo signals from the local backend.'));
    } finally {
      setSignalsLoading(false);
    }
  }, []);

  const loadReviewsSummary = useCallback(async () => {
    setReviewsLoading(true);
    setReviewsError(null);

    try {
      const response = await getReviewsSummary();
      setReviewsSummary(response);
    } catch (error) {
      setReviewsError(getErrorMessage(error, 'Could not load demo trade reviews summary.'));
    } finally {
      setReviewsLoading(false);
    }
  }, []);

  const loadPaperSummary = useCallback(async () => {
    setPaperSummaryLoading(true);
    setPaperSummaryError(null);

    try {
      const response = await getPaperSummary();
      setPaperSummary(response);
    } catch (error) {
      setPaperSummary(null);
      setPaperSummaryError(getErrorMessage(error, 'Could not load the paper portfolio summary.'));
    } finally {
      setPaperSummaryLoading(false);
    }
  }, []);


  const loadProposalsContext = useCallback(async () => {
    setProposalsLoading(true);
    setProposalsError(null);

    try {
      const response = await getTradeProposals();
      setProposals(response);
    } catch (error) {
      setProposals([]);
      setProposalsError(getErrorMessage(error, 'Could not load trade proposals summary.'));
    } finally {
      setProposalsLoading(false);
    }
  }, []);

  const refreshDashboard = useCallback(async () => {
    await Promise.all([
      loadSummary(),
      loadRecentMarkets(),
      loadRealContext(),
      loadSignalsContext(),
      loadReviewsSummary(),
      loadPaperSummary(),
      loadProposalsContext(),
    ]);
  }, [loadPaperSummary, loadProposalsContext, loadRealContext, loadRecentMarkets, loadReviewsSummary, loadSignalsContext, loadSummary]);

  useEffect(() => {
    void refreshDashboard();
  }, [refreshDashboard]);

  useDemoFlowRefresh(refreshDashboard);

  const backendDescription = health.isLoading
    ? 'Checking the local Django health endpoint.'
    : health.isError
      ? 'Backend is currently offline from the frontend perspective. Verify that Django is running and VITE_API_BASE_URL is correct.'
      : 'Backend healthcheck loaded successfully from the local API and is ready for dashboard integrations.';

  const overallEnvironmentTone = health.isError ? 'offline' : health.isLoading ? 'loading' : 'online';
  const overallEnvironmentLabel = health.isError
    ? 'Backend offline'
    : health.isLoading
      ? 'Checking services'
      : 'Local environment ready';

  const marketStats = useMemo(() => (summary ? buildStats(summary) : []), [summary]);
  const actionableProposals = useMemo(() => proposals.filter((proposal) => proposal.is_actionable), [proposals]);
  const workflowItems = useMemo<WorkflowStatusItem[]>(() => {
    const openPositions = paperSummary?.open_positions_count ?? 0;
    const recentReviews = reviewsSummary?.total_reviews ?? 0;
    const actionableSignals = signalsSummary?.actionable_signals ?? 0;
    const activeMarkets = summary?.active_markets ?? 0;

    return [
      {
        label: '1. Discover',
        value: `${activeMarkets} active markets`,
        helperText: 'Start in Markets to inspect the demo catalog and find contracts that deserve attention.',
        tone: activeMarkets > 0 ? 'ready' : 'warning',
        href: '/markets',
        linkLabel: 'Explore markets',
      },
      {
        label: '2. Validate',
        value: `${actionableSignals} actionable signals`,
        helperText: 'Signals gives the quickest view of demo opportunities that can be escalated into market detail.',
        tone: actionableSignals > 0 ? 'ready' : 'neutral',
        href: '/signals',
        linkLabel: 'Review signals',
      },
      {
        label: '3. Execute',
        value: `${openPositions} open positions`,
        helperText: 'Paper execution happens from market detail after the risk check approves or cautions the trade.',
        tone: openPositions > 0 ? 'ready' : 'neutral',
        href: '/portfolio',
        linkLabel: 'Inspect portfolio',
      },
      {
        label: '4. Review',
        value: `${recentReviews} recent reviews`,
        helperText: 'Post-mortem closes the loop with outcomes, lessons, and links back to the trade context.',
        tone: recentReviews > 0 ? 'ready' : 'neutral',
        href: '/postmortem',
        linkLabel: 'Open post-mortem',
      },
    ];
  }, [paperSummary?.open_positions_count, reviewsSummary?.total_reviews, signalsSummary?.actionable_signals, summary?.active_markets]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Control center"
        title={PROJECT_NAME}
        description="Local-first dashboard connected to the Django backend so you can move through the full demo workflow from market discovery to review without feeling like each module is isolated."
        actions={<StatusBadge tone={overallEnvironmentTone}>{overallEnvironmentLabel}</StatusBadge>}
      />

      <section className="content-grid content-grid--two-columns">
        <StatusCard
          title="Backend API"
          status={health.backendStatus}
          description={backendDescription}
          details={[
            { label: 'Health endpoint', value: `${API_BASE_URL}/api/health/` },
            { label: 'Environment', value: health.data?.environment ?? 'Unavailable' },
            { label: 'App mode', value: health.data?.app_mode?.toUpperCase() ?? 'Unavailable' },
            { label: 'Database', value: formatBooleanFlag(health.data?.database_configured) },
            { label: 'Redis', value: formatBooleanFlag(health.data?.redis_configured) },
            { label: 'Redis required', value: formatBooleanFlag(health.data?.redis_required) },
          ]}
        />

        <SectionCard
          eyebrow="Local environment"
          title="Development context"
          description="This app is optimized for local development with a demo dataset, explicit backend visibility, and manual control over seed / signal / review generation."
          aside={
            <StatusBadge tone={summaryError ? 'offline' : summary && summary.total_markets > 0 ? 'ready' : 'loading'}>
              {summaryError ? 'Summary unavailable' : formatCatalogSeeded(summary)}
            </StatusBadge>
          }
        >
          <dl className="dashboard-key-value-list">
            {localEnvironmentHighlights.map((item) => (
              <div key={item.label}>
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
            <div>
              <dt>Health state</dt>
              <dd>{health.backendStatus}</dd>
            </div>
            <div>
              <dt>Demo catalog</dt>
              <dd>{formatCatalogSeeded(summary)}</dd>
            </div>
          </dl>
        </SectionCard>
      </section>

      <WorkflowStatusPanel
        title="Current demo flow"
        description="Recommended narrative: discover a market, validate the signal, evaluate risk in market detail, execute a paper trade, check portfolio impact, and finish in post-mortem."
        items={workflowItems}
      />

      <SectionCard
        eyebrow="Catalog summary"
        title="Market system overview"
        description="Metrics below come directly from GET /api/markets/system-summary/ and help confirm the seeded demo dataset is available."
      >
        <DataStateWrapper
          isLoading={summaryLoading}
          isError={Boolean(summaryError)}
          errorMessage={summaryError ?? undefined}
          isEmpty={!summaryLoading && !summaryError && !summary}
          loadingTitle="Loading market summary"
          loadingDescription="Requesting provider, event, market, and snapshot totals from the backend."
          errorTitle="Could not load market summary"
          emptyTitle="No summary data available"
          emptyDescription="The backend responded without market summary data. Verify the demo seed and the read-only endpoints."
        >
          <DashboardStatGrid stats={marketStats} />
        </DataStateWrapper>
      </SectionCard>

      <SectionCard
        eyebrow="Real data visibility"
        title="Read-only provider connectivity"
        description="Quick visibility for real provider ingestion while keeping the app execution model strictly demo/paper."
        aside={<StatusBadge tone={realContextError ? 'offline' : realMarketCount > 0 ? 'ready' : 'pending'}>{realMarketCount > 0 ? 'Connected' : 'Not ingested yet'}</StatusBadge>}
      >
        <DataStateWrapper
          isLoading={realContextLoading}
          isError={Boolean(realContextError)}
          errorMessage={realContextError ?? undefined}
          loadingTitle="Loading real market context"
          loadingDescription="Checking read-only real markets from the shared markets endpoint."
          errorTitle="Could not load real market context"
          isEmpty={!realContextLoading && !realContextError && realMarketCount === 0}
          emptyTitle="No real markets ingested yet"
          emptyDescription="Run the backend ingestion command for Kalshi or Polymarket, then refresh this dashboard."
        >
          <dl className="dashboard-key-value-list">
            <div><dt>Real markets</dt><dd>{realMarketCount}</dd></div>
            <div><dt>Real paper-tradable</dt><dd>{realPaperTradableCount}</dd></div>
            <div><dt>Real providers</dt><dd>{realProviders.length > 0 ? realProviders.join(', ') : '—'}</dd></div>
            <div><dt>Trading mode</dt><dd>Paper/demo only</dd></div>
          </dl>
          <button className="secondary-button" type="button" onClick={() => navigate('/markets')}>
            Explore real read-only markets
          </button>
        </DataStateWrapper>
      </SectionCard>

      <section className="content-grid content-grid--two-columns">
        <SectionCard
          eyebrow="Navigation"
          title="Quick links"
          description="These links intentionally mirror the recommended end-to-end workflow so the landing page reads like a guided operator console."
        >
          <QuickLinksPanel links={dashboardQuickLinks} />
        </SectionCard>

        <SectionCard
          eyebrow="Proposal engine"
          title="Trade proposals snapshot"
          description="Compact summary for proposal throughput and actionability before entering market detail and trade evaluation."
          aside={
            <StatusBadge tone={proposalsError ? 'offline' : proposalsLoading ? 'loading' : 'ready'}>
              {proposalsLoading ? 'Syncing proposals' : 'Proposals synced'}
            </StatusBadge>
          }
        >
          <DataStateWrapper
            isLoading={proposalsLoading}
            isError={Boolean(proposalsError)}
            errorMessage={proposalsError ?? undefined}
            loadingTitle="Loading proposals snapshot"
            loadingDescription="Requesting proposal engine demo records for dashboard context."
            errorTitle="Could not load proposals snapshot"
          >
            <dl className="dashboard-key-value-list">
              <div><dt>Total proposals</dt><dd>{proposals.length}</dd></div>
              <div><dt>Actionable proposals</dt><dd>{actionableProposals.length}</dd></div>
              <div><dt>Latest proposal</dt><dd>{proposals[0] ? `#${proposals[0].id} · ${proposals[0].direction}` : 'No proposals yet'}</dd></div>
            </dl>
          </DataStateWrapper>
        </SectionCard>
      </section>

      <section className="content-grid content-grid--two-columns">
        <SectionCard
          eyebrow="Execution status"
          title="Project modules"
          description="A compact view of what is already usable versus what remains intentionally deferred in the roadmap."
        >
          <ModuleStatusList modules={dashboardModules} />
        </SectionCard>
      </section>

      <section className="content-grid content-grid--two-columns">
        <SectionCard
          eyebrow="Pipeline summary"
          title="Cross-module indicators"
          description="Small, current indicators that help explain where the demo flow already has data and where you may need to seed or generate more context."
          aside={<StatusBadge tone={paperSummaryError ? 'offline' : paperSummaryLoading ? 'loading' : 'ready'}>{paperSummaryLoading ? 'Syncing flow' : 'Flow synced'}</StatusBadge>}
        >
          <dl className="dashboard-key-value-list">
            <div><dt>Active markets</dt><dd>{summary?.active_markets ?? '—'}</dd></div>
            <div><dt>Actionable signals</dt><dd>{signalsSummary?.actionable_signals ?? '—'}</dd></div>
            <div><dt>Open positions</dt><dd>{paperSummary?.open_positions_count ?? '—'}</dd></div>
            <div><dt>Recent reviews</dt><dd>{reviewsSummary?.total_reviews ?? '—'}</dd></div>
            <div><dt>Recent trades</dt><dd>{paperSummary?.recent_trades.length ?? '—'}</dd></div>
            <div><dt>Next best step</dt><dd>{signalsSummary && signalsSummary.actionable_signals > 0 ? 'Open Signals or a market detail page.' : 'Generate signals or inspect active markets.'}</dd></div>
          </dl>
          {paperSummaryError ? <p className="paper-inline-notice">Portfolio summary unavailable: {paperSummaryError}</p> : null}
        </SectionCard>

        <SectionCard
          eyebrow="Post-mortem bridge"
          title="Trade reviews at a glance"
          description="Small summary from GET /api/reviews/summary/ so the dashboard can point operators toward the retrospective workflow without redesigning the landing page."
          aside={
            <StatusBadge tone={reviewsError ? 'offline' : reviewsSummary && reviewsSummary.unfavorable_reviews > 0 ? 'neutral' : reviewsLoading ? 'loading' : 'ready'}>
              {reviewsSummary ? `${reviewsSummary.total_reviews} reviews` : reviewsLoading ? 'Reviews loading' : 'No reviews'}
            </StatusBadge>
          }
        >
          <DataStateWrapper
            isLoading={reviewsLoading}
            isError={Boolean(reviewsError)}
            errorMessage={reviewsError ?? undefined}
            isEmpty={!reviewsLoading && !reviewsError && !reviewsSummary}
            loadingTitle="Loading review summary"
            loadingDescription="Requesting post-mortem summary counters from the backend."
            errorTitle="Could not load review summary"
            emptyTitle="No reviews summary available"
            emptyDescription="Run `cd apps/backend && python manage.py generate_trade_reviews` to generate demo trade reviews for the retrospective module."
          >
            {reviewsSummary ? (
              <dl className="dashboard-key-value-list">
                <div><dt>Total reviews</dt><dd>{reviewsSummary.total_reviews}</dd></div>
                <div><dt>Favorable</dt><dd>{reviewsSummary.favorable_reviews}</dd></div>
                <div><dt>Unfavorable</dt><dd>{reviewsSummary.unfavorable_reviews}</dd></div>
                <div><dt>Stale</dt><dd>{reviewsSummary.stale_reviews}</dd></div>
                <div><dt>Latest review</dt><dd>{reviewsSummary.latest_reviewed_at ?? '—'}</dd></div>
                <div><dt>Next step</dt><dd>Open /postmortem for the review queue and detail view.</dd></div>
              </dl>
            ) : null}
          </DataStateWrapper>
        </SectionCard>

        <SectionCard
          eyebrow="Recent catalog activity"
          title="Recent markets"
          description="A lightweight sample from GET /api/markets/ so the dashboard feels tied to the live demo catalog instead of acting like a placeholder."
          aside={<StatusBadge tone="neutral">Top 5 records</StatusBadge>}
        >
          <DataStateWrapper
            isLoading={recentMarketsLoading}
            isError={Boolean(recentMarketsError)}
            errorMessage={recentMarketsError ?? undefined}
            isEmpty={!recentMarketsLoading && !recentMarketsError && recentMarkets.length === 0}
            loadingTitle="Loading recent markets"
            loadingDescription="Requesting a small sample of markets from the local backend."
            errorTitle="Could not load recent markets"
            emptyTitle="No markets available yet"
            emptyDescription="Seed the demo catalog or verify the read-only markets endpoint to populate this section."
          >
            <RecentMarketsPanel markets={recentMarkets} />
          </DataStateWrapper>
        </SectionCard>

        <SectionCard
          eyebrow="Signals bridge"
          title="Latest demo signals"
          description="A small operator view that connects market discovery, evaluation, and eventual paper execution."
          aside={
            <StatusBadge tone={signalsError ? 'offline' : signalsSummary && signalsSummary.actionable_signals > 0 ? 'ready' : 'loading'}>
              {signalsSummary ? `${signalsSummary.actionable_signals} actionable` : 'Signals loading'}
            </StatusBadge>
          }
        >
          <DataStateWrapper
            isLoading={signalsLoading}
            isError={Boolean(signalsError)}
            errorMessage={signalsError ?? undefined}
            isEmpty={!signalsLoading && !signalsError && latestSignals.length === 0}
            loadingTitle="Loading latest signals"
            loadingDescription="Requesting the most recent demo signals from the local backend."
            errorTitle="Could not load latest signals"
            emptyTitle="No signals available yet"
            emptyDescription="Run `cd apps/backend && python manage.py generate_demo_signals` to populate the signals workspace."
          >
            <LatestSignalsList signals={latestSignals} />
          </DataStateWrapper>
        </SectionCard>
      </section>

      <SectionCard
        eyebrow="Roadmap"
        title="Next steps"
        description="The dashboard still stays sober and technical, but now it also clarifies what remains manual in the demo flow."
      >
        <ul className="bullet-list">
          {nextProjectSteps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ul>
      </SectionCard>
    </div>
  );
}
