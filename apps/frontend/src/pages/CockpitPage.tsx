import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import { getCockpitAttention, getCockpitQuickLinks, getCockpitSummary, runCockpitAction } from '../services/cockpit';
import { getAutonomyScenarioSummary } from '../services/autonomyScenario';
import {
  acknowledgeRuntimeTuningScope,
  clearRuntimeTuningScopeReview,
  getRuntimeTuningCockpitPanel,
  getRuntimeTuningCockpitPanelDetail,
  getRuntimeTuningContextDiffDetail,
  getRuntimeTuningInvestigation,
  getRuntimeTuningReviewAging,
  getRuntimeTuningReviewEscalation,
  getRuntimeTuningReviewActivity,
  getRuntimeTuningReviewQueue,
  getRuntimeTuningReviewStateDetail,
  getRuntimeTuningScopeTimeline,
  markRuntimeTuningScopeFollowup,
} from '../services/runtime';
import { getScanSummary } from '../services/scanAgent';
import type { CockpitAttentionItem, CockpitQuickActionId, CockpitSnapshot } from '../types/cockpit';
import type {
  RuntimeTuningCockpitPanel,
  RuntimeTuningCockpitPanelDetail,
  RuntimeTuningContextDiff,
  RuntimeTuningInvestigationPacket,
  RuntimeTuningReviewAgingItem,
  RuntimeTuningReviewAging,
  RuntimeTuningReviewQueue,
  RuntimeTuningReviewEscalation,
  RuntimeTuningReviewActivity,
  RuntimeTuningReviewAction,
  RuntimeTuningReviewState,
  RuntimeTuningScopeTimeline,
} from '../types/runtime';

const formatDate = (value: string | null | undefined) => (value ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : 'n/a');

const toneFromStatus = (status: string | null | undefined): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const normalized = (status ?? '').toUpperCase();
  if (['ACTIVE', 'READY', 'RUNNING', 'SUCCESS', 'PARITY_OK', 'COMPLETED', 'NORMAL', 'ACKNOWLEDGED'].includes(normalized)) return 'ready';
  if (['DEGRADED', 'PAUSED', 'WARNING', 'THROTTLED', 'BLOCK_NEW_ENTRIES', 'PARTIAL', 'CAUTION', 'FOLLOWUP', 'STALE', 'UNREVIEWED'].includes(normalized)) return 'pending';
  if (['FAILED', 'STOPPED', 'ROLLED_BACK', 'REJECTED', 'REMEDIATION_REQUIRED', 'RECERTIFICATION_REQUIRED'].includes(normalized)) return 'offline';
  return 'neutral';
};

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

const DEFAULT_TIMELINE_LIMIT = 3;
const REVIEW_STATUS_LABELS: Record<RuntimeTuningReviewState['effective_review_status'], string> = {
  UNREVIEWED: 'UNREVIEWED',
  ACKNOWLEDGED_CURRENT: 'ACKNOWLEDGED',
  FOLLOWUP_REQUIRED: 'FOLLOWUP',
  STALE_REVIEW: 'STALE',
};

const REVIEW_STATUS_HINTS: Record<RuntimeTuningReviewState['effective_review_status'], string> = {
  UNREVIEWED: 'No manual review yet',
  ACKNOWLEDGED_CURRENT: 'Current state acknowledged',
  FOLLOWUP_REQUIRED: 'Follow-up required',
  STALE_REVIEW: 'Review stale',
};

function isAgingQueueItem(item: RuntimeTuningReviewQueue['items'][number] | RuntimeTuningReviewAgingItem): item is RuntimeTuningReviewAgingItem {
  return 'age_bucket' in item && 'age_days' in item && 'aging_rank' in item;
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
  const [scanSummary, setScanSummary] = useState<Awaited<ReturnType<typeof getScanSummary>> | null>(null);
  const [tuningPanel, setTuningPanel] = useState<RuntimeTuningCockpitPanel | null>(null);
  const [reviewQueue, setReviewQueue] = useState<RuntimeTuningReviewQueue | null>(null);
  const [reviewAging, setReviewAging] = useState<RuntimeTuningReviewAging | null>(null);
  const [reviewEscalation, setReviewEscalation] = useState<RuntimeTuningReviewEscalation | null>(null);
  const [reviewActivity, setReviewActivity] = useState<RuntimeTuningReviewActivity | null>(null);
  const [reviewQueueUnresolvedOnly, setReviewQueueUnresolvedOnly] = useState(true);
  const [reviewQueueStatusFilter, setReviewQueueStatusFilter] = useState<RuntimeTuningReviewState['effective_review_status'] | 'ALL'>('ALL');
  const [reviewQueueAgeBucketFilter, setReviewQueueAgeBucketFilter] = useState<'ALL' | 'FRESH' | 'AGING' | 'OVERDUE'>('ALL');
  const [reviewEscalatedOnly, setReviewEscalatedOnly] = useState(true);
  const [reviewEscalationLevelFilter, setReviewEscalationLevelFilter] = useState<'ALL' | 'MONITOR' | 'ELEVATED' | 'URGENT'>('ALL');
  const [reviewActivityActionTypeFilter, setReviewActivityActionTypeFilter] = useState<RuntimeTuningReviewAction['action_type'] | 'ALL'>('ALL');
  const [reviewActivityLimit, setReviewActivityLimit] = useState<number>(10);
  const [reviewQueueError, setReviewQueueError] = useState<string | null>(null);
  const [attentionOnly, setAttentionOnly] = useState(true);
  const [tuningPanelError, setTuningPanelError] = useState<string | null>(null);
  const [openDiffScope, setOpenDiffScope] = useState<string | null>(null);
  const [openRunContextScope, setOpenRunContextScope] = useState<string | null>(null);
  const [openInvestigationScope, setOpenInvestigationScope] = useState<string | null>(null);
  const [queuedInvestigationScope, setQueuedInvestigationScope] = useState<string | null>(null);
  const [diffCache, setDiffCache] = useState<Record<string, RuntimeTuningContextDiff | null>>({});
  const [panelDetailCache, setPanelDetailCache] = useState<Record<string, RuntimeTuningCockpitPanelDetail | null>>({});
  const [investigationCache, setInvestigationCache] = useState<Record<string, RuntimeTuningInvestigationPacket | null>>({});
  const [timelineCache, setTimelineCache] = useState<Record<string, RuntimeTuningScopeTimeline | null>>({});
  const [timelineErrorCache, setTimelineErrorCache] = useState<Record<string, string | null>>({});
  const [timelineLoadingCache, setTimelineLoadingCache] = useState<Record<string, boolean>>({});
  const [timelineLimitByScope, setTimelineLimitByScope] = useState<Record<string, number>>({});
  const [timelineOnlyNonStableByScope, setTimelineOnlyNonStableByScope] = useState<Record<string, boolean>>({});
  const [reviewStateCache, setReviewStateCache] = useState<Record<string, RuntimeTuningReviewState | null>>({});
  const [reviewStateErrorCache, setReviewStateErrorCache] = useState<Record<string, string | null>>({});
  const [reviewActionLoadingByScope, setReviewActionLoadingByScope] = useState<Record<string, boolean>>({});
  const [reviewActionErrorByScope, setReviewActionErrorByScope] = useState<Record<string, string | null>>({});

  const loadCockpit = useCallback(async () => {
    setLoading(true);
    setError(null);
    setTuningPanelError(null);
    setReviewQueueError(null);
    try {
      const [response, scenarioSummary, scanSummaryResponse, tuningPanelResponse, reviewQueueResponse, reviewAgingResponse, reviewEscalationResponse, reviewActivityResponse] = await Promise.all([
        getCockpitSummary(),
        getAutonomyScenarioSummary(),
        getScanSummary(),
        getRuntimeTuningCockpitPanel({ attention_only: attentionOnly, limit: 5 }),
        getRuntimeTuningReviewQueue({
          unresolved_only: reviewQueueUnresolvedOnly,
          effective_review_status: reviewQueueStatusFilter === 'ALL' ? undefined : reviewQueueStatusFilter,
          limit: 8,
        }),
        getRuntimeTuningReviewAging({
          unresolved_only: reviewQueueUnresolvedOnly,
          age_bucket: reviewQueueAgeBucketFilter === 'ALL' ? undefined : reviewQueueAgeBucketFilter,
          limit: 8,
        }),
        getRuntimeTuningReviewEscalation({
          escalated_only: reviewEscalatedOnly,
          escalation_level: reviewEscalationLevelFilter === 'ALL' ? undefined : reviewEscalationLevelFilter,
          limit: 6,
        }),
        getRuntimeTuningReviewActivity({
          action_type: reviewActivityActionTypeFilter === 'ALL' ? undefined : reviewActivityActionTypeFilter,
          limit: reviewActivityLimit,
        }),
      ]);
      setSnapshot(response);
      setAutonomyScenarioSummary(scenarioSummary);
      setScanSummary(scanSummaryResponse);
      setTuningPanel(tuningPanelResponse);
      setReviewQueue(reviewQueueResponse);
      setReviewAging(reviewAgingResponse);
      setReviewEscalation(reviewEscalationResponse);
      setReviewActivity(reviewActivityResponse);
      setReviewStateCache({});
      setReviewStateErrorCache({});
    } catch (loadError) {
      setError(getErrorMessage(loadError, 'Could not load cockpit data.'));
      setSnapshot(null);
      setTuningPanelError(getErrorMessage(loadError, 'Could not load runtime tuning attention panel.'));
      setReviewQueueError(getErrorMessage(loadError, 'Could not load runtime tuning review queue.'));
    } finally {
      setLoading(false);
    }
  }, [
    attentionOnly,
    reviewActivityActionTypeFilter,
    reviewActivityLimit,
    reviewEscalatedOnly,
    reviewEscalationLevelFilter,
    reviewQueueAgeBucketFilter,
    reviewQueueStatusFilter,
    reviewQueueUnresolvedOnly,
  ]);

  useEffect(() => {
    void loadCockpit();
  }, [loadCockpit]);

  useEffect(() => {
    if (!tuningPanel?.items?.length) return;
    const missingScopes = tuningPanel.items
      .map((item) => item.source_scope)
      .filter((scope) => reviewStateCache[scope] === undefined && reviewStateErrorCache[scope] === undefined);
    if (missingScopes.length === 0) return;
    void Promise.all(
      missingScopes.map(async (scope) => {
        try {
          const reviewState = await getRuntimeTuningReviewStateDetail(scope);
          setReviewStateCache((current) => ({ ...current, [scope]: reviewState }));
          setReviewStateErrorCache((current) => ({ ...current, [scope]: null }));
        } catch (reviewError) {
          setReviewStateCache((current) => ({ ...current, [scope]: null }));
          setReviewStateErrorCache((current) => ({
            ...current,
            [scope]: getErrorMessage(reviewError, 'Could not load manual review state.'),
          }));
        }
      }),
    );
  }, [reviewStateCache, reviewStateErrorCache, tuningPanel]);

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

  const viewDiff = useCallback(
    async (sourceScope: string, snapshotId: number | null) => {
      setOpenDiffScope((current) => (current === sourceScope ? null : sourceScope));
      if (!snapshotId || diffCache[sourceScope]) return;
      try {
        const diff = await getRuntimeTuningContextDiffDetail(snapshotId);
        setDiffCache((current) => ({ ...current, [sourceScope]: diff }));
      } catch {
        setDiffCache((current) => ({ ...current, [sourceScope]: null }));
      }
    },
    [diffCache],
  );

  const viewRunContext = useCallback(
    async (sourceScope: string) => {
      setOpenRunContextScope((current) => (current === sourceScope ? null : sourceScope));
      if (panelDetailCache[sourceScope]) return;
      try {
        const detail = await getRuntimeTuningCockpitPanelDetail(sourceScope);
        setPanelDetailCache((current) => ({ ...current, [sourceScope]: detail }));
      } catch {
        setPanelDetailCache((current) => ({ ...current, [sourceScope]: null }));
      }
    },
    [panelDetailCache],
  );

  const loadScopeTimeline = useCallback(
    async (sourceScope: string, overrides?: { limit?: number; onlyNonStable?: boolean }) => {
      const limit = overrides?.limit ?? timelineLimitByScope[sourceScope] ?? DEFAULT_TIMELINE_LIMIT;
      const onlyNonStable = overrides?.onlyNonStable ?? timelineOnlyNonStableByScope[sourceScope] ?? false;

      setTimelineLimitByScope((current) => ({ ...current, [sourceScope]: limit }));
      setTimelineOnlyNonStableByScope((current) => ({ ...current, [sourceScope]: onlyNonStable }));
      setTimelineLoadingCache((current) => ({ ...current, [sourceScope]: true }));
      setTimelineErrorCache((current) => ({ ...current, [sourceScope]: null }));
      try {
        const timeline = await getRuntimeTuningScopeTimeline(sourceScope, {
          limit,
          include_stable: !onlyNonStable,
        });
        setTimelineCache((current) => ({ ...current, [sourceScope]: timeline }));
      } catch (timelineError) {
        setTimelineCache((current) => ({ ...current, [sourceScope]: null }));
        setTimelineErrorCache((current) => ({
          ...current,
          [sourceScope]: getErrorMessage(timelineError, 'Could not load recent timeline.'),
        }));
      } finally {
        setTimelineLoadingCache((current) => ({ ...current, [sourceScope]: false }));
      }
    },
    [timelineLimitByScope, timelineOnlyNonStableByScope],
  );

  const investigateScope = useCallback(async (sourceScope: string) => {
    setOpenInvestigationScope(sourceScope);
    if (!investigationCache[sourceScope]) {
      try {
        const packet = await getRuntimeTuningInvestigation(sourceScope);
        setInvestigationCache((current) => ({ ...current, [sourceScope]: packet }));
      } catch {
        setInvestigationCache((current) => ({ ...current, [sourceScope]: null }));
      }
    }

    if (!timelineCache[sourceScope] && !timelineLoadingCache[sourceScope]) {
      void loadScopeTimeline(sourceScope, { limit: DEFAULT_TIMELINE_LIMIT, onlyNonStable: false });
    }
  }, [investigationCache, loadScopeTimeline, timelineCache, timelineLoadingCache]);

  const runManualReviewAction = useCallback(
    async (sourceScope: string, action: 'ACKNOWLEDGE' | 'FOLLOWUP' | 'CLEAR') => {
      setReviewActionLoadingByScope((current) => ({ ...current, [sourceScope]: true }));
      setReviewActionErrorByScope((current) => ({ ...current, [sourceScope]: null }));
      try {
        if (action === 'ACKNOWLEDGE') {
          await acknowledgeRuntimeTuningScope(sourceScope);
        } else if (action === 'FOLLOWUP') {
          await markRuntimeTuningScopeFollowup(sourceScope);
        } else {
          await clearRuntimeTuningScopeReview(sourceScope);
        }
        const refreshedReviewState = await getRuntimeTuningReviewStateDetail(sourceScope);
        setReviewStateCache((current) => ({ ...current, [sourceScope]: refreshedReviewState }));
        setReviewStateErrorCache((current) => ({ ...current, [sourceScope]: null }));
      } catch (reviewActionError) {
        setReviewActionErrorByScope((current) => ({
          ...current,
          [sourceScope]: getErrorMessage(reviewActionError, 'Manual review action failed.'),
        }));
      } finally {
        setReviewActionLoadingByScope((current) => ({ ...current, [sourceScope]: false }));
      }
    },
    [],
  );

  useEffect(() => {
    if (!queuedInvestigationScope || !tuningPanel?.items?.length) return;
    if (!tuningPanel.items.some((item) => item.source_scope === queuedInvestigationScope)) return;
    void investigateScope(queuedInvestigationScope);
    setQueuedInvestigationScope(null);
  }, [investigateScope, queuedInvestigationScope, tuningPanel]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operator cockpit"
        title="/cockpit"
        description="Single-pane operational command center for manual-first paper/sandbox supervision. Centralizes posture, incidents, governance, and trace-oriented drill-down without replacing specialized pages."
        actions={<div className="button-row"><button className="secondary-button" type="button" onClick={() => void loadCockpit()}>Refresh cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/scan-agent')}>Scan agent</button><button className="ghost-button" type="button" onClick={() => navigate('/autonomy-seed')}>Autonomy seed</button><button className="ghost-button" type="button" onClick={() => navigate('/autonomy-seed-review')}>Seed review</button><button className="ghost-button" type="button" onClick={() => navigate('/evaluation')}>Evaluation</button><button className="ghost-button" type="button" onClick={() => navigate('/tuning')}>Tuning</button><button className="ghost-button" type="button" onClick={() => navigate('/experiments')}>Experiments</button></div>}
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

              <SectionCard eyebrow="Scan intelligence" title="Narrative scan summary" description="Compact scan-agent filter summary for quick handoff posture checks.">
                <ul className="key-value-list">
                  <li><span>Signals</span><strong>{scanSummary?.signal_count ?? 0}</strong></li>
                  <li><span>Shortlisted</span><strong>{scanSummary?.shortlisted_signal_count ?? 0}</strong></li>
                  <li><span>Watch</span><strong>{scanSummary?.watch_signal_count ?? 0}</strong></li>
                  <li><span>Ignored</span><strong>{scanSummary?.ignored_signal_count ?? 0}</strong></li>
                </ul>
                <div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/scan-agent')}>Open scan agent board</button></div>
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
                <div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/promotion')}>Open promotion</button><button className="secondary-button" type="button" onClick={() => navigate('/certification')}>Open certification</button><button className="secondary-button" type="button" onClick={() => navigate('/promotion')}>Open rollout execution board</button><button className="secondary-button" type="button" onClick={() => navigate('/rollout')}>Open rollout</button><button className="secondary-button" type="button" onClick={() => navigate('/policy-rollout')}>Open policy rollout</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy')}>Open autonomy</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-rollout')}>Open autonomy rollout</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-roadmap')}>Open autonomy roadmap</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-scenarios')}>Open autonomy scenarios</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-program')}>Open autonomy program</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-scheduler')}>Open autonomy scheduler</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-launch')}>Open autonomy launch</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-activation')}>Open autonomy activation</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-operations')}>Open autonomy operations</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-interventions')}>Open autonomy interventions</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-recovery')}>Open autonomy recovery</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-disposition')}>Open autonomy disposition</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-closeout')}>Open autonomy closeout</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-followup')}>Open autonomy followup</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-feedback')}>Open autonomy feedback</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-insights')}>Open autonomy insights</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-advisory')}>Open autonomy advisory</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-advisory-resolution')}>Open advisory resolution</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-backlog')}>Open autonomy backlog</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-intake')}>Open autonomy intake</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-planning-review')}>Open planning review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-decision')}>Open autonomy decision</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-package-review')}>Open package review</button><button className="secondary-button" type="button" onClick={() => navigate('/champion-challenger')}>Open C/C</button></div>
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

            <SectionCard
              eyebrow="Runtime tuning"
              title="Runtime Tuning Review Queue"
              description="Compact human-review queue combining manual review state with existing technical attention priority."
            >
              <div className="button-row">
                <label className="muted-text">
                  <input
                    type="checkbox"
                    checked={reviewQueueUnresolvedOnly}
                    onChange={(event) => setReviewQueueUnresolvedOnly(event.target.checked)}
                  />{' '}
                  Unresolved only
                </label>
                <label className="muted-text">
                  Status:{' '}
                  <select value={reviewQueueStatusFilter} onChange={(event) => setReviewQueueStatusFilter(event.target.value as RuntimeTuningReviewState['effective_review_status'] | 'ALL')}>
                    <option value="ALL">All</option>
                    <option value="UNREVIEWED">UNREVIEWED</option>
                    <option value="FOLLOWUP_REQUIRED">FOLLOWUP_REQUIRED</option>
                    <option value="STALE_REVIEW">STALE_REVIEW</option>
                    <option value="ACKNOWLEDGED_CURRENT">ACKNOWLEDGED_CURRENT</option>
                  </select>
                </label>
                <label className="muted-text">
                  Aging:{' '}
                  <select value={reviewQueueAgeBucketFilter} onChange={(event) => setReviewQueueAgeBucketFilter(event.target.value as 'ALL' | 'FRESH' | 'AGING' | 'OVERDUE')}>
                    <option value="ALL">All</option>
                    <option value="OVERDUE">OVERDUE</option>
                    <option value="AGING">AGING</option>
                    <option value="FRESH">FRESH</option>
                  </select>
                </label>
                <label className="muted-text">
                  <input
                    type="checkbox"
                    checked={reviewEscalatedOnly}
                    onChange={(event) => setReviewEscalatedOnly(event.target.checked)}
                  />{' '}
                  Escalated only
                </label>
                <label className="muted-text">
                  Escalation:{' '}
                  <select value={reviewEscalationLevelFilter} onChange={(event) => setReviewEscalationLevelFilter(event.target.value as 'ALL' | 'MONITOR' | 'ELEVATED' | 'URGENT')}>
                    <option value="ALL">All</option>
                    <option value="URGENT">URGENT</option>
                    <option value="ELEVATED">ELEVATED</option>
                    <option value="MONITOR">MONITOR</option>
                  </select>
                </label>
                <label className="muted-text">
                  Activity action:{' '}
                  <select
                    value={reviewActivityActionTypeFilter}
                    onChange={(event) => setReviewActivityActionTypeFilter(event.target.value as RuntimeTuningReviewAction['action_type'] | 'ALL')}
                  >
                    <option value="ALL">All</option>
                    <option value="ACKNOWLEDGE_CURRENT">ACKNOWLEDGE_CURRENT</option>
                    <option value="MARK_FOLLOWUP_REQUIRED">MARK_FOLLOWUP_REQUIRED</option>
                    <option value="CLEAR_REVIEW_STATE">CLEAR_REVIEW_STATE</option>
                  </select>
                </label>
                <label className="muted-text">
                  Activity limit:{' '}
                  <select value={reviewActivityLimit} onChange={(event) => setReviewActivityLimit(Number(event.target.value))}>
                    <option value={5}>5</option>
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                  </select>
                </label>
              </div>
              {reviewQueueError ? <p className="warning-text">{reviewQueueError}</p> : null}
              {!reviewQueue ? null : (
                <>
                  {!reviewEscalation ? null : (
                    <div className="subsection">
                      <p className="section-label">Review Escalation</p>
                      <ul className="key-value-list">
                        <li><span>Urgent</span><strong>{reviewEscalation.urgent_count}</strong></li>
                        <li><span>Elevated</span><strong>{reviewEscalation.elevated_count}</strong></li>
                        <li><span>Monitor</span><strong>{reviewEscalation.monitor_count}</strong></li>
                        <li><span>Highest escalation scope</span><strong>{reviewEscalation.highest_escalation_scope ?? 'n/a'}</strong></li>
                      </ul>
                      <p className={reviewEscalation.urgent_count > 0 ? 'warning-text' : 'muted-text'}>{reviewEscalation.escalation_summary}</p>
                      {reviewEscalation.items.length === 0 ? (
                        <p className="muted-text">No escalated items for the current filters.</p>
                      ) : (
                        <div className="cockpit-attention-list">
                          {reviewEscalation.items.map((item) => (
                            <article key={`escalation-${item.source_scope}`} className="cockpit-attention-item">
                              <div>
                                <p className="section-label">
                                  #{item.escalation_rank} · {item.escalation_level} · {item.effective_review_status} · {item.age_bucket} ({item.age_days}d)
                                </p>
                                <h3>{item.source_scope}</h3>
                                <p>
                                  <strong>{item.attention_priority}</strong> · {item.review_summary || item.technical_summary}
                                </p>
                                {item.requires_immediate_attention ? <p className="warning-text">Requires immediate attention.</p> : null}
                              </div>
                              <div className="button-row">
                                <button
                                  className="secondary-button"
                                  type="button"
                                  onClick={() => {
                                    if (tuningPanel?.items?.some((panelItem) => panelItem.source_scope === item.source_scope)) {
                                      void investigateScope(item.source_scope);
                                      return;
                                    }
                                    setAttentionOnly(false);
                                    setQueuedInvestigationScope(item.source_scope);
                                  }}
                                >
                                  Open review
                                </button>
                                <button className="ghost-button" type="button" onClick={() => navigate(item.runtime_investigation_deep_link)}>Open in runtime</button>
                              </div>
                            </article>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  {!reviewAging ? null : (
                    <div className="subsection">
                      <p className="section-label">Review Aging</p>
                      <ul className="key-value-list">
                        <li><span>Fresh</span><strong>{reviewAging.fresh_count}</strong></li>
                        <li><span>Aging</span><strong>{reviewAging.aging_count}</strong></li>
                        <li><span>Overdue</span><strong>{reviewAging.overdue_count}</strong></li>
                        <li><span>Highest urgency scope</span><strong>{reviewAging.highest_urgency_scope ?? 'n/a'}</strong></li>
                      </ul>
                      <p className={reviewAging.overdue_count > 0 ? 'warning-text' : 'muted-text'}>{reviewAging.aging_summary}</p>
                    </div>
                  )}
                  {!reviewActivity ? null : (
                    <div className="subsection">
                      <p className="section-label">Recent Review Activity</p>
                      <ul className="key-value-list">
                        <li><span>Recent actions</span><strong>{reviewActivity.activity_count}</strong></li>
                        <li><span>Latest action at</span><strong>{formatDate(reviewActivity.latest_action_at)}</strong></li>
                        <li><span>Summary</span><strong>{reviewActivity.activity_summary}</strong></li>
                      </ul>
                      {reviewActivity.items.length === 0 ? (
                        <p className="muted-text">No review actions match the current activity filters.</p>
                      ) : (
                        <div className="cockpit-attention-list">
                          {reviewActivity.items.map((item, index) => (
                            <article key={`activity-${item.source_scope}-${item.created_at}-${index}`} className="cockpit-attention-item">
                              <div>
                                <p className="section-label">{item.activity_label} · {item.resulting_review_status}</p>
                                <h3>{item.source_scope}</h3>
                                <p>{formatDate(item.created_at)} · {item.action_type}</p>
                                <p className="muted-text">{item.scope_review_summary}</p>
                              </div>
                              <div className="button-row">
                                <button
                                  className="secondary-button"
                                  type="button"
                                  onClick={() => {
                                    if (tuningPanel?.items?.some((panelItem) => panelItem.source_scope === item.source_scope)) {
                                      void investigateScope(item.source_scope);
                                      return;
                                    }
                                    setAttentionOnly(false);
                                    setQueuedInvestigationScope(item.source_scope);
                                  }}
                                >
                                  Open review
                                </button>
                                <button className="ghost-button" type="button" onClick={() => navigate(item.runtime_investigation_deep_link)}>Open in runtime</button>
                              </div>
                            </article>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  <ul className="key-value-list">
                    <li><span>Queue scopes</span><strong>{reviewQueue.queue_count}</strong></li>
                    <li><span>Unreviewed</span><strong>{reviewQueue.unreviewed_count}</strong></li>
                    <li><span>Follow-up</span><strong>{reviewQueue.followup_count}</strong></li>
                    <li><span>Stale</span><strong>{reviewQueue.stale_count}</strong></li>
                  </ul>
                  <p className="muted-text">{reviewQueue.queue_summary}</p>
                  {(reviewAging?.items ?? reviewQueue.items).length === 0 ? (
                    <EmptyState eyebrow="Runtime tuning queue" title="No queue items" description="No scopes match the current unresolved/status filters." />
                  ) : (
                    <div className="cockpit-attention-list">
                      {(reviewAging?.items ?? reviewQueue.items).map((item) => (
                        <article key={item.source_scope} className="cockpit-attention-item">
                          <div>
                            <p className="section-label">
                              #{isAgingQueueItem(item) ? item.aging_rank : item.queue_rank} · {item.effective_review_status}{' '}
                              {isAgingQueueItem(item) ? `· ${item.age_bucket} (${item.age_days}d)` : null}
                            </p>
                            <h3>{item.source_scope}</h3>
                            <p>
                              <strong>{item.attention_priority}</strong> · {item.review_summary || item.technical_summary}
                            </p>
                            <p className="muted-text">{item.technical_summary}</p>
                            {isAgingQueueItem(item) && item.overdue ? (
                              <p className="warning-text">Overdue review item. Prioritize manual action for this scope.</p>
                            ) : null}
                            {(item.effective_review_status === 'FOLLOWUP_REQUIRED' || item.effective_review_status === 'STALE_REVIEW') ? (
                              <p className="warning-text">Requires explicit human follow-up before this scope is considered current.</p>
                            ) : null}
                          </div>
                            <div className="button-row">
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => {
                                if (tuningPanel?.items?.some((panelItem) => panelItem.source_scope === item.source_scope)) {
                                  void investigateScope(item.source_scope);
                                  return;
                                }
                                setAttentionOnly(false);
                                setQueuedInvestigationScope(item.source_scope);
                              }}
                            >
                              Open review
                            </button>
                            <button className="ghost-button" type="button" onClick={() => navigate(item.runtime_investigation_deep_link)}>Open in runtime</button>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </>
              )}
            </SectionCard>

            <SectionCard
              eyebrow="Runtime tuning"
              title="Runtime Tuning Attention"
              description="Read-only handoff from runtime_governor review board for high-signal tuning scopes needing operator attention."
            >
              <div className="button-row">
                <label className="muted-text">
                  <input type="checkbox" checked={attentionOnly} onChange={(event) => setAttentionOnly(event.target.checked)} /> Attention only
                </label>
                <button className="secondary-button" type="button" onClick={() => navigate('/runtime')}>Open full runtime view</button>
              </div>
              {tuningPanelError ? <p className="warning-text">{tuningPanelError}</p> : null}
              {!tuningPanel ? null : (
                <>
                  <ul className="key-value-list">
                    <li><span>Scopes needing attention</span><strong>{tuningPanel.attention_scope_count}</strong></li>
                    <li><span>Highest priority scope</span><strong>{tuningPanel.highest_priority_scope ?? 'n/a'}</strong></li>
                    <li><span>Highest priority status</span><strong>{tuningPanel.highest_priority_status ?? 'n/a'}</strong></li>
                  </ul>
                  <p className="muted-text">{tuningPanel.panel_summary}</p>
                  {tuningPanel.items.length === 0 ? (
                    <EmptyState eyebrow="Runtime tuning" title="No runtime tuning attention required" description="All currently tracked scopes are stable for cockpit attention filtering." />
                  ) : (
                    <div className="cockpit-attention-list">
                      {tuningPanel.items.map((item) => {
                        const detail = panelDetailCache[item.source_scope];
                        const diff = diffCache[item.source_scope];
                        const isDiffOpen = openDiffScope === item.source_scope;
                        const isRunContextOpen = openRunContextScope === item.source_scope;
                        const isInvestigationOpen = openInvestigationScope === item.source_scope;
                        const investigation = investigationCache[item.source_scope];
                        const timeline = timelineCache[item.source_scope];
                        const timelineLoading = timelineLoadingCache[item.source_scope] ?? false;
                        const timelineError = timelineErrorCache[item.source_scope] ?? null;
                        const timelineOnlyNonStable = timelineOnlyNonStableByScope[item.source_scope] ?? false;
                        const timelineLimit = timelineLimitByScope[item.source_scope] ?? DEFAULT_TIMELINE_LIMIT;
                        const reviewState = reviewStateCache[item.source_scope];
                        const reviewStateError = reviewStateErrorCache[item.source_scope] ?? null;
                        const reviewStatus = reviewState?.effective_review_status ?? 'UNREVIEWED';
                        const reviewActionLoading = reviewActionLoadingByScope[item.source_scope] ?? false;
                        const reviewActionError = reviewActionErrorByScope[item.source_scope] ?? null;
                        return (
                          <article key={item.source_scope} className="cockpit-attention-item">
                            <div>
                              <p className="section-label">{item.attention_priority}</p>
                              <h3>{item.source_scope}</h3>
                              <p>{item.board_summary}</p>
                              <p className="muted-text">
                                <strong>Manual review:</strong>{' '}
                                <StatusBadge tone={toneFromStatus(reviewStatus)}>{REVIEW_STATUS_LABELS[reviewStatus]}</StatusBadge>{' '}
                                · {reviewState?.review_summary ?? REVIEW_STATUS_HINTS[reviewStatus]}
                              </p>
                              <p className="muted-text"><strong>Drift:</strong> {item.drift_status} | <strong>Diff:</strong> {item.latest_diff_summary ?? 'No comparable diff'}</p>
                              {reviewStateError ? <p className="warning-text">{reviewStateError}</p> : null}
                            </div>
                            <div className="button-row">
                              <button className="secondary-button" type="button" onClick={() => navigate(item.runtime_deep_link)}>Open in runtime</button>
                              <button className="secondary-button" type="button" onClick={() => void investigateScope(item.source_scope)}>Investigate</button>
                              <button className="ghost-button" type="button" onClick={() => void viewDiff(item.source_scope, item.latest_diff_snapshot_id)}>View diff</button>
                              <button className="ghost-button" type="button" onClick={() => void viewRunContext(item.source_scope)}>View run context</button>
                            </div>
                            {isInvestigationOpen ? (
                              <div className="subsection">
                                <p className="section-label">Compact investigation</p>
                                {!investigation ? (
                                  <p className="warning-text">Could not load investigation packet.</p>
                                ) : (
                                  <>
                                    <ul className="key-value-list">
                                      <li><span>Scope</span><strong>{investigation.source_scope}</strong></li>
                                      <li><span>Summary</span><strong>{investigation.investigation_summary}</strong></li>
                                      <li><span>Priority</span><strong>{investigation.attention_priority}</strong></li>
                                      <li><span>Alert status</span><strong>{investigation.alert_status}</strong></li>
                                      <li><span>Drift status</span><strong>{investigation.drift_status}</strong></li>
                                      <li><span>Review reason codes</span><strong>{investigation.review_reason_codes.join(', ') || 'n/a'}</strong></li>
                                    </ul>
                                    <div className="subsection">
                                      <p className="section-label">Recent Timeline</p>
                                      <div className="button-row">
                                        <label className="muted-text">
                                          <input
                                            type="checkbox"
                                            checked={timelineOnlyNonStable}
                                            onChange={(event) => {
                                              void loadScopeTimeline(item.source_scope, {
                                                limit: timelineLimit,
                                                onlyNonStable: event.target.checked,
                                              });
                                            }}
                                          />{' '}
                                          Show only non-stable
                                        </label>
                                        <button
                                          className="ghost-button"
                                          type="button"
                                          onClick={() => void loadScopeTimeline(item.source_scope, {
                                            limit: timelineLimit * 2,
                                            onlyNonStable: timelineOnlyNonStable,
                                          })}
                                        >
                                          Show more timeline
                                        </button>
                                      </div>
                                      {timelineLoading ? <p className="muted-text">Loading recent timeline...</p> : null}
                                      {timelineError ? <p className="warning-text">{timelineError}</p> : null}
                                      {!timelineLoading && !timelineError && timeline ? (
                                        <>
                                          <p className="muted-text">{timeline.timeline_summary}</p>
                                          <ul className="key-value-list">
                                            <li><span>Recently stable</span><strong>{timeline.is_recently_stable ? 'Yes' : 'No'}</strong></li>
                                            <li><span>Recent profile shift</span><strong>{timeline.has_recent_profile_shift ? 'Yes' : 'No'}</strong></li>
                                            <li><span>Recent review now</span><strong>{timeline.has_recent_review_now ? 'Yes' : 'No'}</strong></li>
                                          </ul>
                                          <ul className="key-value-list">
                                            {timeline.entries.map((entry) => (
                                              <li key={entry.snapshot_id}>
                                                <span>
                                                  {formatDate(entry.created_at)} · {entry.timeline_label} · {entry.drift_status} / {entry.alert_status}
                                                </span>
                                                <strong>
                                                  {entry.diff_summary || 'No comparable diff summary.'} · Fields {entry.changed_field_count} · Guardrails {entry.changed_guardrail_count}
                                                  {entry.correlated_run_id ? ` · Run ${entry.correlated_run_id}` : ''}
                                                </strong>
                                              </li>
                                            ))}
                                          </ul>
                                        </>
                                      ) : null}
                                    </div>
                                    <div className="subsection">
                                      <p className="section-label">Manual Review</p>
                                      <ul className="key-value-list">
                                        <li><span>effective_review_status</span><strong>{reviewState?.effective_review_status ?? 'UNREVIEWED'}</strong></li>
                                        <li><span>review_summary</span><strong>{reviewState?.review_summary ?? REVIEW_STATUS_HINTS.UNREVIEWED}</strong></li>
                                        <li><span>last_action_type</span><strong>{reviewState?.last_action_type ?? 'n/a'}</strong></li>
                                        <li><span>last_action_at</span><strong>{formatDate(reviewState?.last_action_at)}</strong></li>
                                        <li><span>has_newer_snapshot_than_reviewed</span><strong>{reviewState?.has_newer_snapshot_than_reviewed ? 'Yes' : 'No'}</strong></li>
                                      </ul>
                                      <div className="button-row">
                                        <button className="secondary-button" type="button" disabled={reviewActionLoading} onClick={() => void runManualReviewAction(item.source_scope, 'ACKNOWLEDGE')}>Acknowledge current</button>
                                        <button className="secondary-button" type="button" disabled={reviewActionLoading} onClick={() => void runManualReviewAction(item.source_scope, 'FOLLOWUP')}>Mark follow-up</button>
                                        <button className="ghost-button" type="button" disabled={reviewActionLoading} onClick={() => void runManualReviewAction(item.source_scope, 'CLEAR')}>Clear review state</button>
                                      </div>
                                      {reviewActionError ? <p className="warning-text">{reviewActionError}</p> : null}
                                    </div>
                                    <div className="subsection">
                                      <p className="section-label">Diff preview</p>
                                      {!investigation.has_comparable_diff ? (
                                        <p>No comparable diff.</p>
                                      ) : (
                                        <ul className="key-value-list">
                                          <li><span>Latest diff summary</span><strong>{investigation.latest_diff_summary ?? 'n/a'}</strong></li>
                                          <li><span>Changed fields</span><strong>{investigation.changed_field_count}</strong></li>
                                          <li><span>Changed guardrails</span><strong>{investigation.changed_guardrail_count}</strong></li>
                                          <li><span>Fields preview</span><strong>{investigation.changed_fields_preview.join(', ') || 'n/a'}</strong></li>
                                          <li><span>Guardrail preview</span><strong>{investigation.changed_guardrail_fields_preview.join(', ') || 'n/a'}</strong></li>
                                        </ul>
                                      )}
                                    </div>
                                    <div className="subsection">
                                      <p className="section-label">Run context preview</p>
                                      {!investigation.has_correlated_run ? (
                                        <p>No correlated run.</p>
                                      ) : (
                                        <ul className="key-value-list">
                                          <li><span>Run id</span><strong>{investigation.correlated_run_id}</strong></li>
                                          <li><span>Timestamp</span><strong>{formatDate(investigation.correlated_run_timestamp)}</strong></li>
                                          <li><span>Profile</span><strong>{investigation.correlated_profile_name ?? 'n/a'}</strong></li>
                                          <li><span>Fingerprint</span><strong>{investigation.correlated_profile_fingerprint ?? 'n/a'}</strong></li>
                                        </ul>
                                      )}
                                    </div>
                                    <div className="button-row">
                                      <button className="secondary-button" type="button" onClick={() => navigate(`/runtime?tuningScope=${encodeURIComponent(investigation.source_scope)}&investigate=1`)}>Open full runtime investigation</button>
                                      <button className="ghost-button" type="button" onClick={() => setOpenInvestigationScope(null)}>Hide investigation</button>
                                    </div>
                                  </>
                                )}
                              </div>
                            ) : null}
                            {isDiffOpen ? (
                              <div className="subsection">
                                <p className="section-label">Diff quick view</p>
                                {!item.latest_diff_snapshot_id ? <p>No comparable diff.</p> : !diff ? <p>No comparable diff.</p> : <p>{diff.diff_summary}</p>}
                              </div>
                            ) : null}
                            {isRunContextOpen ? (
                              <div className="subsection">
                                <p className="section-label">Run context quick view</p>
                                {!item.correlated_run_id ? <p>No correlated run.</p> : (
                                  <ul className="key-value-list">
                                    <li><span>Run id</span><strong>{item.correlated_run_id}</strong></li>
                                    <li><span>Timestamp</span><strong>{formatDate(item.correlated_run_timestamp)}</strong></li>
                                    <li><span>Profile</span><strong>{item.correlated_profile_name ?? 'n/a'}</strong></li>
                                    <li><span>Fingerprint</span><strong>{detail?.correlated_profile_fingerprint ?? item.correlated_profile_fingerprint ?? 'n/a'}</strong></li>
                                  </ul>
                                )}
                              </div>
                            ) : null}
                          </article>
                        );
                      })}
                    </div>
                  )}
                </>
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
