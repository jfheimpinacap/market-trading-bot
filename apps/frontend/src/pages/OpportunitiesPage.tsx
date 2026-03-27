import { useCallback, useEffect, useMemo, useState } from 'react';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { navigate } from '../lib/router';
import { getOpportunityCycles, getOpportunityItems, getOpportunitySummary, runOpportunityCycle } from '../services/opportunities';
import type { OpportunityCycleItem, OpportunityCycleRun, OpportunityExecutionPath, OpportunitySummary } from '../types/opportunities';

function badgeClass(path: OpportunityExecutionPath) {
  if (path === 'AUTO_EXECUTE_PAPER') return 'signal-badge signal-badge--actionable';
  if (path === 'QUEUE') return 'signal-badge signal-badge--monitor';
  if (path === 'BLOCKED') return 'signal-badge signal-badge--bearish';
  return 'signal-badge signal-badge--muted';
}

export function OpportunitiesPage() {
  const [summary, setSummary] = useState<OpportunitySummary | null>(null);
  const [cycles, setCycles] = useState<OpportunityCycleRun[]>([]);
  const [items, setItems] = useState<OpportunityCycleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [profile, setProfile] = useState('balanced_supervisor');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, cyclesRes] = await Promise.all([getOpportunitySummary(), getOpportunityCycles()]);
      setSummary(summaryRes);
      setCycles(cyclesRes);
      if (cyclesRes[0]) {
        const latestItems = await getOpportunityItems(cyclesRes[0].id);
        setItems(latestItems);
      } else {
        setItems([]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load opportunities.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const runCycle = useCallback(async () => {
    setRunning(true);
    setActionMessage(null);
    try {
      const run = await runOpportunityCycle({ profile_slug: profile });
      setActionMessage(`Opportunity cycle #${run.id} completed.`);
      await load();
    } catch (e) {
      setActionMessage(e instanceof Error ? e.message : 'Cycle failed.');
    } finally {
      setRunning(false);
    }
  }, [load, profile]);

  const cards = useMemo(() => [
    { label: 'Opportunities', value: summary?.opportunities_built ?? 0 },
    { label: 'Proposal ready', value: summary?.proposal_ready ?? 0 },
    { label: 'Queued', value: summary?.queued ?? 0 },
    { label: 'Auto executable', value: summary?.auto_executable ?? 0 },
    { label: 'Blocked', value: summary?.blocked ?? 0 },
    { label: 'Throttle', value: summary?.portfolio_throttle_state ?? 'NORMAL' },
  ], [summary]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Opportunity supervisor"
        title="/opportunities"
        description="End-to-end autonomous opportunity cycle (paper/demo only): scan→signal→proposal→allocation→queue or paper auto-execution path."
      />
      <SectionCard eyebrow="Cycle controls" title="Run opportunity cycle" description="Local-first supervisory run. No real-money execution.">
        <div className="markets-filters__actions">
          <label className="field-group">
            <span>Profile</span>
            <select className="select-input" value={profile} onChange={(e) => setProfile(e.target.value)}>
              {(summary?.profiles ?? []).map((p) => <option key={p.slug} value={p.slug}>{p.label}</option>)}
            </select>
          </label>
          <button className="primary-button" type="button" disabled={running} onClick={() => void runCycle()}>{running ? 'Running…' : 'Run opportunity cycle'}</button>
          <button className="secondary-button" type="button" onClick={() => navigate('/operator-queue')}>Open queue</button>
          <button className="secondary-button" type="button" onClick={() => navigate('/proposals')}>Open proposals</button><button className="secondary-button" type="button" onClick={() => navigate('/mission-control')}>Open mission control</button><button className="secondary-button" type="button" onClick={() => navigate('/portfolio-governor')}>Open portfolio governor</button><button className="secondary-button" type="button" onClick={() => navigate('/profile-manager')}>Open profile manager</button><button className="secondary-button" type="button" onClick={() => navigate('/trace')}>Open trace explorer</button>
          {actionMessage ? <span className="muted-text">{actionMessage}</span> : null}
        </div>
      </SectionCard>

      <DataStateWrapper
        isLoading={loading}
        isError={Boolean(error)}
        errorMessage={error ?? undefined}
        loadingTitle="Loading opportunity cycles"
        loadingDescription="Collecting cycle runs, item traces, and supervisor summary."
        errorTitle="Could not load opportunities"
      >
        <SectionCard eyebrow="Summary" title="Supervisor outcomes" description="Paper/demo cycle outputs and execution path counts.">
          {summary?.portfolio_new_entries_blocked ? <p><strong>Portfolio governor is blocking new entries.</strong> Opportunities will remain blocked or queued.</p> : null}
          <div className="dashboard-stat-grid">{cards.map((c) => <article key={c.label} className="dashboard-stat-card"><span>{c.label}</span><strong>{c.value}</strong></article>)}</div>
        </SectionCard>

        <SectionCard eyebrow="Cycle table" title="Latest opportunity items" description="Trace from research context to final execution path.">
          {items.length === 0 ? <p className="muted-text">Run an opportunity cycle to build execution-ready opportunities.</p> : (
            <div className="markets-table-wrapper">
              <table className="markets-table">
                <thead><tr><th>Market</th><th>Research</th><th>Prediction edge</th><th>Risk</th><th>Signal</th><th>Proposal</th><th>Allocation</th><th>Path</th><th>Rationale</th></tr></thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td>{item.market_title}</td>
                      <td>{String(item.research_context.narrative_direction ?? 'n/a')}</td>
                      <td>{String(item.prediction_context.edge ?? 'n/a')}</td>
                      <td>{String(item.risk_context.risk_level ?? 'n/a')}</td>
                      <td>{String(item.signal_context.opportunity_status ?? 'n/a')}</td>
                      <td>{item.proposal_status}</td>
                      <td>{item.allocation_quantity ?? '-'}</td>
                      <td><span className={badgeClass(item.execution_path)}>{item.execution_path}</span></td>
                      <td>{item.execution_plan?.explanation ?? item.rationale}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Recent cycles" title="Run history" description="Latest autonomous opportunity supervisor runs.">
          {cycles.length === 0 ? <p className="muted-text">No cycles yet.</p> : (
            <div className="markets-table-wrapper">
              <table className="markets-table">
                <thead><tr><th>ID</th><th>Status</th><th>Opportunities</th><th>Queue</th><th>Auto</th><th>Blocked</th><th>Summary</th></tr></thead>
                <tbody>{cycles.slice(0, 10).map((run) => <tr key={run.id}><td>#{run.id}</td><td>{run.status}</td><td>{run.opportunities_built}</td><td>{run.queued_count}</td><td>{run.auto_executed_count}</td><td>{run.blocked_count}</td><td>{run.summary}</td></tr>)}</tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
