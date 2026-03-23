import { useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusCard } from '../components/StatusCard';
import { DashboardStatGrid } from '../components/dashboard/DashboardStatGrid';
import { ModuleStatusList } from '../components/dashboard/ModuleStatusList';
import { QuickLinksPanel } from '../components/dashboard/QuickLinksPanel';
import { RecentMarketsPanel } from '../components/dashboard/RecentMarketsPanel';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { LatestSignalsList } from '../components/signals/LatestSignalsList';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { useSystemHealth } from '../app/SystemHealthProvider';
import { API_BASE_URL, PROJECT_NAME } from '../lib/config';
import { dashboardModules, dashboardQuickLinks, localEnvironmentHighlights, nextProjectSteps } from '../lib/dashboard';
import { getMarketSystemSummary, getMarkets } from '../services/markets';
import { getSignals, getSignalsSummary } from '../services/signals';
import type { MarketListItem, MarketSystemSummary } from '../types/markets';
import type { DashboardStatCard, RecentMarketItem } from '../types/dashboard';
import type { MarketSignal, SignalSummary } from '../types/signals';

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

  useEffect(() => {
    let isMounted = true;

    async function loadSummary() {
      setSummaryLoading(true);
      setSummaryError(null);

      try {
        const response = await getMarketSystemSummary();

        if (!isMounted) {
          return;
        }

        setSummary(response);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setSummaryError(getErrorMessage(error, 'Could not load market system summary.'));
      } finally {
        if (isMounted) {
          setSummaryLoading(false);
        }
      }
    }

    void loadSummary();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadRecentMarkets() {
      setRecentMarketsLoading(true);
      setRecentMarketsError(null);

      try {
        const response = await getMarkets();

        if (!isMounted) {
          return;
        }

        setRecentMarkets(mapRecentMarkets(response));
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setRecentMarketsError(getErrorMessage(error, 'Could not load recent markets from the local catalog.'));
      } finally {
        if (isMounted) {
          setRecentMarketsLoading(false);
        }
      }
    }

    void loadRecentMarkets();

    return () => {
      isMounted = false;
    };
  }, []);


  useEffect(() => {
    let isMounted = true;

    async function loadSignalsContext() {
      setSignalsLoading(true);
      setSignalsError(null);

      try {
        const [summaryResponse, latestSignalsResponse] = await Promise.all([
          getSignalsSummary(),
          getSignals({ ordering: '-created_at' }),
        ]);

        if (!isMounted) {
          return;
        }

        setSignalsSummary(summaryResponse);
        setLatestSignals(latestSignalsResponse.slice(0, 3));
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setSignalsError(getErrorMessage(error, 'Could not load demo signals from the local backend.'));
      } finally {
        if (isMounted) {
          setSignalsLoading(false);
        }
      }
    }

    void loadSignalsContext();

    return () => {
      isMounted = false;
    };
  }, []);

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

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Control center"
        title={PROJECT_NAME}
        description="Local-first dashboard connected to the Django backend so you can inspect system health, demo market coverage, and the current project roadmap from one place."
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
            { label: 'Database', value: formatBooleanFlag(health.data?.database_configured) },
            { label: 'Redis', value: formatBooleanFlag(health.data?.redis_configured) },
          ]}
        />

        <SectionCard
          eyebrow="Local environment"
          title="Development context"
          description="This app is optimized for local development with a demo dataset and explicit backend visibility."
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

      <section className="content-grid content-grid--two-columns">
        <SectionCard
          eyebrow="Navigation"
          title="Quick links"
          description="Jump directly into the modules that already exist, while keeping placeholders visible as the roadmap entry points."
        >
          <QuickLinksPanel links={dashboardQuickLinks} />
        </SectionCard>

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
          description="A small operator view that connects markets, paper trading, and the new mock-agent signals layer."
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
            emptyDescription="Run `cd apps/backend && python manage.py generate_demo_signals` to populate the new signals workspace."
          >
            <LatestSignalsList signals={latestSignals} />
          </DataStateWrapper>
        </SectionCard>
      </section>

      <SectionCard
        eyebrow="Roadmap"
        title="Next steps"
        description="The current dashboard intentionally stops at visibility and navigation, but it now prepares the shell for the next practical backend integrations."
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
