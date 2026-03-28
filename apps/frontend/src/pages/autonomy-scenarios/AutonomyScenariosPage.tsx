import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  getAutonomyScenarioOptions,
  getAutonomyScenarioRecommendations,
  getAutonomyScenarioRuns,
  getAutonomyScenarioSummary,
  runAutonomyScenario,
} from '../../services/autonomyScenario';
import type { ScenarioRecommendationCode } from '../../types/autonomyScenario';

const toneForRecommendation = (code: ScenarioRecommendationCode): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (code === 'BEST_NEXT_MOVE' || code === 'SAFE_BUNDLE' || code === 'SEQUENCE_FIRST') return 'ready';
  if (code === 'DELAY_UNTIL_STABLE' || code === 'REQUIRE_APPROVAL_HEAVY') return 'pending';
  if (code === 'DO_NOT_EXECUTE') return 'offline';
  return 'neutral';
};

export function AutonomyScenariosPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyScenarioSummary>> | null>(null);
  const [runs, setRuns] = useState<Awaited<ReturnType<typeof getAutonomyScenarioRuns>>>([]);
  const [optionsPreview, setOptionsPreview] = useState<Awaited<ReturnType<typeof getAutonomyScenarioOptions>> | null>(null);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyScenarioRecommendations>>>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryPayload, runsPayload, optionsPayload, recommendationsPayload] = await Promise.all([
        getAutonomyScenarioSummary(),
        getAutonomyScenarioRuns(),
        getAutonomyScenarioOptions(),
        getAutonomyScenarioRecommendations(),
      ]);
      setSummary(summaryPayload);
      setRuns(runsPayload);
      setOptionsPreview(optionsPayload);
      setRecommendations(recommendationsPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy scenario lab.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runSimulation = useCallback(async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const run = await runAutonomyScenario({ requested_by: 'operator-ui', notes: 'manual-first scenario lab run' });
      setMessage(`Scenario run #${run.id} completed with ${run.options.length} options compared.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run autonomy scenario simulation.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const latestRun = runs[0] ?? null;
  const selectedRecommendation = useMemo(
    () => latestRun?.recommendations.find((item) => item.option_key === latestRun.selected_option_key) ?? null,
    [latestRun],
  );

  const riskByOptionId = useMemo(() => {
    const map = new Map<number, (typeof latestRun)['risk_estimates'][number]>();
    latestRun?.risk_estimates.forEach((risk) => map.set(risk.option, risk));
    return map;
  }, [latestRun]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Scenario lab"
        title="/autonomy-scenarios"
        description="Roadmap simulation and bundle what-if evaluator. Manual-first, simulation-only, recommendation-first. This module does not apply autonomy transitions."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runSimulation()}>Run scenario simulation</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-roadmap')}>Open roadmap</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy')}>Open autonomy</button><button className="secondary-button" type="button" onClick={() => navigate('/approvals')}>Open approvals</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Open trace</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Scenario posture" title="Autonomy roadmap simulation" description="Compare sequence and bundle options before any real apply. DO_NOT_EXECUTE is a valid healthy output when constraints are active.">
          <div className="cockpit-metric-grid">
            <div><strong>Total runs</strong><div>{summary?.total_runs ?? 0}</div></div>
            <div><strong>Preview options</strong><div>{optionsPreview?.options.length ?? 0}</div></div>
            <div><strong>Latest recommendation</strong><div>{summary?.latest_recommendation_code ?? 'n/a'}</div></div>
            <div><strong>Selected option</strong><div>{summary?.latest_selected_option_key ?? 'n/a'}</div></div>
          </div>
        </SectionCard>

        {runs.length === 0 ? (
          <EmptyState
            eyebrow="Scenario lab"
            title="No scenario simulation runs yet"
            description="Run an autonomy scenario simulation to compare domain progression options."
          />
        ) : null}

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Scenario options" title="Generated options" description="Single-domain, sequence, bundle, freeze/promote, and delay options from current evidence.">
            {!latestRun ? <p className="muted-text">Run a simulation first.</p> : (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>Option</th><th>Domains</th><th>Order</th><th>Type</th><th>Bundle</th></tr></thead>
                  <tbody>
                    {latestRun.options.map((item) => (
                      <tr key={item.id}>
                        <td>{item.option_key}</td>
                        <td>{item.domains.join(', ') || 'n/a'}</td>
                        <td>{item.order.join(' → ') || 'n/a'}</td>
                        <td>{item.option_type}</td>
                        <td>{item.is_bundle ? 'YES' : 'NO'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>

          <SectionCard eyebrow="Risk" title="Risk estimate panel" description="Dependency conflicts, approval friction, incident/degraded risk, rollback hint and approval-heavy posture.">
            {!latestRun ? <p className="muted-text">No risk estimate yet.</p> : (
              <div className="page-stack">
                {latestRun.options.slice(0, 8).map((item) => {
                  const risk = riskByOptionId.get(item.id);
                  if (!risk) return null;
                  return (
                    <article key={item.option_key} className="status-card">
                      <p className="status-card__label">{item.option_key}</p>
                      <h3>{risk.bundle_risk_level} risk</h3>
                      <p><StatusBadge tone={risk.approval_heavy ? 'pending' : 'neutral'}>{risk.approval_heavy ? 'APPROVAL_HEAVY' : 'APPROVAL_NORMAL'}</StatusBadge></p>
                      <p className="muted-text">Dependency {risk.dependency_conflict_risk} · Friction {risk.approval_friction_risk} · Degraded {risk.degraded_posture_risk} · Incident {risk.incident_exposure_risk}</p>
                      <p className="muted-text">Blockers: {risk.blockers.join(', ') || 'none'}.</p>
                    </article>
                  );
                })}
              </div>
            )}
          </SectionCard>
        </div>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Recommendations" title="Best next scenario guidance" description="Recommendation-first outputs for scenario comparison and staged execution planning.">
            {!recommendations.length ? <p className="muted-text">No recommendations yet. Run a simulation first.</p> : (
              <div className="page-stack">
                {recommendations.slice(0, 12).map((item) => (
                  <article key={item.id} className="status-card">
                    <p className="status-card__label">{item.option_key}</p>
                    <h3><StatusBadge tone={toneForRecommendation(item.recommendation_code)}>{item.recommendation_code}</StatusBadge> <span className="muted-text">score {item.score}</span></h3>
                    <p>{item.rationale}</p>
                    <p className="muted-text">Reason codes: {item.reason_codes.join(', ') || 'n/a'}.</p>
                    <div className="button-row"><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_scenario_recommendation&root_id=${encodeURIComponent(String(item.id))}`)}>Open trace evidence</button></div>
                  </article>
                ))}
              </div>
            )}
            {selectedRecommendation ? <p className="success-text">Current best move: {selectedRecommendation.option_key} ({selectedRecommendation.recommendation_code}).</p> : null}
          </SectionCard>

          <SectionCard eyebrow="Recent runs" title="Simulation history" description="Auditable scenario run list with selected option and recommendation output.">
            {!runs.length ? <p className="muted-text">No runs yet.</p> : (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>ID</th><th>Created</th><th>Options</th><th>Selected</th><th>Recommendation</th><th>Summary</th></tr></thead>
                  <tbody>
                    {runs.slice(0, 10).map((run) => (
                      <tr key={run.id}>
                        <td>{run.id}</td>
                        <td>{new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(run.created_at))}</td>
                        <td>{run.options.length}</td>
                        <td>{run.selected_option_key || 'n/a'}</td>
                        <td>{run.selected_recommendation_code || 'n/a'}</td>
                        <td>{run.summary}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
