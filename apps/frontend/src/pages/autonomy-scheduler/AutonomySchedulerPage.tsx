import { useCallback, useEffect, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  admitAutonomyCampaign,
  deferAutonomyCampaign,
  getAutonomySchedulerQueue,
  getAutonomySchedulerRecommendations,
  getAutonomySchedulerSummary,
  getAutonomySchedulerWindows,
  runAutonomySchedulerPlan,
} from '../../services/autonomyScheduler';
import type { CampaignAdmissionStatus, ChangeWindowStatus } from '../../types/autonomyScheduler';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['READY', 'ADMITTED', 'OPEN', 'SAFE_TO_ADMIT_NEXT'].includes(v)) return 'ready';
  if (['PENDING', 'UPCOMING', 'DEFERRED', 'WAIT_FOR_WINDOW', 'HOLD_QUEUE'].includes(v)) return 'pending';
  if (['BLOCKED', 'EXPIRED', 'CLOSED', 'FROZEN', 'BLOCK_ADMISSION'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomySchedulerPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [queue, setQueue] = useState<Awaited<ReturnType<typeof getAutonomySchedulerQueue>>>([]);
  const [windows, setWindows] = useState<Awaited<ReturnType<typeof getAutonomySchedulerWindows>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomySchedulerRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomySchedulerSummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [queueData, windowsData, recommendationData, summaryData] = await Promise.all([
        getAutonomySchedulerQueue(),
        getAutonomySchedulerWindows(),
        getAutonomySchedulerRecommendations(),
        getAutonomySchedulerSummary(),
      ]);
      setQueue(queueData);
      setWindows(windowsData);
      setRecommendations(recommendationData.slice(0, 20));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy scheduler.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runPlan = useCallback(async () => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const response = await runAutonomySchedulerPlan({ actor: 'operator-ui' });
      setMessage(`Scheduler run #${response.run.id} generated ${response.recommendations.length} recommendations.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run scheduler plan.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const doAdmit = useCallback(async (campaignId: number) => {
    setBusy(true);
    try {
      await admitAutonomyCampaign(campaignId, { actor: 'operator-ui' });
      setMessage(`Campaign #${campaignId} admitted.`);
      await load();
    } finally {
      setBusy(false);
    }
  }, [load]);

  const doDefer = useCallback(async (campaignId: number) => {
    setBusy(true);
    try {
      await deferAutonomyCampaign(campaignId, { actor: 'operator-ui', reason: 'Deferred from scheduler board' });
      setMessage(`Campaign #${campaignId} deferred.`);
      await load();
    } finally {
      setBusy(false);
    }
  }, [load]);

  const activeWindow = windows.find((item) => item.id === summary?.active_window_id) ?? windows[0] ?? null;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy scheduler"
        title="/autonomy-scheduler"
        description="Campaign admission board and safe-start window planner. Manual-first, recommendation-driven, and explicitly non-opaque (no mass auto-start orchestration)."
        actions={<div className="button-row"><button className="primary-button" type="button" onClick={() => void runPlan()} disabled={busy}>Run scheduler plan</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-program')}>Autonomy program</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-launch')}>Autonomy launch</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-activation')}>Autonomy activation</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-campaigns')}>Autonomy campaigns</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}
      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Posture and windows" title="Admission readiness snapshot" description="WAIT_FOR_WINDOW and HOLD states are valid safety outcomes, not system failures.">
          <div className="cockpit-metric-grid">
            <div><strong>Program posture</strong><div>{summary?.current_program_posture ? <StatusBadge tone={tone(summary.current_program_posture)}>{summary.current_program_posture}</StatusBadge> : 'n/a'}</div></div>
            <div><strong>Active window</strong><div>{activeWindow ? <StatusBadge tone={tone(activeWindow.status)}>{activeWindow.name} · {activeWindow.status}</StatusBadge> : 'none'}</div></div>
            <div><strong>Ready candidates</strong><div>{summary?.queue_counts.READY ?? 0}</div></div>
            <div><strong>Blocked candidates</strong><div>{summary?.queue_counts.BLOCKED ?? 0}</div></div>
            <div><strong>Deferred candidates</strong><div>{summary?.queue_counts.DEFERRED ?? 0}</div></div>
            <div><strong>Max admissible starts</strong><div>{summary?.max_admissible_starts ?? 0}</div></div>
          </div>
        </SectionCard>

        {queue.length === 0 ? <EmptyState eyebrow="Admission queue" title="No autonomy campaigns are queued for admission right now." description="Create candidate campaigns from roadmap/scenario or add manual entries before running scheduler planning." /> : null}

        <SectionCard eyebrow="Queue" title="Campaign admission backlog" description="Explicit, auditable queue ordering and blockers with manual admit/defer controls.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Campaign</th><th>Status</th><th>Priority</th><th>Readiness</th><th>Blockers</th><th>Requested window</th><th>Links</th><th>Actions</th></tr></thead>
              <tbody>
                {queue.map((item) => (
                  <tr key={item.id}>
                    <td>{item.campaign_title ?? `#${item.campaign}`}</td>
                    <td><StatusBadge tone={tone(item.status as CampaignAdmissionStatus)}>{item.status}</StatusBadge></td>
                    <td>{item.priority_score}</td>
                    <td>{item.readiness_score}</td>
                    <td>{item.blocked_reasons.join(', ') || 'none'}</td>
                    <td>{item.requested_window ?? 'n/a'}</td>
                    <td><button type="button" className="link-button" onClick={() => navigate('/autonomy-campaigns')}>Campaigns</button><button type="button" className="link-button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Trace</button></td>
                    <td><button type="button" className="link-button" disabled={busy || item.status === 'ADMITTED'} onClick={() => void doAdmit(item.campaign)}>Admit</button><button type="button" className="link-button" disabled={busy || item.status === 'DEFERRED'} onClick={() => void doDefer(item.campaign)}>Defer</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Recommendations" title="ADMIT / DEFER / HOLD / WAIT guidance" description="Recommendations are visible and reasoned; execution remains operator-approved.">
            {!recommendations.length ? <p className="muted-text">No recommendations yet. Run scheduler plan.</p> : (
              <div className="page-stack">
                {recommendations.map((item) => (
                  <article key={item.id} className="status-card">
                    <p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p>
                    <h3>{item.target_campaign_title ?? (item.target_campaign ? `Campaign #${item.target_campaign}` : 'Queue-level')}</h3>
                    <p>{item.rationale}</p>
                    <p className="muted-text">Reason codes: {item.reason_codes.join(', ') || 'none'} · Blockers: {item.blockers.join(', ') || 'none'} · Domains: {item.impacted_domains.join(', ') || 'none'} · Confidence: {item.confidence}</p>
                    <div className="button-row"><button type="button" className="link-button" onClick={() => navigate('/approvals')}>Approvals</button><button type="button" className="link-button" onClick={() => navigate('/trace')}>Trace</button></div>
                  </article>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard eyebrow="Windows" title="Safe start windows" description="Simple and explicit change windows. No enterprise calendar orchestration.">
            {windows.length === 0 ? <p className="muted-text">No windows configured yet.</p> : (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>Name</th><th>Status</th><th>Type</th><th>Max admissions</th><th>Allowed posture</th><th>Blocked domains</th></tr></thead>
                  <tbody>
                    {windows.map((window) => (
                      <tr key={window.id}>
                        <td>{window.name}</td>
                        <td><StatusBadge tone={tone(window.status as ChangeWindowStatus)}>{window.status}</StatusBadge></td>
                        <td>{window.window_type}</td>
                        <td>{window.max_new_admissions}</td>
                        <td>{window.allowed_postures.join(', ') || 'any'}</td>
                        <td>{window.blocked_domains.join(', ') || 'none'}</td>
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
