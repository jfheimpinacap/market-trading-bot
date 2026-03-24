import { useCallback, useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { ProposalsTable } from '../components/proposals/ProposalsTable';
import { getTradeProposals } from '../services/proposals';
import { navigate } from '../lib/router';
import type { TradeProposal } from '../types/proposals';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function ProposalsPage() {
  const [proposals, setProposals] = useState<TradeProposal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProposals = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await getTradeProposals();
      setProposals(response);
    } catch (loadError) {
      setProposals([]);
      setError(getErrorMessage(loadError, 'Could not load trade proposals.'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProposals();
  }, [loadProposals]);

  const actionableCount = useMemo(
    () => proposals.filter((proposal) => proposal.is_actionable).length,
    [proposals],
  );

  const latestProposal = proposals[0] ?? null;

  function handleOpenLatestMarket() {
    if (!latestProposal) {
      return;
    }

    navigate(`/markets/${latestProposal.market}`);
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Proposal engine demo"
        title="Trade proposals"
        description="Review generated demo proposals, verify direction and sizing suggestions, inspect risk and policy outcomes, and continue naturally into market detail and paper trading."
      />

      <section className="content-grid content-grid--three-columns">
        <SectionCard eyebrow="Summary" title="Total proposals" description="Stored proposal records from the local backend.">
          <p><strong>{proposals.length}</strong></p>
        </SectionCard>
        <SectionCard eyebrow="Summary" title="Actionable proposals" description="Proposals that currently pass risk and policy gates.">
          <p><strong>{actionableCount}</strong></p>
        </SectionCard>
        <SectionCard
          eyebrow="Summary"
          title="Latest proposal"
          description={latestProposal ? latestProposal.headline : 'No generated proposals yet.'}
          aside={latestProposal ? <button className="secondary-button" type="button" onClick={() => void handleOpenLatestMarket()}>Open market</button> : null}
        >
          <p className="muted-text">{latestProposal ? `${latestProposal.market_title} · ${latestProposal.direction}` : 'Generate a trade proposal for any market from market detail.'}</p>
        </SectionCard>
      </section>

      <SectionCard
        eyebrow="Inbox"
        title="Proposals list"
        description="Desktop-first queue showing proposal thesis, direction, suggested quantity, risk and policy decisions, and actionable state."
      >
        <DataStateWrapper
          isLoading={isLoading}
          isError={Boolean(error)}
          errorMessage={error ?? undefined}
          isEmpty={!isLoading && !error && proposals.length === 0}
          loadingTitle="Loading trade proposals"
          loadingDescription="Requesting the latest local proposal records from the proposal engine demo endpoint."
          errorTitle="Could not load proposals"
          emptyTitle="No proposals generated yet"
          emptyDescription="Generate a trade proposal for this market from /markets/:marketId to populate this inbox. Signals are not strong enough for a demo proposal can also produce non-actionable entries."
          action={<button className="secondary-button" type="button" onClick={() => navigate('/markets')}>Open markets</button>}
        >
          <ProposalsTable proposals={proposals} />
        </DataStateWrapper>
      </SectionCard>
    </div>
  );
}
