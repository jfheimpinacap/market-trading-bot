import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../../components/EmptyState';
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
import { API_BASE_URL } from '../../lib/config';
import { getTradeReviews } from '../../services/reviews';
import {
  getPaperAccount,
  getPaperPositions,
  getPaperSnapshots,
  getPaperSummary,
  getPaperTrades,
  revaluePaperPortfolio,
} from '../../services/paperTrading';
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
      setAccount(null);
      setAccountError(getErrorMessage(accountResult.reason, 'Could not load the active paper account.'));
    }

    if (summaryResult.status === 'fulfilled') {
      setSummary(summaryResult.value);
    } else {
      setSummary(null);
      setSummaryError(getErrorMessage(summaryResult.reason, 'Could not load the portfolio summary.'));
    }

    if (positionsResult.status === 'fulfilled') {
      setPositions(positionsResult.value);
    } else {
      setPositions([]);
      setPositionsError(getErrorMessage(positionsResult.reason, 'Could not load paper positions.'));
    }

    if (tradesResult.status === 'fulfilled') {
      setTrades(tradesResult.value);
    } else {
      setTrades([]);
      setTradesError(getErrorMessage(tradesResult.reason, 'Could not load paper trades.'));
    }

    if (snapshotsResult.status === 'fulfilled') {
      setSnapshots(snapshotsResult.value);
    } else {
      setSnapshots([]);
      setSnapshotsError(getErrorMessage(snapshotsResult.reason, 'Could not load portfolio snapshots.'));
    }

    if (reviewsResult.status === 'fulfilled') {
      setReviews(reviewsResult.value);
    } else {
      setReviews([]);
      setReviewsError(getErrorMessage(reviewsResult.reason, 'Could not load trade reviews for the portfolio links.'));
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

  const handleRevalue = useCallback(async () => {
    setIsRevaluing(true);
    setRevalueMessage(null);
    setRevalueError(null);

    try {
      const updatedAccount = await revaluePaperPortfolio();
      setAccount(updatedAccount);
      await loadPortfolio();
      setRevalueMessage(`Portfolio revalued successfully. Last backend update: ${formatTechnicalTimestamp(updatedAccount.updated_at)}.`);
    } catch (error) {
      setRevalueError(getErrorMessage(error, 'Could not revalue the demo portfolio.'));
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
      return 'Waiting for the first successful account response.';
    }

    return `Last account refresh: ${formatTechnicalTimestamp(account.updated_at)}.`;
  }, [account?.updated_at]);

  const currency = account?.currency ?? summary?.account.currency ?? 'USD';
  const openPositions = useMemo(
    () => positions.filter((position) => position.status === 'OPEN' && Number(position.quantity) > 0),
    [positions],
  );
  const reviewLookup = useMemo(() => Object.fromEntries(reviews.map((review) => [review.trade_id, review])), [reviews]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Paper trading"
        title="Portfolio"
        description="Live local demo portfolio view for paper account balances, open positions, execution history, and backend-triggered manual revaluation."
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

      {totalFailure ? (
        <EmptyState
          eyebrow="Backend unavailable"
          title="Could not load the paper trading workspace"
          description={`The frontend could not load any of the paper trading endpoints from ${API_BASE_URL}. Verify the backend is running and seed the demo account with \`cd apps/backend && python manage.py seed_paper_account\`.`}
          action={
            <button className="secondary-button" type="button" onClick={() => void loadPortfolio()}>
              Retry portfolio requests
            </button>
          }
        />
      ) : null}

      <SectionCard
        eyebrow="Demo account summary"
        title="Account metrics"
        description="These cards combine GET /api/paper/account/, GET /api/paper/summary/, and GET /api/paper/trades/ so the demo portfolio reads like a usable operator view instead of a placeholder."
        aside={<StatusBadge tone={accountError ? 'offline' : accountLoading ? 'loading' : 'ready'}>{accountError ? 'Account unavailable' : accountLoading ? 'Loading account' : 'Account synced'}</StatusBadge>}
      >
        <DataStateWrapper
          isLoading={accountLoading || summaryLoading || tradesLoading}
          isError={Boolean(accountError)}
          errorMessage={accountError ?? undefined}
          isEmpty={!accountLoading && !accountError && !account}
          loadingTitle="Loading paper account"
          loadingDescription="Requesting paper account, summary, and trade counters from the backend."
          errorTitle="Could not load paper account"
          emptyTitle="No paper account available"
          emptyDescription="Run `cd apps/backend && python manage.py seed_paper_account` and refresh this page to populate the demo portfolio."
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
        eyebrow="Account overview"
        title="Paper account details"
        description="Technical account metadata and summary diagnostics for the active demo portfolio."
      >
        <DataStateWrapper
          isLoading={accountLoading || summaryLoading}
          isError={Boolean(accountError)}
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
        eyebrow="Portfolio history"
        title="Equity and balance history"
        description="Snapshot-based chart from GET /api/paper/snapshots/ to visualize how equity, cash balance, and total PnL evolve after paper trades and manual revaluation."
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
        eyebrow="Open and closed positions"
        title="Positions"
        description="Desktop-first table of positions returned by GET /api/paper/positions/, including current marks, realized/unrealized PnL, and direct links back to Markets."
        aside={<StatusBadge tone={positionsError ? 'offline' : positionsLoading ? 'loading' : 'ready'}>{positionsError ? 'Positions unavailable' : `${openPositions.length} open positions`}</StatusBadge>}
      >
        <DataStateWrapper
          isLoading={positionsLoading}
          isError={Boolean(positionsError)}
          errorMessage={positionsError ?? undefined}
          isEmpty={!positionsLoading && !positionsError && positions.length === 0}
          loadingTitle="Loading paper positions"
          loadingDescription="Requesting position rows from the backend demo account."
          errorTitle="Could not load paper positions"
          emptyTitle="No positions yet"
          emptyDescription="The demo account exists, but there are no paper positions yet. Execute a few backend paper trades and revalue the portfolio to populate this table."
        >
          <PaperPositionsTable positions={positions} currency={currency} />
        </DataStateWrapper>
      </SectionCard>

      <SectionCard
        eyebrow="Execution history"
        title="Trades"
        description="Recent paper trade history from GET /api/paper/trades/, ordered by most recent execution so the demo account activity can be audited quickly. When reviews exist, the table also links each trade to /postmortem."
        aside={<StatusBadge tone={tradesError ? 'offline' : tradesLoading ? 'loading' : 'ready'}>{tradesError ? 'Trades unavailable' : `${trades.length} trades loaded`}</StatusBadge>}
      >
        <DataStateWrapper
          isLoading={tradesLoading}
          isError={Boolean(tradesError)}
          errorMessage={tradesError ?? undefined}
          isEmpty={!tradesLoading && !tradesError && trades.length === 0}
          loadingTitle="Loading trade history"
          loadingDescription="Requesting recent demo trades from the backend."
          errorTitle="Could not load trade history"
          emptyTitle="No trades recorded yet"
          emptyDescription="The paper account has not executed demo trades yet. Use the backend paper trading flows first, then return here to inspect the history."
        >
          {reviewsError ? <p className="paper-inline-notice">Review links unavailable: {reviewsError}</p> : null}
          <PaperTradesTable trades={trades} currency={currency} reviewLookup={reviewLookup} />
        </DataStateWrapper>
      </SectionCard>

      <SectionCard
        eyebrow="Portfolio history"
        title="Snapshots"
        description="Compact portfolio history from GET /api/paper/snapshots/, useful for checking how cash, equity, and PnL changed after manual revaluations or trade execution."
        aside={<StatusBadge tone={snapshotsError ? 'offline' : snapshotsLoading ? 'loading' : 'ready'}>{snapshotsError ? 'Snapshots unavailable' : `${snapshots.length} snapshots loaded`}</StatusBadge>}
      >
        <DataStateWrapper
          isLoading={snapshotsLoading}
          isError={Boolean(snapshotsError)}
          errorMessage={snapshotsError ?? undefined}
          isEmpty={!snapshotsLoading && !snapshotsError && snapshots.length === 0}
          loadingTitle="Loading portfolio snapshots"
          loadingDescription="Requesting portfolio snapshots captured by the paper trading backend."
          errorTitle="Could not load portfolio snapshots"
          emptyTitle="No snapshots captured yet"
          emptyDescription="Snapshots are created when the portfolio is revalued with snapshot creation enabled. Use the Revalue portfolio action to generate the first snapshot from the UI."
        >
          <PaperSnapshotsPanel snapshots={snapshots} currency={currency} />
        </DataStateWrapper>
      </SectionCard>
    </div>
  );
}
