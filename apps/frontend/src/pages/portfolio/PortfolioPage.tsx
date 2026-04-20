import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../../components/EmptyState';
import { ContextLinksPanel } from '../../components/flow/ContextLinksPanel';
import { WorkflowStatusPanel } from '../../components/flow/WorkflowStatusPanel';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PaperAccountPanel } from '../../components/paper-trading/PaperAccountPanel';
import { PaperPositionsTable } from '../../components/paper-trading/PaperPositionsTable';
import { PortfolioHistoryChart } from '../../components/paper-trading/PortfolioHistoryChart';
import { PaperSnapshotsPanel } from '../../components/paper-trading/PaperSnapshotsPanel';
import { PortfolioSummaryCards } from '../../components/paper-trading/PortfolioSummaryCards';
import { PaperTradesTable } from '../../components/paper-trading/PaperTradesTable';
import { RevalueToolbar } from '../../components/paper-trading/RevalueToolbar';
import { formatTechnicalTimestamp } from '../../components/paper-trading/utils';
import { useDemoFlowRefresh } from '../../hooks/useDemoFlowRefresh';
import { buildReviewLookupByTradeId, publishDemoFlowRefresh } from '../../lib/demoFlow';
import { navigate } from '../../lib/router';
import { API_BASE_URL } from '../../lib/config';
import { getTradeReviews } from '../../services/reviews';
import { isNotFoundApiError } from '../../services/api/client';
import {
  getPaperAccount,
  getPaperPositions,
  getPaperSnapshots,
  getPaperSummary,
  getPaperTrades,
  revaluePaperPortfolio,
} from '../../services/paperTrading';
import type { ContextLinkItem, WorkflowStatusItem } from '../../types/demoFlow';
import type {
  PaperAccount,
  PaperPortfolioSnapshot,
  PaperPortfolioSummary,
  PaperPosition,
  PaperTrade,
} from '../../types/paperTrading';
import type { TradeReview } from '../../types/reviews';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function PortfolioPage() {
  const [account, setAccount] = useState<PaperAccount | null>(null);
  const [summary, setSummary] = useState<PaperPortfolioSummary | null>(null);
  const [positions, setPositions] = useState<PaperPosition[]>([]);
  const [trades, setTrades] = useState<PaperTrade[]>([]);
  const [snapshots, setSnapshots] = useState<PaperPortfolioSnapshot[]>([]);
  const [reviews, setReviews] = useState<TradeReview[]>([]);

  const [accountLoading, setAccountLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [positionsLoading, setPositionsLoading] = useState(true);
  const [tradesLoading, setTradesLoading] = useState(true);
  const [snapshotsLoading, setSnapshotsLoading] = useState(true);
  const [reviewsLoading, setReviewsLoading] = useState(true);

  const [accountError, setAccountError] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [positionsError, setPositionsError] = useState<string | null>(null);
  const [tradesError, setTradesError] = useState<string | null>(null);
  const [snapshotsError, setSnapshotsError] = useState<string | null>(null);
  const [reviewsError, setReviewsError] = useState<string | null>(null);

  const [isRevaluing, setIsRevaluing] = useState(false);
  const [revalueMessage, setRevalueMessage] = useState<string | null>(null);
  const [revalueError, setRevalueError] = useState<string | null>(null);

  const loadPortfolio = useCallback(async () => {
    setAccountLoading(true);
    setSummaryLoading(true);
    setPositionsLoading(true);
    setTradesLoading(true);
    setSnapshotsLoading(true);
    setReviewsLoading(true);

    setAccountError(null);
    setSummaryError(null);
    setPositionsError(null);
    setTradesError(null);
    setSnapshotsError(null);
    setReviewsError(null);

    const [
      accountResult,
      summaryResult,
      positionsResult,
      tradesResult,
      snapshotsResult,
      reviewsResult,
    ] = await Promise.allSettled([
      getPaperAccount(),
      getPaperSummary(),
      getPaperPositions(),
      getPaperTrades(),
      getPaperSnapshots(),
      getTradeReviews({ ordering: '-reviewed_at' }),
    ]);

    if (accountResult.status === 'fulfilled') {
      setAccount(accountResult.value);
    } else {
      setAccountError(getErrorMessage(accountResult.reason, 'Could not load the active paper account.'));
    }

    if (summaryResult.status === 'fulfilled') {
      setSummary(summaryResult.value);
    } else {
      setSummaryError(getErrorMessage(summaryResult.reason, 'Could not load the portfolio summary.'));
    }

    if (positionsResult.status === 'fulfilled') {
      setPositions(positionsResult.value);
    } else {
      setPositionsError(getErrorMessage(positionsResult.reason, 'Could not load paper positions.'));
    }

    if (tradesResult.status === 'fulfilled') {
      setTrades(tradesResult.value);
    } else {
      setTradesError(getErrorMessage(tradesResult.reason, 'Could not load paper trades.'));
    }

    if (snapshotsResult.status === 'fulfilled') {
      setSnapshots(snapshotsResult.value);
    } else {
      setSnapshotsError(getErrorMessage(snapshotsResult.reason, 'Could not load portfolio snapshots.'));
    }

    if (reviewsResult.status === 'fulfilled') {
      setReviews(reviewsResult.value);
    } else {
      if (!isNotFoundApiError(reviewsResult.reason)) {
        setReviewsError(getErrorMessage(reviewsResult.reason, 'Could not load trade reviews for the portfolio links.'));
      }
    }

    setAccountLoading(false);
    setSummaryLoading(false);
    setPositionsLoading(false);
    setTradesLoading(false);
    setSnapshotsLoading(false);
    setReviewsLoading(false);
  }, []);

  useEffect(() => {
    void loadPortfolio();
  }, [loadPortfolio]);

  useDemoFlowRefresh(loadPortfolio);

  const handleRevalue = useCallback(async () => {
    setIsRevaluing(true);
    setRevalueMessage(null);
    setRevalueError(null);

    try {
      const updatedAccount = await revaluePaperPortfolio();
      setAccount(updatedAccount);
      await loadPortfolio();
      setRevalueMessage(`Portafolio actualizado correctamente. Última actualización: ${formatTechnicalTimestamp(updatedAccount.updated_at)}.`);
      publishDemoFlowRefresh('portfolio-revalued');
    } catch (error) {
      setRevalueError(getErrorMessage(error, 'No se pudo actualizar la valuación del portafolio.'));
    } finally {
      setIsRevaluing(false);
    }
  }, [loadPortfolio]);

  const totalFailure = !accountLoading && !summaryLoading && !positionsLoading && !tradesLoading && !snapshotsLoading
    && Boolean(accountError)
    && Boolean(summaryError)
    && Boolean(positionsError)
    && Boolean(tradesError)
    && Boolean(snapshotsError);

  const lastUpdatedLabel = useMemo(() => {
    if (!account?.updated_at) {
      return 'Esperando la primera actualización de cuenta.';
    }

    return `Última actualización de cuenta: ${formatTechnicalTimestamp(account.updated_at)}.`;
  }, [account?.updated_at]);

  const currency = account?.currency ?? summary?.account.currency ?? 'USD';
  const openPositions = useMemo(
    () => positions.filter((position) => position.status === 'OPEN' && Number(position.quantity) > 0),
    [positions],
  );
  const reviewLookup = useMemo(() => buildReviewLookupByTradeId(reviews), [reviews]);
  const recentReviews = useMemo(() => reviews.slice(0, 3), [reviews]);

  const workflowItems = useMemo<WorkflowStatusItem[]>(() => [
    {
      label: 'Exposición activa',
      value: `${openPositions.length} open positions`,
      helperText: openPositions.length > 0 ? 'Revisa posiciones abiertas para entender dónde está el riesgo actual.' : 'Todavía no hay exposición activa. Puedes empezar desde Markets.',
      tone: openPositions.length > 0 ? 'ready' : 'neutral',
      href: '/markets',
      linkLabel: 'Ver mercados',
    },
    {
      label: 'Historial de operaciones',
      value: `${trades.length} trades`,
      helperText: trades.length > 0 ? 'Úsalo para revisar actividad reciente y detectar cambios de ritmo.' : 'Aún no hay operaciones ejecutadas.',
      tone: trades.length > 0 ? 'ready' : 'warning',
    },
    {
      label: 'Cobertura de revisiones',
      value: `${reviews.length} reviews`,
      helperText: reviews.length > 0 ? 'Las revisiones ayudan a entender por qué cambió el resultado del portafolio.' : 'Sin revisiones recientes todavía.',
      tone: reviews.length > 0 ? 'ready' : 'neutral',
      href: '/postmortem',
      linkLabel: 'Abrir revisiones',
    },
    {
      label: 'Historial de capital',
      value: `${snapshots.length} snapshots`,
      helperText: snapshots.length > 1 ? 'La curva de capital ya tiene historial suficiente para detectar tendencia.' : 'Aún no hay historial suficiente para tendencia.',
      tone: snapshots.length > 1 ? 'ready' : 'neutral',
    },
  ], [openPositions.length, reviews.length, snapshots.length, trades.length]);

  const contextLinks = useMemo<ContextLinkItem[]>(() => [
    {
      title: 'Buscar nuevas oportunidades',
      description: 'Vuelve al catálogo cuando quieras abrir o comparar nuevas posiciones.',
      href: '/markets',
      actionLabel: 'Abrir Markets',
      tone: 'primary',
    },
    {
      title: 'Revisar señales',
      description: 'Si quieres más contexto antes de operar, revisa Signals.',
      href: '/signals',
      actionLabel: 'Abrir Signals',
      tone: 'secondary',
    },
  ], []);

  return (
    <div className="page-stack portfolio-page">
      <PageHeader
        title="Portfolio"
        actions={
          <RevalueToolbar
            onRevalue={handleRevalue}
            isRefreshing={isRevaluing}
            statusMessage={revalueMessage}
            errorMessage={revalueError}
            lastUpdatedLabel={lastUpdatedLabel}
          />
        }
      />

      <details className="portfolio-secondary-blocks">
        <summary>Ver estado ampliado y accesos</summary>
        <div className="portfolio-secondary-blocks__content">
          <WorkflowStatusPanel
            title="Estado general del portafolio"
            description="Revisa impacto, actividad y evolución del capital en una sola vista."
            items={workflowItems}
          />
          <ContextLinksPanel
            title="Siguientes pasos"
            description="Accesos rápidos para continuar el flujo principal."
            links={contextLinks}
          />
        </div>
      </details>

      {totalFailure ? (
        <EmptyState
          eyebrow="Servicio no disponible"
          title="No pudimos cargar el portafolio paper"
          description={`El frontend no pudo obtener datos desde ${API_BASE_URL}. Verifica que el backend esté activo y que exista una cuenta demo.`}
          action={
            <button className="secondary-button" type="button" onClick={() => void loadPortfolio()}>
              Reintentar
            </button>
          }
        />
      ) : null}

      <SectionCard
        eyebrow="Resumen"
        title="Account metrics"
        aside={<StatusBadge tone={accountError ? 'offline' : accountLoading ? 'loading' : 'ready'}>{accountError ? 'Account unavailable' : accountLoading ? 'Loading account' : 'Account synced'}</StatusBadge>}
      >
        <DataStateWrapper
          isLoading={accountLoading || summaryLoading || tradesLoading}
          isError={Boolean(accountError)}
          hasData={Boolean(account)}
          staleWhileRevalidate
          errorMessage={accountError ?? undefined}
          isEmpty={!accountLoading && !accountError && !account}
          loadingTitle="Loading paper account"
          loadingDescription="Requesting paper account, summary, and trade counters from the backend."
          errorTitle="Could not load paper account"
          emptyTitle="No paper account available"
          emptyDescription="Run `cd apps/backend && python manage.py seed_paper_account` and refresh this page to populate the demo portfolio."
          action={
            <button className="secondary-button" type="button" onClick={() => void loadPortfolio()}>
              Retry account sync
            </button>
          }
        >
          {account ? (
            <>
              {summaryError || tradesError ? (
                <p className="paper-inline-notice">
                  Partial data warning: {summaryError ?? tradesError}. Core account metrics are still visible using the endpoints that responded successfully.
                </p>
              ) : null}
              <PortfolioSummaryCards account={account} summary={summary} totalTrades={trades.length} />
            </>
          ) : null}
        </DataStateWrapper>
      </SectionCard>

      <SectionCard
        eyebrow="Evolución"
        title="Equity and balance history"
        aside={<StatusBadge tone={snapshotsError ? 'offline' : snapshotsLoading ? 'loading' : 'ready'}>{snapshotsError ? 'History unavailable' : `${snapshots.length} snapshots loaded`}</StatusBadge>}
      >
        <PortfolioHistoryChart
          snapshots={snapshots}
          currency={currency}
          isLoading={snapshotsLoading}
          error={snapshotsError}
        />
      </SectionCard>

      <SectionCard
        eyebrow="Posiciones"
        title="Positions"
        aside={<StatusBadge tone={positionsError ? 'offline' : positionsLoading ? 'loading' : 'ready'}>{positionsError ? 'Positions unavailable' : `${openPositions.length} open positions`}</StatusBadge>}
      >
        <DataStateWrapper
          isLoading={positionsLoading}
          isError={Boolean(positionsError)}
          hasData={positions.length > 0}
          staleWhileRevalidate
          errorMessage={positionsError ?? undefined}
          isEmpty={!positionsLoading && !positionsError && positions.length === 0}
          loadingTitle="Loading paper positions"
          loadingDescription="Requesting position rows from the backend demo account."
          errorTitle="Could not load paper positions"
          emptyTitle="No positions yet"
          emptyDescription="Open a market and place a paper trade to create the first position, or review signals first if you want a guided next step."
          action={
            <button className="secondary-button" type="button" onClick={() => navigate('/markets')}>
              Explore markets
            </button>
          }
        >
          <PaperPositionsTable positions={positions} currency={currency} />
        </DataStateWrapper>
      </SectionCard>

      <SectionCard
        eyebrow="Actividad"
        title="Trades"
        aside={<StatusBadge tone={tradesError ? 'offline' : tradesLoading ? 'loading' : 'ready'}>{tradesError ? 'Trades unavailable' : `${trades.length} trades loaded`}</StatusBadge>}
      >
        <DataStateWrapper
          isLoading={tradesLoading}
          isError={Boolean(tradesError)}
          hasData={trades.length > 0}
          staleWhileRevalidate
          errorMessage={tradesError ?? undefined}
          isEmpty={!tradesLoading && !tradesError && trades.length === 0}
          loadingTitle="Loading trade history"
          loadingDescription="Requesting recent demo trades from the backend."
          errorTitle="Could not load trade history"
          emptyTitle="No trades recorded yet"
          emptyDescription="Open a market and execute a paper trade first, then return here to inspect history, review links, and portfolio impact."
          action={
            <button className="secondary-button" type="button" onClick={() => navigate('/markets')}>
              Open market detail flow
            </button>
          }
        >
          {reviewsError ? <p className="paper-inline-notice">Review links unavailable: {reviewsError}</p> : null}
          <PaperTradesTable trades={trades} currency={currency} reviewLookup={reviewLookup} />
        </DataStateWrapper>
      </SectionCard>

      <details className="portfolio-secondary-blocks">
        <summary>Ver historial técnico (snapshots)</summary>
        <SectionCard
          eyebrow="Detalle técnico"
          title="Snapshots"
          aside={<StatusBadge tone={snapshotsError ? 'offline' : snapshotsLoading ? 'loading' : 'ready'}>{snapshotsError ? 'Snapshots unavailable' : `${snapshots.length} snapshots loaded`}</StatusBadge>}
        >
          <DataStateWrapper
            isLoading={snapshotsLoading}
            isError={Boolean(snapshotsError)}
            hasData={snapshots.length > 0}
            staleWhileRevalidate
            errorMessage={snapshotsError ?? undefined}
            isEmpty={!snapshotsLoading && !snapshotsError && snapshots.length === 0}
            loadingTitle="Loading portfolio snapshots"
            loadingDescription="Requesting portfolio snapshots captured by the paper trading backend."
            errorTitle="Could not load portfolio snapshots"
            emptyTitle="No snapshots captured yet"
            emptyDescription="Run simulation or revalue the portfolio to create enough snapshots for the chart and technical history panels."
            action={
              <button className="secondary-button" type="button" onClick={() => void handleRevalue()}>
                Revalue portfolio
              </button>
            }
          >
            <PaperSnapshotsPanel snapshots={snapshots} currency={currency} />
          </DataStateWrapper>
        </SectionCard>
      </details>

      <details className="portfolio-secondary-blocks">
        <summary>Ver detalle técnico y contexto</summary>
        <section className="content-grid content-grid--two-columns">
          <SectionCard
            eyebrow="Cuenta"
            title="Paper account details"
          >
            <DataStateWrapper
              isLoading={accountLoading || summaryLoading}
              isError={Boolean(accountError)}
              hasData={Boolean(account)}
              staleWhileRevalidate
              errorMessage={accountError ?? summaryError ?? undefined}
              isEmpty={!accountLoading && !accountError && !account}
              loadingTitle="Loading account details"
              loadingDescription="Waiting for the account and summary endpoints to respond."
              errorTitle="Could not load account details"
              emptyTitle="Paper account missing"
              emptyDescription="Seed the demo account from the backend and refresh the page to unlock this section."
            >
              {account ? (
                <>
                  {summaryError ? <p className="paper-inline-notice">Summary endpoint unavailable: {summaryError}</p> : null}
                  <PaperAccountPanel account={account} summary={summary} />
                </>
              ) : null}
            </DataStateWrapper>
          </SectionCard>

          <SectionCard
            eyebrow="Review bridge"
            title="Recent reviews summary"
            aside={<StatusBadge tone={reviewsError ? 'offline' : reviewsLoading ? 'loading' : 'ready'}>{reviewsLoading ? 'Loading reviews' : `${reviews.length} reviews`}</StatusBadge>}
          >
            <DataStateWrapper
              isLoading={reviewsLoading}
              isError={Boolean(reviewsError)}
              hasData={recentReviews.length > 0}
              staleWhileRevalidate
              errorMessage={reviewsError ?? undefined}
              isEmpty={!reviewsLoading && !reviewsError && recentReviews.length === 0}
              loadingTitle="Loading review context"
              loadingDescription="Requesting recent trade reviews for the portfolio workspace."
              errorTitle="Could not load review context"
              emptyTitle="No reviews linked yet"
              emptyDescription="Generate trade reviews after a few paper trades so this page can point directly into the post-mortem loop."
              action={
                <button className="secondary-button" type="button" onClick={() => navigate('/postmortem')}>
                  Open post-mortem
                </button>
              }
            >
              <div className="table-link-stack">
                {recentReviews.map((review) => (
                  <a key={review.id} href={`/postmortem/${review.id}`} className="market-link" onClick={(event) => {
                    event.preventDefault();
                    navigate(`/postmortem/${review.id}`);
                  }}>
                    <strong>{review.market_title}</strong>
                    <span>Trade #{review.trade_id} · {review.recommendation || review.summary}</span>
                  </a>
                ))}
              </div>
            </DataStateWrapper>
          </SectionCard>
        </section>
      </details>
    </div>
  );
}
