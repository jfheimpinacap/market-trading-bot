import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import { getChampionChallengerRuns, getChampionChallengerSummary, runChampionChallenger } from '../../services/championChallenger';
import type { ChampionChallengerRun, ChampionChallengerSummary } from '../../types/championChallenger';

const recommendationClass = (code: string) => {
  if (code === 'CHALLENGER_PROMISING') return 'signal-badge signal-badge--actionable';
  if (code === 'CHALLENGER_UNDERPERFORMS') return 'signal-badge signal-badge--bearish';
  if (code === 'KEEP_CHAMPION') return 'signal-badge signal-badge--monitor';
  return 'signal-badge signal-badge--neutral';
};

const fmtDate = (v: string | null) => (v ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(v)) : 'Pending');

export function ChampionChallengerPage() {
  const [summary, setSummary] = useState<ChampionChallengerSummary | null>(null);
  const [runs, setRuns] = useState<ChampionChallengerRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [lookbackHours, setLookbackHours] = useState(24);
  const [executionProfile, setExecutionProfile] = useState('balanced_paper');
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, runsRes] = await Promise.all([getChampionChallengerSummary(), getChampionChallengerRuns()]);
      setSummary(summaryRes);
      setRuns(runsRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load champion-challenger benchmark data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onRun = useCallback(async () => {
    setRunning(true);
    setMessage(null);
    try {
      const run = await runChampionChallenger({
        lookback_hours: lookbackHours,
        challenger_name: `challenger_${executionProfile}`,
        challenger_overrides: { execution_profile: executionProfile },
      });
      setMessage(`Shadow benchmark #${run.id} finished with recommendation ${run.recommendation_code}.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Shadow benchmark failed.');
    } finally {
      setRunning(false);
    }
  }, [executionProfile, load, lookbackHours]);

  const latest = summary?.latest_run;
  const cards = useMemo(
    () => [
      { label: 'Opportunities Δ', value: String(latest?.comparison_result?.deltas?.opportunity_delta ?? '—') },
      { label: 'Proposals Δ', value: String(latest?.comparison_result?.deltas?.proposal_delta ?? '—') },
      { label: 'Fill rate Δ', value: String(latest?.comparison_result?.deltas?.fill_rate_delta ?? '—') },
      { label: 'Execution-adjusted PnL Δ', value: String(latest?.comparison_result?.deltas?.execution_adjusted_pnl_delta ?? '—') },
      { label: 'Recommendation', value: latest?.recommendation_code ?? 'INCONCLUSIVE', badge: true },
    ],
    [latest],
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Champion challenger shadow mode"
        title="/champion-challenger"
        description="Live paper benchmark supervisor for active champion vs candidate challengers. Shadow-only, auditable, paper/demo only (no real money and no auto-switching)."
        actions={<div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/prediction')}>Open Prediction</button><button className="secondary-button" type="button" onClick={() => navigate('/profile-manager')}>Open Profile Manager</button><button className="secondary-button" type="button" onClick={() => navigate('/mission-control')}>Open Mission Control</button><button className="secondary-button" type="button" onClick={() => navigate('/readiness')}>Open Readiness</button><button className="secondary-button" type="button" onClick={() => navigate('/promotion')}>Open Promotion</button><button className="secondary-button" type="button" onClick={() => navigate('/rollout')}>Open Rollout</button></div>}
      />

      <SectionCard eyebrow="Champion stack" title="Current active champion binding" description="Explicit stack binding used as the baseline for shadow benchmarks.">
        {!summary?.current_champion ? <p className="muted-text">Loading champion binding…</p> : (
          <div className="system-metadata-grid">
            <div><strong>Name:</strong> {summary.current_champion.name}</div>
            <div><strong>Prediction profile:</strong> {summary.current_champion.prediction_profile_slug || 'n/a'}</div>
            <div><strong>Research profile:</strong> {summary.current_champion.research_profile_slug || 'n/a'}</div>
            <div><strong>Signal profile:</strong> {summary.current_champion.signal_profile_slug || 'n/a'}</div>
            <div><strong>Opportunity supervisor:</strong> {summary.current_champion.opportunity_supervisor_profile_slug || 'n/a'}</div>
            <div><strong>Mission control:</strong> {summary.current_champion.mission_control_profile_slug || 'n/a'}</div>
            <div><strong>Portfolio governor:</strong> {summary.current_champion.portfolio_governor_profile_slug || 'n/a'}</div>
            <div><strong>Execution profile:</strong> {summary.current_champion.execution_profile}</div>
          </div>
        )}
      </SectionCard>

      <SectionCard eyebrow="Run benchmark" title="Champion vs challenger shadow run" description="Run a parallel shadow benchmark without touching the active champion operation.">
        <div className="button-row">
          <label className="field-group"><span>Lookback hours</span><input className="text-input" type="number" min={1} max={336} value={lookbackHours} onChange={(e) => setLookbackHours(Number(e.target.value) || 24)} /></label>
          <label className="field-group"><span>Challenger execution profile</span><select className="select-input" value={executionProfile} onChange={(e) => setExecutionProfile(e.target.value)}><option value="optimistic_paper">optimistic_paper</option><option value="balanced_paper">balanced_paper</option><option value="conservative_paper">conservative_paper</option></select></label>
          <button className="primary-button" type="button" onClick={() => void onRun()} disabled={running}>{running ? 'Running shadow benchmark…' : 'Run shadow benchmark'}</button>
          {message ? <span className="muted-text">{message}</span> : null}
        </div>
      </SectionCard>

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Latest comparison" title="Champion vs challenger deltas" description="Key benchmark deltas and recommendation for manual governance follow-up.">
          <div className="dashboard-stat-grid">
            {cards.map((card) => (
              <article key={card.label} className="dashboard-stat-card">
                <span>{card.label}</span>
                <strong>{card.badge ? <span className={recommendationClass(String(card.value))}>{card.value}</span> : card.value}</strong>
              </article>
            ))}
          </div>
          {!latest ? <p className="muted-text">Run a shadow benchmark to compare the active stack with a challenger.</p> : null}
        </SectionCard>

        <SectionCard eyebrow="Detailed metrics" title="Side-by-side benchmark" description="Execution-aware metric comparison with divergence and recommendation rationale.">
          {!latest?.comparison_result ? <p className="muted-text">No comparison result available yet.</p> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Metric</th><th>Champion</th><th>Challenger</th><th>Delta</th></tr></thead>
                <tbody>
                  {Object.entries(latest.comparison_result.champion_metrics).map(([metric, value]) => (
                    <tr key={metric}>
                      <td>{metric}</td>
                      <td>{String(value)}</td>
                      <td>{String(latest.comparison_result?.challenger_metrics?.[metric] ?? '—')}</td>
                      <td>{String(latest.comparison_result?.deltas?.[`${metric.replace('_count', '').replace('_ready', '').replace('_metrics', '')}_delta`] ?? latest.comparison_result?.deltas?.[`${metric}_delta`] ?? '—')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {latest?.recommendation_reasons?.length ? <p><strong>Rationale:</strong> {latest.recommendation_reasons.join(', ')}.</p> : <p className="muted-text">Inconclusive challenger evidence is surfaced as manual review, not as an error.</p>}
        </SectionCard>

        <SectionCard eyebrow="Recent runs" title="Shadow benchmark history" description="Recent champion-challenger runs for auditable tracking and governance evidence.">
          {runs.length === 0 ? (
            <EmptyState
              eyebrow="Champion challenger"
              title="No shadow benchmark runs yet"
              description="Run a shadow benchmark to compare the active stack with a challenger."
            />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>ID</th><th>Status</th><th>Created</th><th>Finished</th><th>PnL Δ</th><th>Recommendation</th><th>Summary</th></tr></thead>
                <tbody>
                  {runs.slice(0, 15).map((run) => (
                    <tr key={run.id}>
                      <td>#{run.id}</td>
                      <td>{run.status}</td>
                      <td>{fmtDate(run.created_at)}</td>
                      <td>{fmtDate(run.finished_at)}</td>
                      <td>{run.pnl_delta_execution_adjusted}</td>
                      <td><span className={recommendationClass(run.recommendation_code)}>{run.recommendation_code}</span></td>
                      <td>{run.summary}</td>
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
