import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  getAutonomyProgramHealth,
  getAutonomyProgramRecommendations,
  getAutonomyProgramRules,
  getAutonomyProgramState,
  getAutonomyProgramSummary,
  runAutonomyProgramReview,
} from '../../services/autonomyProgram';
import type { CampaignHealthStatus, ProgramConcurrencyPosture } from '../../types/autonomyProgram';

const postureTone = (status: ProgramConcurrencyPosture): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (status === 'NORMAL') return 'ready';
  if (status === 'CONSTRAINED') return 'pending';
  if (status === 'HIGH_RISK' || status === 'FROZEN') return 'offline';
  return 'neutral';
};

const healthTone = (status: CampaignHealthStatus): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (status === 'HEALTHY') return 'ready';
  if (status === 'CAUTION') return 'pending';
  if (status === 'BLOCKED' || status === 'AT_RISK') return 'offline';
  return 'neutral';
};

export function AutonomyProgramPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [state, setState] = useState<Awaited<ReturnType<typeof getAutonomyProgramState>> | null>(null);
  const [rules, setRules] = useState<Awaited<ReturnType<typeof getAutonomyProgramRules>>>([]);
  const [health, setHealth] = useState<Awaited<ReturnType<typeof getAutonomyProgramHealth>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyProgramRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyProgramSummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statePayload, rulesPayload, healthPayload, recommendationsPayload, summaryPayload] = await Promise.all([
        getAutonomyProgramState(),
        getAutonomyProgramRules(),
        getAutonomyProgramHealth(),
        getAutonomyProgramRecommendations(),
        getAutonomyProgramSummary(),
      ]);
      setState(statePayload);
      setRules(rulesPayload);
      setHealth(healthPayload);
      setRecommendations(recommendationsPayload.slice(0, 12));
      setSummary(summaryPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy program control tower.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runReview = useCallback(async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const review = await runAutonomyProgramReview({ actor: 'operator-ui', apply_pause_gating: true });
      setMessage(`Program review completed. Applied ${review.pause_gates_applied} pause gates.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run program review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const atRiskCount = useMemo(() => health.filter((item) => item.health_status === 'AT_RISK' || item.health_status === 'BLOCKED').length, [health]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy program control tower"
        title="/autonomy-program"
        description="Cross-campaign concurrency guard and health governance. Manual-first and recommendation-driven; no opaque multi-campaign auto-orchestration."
        actions={<div className="button-row"><button className="primary-button" type="button" onClick={() => void runReview()} disabled={busy}>Run program review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-campaigns')}>Autonomy campaigns</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="secondary-button" type="button" onClick={() => navigate('/approvals')}>Approvals</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />
      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Program posture" title="Global campaign concurrency status" description="HOLD_NEW_CAMPAIGNS or BLOCKED posture is an intentional safe mode, not a failure.">
          <div className="cockpit-metric-grid">
            <div><strong>Active campaigns</strong><div>{summary?.active_campaigns_count ?? state?.state.active_campaigns_count ?? 0}</div></div>
            <div><strong>Blocked campaigns</strong><div>{summary?.blocked_campaigns_count ?? state?.state.blocked_campaigns_count ?? 0}</div></div>
            <div><strong>Observing campaigns</strong><div>{summary?.observing_campaigns_count ?? state?.state.observing_campaigns_count ?? 0}</div></div>
            <div><strong>Waiting approvals</strong><div>{summary?.waiting_approval_count ?? state?.state.waiting_approval_count ?? 0}</div></div>
            <div><strong>Concurrency posture</strong><div>{state?.state.concurrency_posture ? <StatusBadge tone={postureTone(state.state.concurrency_posture)}>{state.state.concurrency_posture}</StatusBadge> : 'n/a'}</div></div>
            <div><strong>Max active capacity</strong><div>{state?.max_active_campaigns ?? 'n/a'}</div></div>
          </div>
        </SectionCard>

        {health.length === 0 ? <EmptyState eyebrow="Program health" title="No active autonomy campaigns right now." description="Create or start a campaign and run review to populate cross-campaign health snapshots." /> : null}

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Health" title="Campaign health snapshots" description="Operational risk and blockers across active campaigns.">
            <p className="muted-text">At-risk campaigns: {atRiskCount}. Locked domains: {(summary?.locked_domains ?? state?.state.locked_domains ?? []).join(', ') || 'none'}.</p>
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Campaign</th><th>Wave</th><th>Status</th><th>Score</th><th>Blockers</th><th>Influence</th><th>Links</th></tr></thead>
                <tbody>
                  {health.slice(0, 30).map((item) => (
                    <tr key={item.id}>
                      <td>{item.campaign_title ?? `#${item.campaign}`}</td>
                      <td>{item.active_wave}</td>
                      <td><StatusBadge tone={healthTone(item.health_status)}>{item.health_status}</StatusBadge></td>
                      <td>{item.health_score}</td>
                      <td>{item.blocked_checkpoints} checkpoints · {item.open_approvals} approvals</td>
                      <td>{item.rollout_warnings} rollout · {item.incident_impact} incidents · {item.degraded_impact} degraded</td>
                      <td><button type="button" className="link-button" onClick={() => navigate('/autonomy-campaigns')}>Campaign</button><button type="button" className="link-button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Trace</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Continue / pause / reorder / hold decisions" description="Explicit guidance for operator sequencing and safety-first execution.">
            {!recommendations.length ? <p className="muted-text">No recommendations yet. Run review.</p> : (
              <div className="page-stack">
                {recommendations.map((item) => (
                  <article key={item.id} className="status-card">
                    <p className="status-card__label"><StatusBadge tone={item.recommendation_type === 'HOLD_NEW_CAMPAIGNS' ? 'pending' : 'neutral'}>{item.recommendation_type}</StatusBadge></p>
                    <h3>{item.target_campaign_title ?? (item.target_campaign ? `Campaign #${item.target_campaign}` : 'Program-level')}</h3>
                    <p>{item.rationale}</p>
                    <p className="muted-text">Reason codes: {item.reason_codes.join(', ') || 'none'} · Domains: {item.impacted_domains.join(', ') || 'none'} · Confidence: {item.confidence}</p>
                    <div className="button-row"><button className="link-button" type="button" onClick={() => navigate('/autonomy-campaigns')}>Open campaigns</button><button className="link-button" type="button" onClick={() => navigate('/approvals')}>Approvals</button></div>
                  </article>
                ))}
              </div>
            )}
          </SectionCard>
        </div>

        <SectionCard eyebrow="Concurrency rules" title="Program guardrails" description="Conservative rules to prevent unsafe cross-campaign parallelism.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Rule type</th><th>Scope</th><th>Config</th><th>Rationale</th></tr></thead>
              <tbody>
                {rules.map((rule) => (
                  <tr key={rule.id}>
                    <td>{rule.rule_type}</td>
                    <td>{rule.scope}</td>
                    <td><code>{JSON.stringify(rule.config)}</code></td>
                    <td>{rule.rationale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
