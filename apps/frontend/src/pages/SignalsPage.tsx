import { useCallback, useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { formatDateTime, formatPercent, titleize } from '../components/markets/utils';
import { navigate } from '../lib/router';
import {
  getOpportunitySignals,
  getSignalBoardSummary,
  getSignalRuns,
  runFusionToProposal,
  runSignalFusion,
} from '../services/signals';
import type { OpportunitySignal, SignalBoardSummary, SignalFusionRun, SignalProfileSlug } from '../types/signals';

const profileOptions: Array<{ value: SignalProfileSlug; label: string }> = [
  { value: 'conservative_signal', label: 'Conservative' },
  { value: 'balanced_signal', label: 'Balanced' },
  { value: 'aggressive_light_signal', label: 'Aggressive light' },
];

function getStatusClass(status: string) {
  const normalized = status.toLowerCase();
  if (normalized === 'proposal_ready') {
    return 'signal-badge signal-badge--actionable';
  }
  if (normalized === 'candidate') {
    return 'signal-badge signal-badge--monitor';
  }
  if (normalized === 'blocked') {
    return 'signal-badge signal-badge--bearish';
  }
  return 'signal-badge signal-badge--muted';
}

function getLevelBadge(value: number) {
  if (value >= 70) {
    return <span className="signal-badge signal-badge--actionable">HIGH</span>;
  }
  if (value >= 45) {
    return <span className="signal-badge signal-badge--monitor">MEDIUM</span>;
  }
  return <span className="signal-badge signal-badge--muted">LOW</span>;
}

export function SignalsPage() {
  const [profile, setProfile] = useState<SignalProfileSlug>('balanced_signal');
  const [summary, setSummary] = useState<SignalBoardSummary | null>(null);
  const [runs, setRuns] = useState<SignalFusionRun[]>([]);
  const [opportunities, setOpportunities] = useState<OpportunitySignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryResponse, runsResponse, opportunitiesResponse] = await Promise.all([
        getSignalBoardSummary(),
        getSignalRuns(),
        getOpportunitySignals(),
      ]);
      setSummary(summaryResponse);
      setRuns(runsResponse);
      setOpportunities(opportunitiesResponse);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load the opportunity board.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleRunFusion = useCallback(async () => {
    setActionBusy(true);
    setActionMessage(null);
    try {
      const run = await runSignalFusion({ profile_slug: profile });
      setActionMessage(`Signal fusion run #${run.id} completed.`);
      await loadData();
    } catch (runError) {
      setActionMessage(runError instanceof Error ? runError.message : 'Signal fusion failed.');
    } finally {
      setActionBusy(false);
    }
  }, [loadData, profile]);

  const handleRunToProposal = useCallback(async (runId: number) => {
    setActionBusy(true);
    setActionMessage(null);
    try {
      const result = await runFusionToProposal({ run_id: runId });
      setActionMessage(`Generated ${result.proposals_created} proposal drafts from run #${runId}.`);
    } catch (runError) {
      setActionMessage(runError instanceof Error ? runError.message : 'Could not generate proposals from signal run.');
    } finally {
      setActionBusy(false);
    }
  }, []);

  const hasOpportunities = opportunities.length > 0;
  const latestRun = runs[0] ?? summary?.latest_run ?? null;

  const quickCards = useMemo(() => [
    { label: 'Watch', value: String(summary?.watch_count ?? 0) },
    { label: 'Candidate', value: String(summary?.candidate_count ?? 0) },
    { label: 'Proposal ready', value: String(summary?.proposal_ready_count ?? 0) },
    { label: 'Blocked', value: String(summary?.blocked_count ?? 0) },
  ], [summary]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Signal fusion"
        title="Opportunity board"
        description="Paper/demo-only signal fusion board. Consolidates research + prediction + risk into ranked opportunities and explicit proposal gating."
      />

      <SectionCard
        eyebrow="Fusion controls"
        title="Run a new signal fusion cycle"
        description="Choose a profile and generate a transparent composite signal run. No real-money execution is performed."
      >
        <div className="markets-filters__grid">
          <label className="field-group">
            <span>Signal profile</span>
            <select className="select-input" value={profile} onChange={(event) => setProfile(event.target.value as SignalProfileSlug)}>
              {profileOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="markets-filters__actions" style={{ marginTop: 12 }}>
          <button className="primary-button" type="button" onClick={() => void handleRunFusion()} disabled={actionBusy}>
            {actionBusy ? 'Running fusion...' : 'Run signal fusion'}
          </button>
          {latestRun ? (
            <button className="secondary-button" type="button" onClick={() => void handleRunToProposal(latestRun.id)} disabled={actionBusy}>
              Run to proposal
            </button>
          ) : null}
          <button className="secondary-button" type="button" onClick={() => navigate('/opportunities')}>
            Open opportunities supervisor
          </button>
          {actionMessage ? <span className="muted-text">{actionMessage}</span> : null}
        </div>
      </SectionCard>

      <DataStateWrapper
        isLoading={loading}
        isError={Boolean(error)}
        errorMessage={error ?? undefined}
        loadingTitle="Loading opportunity board"
        loadingDescription="Collecting signal runs, opportunities, and summary counters from the backend."
        errorTitle="Could not load opportunity board"
      >
        <SectionCard
          eyebrow="Summary"
          title="Board status"
          description="Counts by opportunity state for quick triage and proposal readiness tracking."
        >
          <div className="dashboard-stat-grid">
            {quickCards.map((item) => (
              <article key={item.label} className="dashboard-stat-card">
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Opportunity board"
          title="Ranked opportunities"
          description="WATCH / CANDIDATE / PROPOSAL_READY / BLOCKED status with rationale and next actions."
        >
          {!hasOpportunities ? (
            <p className="muted-text">Run signal fusion to build the opportunity board.</p>
          ) : (
            <div className="markets-table-wrapper">
              <table className="markets-table signals-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Market</th>
                    <th>Provider</th>
                    <th>Narrative</th>
                    <th>Edge</th>
                    <th>Confidence</th>
                    <th>Risk</th>
                    <th>Score</th>
                    <th>Status</th>
                    <th>Rationale</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {opportunities.map((opportunity) => {
                    const edgePct = Number(opportunity.edge) * 100;
                    const confidencePct = Number(opportunity.prediction_confidence) * 100;
                    return (
                      <tr key={opportunity.id}>
                        <td>{opportunity.rank}</td>
                        <td>
                          <strong>{opportunity.market_title}</strong>
                        </td>
                        <td>{opportunity.market_provider_slug || opportunity.provider_slug}</td>
                        <td>{titleize(opportunity.narrative_direction || 'uncertain')}</td>
                        <td>
                          <div className="table-inline-stack">
                            <span>{formatPercent(opportunity.edge)}</span>
                            {getLevelBadge(Math.abs(edgePct) * 10)}
                          </div>
                        </td>
                        <td>
                          <div className="table-inline-stack">
                            <span>{Math.round(confidencePct)}%</span>
                            {getLevelBadge(confidencePct)}
                          </div>
                        </td>
                        <td><span className="signal-badge signal-badge--muted">{opportunity.risk_level}</span></td>
                        <td>{opportunity.opportunity_score}</td>
                        <td><span className={getStatusClass(opportunity.opportunity_status)}>{opportunity.opportunity_status}</span></td>
                        <td>{opportunity.rationale}</td>
                        <td>
                          <div className="table-link-stack">
                            <a href={`/prediction?market_id=${opportunity.market}`} onClick={(event) => { event.preventDefault(); navigate(`/prediction`); }} className="market-link">Open prediction</a>
                            <a href={`/markets/${opportunity.market}`} onClick={(event) => { event.preventDefault(); navigate(`/markets/${opportunity.market}`); }} className="market-link">Open market</a>
                            {opportunity.proposal_gate?.should_generate_proposal ? (
                              <a href="/proposals" onClick={(event) => { event.preventDefault(); navigate('/proposals'); }} className="market-link">Generate proposal</a>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard
          eyebrow="Recent runs"
          title="Signal fusion history"
          description="Last fusion cycles with evaluated markets and proposal-ready counts."
        >
          {runs.length === 0 ? (
            <p className="muted-text">No fusion runs yet.</p>
          ) : (
            <div className="markets-table-wrapper">
              <table className="markets-table">
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Status</th>
                    <th>Profile</th>
                    <th>Markets evaluated</th>
                    <th>Proposal ready</th>
                    <th>Created at</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id}>
                      <td>#{run.id}</td>
                      <td>{run.status}</td>
                      <td>{run.profile_slug}</td>
                      <td>{run.markets_evaluated}</td>
                      <td>{run.proposal_ready_count}</td>
                      <td>{formatDateTime(run.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
