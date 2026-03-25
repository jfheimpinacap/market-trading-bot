import { useCallback, useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusCard } from '../components/StatusCard';
import { DashboardStatGrid } from '../components/dashboard/DashboardStatGrid';
import { ModuleStatusList } from '../components/dashboard/ModuleStatusList';
import { QuickLinksPanel } from '../components/dashboard/QuickLinksPanel';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DeveloperOperationsPanel } from '../components/system/DeveloperOperationsPanel';
import { RefreshToolbar } from '../components/system/RefreshToolbar';
import { RuntimeContextPanel } from '../components/system/RuntimeContextPanel';
import { SimulationActivityPanel } from '../components/system/SimulationActivityPanel';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { useSystemHealth } from '../app/SystemHealthProvider';
import { API_BASE_URL } from '../lib/config';
import { developerCommandGroups, systemModuleReadiness, systemQuickLinks } from '../lib/system';
import { getMarketSystemSummary, getMarkets } from '../services/markets';
import { getRealSyncRuns, getRealSyncStatus, runRealSync } from '../services/realSync';
import type { DashboardStatCard } from '../types/dashboard';
import type { MarketListItem, MarketSystemSummary } from '../types/markets';
import type { RealSyncRun, RealSyncStatusResponse } from '../types/realSync';
import type { SimulationActivityItem, SimulationObservation, SystemRuntimeInfo } from '../types/system';

const ACTIVITY_MARKET_LIMIT = 5;

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function formatBooleanFlag(value: boolean | undefined) {
  if (value === undefined) {
    return 'Unavailable';
  }

  return value ? 'Configured' : 'Not configured';
}

function formatTimestamp(value: string | null) {
  if (!value) {
    return 'Pending';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function formatStatusCount(statuses: Record<string, number>) {
  return [`${statuses.open ?? 0} open`, `${statuses.paused ?? 0} paused`, `${(statuses.closed ?? 0) + (statuses.resolved ?? 0)} closed/resolved`].join(
    ' · ',
  );
}

function buildSummaryStats(summary: MarketSystemSummary): DashboardStatCard[] {
  return [
    {
      label: 'Providers',
      value: String(summary.total_providers),
      helperText: 'Registered provider records in the current local demo dataset.',
    },
    {
      label: 'Events',
      value: String(summary.total_events),
      helperText: 'Underlying events currently exposed through the read-only markets API.',
    },
    {
      label: 'Markets',
      value: String(summary.total_markets),
      helperText: 'Contracts available to inspect from the seeded catalog.',
    },
    {
      label: 'Active markets',
      value: String(summary.active_markets),
      helperText: 'Markets that still appear active/open in the local dataset.',
    },
    {
      label: 'Resolved markets',
      value: String(summary.resolved_markets),
      helperText: 'Markets already settled or terminal inside the demo catalog.',
    },
    {
      label: 'Snapshots',
      value: String(summary.total_snapshots),
      helperText: 'Historical snapshot rows available for recent activity inspection.',
    },
  ];
}

function mapSimulationActivity(markets: MarketListItem[]): SimulationActivityItem[] {
  return [...markets]
    .sort((left, right) => {
      const leftTimestamp = left.latest_snapshot_at ?? left.updated_at;
      const rightTimestamp = right.latest_snapshot_at ?? right.updated_at;
      return new Date(rightTimestamp).getTime() - new Date(leftTimestamp).getTime();
    })
    .slice(0, ACTIVITY_MARKET_LIMIT)
    .map((market) => ({
      id: market.id,
      title: market.title,
      providerName: market.provider.name,
      eventTitle: market.event_title,
      status: market.status,
      probability: market.current_market_probability,
      liquidity: market.liquidity,
      volume24h: market.volume_24h,
      snapshotCount: market.snapshot_count,
      latestSnapshotAt: market.latest_snapshot_at,
      updatedAt: market.updated_at,
      activitySource: market.latest_snapshot_at ? 'latest_snapshot_at' : 'updated_at',
    }));
}

function countChangedMarkets(previousMarkets: MarketListItem[] | null, currentMarkets: MarketListItem[]) {
  if (!previousMarkets || previousMarkets.length === 0) {
    return null;
  }

  const previousMap = new Map(previousMarkets.map((market) => [market.id, market]));

  return currentMarkets.reduce((count, market) => {
    const previousMarket = previousMap.get(market.id);

    if (!previousMarket) {
      return count + 1;
    }

    const hasChanged =
      previousMarket.updated_at !== market.updated_at ||
      previousMarket.latest_snapshot_at !== market.latest_snapshot_at ||
      previousMarket.snapshot_count !== market.snapshot_count ||
      previousMarket.current_market_probability !== market.current_market_probability ||
      previousMarket.liquidity !== market.liquidity ||
      previousMarket.volume_24h !== market.volume_24h ||
      previousMarket.status !== market.status;

    return hasChanged ? count + 1 : count;
  }, 0);
}

function buildObservations(
  summary: MarketSystemSummary | null,
  previousSummary: MarketSystemSummary | null,
  markets: MarketListItem[],
  previousMarkets: MarketListItem[] | null,
): SimulationObservation[] {
  const latestSnapshotAt = markets.reduce<string | null>((latest, market) => {
    if (!market.latest_snapshot_at) {
      return latest;
    }

    if (!latest) {
      return market.latest_snapshot_at;
    }

    return new Date(market.latest_snapshot_at).getTime() > new Date(latest).getTime() ? market.latest_snapshot_at : latest;
  }, null);

  const marketsWithSnapshots = markets.filter((market) => market.snapshot_count > 0).length;
  const snapshotDelta = summary && previousSummary ? summary.total_snapshots - previousSummary.total_snapshots : null;
  const changedMarkets = countChangedMarkets(previousMarkets, markets);
  const statusCounts = markets.reduce<Record<string, number>>((accumulator, market) => {
    const key = market.status.toLowerCase();
    accumulator[key] = (accumulator[key] ?? 0) + 1;
    return accumulator;
  }, {});

  return [
    {
      label: 'Latest observed snapshot',
      value: formatTimestamp(latestSnapshotAt),
      helperText: latestSnapshotAt
        ? 'Taken from the most recent `latest_snapshot_at` returned by GET /api/markets/.'
        : 'No snapshot timestamp was returned yet, so activity has not been observed from snapshot metadata.',
      badge: latestSnapshotAt ? 'Snapshot seen' : 'No snapshot yet',
      tone: latestSnapshotAt ? 'ready' : 'loading',
    },
    {
      label: 'Snapshot coverage',
      value: `${marketsWithSnapshots}/${markets.length || 0} markets`,
      helperText: 'Markets with at least one snapshot provide the strongest local signal that simulation data exists and can keep moving.',
      badge: marketsWithSnapshots > 0 ? 'Catalog seeded' : 'Needs seed',
      tone: marketsWithSnapshots > 0 ? 'online' : 'pending',
    },
    {
      label: 'Snapshot delta since refresh',
      value: snapshotDelta === null ? 'Awaiting baseline' : `${snapshotDelta >= 0 ? '+' : ''}${snapshotDelta}`,
      helperText:
        snapshotDelta === null
          ? 'Run one more refresh after a simulation tick to compare total snapshots against the previous successful summary load.'
          : 'Compared against the previous GET /api/markets/system-summary/ result captured by this page.',
      badge: snapshotDelta === null ? 'Needs compare' : snapshotDelta > 0 ? 'Growth observed' : 'No growth seen',
      tone: snapshotDelta === null ? 'loading' : snapshotDelta > 0 ? 'ready' : 'neutral',
    },
    {
      label: 'Changed market rows',
      value: changedMarkets === null ? 'Awaiting baseline' : String(changedMarkets),
      helperText:
        changedMarkets === null
          ? 'This card compares the current market list with the previous successful refresh once a baseline exists.'
          : 'A row counts as changed when timestamps, snapshot counts, probability, liquidity, volume, or status differ.',
      badge: changedMarkets === null ? 'Needs compare' : changedMarkets > 0 ? 'Movement detected' : 'No row changes',
      tone: changedMarkets === null ? 'loading' : changedMarkets > 0 ? 'ready' : 'neutral',
    },
    {
      label: 'Status mix',
      value: formatStatusCount(statusCounts),
      helperText: 'Useful for spotting whether the demo catalog still contains a healthy mix of open, paused, and terminal markets.',
      badge: 'Current catalog',
      tone: 'neutral',
    },
  ];
}

export function SystemPage() {
  const { data, error, backendStatus, isError, isLoading, lastCheckedAt, refresh: refreshHealth } = useSystemHealth();

  const [summary, setSummary] = useState<MarketSystemSummary | null>(null);
  const [previousSummary, setPreviousSummary] = useState<MarketSystemSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [markets, setMarkets] = useState<MarketListItem[]>([]);
  const [previousMarkets, setPreviousMarkets] = useState<MarketListItem[] | null>(null);
  const [marketsLoading, setMarketsLoading] = useState(true);
  const [marketsError, setMarketsError] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [realSyncStatus, setRealSyncStatus] = useState<RealSyncStatusResponse | null>(null);
  const [realSyncRuns, setRealSyncRuns] = useState<RealSyncRun[]>([]);
  const [realSyncError, setRealSyncError] = useState<string | null>(null);
  const [isRealSyncLoading, setIsRealSyncLoading] = useState(true);
  const [realSyncTriggerState, setRealSyncTriggerState] = useState<'idle' | 'running'>('idle');

  useEffect(() => {
    let isMounted = true;

    async function loadInitialData() {
      setIsRefreshing(true);
      setSummaryLoading(true);
      setMarketsLoading(true);
      setSummaryError(null);
      setMarketsError(null);

      const [summaryResult, marketsResult, realSyncStatusResult, realSyncRunsResult] = await Promise.allSettled([
        getMarketSystemSummary(),
        getMarkets(),
        getRealSyncStatus(),
        getRealSyncRuns({ limit: 8 }),
      ]);

      if (!isMounted) {
        return;
      }

      if (summaryResult.status === 'fulfilled') {
        setSummary(summaryResult.value);
      } else {
        setSummaryError(getErrorMessage(summaryResult.reason, 'Could not load market system summary.'));
      }

      if (marketsResult.status === 'fulfilled') {
        setMarkets(marketsResult.value);
      } else {
        setMarketsError(getErrorMessage(marketsResult.reason, 'Could not load markets from the local catalog.'));
      }
      if (realSyncStatusResult.status === 'fulfilled' && realSyncRunsResult.status === 'fulfilled') {
        setRealSyncStatus(realSyncStatusResult.value);
        setRealSyncRuns(realSyncRunsResult.value);
        setRealSyncError(null);
      } else {
        setRealSyncError('Could not load real-data sync status from /api/real-sync/.');
      }

      setSummaryLoading(false);
      setMarketsLoading(false);
      setIsRealSyncLoading(false);
      setLastRefreshedAt(new Date().toISOString());
      setIsRefreshing(false);
    }

    void loadInitialData();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleRefresh = useCallback(async () => {
    const currentSummary = summary;
    const currentMarkets = markets;

    setIsRefreshing(true);
    setSummaryLoading(true);
    setMarketsLoading(true);
    setSummaryError(null);
    setMarketsError(null);

    const [healthResult, summaryResult, marketsResult, realSyncStatusResult, realSyncRunsResult] = await Promise.allSettled([
      refreshHealth(),
      getMarketSystemSummary(),
      getMarkets(),
      getRealSyncStatus(),
      getRealSyncRuns({ limit: 8 }),
    ]);

    void healthResult;

    if (summaryResult.status === 'fulfilled') {
      setPreviousSummary(currentSummary);
      setSummary(summaryResult.value);
    } else {
      setSummaryError(getErrorMessage(summaryResult.reason, 'Could not refresh market system summary.'));
    }

    if (marketsResult.status === 'fulfilled') {
      setPreviousMarkets(currentMarkets);
      setMarkets(marketsResult.value);
    } else {
      setMarketsError(getErrorMessage(marketsResult.reason, 'Could not refresh markets from the local catalog.'));
    }
    if (realSyncStatusResult.status === 'fulfilled' && realSyncRunsResult.status === 'fulfilled') {
      setRealSyncStatus(realSyncStatusResult.value);
      setRealSyncRuns(realSyncRunsResult.value);
      setRealSyncError(null);
    } else {
      setRealSyncError('Could not refresh real-data sync status.');
    }

    setSummaryLoading(false);
    setMarketsLoading(false);
    setLastRefreshedAt(new Date().toISOString());
    setIsRefreshing(false);
  }, [markets, refreshHealth, summary]);

  const summaryStats = useMemo(() => (summary ? buildSummaryStats(summary) : []), [summary]);
  const providerStatusItems = useMemo(() => {
    if (!realSyncStatus) {
      return [];
    }
    return Object.values(realSyncStatus.providers);
  }, [realSyncStatus]);
  const realMarketsCount = useMemo(
    () => markets.filter((market) => market.source_type === 'real_read_only').length,
    [markets],
  );
  const realProviders = useMemo(
    () => Array.from(new Set(markets.filter((market) => market.source_type === 'real_read_only').map((market) => market.provider.name))).sort((left, right) => left.localeCompare(right)),
    [markets],
  );
  const runtimeItems = useMemo<SystemRuntimeInfo[]>(
    () => [
      { label: 'API base URL', value: API_BASE_URL },
      { label: 'Backend health endpoint', value: `${API_BASE_URL}/api/health/` },
      { label: 'Execution mode', value: 'Local demo' },
      { label: 'App mode', value: data?.app_mode?.toUpperCase() ?? 'Unavailable until health responds' },
      { label: 'Simulation engine', value: 'Available via management commands' },
      { label: 'Data source', value: `Demo + real read-only (${realMarketsCount} real markets)` },
      { label: 'Real providers', value: realProviders.length > 0 ? realProviders.join(', ') : 'No real providers ingested yet' },
      { label: 'Backend environment', value: data?.environment ?? 'Unavailable until health responds' },
    ],
    [data?.app_mode, data?.environment, realMarketsCount, realProviders],
  );
  const activityItems = useMemo(() => mapSimulationActivity(markets), [markets]);
  const observations = useMemo(
    () => buildObservations(summary, previousSummary, markets, previousMarkets),
    [markets, previousMarkets, previousSummary, summary],
  );
  const systemSummaryTone = summaryError ? 'offline' : summary && summary.total_markets > 0 ? 'ready' : 'loading';
  const systemSummaryLabel = summaryError
    ? 'Summary unavailable'
    : summary && summary.total_markets > 0
      ? 'Demo catalog detected'
      : 'Checking catalog';

  const handleTriggerRealSync = useCallback(
    async (provider: 'kalshi' | 'polymarket') => {
      setRealSyncTriggerState('running');
      try {
        await runRealSync({
          provider,
          sync_type: 'active_only',
          active_only: true,
          limit: 100,
          triggered_from: 'system_page',
        });
        await handleRefresh();
      } finally {
        setRealSyncTriggerState('idle');
      }
    },
    [handleRefresh],
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Technical panel"
        title="System"
        description="Local-first monitoring page for backend health, runtime context, demo catalog coverage, and observable simulation movement without adding new backend endpoints."
        actions={<RefreshToolbar lastRefreshedAt={lastRefreshedAt} isRefreshing={isRefreshing} onRefresh={() => void handleRefresh()} />}
      />

      <section className="content-grid content-grid--two-columns">
        <StatusCard
          title="Backend health"
          status={backendStatus}
          description={
            isLoading
              ? 'Checking the shared health endpoint used by the dashboard and system views.'
              : isError
                ? error ?? 'Backend health is currently unavailable from the frontend perspective.'
                : 'Backend connectivity is healthy and the shared health provider is available for local monitoring.'
          }
          details={[
            { label: 'Backend online', value: backendStatus === 'online' ? 'Yes' : backendStatus === 'loading' ? 'Checking' : 'No' },
            { label: 'Environment', value: data?.environment ?? 'Unavailable' },
            { label: 'App mode', value: data?.app_mode?.toUpperCase() ?? 'Unavailable' },
            { label: 'Database configured', value: formatBooleanFlag(data?.database_configured) },
            { label: 'Redis configured', value: formatBooleanFlag(data?.redis_configured) },
            { label: 'Redis required', value: formatBooleanFlag(data?.redis_required) },
            { label: 'Last checked', value: formatTimestamp(lastCheckedAt) },
          ]}
        />

        <RuntimeContextPanel items={runtimeItems} />
      </section>

      <SectionCard
        eyebrow="Catalog summary"
        title="Market system overview"
        description="Metrics below come directly from GET /api/markets/system-summary/ and confirm whether the local demo catalog and snapshot history are available."
        aside={<StatusBadge tone={systemSummaryTone}>{systemSummaryLabel}</StatusBadge>}
      >
        <DataStateWrapper
          isLoading={summaryLoading}
          isError={Boolean(summaryError)}
          errorMessage={summaryError ?? undefined}
          isEmpty={!summaryLoading && !summaryError && !summary}
          loadingTitle="Loading market system overview"
          loadingDescription="Requesting providers, events, markets, and snapshot totals from the backend."
          errorTitle="Could not load market system overview"
          emptyTitle="No summary data available"
          emptyDescription="The backend responded without summary data. Confirm the demo seed and the read-only markets API."
        >
          <DashboardStatGrid stats={summaryStats} />
        </DataStateWrapper>
      </SectionCard>

      <SimulationActivityPanel items={activityItems} observations={observations} isLoading={marketsLoading} errorMessage={marketsError} />

      <SectionCard
        eyebrow="Read-only provider sync"
        title="Real-data sync status"
        description="Technical status of hardened Kalshi/Polymarket refresh runs for real read-only markets and snapshots."
      >
        <DataStateWrapper
          isLoading={isRealSyncLoading}
          isError={Boolean(realSyncError)}
          errorMessage={realSyncError ?? undefined}
          isEmpty={!isRealSyncLoading && !realSyncError && providerStatusItems.length === 0}
          loadingTitle="Loading provider sync status"
          loadingDescription="Fetching recent sync runs and provider health signals."
          errorTitle="Could not load provider sync state"
          emptyTitle="Run a real-data sync to populate fresh provider state."
          emptyDescription="No sync runs exist yet for real read-only providers."
        >
          <div className="stack-md">
            <div className="content-grid content-grid--two-columns">
              {providerStatusItems.map((item) => (
                <StatusCard
                  key={item.provider}
                  title={item.provider.toUpperCase()}
                  status={item.availability === 'available' && !item.stale ? 'online' : 'degraded'}
                  description={item.warning || `Latest status: ${item.latest_status ?? 'N/A'}`}
                  details={[
                    { label: 'Last success', value: formatTimestamp(item.last_success_at) },
                    { label: 'Last failed', value: formatTimestamp(item.last_failed_at) },
                    { label: 'Consecutive failures', value: String(item.consecutive_failures) },
                  ]}
                />
              ))}
            </div>
            <div className="button-row">
              <button type="button" className="secondary-button" disabled={realSyncTriggerState === 'running'} onClick={() => void handleTriggerRealSync('kalshi')}>
                Sync Kalshi (active-only)
              </button>
              <button type="button" className="secondary-button" disabled={realSyncTriggerState === 'running'} onClick={() => void handleTriggerRealSync('polymarket')}>
                Sync Polymarket (active-only)
              </button>
            </div>
            <ul className="simple-list">
              {realSyncRuns.map((run) => (
                <li key={run.id}>
                  <strong>#{run.id}</strong> {run.provider} · {run.sync_type} · <StatusBadge tone={run.status === 'SUCCESS' ? 'ready' : run.status === 'FAILED' ? 'offline' : 'pending'}>{run.status}</StatusBadge> · {run.summary}
                </li>
              ))}
            </ul>
          </div>
        </DataStateWrapper>
      </SectionCard>

      <section className="content-grid content-grid--two-columns">
        <SectionCard
          eyebrow="Execution status"
          title="Module readiness"
          description="A compact readiness map showing what local-first modules are already usable versus what remains intentionally pending."
        >
          <ModuleStatusList modules={systemModuleReadiness} />
        </SectionCard>

        <SectionCard
          eyebrow="Quick navigation"
          title="Quick links"
          description="Jump directly into the main routes that matter while iterating on the local demo stack."
        >
          <QuickLinksPanel links={systemQuickLinks} />
        </SectionCard>
      </section>

      <DeveloperOperationsPanel groups={developerCommandGroups} />
    </div>
  );
}
