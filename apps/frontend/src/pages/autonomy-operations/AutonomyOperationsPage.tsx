import { useCallback, useEffect, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  acknowledgeAutonomySignal,
  getAutonomyOperationsRecommendations,
  getAutonomyOperationsRuntime,
  getAutonomyOperationsSignals,
  getAutonomyOperationsSummary,
  runAutonomyOperationsMonitor,
} from '../../services/autonomyOperations';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['ON_TRACK', 'CONTINUE_CAMPAIGN', 'CLEAR_TO_CONTINUE', 'RESOLVED'].includes(v)) return 'ready';
  if (['CAUTION', 'OBSERVING', 'WAITING_APPROVAL', 'OPEN', 'ACKNOWLEDGED', 'WAIT_FOR_CHECKPOINT', 'ESCALATE_TO_APPROVAL', 'REORDER_OPERATOR_ATTENTION'].includes(v)) return 'pending';
  if (['STALLED', 'BLOCKED', 'PAUSE_CAMPAIGN', 'REVIEW_FOR_ABORT', 'CRITICAL', 'HIGH'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyOperationsPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [runtime, setRuntime] = useState<Awaited<ReturnType<typeof getAutonomyOperationsRuntime>>>([]);
  const [signals, setSignals] = useState<Awaited<ReturnType<typeof getAutonomyOperationsSignals>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyOperationsRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyOperationsSummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [runtimeData, signalsData, recommendationData, summaryData] = await Promise.all([
        getAutonomyOperationsRuntime(),
        getAutonomyOperationsSignals(),
        getAutonomyOperationsRecommendations(),
        getAutonomyOperationsSummary(),
      ]);
      setRuntime(runtimeData.slice(0, 40));
      setSignals(signalsData.slice(0, 40));
      setRecommendations(recommendationData.slice(0, 40));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy operations monitor.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runMonitor = useCallback(async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await runAutonomyOperationsMonitor({ actor: 'operator-ui' });
      setMessage(`Operations run #${result.run} created ${result.runtime_count} runtime snapshots and ${result.signal_count} attention signals.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run autonomy operations monitor.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const acknowledge = useCallback(async (signalId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await acknowledgeAutonomySignal(signalId, { actor: 'operator-ui' });
      setMessage(`Signal #${signalId} acknowledged.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not acknowledge signal.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy operations monitor"
        title="/autonomy-operations"
        description="Active campaign runtime board and progress escalation control. Manual-first recommendation layer only: no opaque auto-remediation, no real trading execution."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runMonitor()}>Run monitor</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-activation')}>Autonomy activation</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-launch')}>Autonomy launch</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-program')}>Autonomy program</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-campaigns')}>Autonomy campaigns</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-interventions')}>Autonomy interventions</button><button className="ghost-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}
      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Runtime summary" title="Active campaign monitoring posture" description="ON_TRACK and ACKNOWLEDGED are valid states. This board is recommendation-first and fully auditable.">
          <div className="cockpit-metric-grid">
            <div><strong>Active campaigns</strong><div>{summary?.active_campaign_count ?? 0}</div></div>
            <div><strong>On track</strong><div>{summary?.on_track_count ?? 0}</div></div>
            <div><strong>Stalled</strong><div>{summary?.stalled_count ?? 0}</div></div>
            <div><strong>Blocked</strong><div>{summary?.blocked_count ?? 0}</div></div>
            <div><strong>Waiting approval</strong><div>{summary?.waiting_approval_count ?? 0}</div></div>
            <div><strong>Observing</strong><div>{summary?.observing_count ?? 0}</div></div>
            <div><strong>Attention signals open</strong><div>{summary?.open_attention_signal_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {runtime.length === 0 ? <EmptyState eyebrow="Runtime board" title="No active autonomy campaigns require operations monitoring right now." description="When campaigns are started and active, run monitor to generate runtime snapshots, attention signals, and recommendations." /> : null}

        <SectionCard eyebrow="Runtime panel" title="Active campaigns" description="Current wave/step/checkpoint, progress pressure, blockers, and trace/approval links.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Campaign</th><th>Status</th><th>Wave / step / checkpoint</th><th>Progress</th><th>Pressure</th><th>Blockers</th><th>Links</th></tr></thead>
              <tbody>
                {runtime.map((item) => (
                  <tr key={item.id}>
                    <td>{item.campaign_title ?? `#${item.campaign}`}</td>
                    <td><StatusBadge tone={tone(item.runtime_status)}>{item.runtime_status}</StatusBadge><div className="muted-text">campaign: {item.campaign_status}</div></td>
                    <td>w{item.current_wave ?? 'n/a'} · step {item.current_step_order ?? 'n/a'} · {item.current_checkpoint_summary ?? 'n/a'}</td>
                    <td>last: {item.last_progress_at ? new Date(item.last_progress_at).toLocaleString() : 'n/a'} · stalled: {item.stalled_duration_seconds ?? 0}s · score: {item.progress_score}</td>
                    <td>checkpoints: {item.open_checkpoints_count} · approvals: {item.pending_approvals_count} · blocked steps: {item.blocked_steps_count} · incidents: {item.incident_impact} · degraded: {item.degraded_impact} · rollout: {item.rollout_observation_impact}</td>
                    <td>{item.blockers.join(', ') || 'none'}</td>
                    <td><button type="button" className="link-button" onClick={() => navigate('/autonomy-campaigns')}>Campaign</button><button type="button" className="link-button" onClick={() => navigate('/approvals')}>Approvals</button><button type="button" className="link-button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Trace</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Attention signals" title="Operational attention queue" description="Explicit signal severity/type with manual acknowledge action.">
            {!signals.length ? <p className="muted-text">No attention signals yet.</p> : (
              <div className="page-stack">
                {signals.map((item) => (
                  <article key={item.id} className="status-card">
                    <p className="status-card__label"><StatusBadge tone={tone(item.severity)}>{item.severity}</StatusBadge> <StatusBadge tone={tone(item.status)}>{item.status}</StatusBadge></p>
                    <h3>{item.signal_type} · {item.campaign_title ?? `#${item.campaign}`}</h3>
                    <p>{item.rationale}</p>
                    <p className="muted-text">Reason codes: {item.reason_codes.join(', ') || 'none'} · Blockers: {item.blockers.join(', ') || 'none'}</p>
                    <div className="button-row"><button type="button" className="secondary-button" disabled={busy || item.status !== 'OPEN'} onClick={() => void acknowledge(item.id)}>Acknowledge</button><button type="button" className="ghost-button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Trace</button></div>
                  </article>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Manual-first operations recommendations" description="Continue/Pause/Resume/Escalate/Review guidance only; operator remains in control.">
            {!recommendations.length ? <p className="muted-text">No operations recommendations yet. Run monitor.</p> : (
              <div className="page-stack">
                {recommendations.map((item) => (
                  <article key={item.id} className="status-card">
                    <p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p>
                    <h3>{item.target_campaign_title ?? (item.target_campaign ? `Campaign #${item.target_campaign}` : 'Program attention')}</h3>
                    <p>{item.rationale}</p>
                    <p className="muted-text">Reason codes: {item.reason_codes.join(', ') || 'none'} · Blockers: {item.blockers.join(', ') || 'none'} · Domains: {item.impacted_domains.join(', ') || 'none'} · Confidence: {item.confidence}</p>
                  </article>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
