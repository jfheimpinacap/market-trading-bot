import { useCallback, useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { navigate } from '../lib/router';
import { SectionCard } from '../components/SectionCard';
import { ContextLinksPanel } from '../components/flow/ContextLinksPanel';
import { WorkflowStatusPanel } from '../components/flow/WorkflowStatusPanel';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { SignalsFilters } from '../components/signals/SignalsFilters';
import { SignalsSummaryCards } from '../components/signals/SignalsSummaryCards';
import { SignalsTable } from '../components/signals/SignalsTable';
import { useDemoFlowRefresh } from '../hooks/useDemoFlowRefresh';
import { buildReviewLookupByTradeId, getLatestReviewForMarket, getLatestTradeForMarket, getOpenPositionsForMarket } from '../lib/demoFlow';
import {
  getPaperPositions,
  getPaperTrades,
} from '../services/paperTrading';
import { getTradeReviews } from '../services/reviews';
import { getSignalAgents, getSignals, getSignalsSummary } from '../services/signals';
import type { ContextLinkItem, WorkflowStatusItem } from '../types/demoFlow';
import type { PaperPosition, PaperTrade } from '../types/paperTrading';
import type { TradeReview } from '../types/reviews';
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
  const [positions, setPositions] = useState<PaperPosition[]>([]);
  const [trades, setTrades] = useState<PaperTrade[]>([]);
  const [reviews, setReviews] = useState<TradeReview[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [signalsLoading, setSignalsLoading] = useState(true);
  const [signalsError, setSignalsError] = useState<string | null>(null);
  const [contextWarning, setContextWarning] = useState<string | null>(null);

  const loadCatalog = useCallback(async () => {
    setCatalogLoading(true);
    setCatalogError(null);
    setContextWarning(null);

    const [summaryResult, agentsResult, positionsResult, tradesResult, reviewsResult] = await Promise.allSettled([
      getSignalsSummary(),
      getSignalAgents(),
      getPaperPositions(),
      getPaperTrades(),
      getTradeReviews({ ordering: '-reviewed_at' }),
    ]);

    if (summaryResult.status === 'fulfilled') {
      setSummary(summaryResult.value);
    } else {
      setSummary(null);
      setCatalogError(getErrorMessage(summaryResult.reason, 'Could not load the signals summary.'));
    }

    if (agentsResult.status === 'fulfilled') {
      setAgents(agentsResult.value);
    } else {
      setAgents([]);
      setCatalogError((current) => current ?? getErrorMessage(agentsResult.reason, 'Could not load the agent registry.'));
    }

    const warnings: string[] = [];

    if (positionsResult.status === 'fulfilled') {
      setPositions(positionsResult.value);
    } else {
      setPositions([]);
      warnings.push(getErrorMessage(positionsResult.reason, 'Paper positions unavailable.'));
    }

    if (tradesResult.status === 'fulfilled') {
      setTrades(tradesResult.value);
    } else {
      setTrades([]);
      warnings.push(getErrorMessage(tradesResult.reason, 'Paper trades unavailable.'));
    }

    if (reviewsResult.status === 'fulfilled') {
      setReviews(reviewsResult.value);
    } else {
      setReviews([]);
      warnings.push(getErrorMessage(reviewsResult.reason, 'Trade reviews unavailable.'));
    }

    setContextWarning(warnings.length > 0 ? warnings.join(' ') : null);
    setCatalogLoading(false);
  }, []);

  const loadSignalsList = useCallback(async () => {
    setSignalsLoading(true);
    setSignalsError(null);

    try {
      const response = await getSignals(filters);
      setSignals(response);
    } catch (error) {
      setSignalsError(getErrorMessage(error, 'Could not load demo signals for the selected filters.'));
    } finally {
      setSignalsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog]);

  useEffect(() => {
    void loadSignalsList();
  }, [loadSignalsList]);

  useDemoFlowRefresh(async () => {
    await Promise.all([loadCatalog(), loadSignalsList()]);
  });

  const activeFilterCount = useMemo(
    () => Object.entries(filters).filter(([key, value]) => key !== 'ordering' && value.trim().length > 0).length,
    [filters],
  );

  const workflowItems = useMemo<WorkflowStatusItem[]>(() => {
    const actionableSignals = summary?.actionable_signals ?? 0;
    const openPositions = positions.filter((position) => position.status === 'OPEN' && Number(position.quantity) > 0).length;

    return [
      {
        label: 'Signals ready',
        value: `${summary?.total_signals ?? 0} total`,
        helperText: 'Use the signal queue to identify which markets deserve a closer look before trading.',
        tone: (summary?.total_signals ?? 0) > 0 ? 'ready' : 'warning',
      },
      {
        label: 'Actionable now',
        value: `${actionableSignals} actionable`,
        helperText: 'These are the best candidates to open in market detail and evaluate with the risk panel.',
        tone: actionableSignals > 0 ? 'ready' : 'neutral',
        href: '/markets',
        linkLabel: 'Browse markets',
      },
      {
        label: 'Portfolio context',
        value: `${openPositions} open positions`,
        helperText: 'Signals now surface whether a market already has live paper exposure in the portfolio.',
        tone: openPositions > 0 ? 'ready' : 'neutral',
        href: '/portfolio',
        linkLabel: 'Open portfolio',
      },
      {
        label: 'Review coverage',
        value: `${reviews.length} reviews linked`,
        helperText: 'If a signal already led to a trade and review, you can jump directly into the learning loop.',
        tone: reviews.length > 0 ? 'ready' : 'neutral',
        href: '/postmortem',
        linkLabel: 'Open post-mortem',
      },
    ];
  }, [positions, reviews.length, summary?.actionable_signals, summary?.total_signals]);

  const contextLinks = useMemo<ContextLinkItem[]>(() => [
    {
      title: 'Open the live catalog',
      description: 'Move from the signal board into Markets when you want wider market context before focusing on one contract.',
      href: '/markets',
      actionLabel: 'Explore markets',
      tone: 'neutral',
    },
    {
      title: 'Evaluate a trade in market detail',
      description: 'Use the risk demo and paper trade panel directly inside /markets/:marketId when a signal looks actionable.',
      href: '/markets',
      actionLabel: 'Go to market detail',
      tone: 'primary',
    },
    {
      title: 'Check existing exposure',
      description: 'Open the portfolio to verify if this market already has a position or a recent execution worth reviewing.',
      href: '/portfolio',
      actionLabel: 'View portfolio',
      tone: 'secondary',
    },
  ], []);

  const workflowContextByMarket = useMemo(() => {
    return Object.fromEntries(
      signals.map((signal) => {
        const openPositions = getOpenPositionsForMarket(positions, signal.market);
        const latestTrade = getLatestTradeForMarket(trades, signal.market);
        const latestReview = getLatestReviewForMarket(reviews, signal.market)
          ?? (latestTrade ? buildReviewLookupByTradeId(reviews)[latestTrade.id] : null)
          ?? null;

        return [
          signal.market,
          {
            hasOpenPosition: openPositions.length > 0,
            latestTradeId: latestTrade?.id,
            latestReviewId: latestReview?.id,
            latestReviewOutcome: latestReview?.outcome,
            latestReviewStatus: latestReview?.review_status,
          },
        ];
      }),
    );
  }, [positions, reviews, signals, trades]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Decision support"
        title="Signals"
        description="Demo-only opportunity board powered by local heuristics, mock agents, and the existing market catalog. The page now acts as a stronger bridge into market detail, portfolio context, and post-mortem."
      />

      <WorkflowStatusPanel
        title="How to use this board"
        description="Review the queue, open a market when the thesis looks actionable, evaluate risk in market detail, then come back through portfolio and post-mortem to understand what happened."
        items={workflowItems}
      />

      <ContextLinksPanel
        title="Where to go next"
        description="The signals page is intentionally lightweight, so the main UX improvement here is better navigation into the rest of the workflow."
        links={contextLinks}
      />

      <DataStateWrapper
        isLoading={catalogLoading}
        isError={Boolean(catalogError)}
        errorMessage={catalogError ?? undefined}
        loadingTitle="Loading signals workspace"
        loadingDescription="Requesting the summary, agent registry, and cross-module workflow context from the local backend."
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
            {contextWarning ? <p className="paper-inline-notice">Cross-module context warning: {contextWarning}</p> : null}
          </SectionCard>
        ) : null}

        <SignalsFilters filters={filters} agents={agents} onChange={setFilters} onReset={() => setFilters(defaultFilters)} />

        <SectionCard
          eyebrow="Ideas queue"
          title="Signal list"
          description="Desktop-first table for scanning demo signals, their thesis, related market, context-aware workflow links, and actionability state."
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
            emptyDescription="Generate demo signals locally with `cd apps/backend && python manage.py generate_demo_signals`, go to Markets to inspect the seeded catalog, or clear some filters to broaden the current view."
            action={
              activeFilterCount > 0 ? (
                <button className="secondary-button" type="button" onClick={() => setFilters(defaultFilters)}>
                  Clear filters
                </button>
              ) : (
                <button className="secondary-button" type="button" onClick={() => navigate('/markets')}>
                  Go to markets
                </button>
              )
            }
          >
            <SignalsTable signals={signals} workflowContextByMarket={workflowContextByMarket} />
          </DataStateWrapper>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
