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

        setCatalogError(getErrorMessage(error, 'No se pudo cargar el resumen de mercados y filtros.'));
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
        if (isMounted) {
          setEvents([]);
        }
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
    <div className="page-stack">
      <PageHeader
        eyebrow="Exploración"
        title="Markets"
        description="Explora oportunidades en modo simple: mercados demo y mercados reales en solo lectura, siempre separados claramente."
      />

      <DataStateWrapper
        isLoading={catalogLoading}
        isError={Boolean(catalogError)}
        errorMessage={catalogError ?? undefined}
        loadingTitle="Cargando vista de mercados"
        loadingDescription="Consultando resumen, proveedores y categorías."
        errorTitle="No se pudo cargar la vista de mercados"
      >
        {summary ? <MarketsSummaryCards summary={summary} /> : null}

        <MarketsFilters filters={filters} providers={providers} events={events} onChange={setFilters} onReset={() => setFilters(defaultFilters)} />

        <SectionCard
          eyebrow="Catalog"
          title="Lista de mercados"
          description="Lista principal para revisar mercados y abrir el detalle cuando quieras profundizar."
          aside={<span className="muted-text">{activeFilterCount} filtros activos · {demoMarketCount} demo · {realMarketCount} reales · {realPaperTradableCount} aptos para paper</span>}
        >
          <DataStateWrapper
            isLoading={marketsLoading}
            isError={Boolean(marketsError)}
            errorMessage={marketsError ?? undefined}
            isEmpty={!marketsLoading && !marketsError && markets.length === 0}
            loadingTitle="Cargando mercados"
            loadingDescription="Buscando mercados que cumplan los filtros actuales."
            errorTitle="No se pudo cargar la lista"
            emptyTitle={emptyTitle}
            emptyDescription={emptyDescription}
            action={
              activeFilterCount > 0 ? (
                <button className="secondary-button" type="button" onClick={() => setFilters(defaultFilters)}>
                  Limpiar filtros
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
