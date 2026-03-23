import { useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { SignalsFilters } from '../components/signals/SignalsFilters';
import { SignalsSummaryCards } from '../components/signals/SignalsSummaryCards';
import { SignalsTable } from '../components/signals/SignalsTable';
import { getSignalAgents, getSignals, getSignalsSummary } from '../services/signals';
import type { MarketSignal, MockAgent, SignalFilters, SignalSummary } from '../types/signals';

const defaultFilters: SignalFilters = {
  market: '',
  agent: '',
  signal_type: '',
  status: '',
  direction: '',
  is_actionable: '',
  ordering: '-created_at',
};

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function SignalsPage() {
  const [filters, setFilters] = useState<SignalFilters>(defaultFilters);
  const [summary, setSummary] = useState<SignalSummary | null>(null);
  const [agents, setAgents] = useState<MockAgent[]>([]);
  const [signals, setSignals] = useState<MarketSignal[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [signalsLoading, setSignalsLoading] = useState(true);
  const [signalsError, setSignalsError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadCatalog() {
      setCatalogLoading(true);
      setCatalogError(null);

      try {
        const [summaryResponse, agentsResponse] = await Promise.all([getSignalsSummary(), getSignalAgents()]);

        if (!isMounted) {
          return;
        }

        setSummary(summaryResponse);
        setAgents(agentsResponse);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setCatalogError(getErrorMessage(error, 'Could not load the signals summary and agent registry.'));
      } finally {
        if (isMounted) {
          setCatalogLoading(false);
        }
      }
    }

    void loadCatalog();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadSignals() {
      setSignalsLoading(true);
      setSignalsError(null);

      try {
        const response = await getSignals(filters);

        if (!isMounted) {
          return;
        }

        setSignals(response);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setSignalsError(getErrorMessage(error, 'Could not load demo signals for the selected filters.'));
      } finally {
        if (isMounted) {
          setSignalsLoading(false);
        }
      }
    }

    void loadSignals();

    return () => {
      isMounted = false;
    };
  }, [filters]);

  const activeFilterCount = useMemo(
    () => Object.entries(filters).filter(([key, value]) => key !== 'ordering' && value.trim().length > 0).length,
    [filters],
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Decision support"
        title="Signals"
        description="Demo-only opportunity board powered by local heuristics, mock agents, and the existing market catalog. No external data, LLM orchestration, or ML models are used in this stage."
      />

      <DataStateWrapper
        isLoading={catalogLoading}
        isError={Boolean(catalogError)}
        errorMessage={catalogError ?? undefined}
        loadingTitle="Loading signals workspace"
        loadingDescription="Requesting the summary and mock-agent registry from the local backend."
        errorTitle="Could not load the signals workspace"
      >
        {summary ? (
          <SectionCard
            eyebrow="Overview"
            title="Demo signals summary"
            description="These cards summarize the current local queue of scored opportunities, monitoring items, and risk-style observations."
          >
            <SignalsSummaryCards summary={summary} />
            {summary.latest_run ? (
              <p className="muted-text signals-run-note">
                Latest generation run #{summary.latest_run.id} evaluated {summary.latest_run.markets_evaluated} markets and created {summary.latest_run.signals_created} signals.
              </p>
            ) : null}
          </SectionCard>
        ) : null}

        <SignalsFilters filters={filters} agents={agents} onChange={setFilters} onReset={() => setFilters(defaultFilters)} />

        <SectionCard
          eyebrow="Ideas queue"
          title="Signal list"
          description="Desktop-first table for scanning demo signals, their thesis, associated market, mock agent, and actionability state."
          aside={<span className="muted-text">{activeFilterCount} active filters</span>}
        >
          <DataStateWrapper
            isLoading={signalsLoading}
            isError={Boolean(signalsError)}
            errorMessage={signalsError ?? undefined}
            isEmpty={!signalsLoading && !signalsError && signals.length === 0}
            loadingTitle="Loading demo signals"
            loadingDescription="Querying the local backend for the current demo signals queue."
            errorTitle="Could not load the signals list"
            emptyTitle="No demo signals found"
            emptyDescription="Generate signals locally with `cd apps/backend && python manage.py generate_demo_signals`, or clear some filters to broaden the current view."
            action={
              activeFilterCount > 0 ? (
                <button className="secondary-button" type="button" onClick={() => setFilters(defaultFilters)}>
                  Clear filters
                </button>
              ) : undefined
            }
          >
            <SignalsTable signals={signals} />
          </DataStateWrapper>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
