import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import { getCockpitAttention, getCockpitQuickLinks, getCockpitSummary, runCockpitAction } from '../services/cockpit';
import { getAutonomyScenarioSummary } from '../services/autonomyScenario';
import type { CockpitAttentionItem, CockpitQuickActionId, CockpitSnapshot } from '../types/cockpit';

const formatDate = (value: string | null | undefined) => (value ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : 'n/a');

const toneFromStatus = (status: string | null | undefined): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const normalized = (status ?? '').toUpperCase();
  if (['ACTIVE', 'READY', 'RUNNING', 'SUCCESS', 'PARITY_OK', 'COMPLETED', 'NORMAL'].includes(normalized)) return 'ready';
  if (['DEGRADED', 'PAUSED', 'WARNING', 'THROTTLED', 'BLOCK_NEW_ENTRIES', 'PARTIAL', 'CAUTION'].includes(normalized)) return 'pending';
  if (['FAILED', 'STOPPED', 'ROLLED_BACK', 'REJECTED', 'REMEDIATION_REQUIRED', 'RECERTIFICATION_REQUIRED'].includes(normalized)) return 'offline';
  return 'neutral';
};

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function TraceButton({ item }: { item: CockpitAttentionItem }) {
  if (!item.traceRootType || !item.traceRootId) {
    return null;
  }
  return (
    <button
      className="ghost-button"
      type="button"
      onClick={() => navigate(`/trace?root_type=${encodeURIComponent(item.traceRootType ?? '')}&root_id=${encodeURIComponent(item.traceRootId ?? '')}`)}
    >
      Open trace
    </button>
  );
}

export function CockpitPage() {
  const [snapshot, setSnapshot] = useState<CockpitSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [runningAction, setRunningAction] = useState<CockpitQuickActionId | null>(null);
  const [autonomyScenarioSummary, setAutonomyScenarioSummary] = useState<Awaited<ReturnType<typeof getAutonomyScenarioSummary>> | null>(null);

  const loadCockpit = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [response, scenarioSummary] = await Promise.all([getCockpitSummary(), getAutonomyScenarioSummary()]);
      setSnapshot(response);
      setAutonomyScenarioSummary(scenarioSummary);
    } catch (loadError) {
      setError(getErrorMessage(loadError, 'Could not load cockpit data.'));
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCockpit();
  }, [loadCockpit]);

  const attention = useMemo(() => (snapshot ? getCockpitAttention(snapshot) : []), [snapshot]);
  const quickLinks = useMemo(() => getCockpitQuickLinks(), []);

  const runAction = useCallback(
    async (action: CockpitQuickActionId) => {
      if (!snapshot) return;
      setRunningAction(action);
      setActionError(null);
      setActionMessage(null);
      try {
        const runId = snapshot.rollout?.current_run?.id;
        await runCockpitAction(action, runId ? { runId } : undefined);
        setActionMessage(`Action ${action} executed.`);
        await loadCockpit();
      } catch (err) {
        setActionError(getErrorMessage(err, `Action ${action} failed.`));
      } finally {
        setRunningAction(null);
      }
    },
    [loadCockpit, snapshot],
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operator cockpit"
        title="/cockpit"
        description="Single-pane operational command center for manual-first paper/sandbox supervision. Centralizes posture, incidents, governance, and trace-oriented drill-down without replacing specialized pages."
        actions={<button className="secondary-button" type="button" onClick={() => void loadCockpit()}>Refresh cockpit</button>}
      />

      <SectionCard eyebrow="Quick actions" title="Manual-first controls" description="Triggers existing operations; no new execution logic is introduced.">
        <div className="button-row">
          <button className="primary-button" type="button" disabled={runningAction !== null} onClick={() => void runAction('MISSION_CONTROL_START')}>Start mission</button>
          <button className="secondary-button" type="button" disabled={runningAction !== null} onClick={() => void runAction('MISSION_CONTROL_PAUSE')}>Pause mission</button>
          <button className="secondary-button" type="button" disabled={runningAction !== null} onClick={() => void runAction('MISSION_CONTROL_RESUME')}>Resume mission</button>
          <button className="secondary-button" type="button" disabled={runningAction !== null} onClick={() => void runAction('INCIDENT_DETECTION')}>Run incident detection</button>
          <button className="secondary-button" type="button" disabled={runningAction !== null} onClick={() => void runAction('CERTIFICATION_REVIEW')}>Run certification review</button>
          <button className="secondary-button" type="button" disabled={runningAction !== null} onClick={() => void runAction('PORTFOLIO_GOVERNANCE')}>Run portfolio governance</button>
          <button className="secondary-button" type="button" disabled={runningAction !== null} onClick={() => void runAction('PROFILE_GOVERNANCE')}>Run profile governance</button>
          <button className="ghost-button" type="button" disabled={runningAction !== null || !snapshot?.rollout?.current_run?.id} onClick={() => void runAction('ROLLOUT_PAUSE')}>Pause rollout</button>
          <button className="ghost-button" type="button" disabled={runningAction !== null || !snapshot?.rollout?.current_run?.id} onClick={() => void runAction('ROLLOUT_ROLLBACK')}>Rollback rollout</button>
        </div>
        {actionMessage ? <p className="success-text">{actionMessage}</p> : null}
        {actionError ? <p className="error-text">{actionError}</p> : null}
      </SectionCard>

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        {!snapshot ? null : (
          <>
            <SectionCard eyebrow="System posture" title="Runtime, degraded mode, certification and profile" description="Fast answer to whether the stack is healthy or constrained.">
              <div className="cockpit-metric-grid">
                <div><strong>Runtime mode:</strong> <StatusBadge tone={toneFromStatus(snapshot.runtime?.state.current_mode)}>{snapshot.runtime?.state.current_mode ?? 'n/a'}</StatusBadge></div>
                <div><strong>Runtime status:</strong> <StatusBadge tone={toneFromStatus(snapshot.runtime?.state.status)}>{snapshot.runtime?.state.status ?? 'n/a'}</StatusBadge></div>
                <div><strong>Degraded mode:</strong> <StatusBadge tone={toneFromStatus(snapshot.incidents?.degraded_mode.state)}>{snapshot.incidents?.degraded_mode.state ?? 'n/a'}</StatusBadge></div>
                <div><strong>Certification:</strong> <StatusBadge tone={toneFromStatus(snapshot.certification?.latest_run?.certification_level)}>{snapshot.certification?.latest_run?.certification_level ?? 'NOT_CERTIFIED'}</StatusBadge></div>
                <div><strong>Profile regime:</strong> <StatusBadge tone={toneFromStatus(snapshot.profile?.current_regime)}>{snapshot.profile?.current_regime ?? 'n/a'}</StatusBadge></div>
                <div><strong>Profile recommendation:</strong> {snapshot.profile?.target_profiles.mission_control ?? 'n/a'}</div>
              </div>
            </SectionCard>

            <div className="content-grid content-grid--two-columns">
              <SectionCard eyebrow="Mission control & operations" title="Cycle posture and impact" description="Mission status, cycle context, and operational incidents.">
                <ul className="key-value-list">
                  <li><span>Mission status</span><strong>{snapshot.missionControl?.state.status ?? 'n/a'}</strong></li>
                  <li><span>Last heartbeat</span><strong>{formatDate(snapshot.missionControl?.state.last_heartbeat_at)}</strong></li>
                  <li><span>Latest cycle status</span><strong>{snapshot.missionControl?.latest_cycle?.status ?? 'n/a'}</strong></li>
                  <li><span>Latest cycle summary</span><strong>{snapshot.missionControl?.latest_cycle?.summary ?? 'n/a'}</strong></li>
                  <li><span>Open incidents</span><strong>{snapshot.incidents?.summary.active_incidents ?? 0}</strong></li>
                </ul>
                <div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/mission-control')}>Open mission control</button><button className="secondary-button" type="button" onClick={() => navigate('/incidents')}>Open incidents</button></div>
              </SectionCard>

              <SectionCard eyebrow="Risk & exposure" title="Portfolio governance and position review" description="Open exposure, throttle state, and decisions requiring manual attention.">
                <ul className="key-value-list">
                  <li><span>Governor state</span><strong>{snapshot.portfolioGovernor?.latest_throttle_state ?? 'n/a'}</strong></li>
                  <li><span>Open positions</span><strong>{snapshot.portfolioGovernor?.open_positions ?? 0}</strong></li>
                  <li><span>Throttle decision</span><strong>{snapshot.portfolioThrottle?.state ?? 'n/a'}</strong></li>
                  <li><span>Review required</span><strong>{snapshot.positionDecisions.filter((item) => item.status === 'REVIEW_REQUIRED').length}</strong></li>
                </ul>
                <div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/portfolio-governor')}>Open portfolio governor</button><button className="secondary-button" type="button" onClick={() => navigate('/positions')}>Open positions</button></div>
              </SectionCard>

              <SectionCard eyebrow="Execution & venue" title="Bridge, parity and account reconciliation" description="Snapshot of sandbox execution readiness and parity quality.">
                <ul className="key-value-list">
                  <li><span>Bridge validations</span><strong>{snapshot.brokerBridge?.validated ?? 0}</strong></li>
                  <li><span>Bridge rejects</span><strong>{snapshot.brokerBridge?.rejected ?? 0}</strong></li>
                  <li><span>Parity gaps</span><strong>{snapshot.executionVenue?.parity_gap ?? 0}</strong></li>
                  <li><span>Reconciliation mismatches</span><strong>{snapshot.venueAccount?.latest_reconciliation?.mismatches_count ?? 0}</strong></li>
                </ul>
                <div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/broker-bridge')}>Open bridge</button><button className="secondary-button" type="button" onClick={() => navigate('/execution-venue')}>Open venue</button><button className="secondary-button" type="button" onClick={() => navigate('/venue-account')}>Open account</button></div>
              </SectionCard>


              <SectionCard eyebrow="Runbooks" title="Guided remediation workflows" description="Manual-first playbook coverage for incidents, degradations and recurring operator procedures.">
                <ul className="key-value-list">
                  <li><span>Open</span><strong>{snapshot.runbookSummary?.counts.open ?? 0}</strong></li>
                  <li><span>In progress</span><strong>{snapshot.runbookSummary?.counts.in_progress ?? 0}</strong></li>
                  <li><span>Blocked</span><strong>{snapshot.runbookSummary?.counts.blocked ?? 0}</strong></li>
                  <li><span>Autopilot paused</span><strong>{snapshot.runbookAutopilotSummary?.counts.paused_for_approval ?? 0}</strong></li>
                  <li><span>Autopilot blocked</span><strong>{snapshot.runbookAutopilotSummary?.counts.blocked ?? 0}</strong></li>
                  <li><span>Autopilot completed</span><strong>{snapshot.runbookAutopilotSummary?.counts.completed ?? 0}</strong></li>
                  <li><span>Approval center pending</span><strong>{snapshot.approvalSummary?.pending ?? 0}</strong></li>
                  <li><span>High priority approvals</span><strong>{snapshot.approvalSummary?.high_priority_pending ?? 0}</strong></li>
                </ul>
                <div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/runbooks')}>Open runbooks</button><button className="ghost-button" type="button" onClick={() => navigate('/approvals')}>Open approvals</button><button className="ghost-button" type="button" onClick={() => navigate('/trust-calibration')}>Open trust calibration</button><button className="ghost-button" type="button" onClick={() => navigate('/policy-tuning')}>Open policy tuning</button></div>
              </SectionCard>

              <SectionCard eyebrow="Change governance" title="Promotion, rollout and champion/challenger" description="Current promotion recommendations and rollout status.">
                <ul className="key-value-list">
                  <li><span>Promotion recommendation</span><strong>{snapshot.promotionSummary?.latest_run?.recommendation_code ?? 'n/a'}</strong></li>
                  <li><span>Rollout status</span><strong>{snapshot.rollout?.current_run?.status ?? snapshot.rollout?.latest_run?.status ?? 'n/a'}</strong></li>
                  <li><span>Policy rollout observing</span><strong>{snapshot.policyRolloutSummary?.observing_runs ?? 0}</strong></li>
                  <li><span>Policy rollback recommended</span><strong>{snapshot.policyRolloutSummary?.rollback_recommended_runs ?? 0}</strong></li>
                  <li><span>Champion/challenger mode</span><strong>{snapshot.championChallengerSummary?.latest_run?.status ?? 'n/a'}</strong></li>
                  <li><span>Champion/challenger result</span><strong>{snapshot.championChallengerSummary?.latest_run?.recommendation_code ?? 'n/a'}</strong></li>
                  <li><span>Autonomy pending changes</span><strong>{snapshot.autonomySummary?.pending_stage_changes ?? 0}</strong></li>
                  <li><span>Autonomy degraded/blocked</span><strong>{(snapshot.autonomySummary?.degraded_domains ?? 0) + (snapshot.autonomySummary?.blocked_domains ?? 0)}</strong></li><li><span>Autonomy rollout observing</span><strong>{snapshot.autonomyRolloutSummary?.observing_runs ?? 0}</strong></li><li><span>Autonomy freeze/rollback warnings</span><strong>{(snapshot.autonomyRolloutSummary?.freeze_recommended_runs ?? 0) + (snapshot.autonomyRolloutSummary?.rollback_recommended_runs ?? 0)}</strong></li><li><span>Roadmap blocked domains</span><strong>{snapshot.autonomyRoadmapSummary?.latest_blocked_domains.length ?? 0}</strong></li><li><span>Active campaigns</span><strong>{snapshot.autonomyCampaignSummary?.active_campaigns ?? 0}</strong></li><li><span>Latest campaign status</span><strong>{snapshot.autonomyCampaignSummary?.latest_status ?? 'n/a'}</strong></li><li><span>Roadmap next best sequence</span><strong>{snapshot.autonomyRoadmapSummary?.latest_recommended_sequence.slice(0, 2).join(' → ') || 'n/a'}</strong></li><li><span>Scenario best next move</span><strong>{autonomyScenarioSummary?.latest_selected_option_key ?? 'n/a'}</strong></li><li><span>Scenario recommendation</span><strong>{autonomyScenarioSummary?.latest_recommendation_code ?? 'n/a'}</strong></li>
                </ul>
                <div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/promotion')}>Open promotion</button><button className="secondary-button" type="button" onClick={() => navigate('/rollout')}>Open rollout</button><button className="secondary-button" type="button" onClick={() => navigate('/policy-rollout')}>Open policy rollout</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy')}>Open autonomy</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-rollout')}>Open autonomy rollout</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-roadmap')}>Open autonomy roadmap</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-scenarios')}>Open autonomy scenarios</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-program')}>Open autonomy program</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-scheduler')}>Open autonomy scheduler</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-launch')}>Open autonomy launch</button><button className="secondary-button" type="button" onClick={() => navigate('/champion-challenger')}>Open C/C</button></div>
              </SectionCard>
            </div>

            <SectionCard eyebrow="Attention queue" title="Prioritized attention and trace drill-down" description="Severity-first queue across incidents, parity, queue pressure, and blocked opportunities.">
              {attention.length === 0 ? <EmptyState eyebrow="Attention" title="No urgent blockers" description="No critical/high attention items were detected in this snapshot." /> : (
                <div className="cockpit-attention-list">
                  {attention.map((item) => (
                    <article key={item.id} className="cockpit-attention-item">
                      <div>
                        <p className="section-label">{item.severity}</p>
                        <h3>{item.title}</h3>
                        <p>{item.summary}</p>
                      </div>
                      <div className="button-row">
                        <button className="secondary-button" type="button" onClick={() => navigate(item.route)}>Open module</button>
                        <TraceButton item={item} />
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </SectionCard>

            <div className="content-grid content-grid--two-columns">
              <SectionCard eyebrow="Trace" title="Recent trace availability" description="Use trace explorer as the drill-down layer; cockpit does not duplicate it.">
                <ul className="key-value-list">
                  <li><span>Trace roots</span><strong>{snapshot.traceSummary?.total_roots ?? 0}</strong></li>
                  <li><span>Trace nodes</span><strong>{snapshot.traceSummary?.total_nodes ?? 0}</strong></li>
                  <li><span>Latest query</span><strong>{formatDate(snapshot.traceSummary?.latest_query_run?.created_at)}</strong></li>
                </ul>
                <div className="button-row">
                  <button className="secondary-button" type="button" onClick={() => navigate('/trace')}>Open trace explorer</button>
                </div>
              </SectionCard>

              <SectionCard eyebrow="Quick links" title="Specialized pages" description="Cockpit centralizes operations but keeps module pages as source of truth.">
                <div className="button-row">
                  {quickLinks.map((link) => (
                    <button key={link.path} className="ghost-button" type="button" onClick={() => navigate(link.path)}>{link.label}</button>
                  ))}
                </div>
                <p className="muted-text">Last cockpit refresh: {formatDate(snapshot.lastUpdatedAt)}.</p>
                {Object.keys(snapshot.failures).length > 0 ? <p className="warning-text">Partial data: {Object.entries(snapshot.failures).map(([key, value]) => `${key}: ${value}`).join(' | ')}</p> : null}
              </SectionCard>
            </div>
          </>
        )}
      </DataStateWrapper>
    </div>
  );
}
