import { useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { PostMortemSummaryCards } from '../components/postmortem/PostMortemSummaryCards';
import { ReviewDetailPanel } from '../components/postmortem/ReviewDetailPanel';
import { TradeReviewsTable } from '../components/postmortem/TradeReviewsTable';
import { usePathname } from '../lib/router';
import { getTradeReview, getTradeReviews, getReviewsSummary } from '../services/reviews';
import type { ReviewFilters, TradeReview, TradeReviewDetail, TradeReviewSummary } from '../types/reviews';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function getReviewIdFromPath(pathname: string) {
  const match = pathname.match(/^\/postmortem\/(\d+)\/?$/);
  return match ? Number(match[1]) : null;
}

export function PostMortemPage() {
  const pathname = usePathname();
  const selectedReviewId = useMemo(() => getReviewIdFromPath(pathname), [pathname]);
  const [outcomeFilter, setOutcomeFilter] = useState<'ALL' | 'FAVORABLE' | 'NEUTRAL' | 'UNFAVORABLE'>('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'REVIEWED' | 'STALE'>('ALL');
  const [reviews, setReviews] = useState<TradeReview[]>([]);
  const [summary, setSummary] = useState<TradeReviewSummary | null>(null);
  const [selectedReview, setSelectedReview] = useState<TradeReviewDetail | null>(null);
  const [reviewsLoading, setReviewsLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [reviewsError, setReviewsError] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  const reviewFilters = useMemo<ReviewFilters>(() => ({
    ordering: '-reviewed_at',
    outcome: outcomeFilter === 'ALL' ? undefined : outcomeFilter,
    review_status: statusFilter === 'ALL' ? undefined : statusFilter,
  }), [outcomeFilter, statusFilter]);

  useEffect(() => {
    let isMounted = true;

    async function loadReviewsContext() {
      setReviewsLoading(true);
      setSummaryLoading(true);
      setReviewsError(null);
      setSummaryError(null);

      const [reviewsResult, summaryResult] = await Promise.allSettled([
        getTradeReviews(reviewFilters),
        getReviewsSummary(),
      ]);

      if (!isMounted) {
        return;
      }

      if (reviewsResult.status === 'fulfilled') {
        setReviews(reviewsResult.value);
      } else {
        setReviews([]);
        setReviewsError(getErrorMessage(reviewsResult.reason, 'Could not load trade reviews from the backend.'));
      }

      if (summaryResult.status === 'fulfilled') {
        setSummary(summaryResult.value);
      } else {
        setSummary(null);
        setSummaryError(getErrorMessage(summaryResult.reason, 'Could not load the reviews summary.'));
      }

      setReviewsLoading(false);
      setSummaryLoading(false);
    }

    void loadReviewsContext();

    return () => {
      isMounted = false;
    };
  }, [reviewFilters]);

  useEffect(() => {
    let isMounted = true;

    async function loadReviewDetail(reviewId: number) {
      setDetailLoading(true);
      setDetailError(null);

      try {
        const response = await getTradeReview(reviewId);
        if (!isMounted) {
          return;
        }
        setSelectedReview(response);
      } catch (error) {
        if (!isMounted) {
          return;
        }
        setSelectedReview(null);
        setDetailError(getErrorMessage(error, 'Could not load the selected review detail.'));
      } finally {
        if (isMounted) {
          setDetailLoading(false);
        }
      }
    }

    if (selectedReviewId) {
      void loadReviewDetail(selectedReviewId);
      return () => {
        isMounted = false;
      };
    }

    setSelectedReview(null);
    setDetailError(null);
    setDetailLoading(false);

    return () => {
      isMounted = false;
    };
  }, [selectedReviewId]);

  const emptyDescription = outcomeFilter === 'ALL' && statusFilter === 'ALL'
    ? 'There are no trade reviews yet. Generate them locally with `cd apps/backend && python manage.py generate_trade_reviews`, then refresh this page.'
    : 'No reviews match the current filters. Clear the filters or generate more demo reviews from the backend.';

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Learning loop"
        title="Post-Mortem"
        description="Review executed paper trades with simple demo heuristics so the workflow closes the loop from market discovery to trade review. Everything here is local-first, deterministic, and explicitly mock."
        actions={<StatusBadge tone={reviewsError ? 'offline' : reviewsLoading ? 'loading' : 'ready'}>{reviewsError ? 'Reviews unavailable' : reviewsLoading ? 'Loading reviews' : `${reviews.length} reviews loaded`}</StatusBadge>}
      />

      {summaryError && !summaryLoading ? (
        <EmptyState
          eyebrow="Partial warning"
          title="Summary unavailable"
          description={`${summaryError} The reviews list can still render if the list endpoint responded correctly.`}
        />
      ) : null}

      <SectionCard
        eyebrow="Outcome overview"
        title="Trade review summary"
        description="Summary cards from GET /api/reviews/summary/ to show how many demo trades currently look favorable, neutral, unfavorable, or stale."
      >
        <DataStateWrapper
          isLoading={summaryLoading}
          isError={Boolean(summaryError) && !summary}
          errorMessage={summaryError ?? undefined}
          isEmpty={!summaryLoading && !summaryError && !summary}
          loadingTitle="Loading review summary"
          loadingDescription="Requesting aggregate post-mortem counts from the backend."
          errorTitle="Could not load review summary"
          emptyTitle="No review summary available"
          emptyDescription="Generate trade reviews from the backend to populate the retrospective overview."
        >
          {summary ? <PostMortemSummaryCards summary={summary} /> : null}
        </DataStateWrapper>
      </SectionCard>

      <SectionCard
        eyebrow="Review queue"
        title="Trade reviews"
        description="Desktop-first review tray from GET /api/reviews/ with quick filters, linked markets, linked trade review detail, and short recommendations for the next demo iteration."
        aside={(
          <div className="postmortem-filters">
            <label>
              Outcome
              <select value={outcomeFilter} onChange={(event) => setOutcomeFilter(event.target.value as typeof outcomeFilter)}>
                <option value="ALL">All</option>
                <option value="FAVORABLE">Favorable</option>
                <option value="NEUTRAL">Neutral</option>
                <option value="UNFAVORABLE">Unfavorable</option>
              </select>
            </label>
            <label>
              Status
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}>
                <option value="ALL">All</option>
                <option value="REVIEWED">Reviewed</option>
                <option value="STALE">Stale</option>
              </select>
            </label>
          </div>
        )}
      >
        <DataStateWrapper
          isLoading={reviewsLoading}
          isError={Boolean(reviewsError)}
          errorMessage={reviewsError ?? undefined}
          isEmpty={!reviewsLoading && !reviewsError && reviews.length === 0}
          loadingTitle="Loading trade reviews"
          loadingDescription="Requesting the demo post-mortem queue from the backend."
          errorTitle="Could not load trade reviews"
          emptyTitle="No trade reviews yet"
          emptyDescription={emptyDescription}
        >
          {summaryError && !summaryLoading ? <p className="paper-inline-notice">Summary endpoint unavailable: {summaryError}</p> : null}
          <TradeReviewsTable reviews={reviews} />
        </DataStateWrapper>
      </SectionCard>

      {selectedReviewId ? (
        <SectionCard
          eyebrow="Selected review"
          title={`Review #${selectedReviewId}`}
          description="Detailed explanation for one paper trade review, including rationale, lesson, recommendation, and linked navigation back to Markets or Portfolio."
        >
          <DataStateWrapper
            isLoading={detailLoading}
            isError={Boolean(detailError)}
            errorMessage={detailError ?? undefined}
            isEmpty={!detailLoading && !detailError && !selectedReview}
            loadingTitle="Loading review detail"
            loadingDescription="Fetching the selected post-mortem detail from the backend."
            errorTitle="Could not load review detail"
            emptyTitle="Review detail not found"
            emptyDescription="The requested review does not exist or is no longer available."
          >
            {selectedReview ? <ReviewDetailPanel review={selectedReview} /> : null}
          </DataStateWrapper>
        </SectionCard>
      ) : null}
    </div>
  );
}
