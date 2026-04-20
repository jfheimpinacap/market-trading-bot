import { useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../../components/PageHeader';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { MarketsFilters } from '../../components/markets/MarketsFilters';
import { MarketsSummaryCards } from '../../components/markets/MarketsSummaryCards';
import { MarketsTable } from '../../components/markets/MarketsTable';
import { SectionCard } from '../../components/SectionCard';
import { getViewCache, setViewCache } from '../../lib/viewCache';
import { getEvents, getMarketSystemSummary, getMarkets, getProviders } from '../../services/markets';
import { isNotFoundApiError } from '../../services/api/client';
import type { MarketEvent, MarketFilters, MarketListItem, MarketProvider, MarketSystemSummary } from '../../types/markets';

const defaultFilters: MarketFilters = {
  source_type: '',
  provider: '',
  paper_tradable: '',
  category: '',
  status: '',
  is_active: '',
  search: '',
  ordering: '',
};

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

const MARKETS_CACHE_KEY = 'markets:overview';

type MarketsCache = {
  filters: MarketFilters;
  summary: MarketSystemSummary | null;
  providers: MarketProvider[];
  events: MarketEvent[];
  markets: MarketListItem[];
  catalogLoaded: boolean;
  marketsLoaded: boolean;
};

export function MarketsPage() {
  const cached = getViewCache<MarketsCache>(MARKETS_CACHE_KEY);
  const [filters, setFilters] = useState<MarketFilters>(cached?.filters ?? defaultFilters);
  const [summary, setSummary] = useState<MarketSystemSummary | null>(cached?.summary ?? null);
  const [providers, setProviders] = useState<MarketProvider[]>(cached?.providers ?? []);
  const [events, setEvents] = useState<MarketEvent[]>(cached?.events ?? []);
  const [markets, setMarkets] = useState<MarketListItem[]>(cached?.markets ?? []);

  const [catalogLoading, setCatalogLoading] = useState(!cached?.catalogLoaded);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [marketsLoading, setMarketsLoading] = useState(!cached?.marketsLoaded);
  const [marketsError, setMarketsError] = useState<string | null>(null);
  const [catalogLoaded, setCatalogLoaded] = useState(cached?.catalogLoaded ?? false);
  const [marketsLoaded, setMarketsLoaded] = useState(cached?.marketsLoaded ?? false);

  useEffect(() => {
    let isMounted = true;

    async function loadCatalog() {
      setCatalogLoading(true);
      setCatalogError(null);

      const [summaryResult, providersResult, eventsResult] = await Promise.allSettled([
        getMarketSystemSummary(),
        getProviders(),
        getEvents(),
      ]);

      if (!isMounted) {
        return;
      }

      if (summaryResult.status === 'fulfilled') {
        setSummary(summaryResult.value);
      } else if (!isNotFoundApiError(summaryResult.reason)) {
        setCatalogError(getErrorMessage(summaryResult.reason, 'No se pudo cargar el resumen de mercados y filtros.'));
      }

      if (providersResult.status === 'fulfilled') {
        setProviders(providersResult.value);
      } else if (isNotFoundApiError(providersResult.reason)) {
        setProviders([]);
      } else {
        setCatalogError((current) => current ?? getErrorMessage(providersResult.reason, 'No se pudo cargar la lista de proveedores.'));
      }

      if (eventsResult.status === 'fulfilled') {
        setEvents(eventsResult.value);
      } else if (isNotFoundApiError(eventsResult.reason)) {
        setEvents([]);
      } else {
        setCatalogError((current) => current ?? getErrorMessage(eventsResult.reason, 'No se pudieron cargar las categorías/eventos.'));
      }

      if (isMounted) {
        setCatalogLoaded(true);
        setCatalogLoading(false);
      }
    }

    void loadCatalog();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadEventsForFilters() {
      try {
        const response = await getEvents({
          provider: filters.provider || undefined,
          status: filters.status || undefined,
          source_type: filters.source_type || undefined,
        });
        if (isMounted) {
          setEvents(response);
        }
      } catch {
        // Preserve the latest successful event list to avoid flicker while filters are revalidated.
      }
    }

    void loadEventsForFilters();

    return () => {
      isMounted = false;
    };
  }, [filters.provider, filters.source_type, filters.status]);

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

        setMarketsError(getErrorMessage(error, 'No se pudieron cargar mercados para los filtros seleccionados.'));
      } finally {
        if (isMounted) {
          setMarketsLoaded(true);
          setMarketsLoading(false);
        }
      }
    }

    void loadMarkets();

    return () => {
      isMounted = false;
    };
  }, [filters]);

  useEffect(() => {
    setViewCache<MarketsCache>(MARKETS_CACHE_KEY, {
      filters,
      summary,
      providers,
      events,
      markets,
      catalogLoaded,
      marketsLoaded,
    });
  }, [catalogLoaded, events, filters, markets, marketsLoaded, providers, summary]);

  const activeFilterCount = useMemo(
    () => Object.values(filters).filter((value) => value.trim().length > 0).length,
    [filters],
  );
  const realMarketCount = useMemo(
    () => markets.filter((market) => market.source_type === 'real_read_only').length,
    [markets],
  );
  const realPaperTradableCount = useMemo(
    () => markets.filter((market) => market.source_type === 'real_read_only' && market.paper_tradable).length,
    [markets],
  );
  const demoMarketCount = useMemo(
    () => markets.filter((market) => market.source_type === 'demo').length,
    [markets],
  );
  const selectedSource = filters.source_type || 'all';
  const emptyTitle = selectedSource === 'real_read_only'
    ? 'No hay mercados reales disponibles'
    : selectedSource === 'demo'
      ? 'No hay mercados demo con esos filtros'
      : 'No encontramos mercados con esos filtros';
  const emptyDescription = selectedSource === 'real_read_only'
    ? 'Todavía no hay mercados reales cargados en este entorno local. Puedes seguir con mercados demo mientras tanto.'
    : selectedSource === 'demo'
      ? 'Prueba limpiar uno o más filtros para ampliar la búsqueda.'
      : 'Puedes limpiar filtros o cambiar la fuente para ver más opciones.';

  return (
    <div className="page-stack markets-page">
      <PageHeader
        title="Markets"
      />

      <DataStateWrapper
        isLoading={catalogLoading}
        isError={Boolean(catalogError)}
        hasData={catalogLoaded || Boolean(summary) || providers.length > 0 || events.length > 0}
        staleWhileRevalidate
        errorMessage={catalogError ?? undefined}
        loadingTitle="Cargando vista de mercados"
        loadingDescription="Consultando resumen, proveedores y categorías."
        errorTitle="No se pudo cargar la vista de mercados"
      >
        {summary ? <MarketsSummaryCards summary={summary} /> : null}

        <details className="markets-secondary-blocks" open={activeFilterCount > 0}>
          <summary>
            Filtros {activeFilterCount > 0 ? `(${activeFilterCount})` : '(rápido)'}
          </summary>
          <MarketsFilters filters={filters} providers={providers} events={events} onChange={setFilters} onReset={() => setFilters(defaultFilters)} />
        </details>

        <SectionCard
          title="Mercados"
          aside={(
            <div className="markets-compact-aside">
              <span className="muted-text">{demoMarketCount} demo · {realPaperTradableCount}/{realMarketCount} reales aptos</span>
              {activeFilterCount > 0 ? (
                <details>
                  <summary>Más</summary>
                  <button className="secondary-button" type="button" onClick={() => setFilters(defaultFilters)}>
                    Limpiar filtros
                  </button>
                </details>
              ) : null}
            </div>
          )}
        >
          <DataStateWrapper
            isLoading={marketsLoading}
            isError={Boolean(marketsError)}
            hasData={marketsLoaded || markets.length > 0}
            staleWhileRevalidate
            errorMessage={marketsError ?? undefined}
            isEmpty={!marketsLoading && !marketsError && markets.length === 0}
            loadingTitle="Cargando mercados"
            loadingDescription="Buscando mercados que cumplan los filtros actuales."
            errorTitle="No se pudo cargar la lista"
            emptyTitle={emptyTitle}
            emptyDescription={emptyDescription}
          >
            <MarketsTable markets={markets} />
          </DataStateWrapper>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
