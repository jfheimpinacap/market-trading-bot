import { useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../../components/PageHeader';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { MarketsFilters } from '../../components/markets/MarketsFilters';
import { MarketsSummaryCards } from '../../components/markets/MarketsSummaryCards';
import { MarketsTable } from '../../components/markets/MarketsTable';
import { SectionCard } from '../../components/SectionCard';
import { getEvents, getMarketSystemSummary, getMarkets, getProviders } from '../../services/markets';
import type { MarketEvent, MarketFilters, MarketListItem, MarketProvider, MarketSystemSummary } from '../../types/markets';

const defaultFilters: MarketFilters = {
  provider: '',
  category: '',
  status: '',
  is_active: '',
  search: '',
  ordering: '',
};

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function MarketsPage() {
  const [filters, setFilters] = useState<MarketFilters>(defaultFilters);
  const [summary, setSummary] = useState<MarketSystemSummary | null>(null);
  const [providers, setProviders] = useState<MarketProvider[]>([]);
  const [events, setEvents] = useState<MarketEvent[]>([]);
  const [markets, setMarkets] = useState<MarketListItem[]>([]);

  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [marketsLoading, setMarketsLoading] = useState(true);
  const [marketsError, setMarketsError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadCatalog() {
      setCatalogLoading(true);
      setCatalogError(null);

      try {
        const [summaryResponse, providersResponse, eventsResponse] = await Promise.all([
          getMarketSystemSummary(),
          getProviders(),
          getEvents(),
        ]);

        if (!isMounted) {
          return;
        }

        setSummary(summaryResponse);
        setProviders(providersResponse);
        setEvents(eventsResponse);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setCatalogError(getErrorMessage(error, 'Could not load market summary and filter metadata.'));
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

    async function loadMarkets() {
      setMarketsLoading(true);
      setMarketsError(null);

      try {
        const response = await getMarkets(filters);
        if (!isMounted) {
          return;
        }
        setMarkets(response);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setMarketsError(getErrorMessage(error, 'Could not load markets for the selected filters.'));
      } finally {
        if (isMounted) {
          setMarketsLoading(false);
        }
      }
    }

    void loadMarkets();

    return () => {
      isMounted = false;
    };
  }, [filters]);

  const activeFilterCount = useMemo(
    () => Object.values(filters).filter((value) => value.trim().length > 0).length,
    [filters],
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Discovery"
        title="Markets"
        description="Explore the local demo market catalog, inspect platform summary metrics, and drill into market-level rules and recent snapshots."
      />

      <DataStateWrapper
        isLoading={catalogLoading}
        isError={Boolean(catalogError)}
        errorMessage={catalogError ?? undefined}
        loadingTitle="Loading market workspace"
        loadingDescription="Requesting summary cards, providers, and categories from the local backend."
        errorTitle="Could not load market workspace"
      >
        {summary ? <MarketsSummaryCards summary={summary} /> : null}

        <MarketsFilters filters={filters} providers={providers} events={events} onChange={setFilters} onReset={() => setFilters(defaultFilters)} />

        <SectionCard
          eyebrow="Catalog"
          title="Market list"
          description="Desktop-first table for browsing demo markets and opening a focused detail page for each contract."
          aside={<span className="muted-text">{activeFilterCount} active filters</span>}
        >
          <DataStateWrapper
            isLoading={marketsLoading}
            isError={Boolean(marketsError)}
            errorMessage={marketsError ?? undefined}
            isEmpty={!marketsLoading && !marketsError && markets.length === 0}
            loadingTitle="Loading markets"
            loadingDescription="Querying the local backend for market rows that match the current filters."
            errorTitle="Could not load market list"
            emptyTitle="No markets found for the selected filters"
            emptyDescription="Try clearing one or more filters to broaden the local demo market catalog."
            action={
              activeFilterCount > 0 ? (
                <button className="secondary-button" type="button" onClick={() => setFilters(defaultFilters)}>
                  Clear filters
                </button>
              ) : undefined
            }
          >
            <MarketsTable markets={markets} />
          </DataStateWrapper>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
