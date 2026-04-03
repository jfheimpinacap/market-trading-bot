import { useCallback, useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import {
  getAutonomousHeartbeatDecisions,
  getAutonomousHeartbeatRecommendations,
  getAutonomousHeartbeatRuns,
  getAutonomousHeartbeatSummary,
  getAutonomousRunnerState,
  getAutonomousSessionSummary,
  getAutonomousSessions,
  getAutonomousTickDispatchAttempts,
  getProfileRecommendations,
  getProfileSelectionSummary,
  getProfileSwitchDecisions,
  getProfileSwitchRecords,
  getScheduleProfiles,
  getSessionAnomalies,
  getSessionContextReviews,
  getSessionHealthRecommendations,
  getSessionHealthSnapshots,
  getSessionHealthSummary,
  getSessionRecoveryBlockers,
  getSessionRecoveryRecommendations,
  getSessionResumeRecords,
  getSessionRecoverySnapshots,
  getSessionRecoverySummary,
  getSessionResumeDecisions,
  getGlobalCapacitySnapshots,
  getSessionAdmissionReviews,
  getSessionAdmissionDecisions,
  getSessionAdmissionRecommendations,
  getSessionAdmissionSummary,
  getGovernanceReviewItems,
  getGovernanceReviewResolutions,
  getGovernanceReviewRecommendations,
  getGovernanceReviewSummary,
  resolveGovernanceReviewItem,
  runSessionAdmissionReview,
  runGovernanceReviewQueue,
  getSessionInterventionDecisions,
  getSessionTimingDecisions,
  getSessionTimingRecommendations,
  getSessionTimingSnapshots,
  getSessionTimingSummary,
  getStopConditionEvaluations,
  pauseAutonomousRunner,
  resumeAutonomousRunner,
  runSessionTimingReview,
  runSessionHealthReview,
  runSessionRecoveryReview,
  runSessionRecoveryReviewSafeAutoApply,
  applySessionResume,
  runProfileSelectionReview,
  runAutonomousHeartbeat,
  startAutonomousRunner,
  stopAutonomousRunner,
} from '../../services/missionControl';
import type {
  AutonomousHeartbeatDecision,
  AutonomousHeartbeatRecommendation,
  AutonomousHeartbeatRun,
  AutonomousHeartbeatSummary,
  AutonomousRunnerState,
  AutonomousRuntimeSession,
  AutonomousSessionAnomaly,
  AutonomousProfileRecommendation,
  AutonomousProfileSwitchDecision,
  AutonomousProfileSwitchRecord,
  AutonomousScheduleProfile,
  AutonomousSessionContextReview,
  AutonomousSessionHealthRecommendation,
  AutonomousSessionHealthSnapshot,
  AutonomousSessionInterventionDecision,
  AutonomousSessionTimingSnapshot,
  AutonomousStopConditionEvaluation,
  AutonomousTimingDecision,
  AutonomousTimingRecommendation,
  AutonomousSessionSummary,
  SessionTimingSummary,
  ProfileSelectionSummary,
  SessionHealthSummary,
  AutonomousRecoveryBlocker,
  AutonomousResumeDecision,
  AutonomousSessionRecoveryRecommendation,
  AutonomousResumeRecord,
  AutonomousSessionRecoverySnapshot,
  SessionRecoverySummary,
  AutonomousTickDispatchAttempt,
  AutonomousGlobalCapacitySnapshot,
  AutonomousSessionAdmissionReview,
  AutonomousSessionAdmissionDecision,
  AutonomousSessionAdmissionRecommendation,
  SessionAdmissionSummary,
  GovernanceReviewItem,
  GovernanceReviewRecommendation,
  GovernanceReviewResolution,
  GovernanceReviewSummary,
} from '../../types/missionControl';

export function MissionControlPage() {
  const [sessions, setSessions] = useState<AutonomousRuntimeSession[]>([]);
  const [runnerState, setRunnerState] = useState<AutonomousRunnerState | null>(null);
  const [heartbeatRuns, setHeartbeatRuns] = useState<AutonomousHeartbeatRun[]>([]);
  const [decisions, setDecisions] = useState<AutonomousHeartbeatDecision[]>([]);
  const [dispatchAttempts, setDispatchAttempts] = useState<AutonomousTickDispatchAttempt[]>([]);
  const [recommendations, setRecommendations] = useState<AutonomousHeartbeatRecommendation[]>([]);
  const [summary, setSummary] = useState<AutonomousSessionSummary | null>(null);
  const [heartbeatSummary, setHeartbeatSummary] = useState<AutonomousHeartbeatSummary | null>(null);
  const [scheduleProfiles, setScheduleProfiles] = useState<AutonomousScheduleProfile[]>([]);
  const [timingSnapshots, setTimingSnapshots] = useState<AutonomousSessionTimingSnapshot[]>([]);
  const [stopEvaluations, setStopEvaluations] = useState<AutonomousStopConditionEvaluation[]>([]);
  const [timingDecisions, setTimingDecisions] = useState<AutonomousTimingDecision[]>([]);
  const [timingRecommendations, setTimingRecommendations] = useState<AutonomousTimingRecommendation[]>([]);
  const [timingSummary, setTimingSummary] = useState<SessionTimingSummary | null>(null);
  const [contextReviews, setContextReviews] = useState<AutonomousSessionContextReview[]>([]);
  const [profileSwitchDecisions, setProfileSwitchDecisions] = useState<AutonomousProfileSwitchDecision[]>([]);
  const [profileSwitchRecords, setProfileSwitchRecords] = useState<AutonomousProfileSwitchRecord[]>([]);
  const [profileRecommendations, setProfileRecommendations] = useState<AutonomousProfileRecommendation[]>([]);
  const [profileSelectionSummary, setProfileSelectionSummary] = useState<ProfileSelectionSummary | null>(null);
  const [healthSnapshots, setHealthSnapshots] = useState<AutonomousSessionHealthSnapshot[]>([]);
  const [healthAnomalies, setHealthAnomalies] = useState<AutonomousSessionAnomaly[]>([]);
  const [healthDecisions, setHealthDecisions] = useState<AutonomousSessionInterventionDecision[]>([]);
  const [healthRecommendations, setHealthRecommendations] = useState<AutonomousSessionHealthRecommendation[]>([]);
  const [healthSummary, setHealthSummary] = useState<SessionHealthSummary | null>(null);
  const [recoverySnapshots, setRecoverySnapshots] = useState<AutonomousSessionRecoverySnapshot[]>([]);
  const [recoveryBlockers, setRecoveryBlockers] = useState<AutonomousRecoveryBlocker[]>([]);
  const [resumeDecisions, setResumeDecisions] = useState<AutonomousResumeDecision[]>([]);
  const [recoveryRecommendations, setRecoveryRecommendations] = useState<AutonomousSessionRecoveryRecommendation[]>([]);
  const [resumeRecords, setResumeRecords] = useState<AutonomousResumeRecord[]>([]);
  const [recoverySummary, setRecoverySummary] = useState<SessionRecoverySummary | null>(null);
  const [capacitySnapshots, setCapacitySnapshots] = useState<AutonomousGlobalCapacitySnapshot[]>([]);
  const [admissionReviews, setAdmissionReviews] = useState<AutonomousSessionAdmissionReview[]>([]);
  const [admissionDecisions, setAdmissionDecisions] = useState<AutonomousSessionAdmissionDecision[]>([]);
  const [admissionRecommendations, setAdmissionRecommendations] = useState<AutonomousSessionAdmissionRecommendation[]>([]);
  const [admissionSummary, setAdmissionSummary] = useState<SessionAdmissionSummary | null>(null);
  const [governanceSummary, setGovernanceSummary] = useState<GovernanceReviewSummary | null>(null);
  const [governanceItems, setGovernanceItems] = useState<GovernanceReviewItem[]>([]);
  const [governanceRecommendations, setGovernanceRecommendations] = useState<GovernanceReviewRecommendation[]>([]);
  const [governanceResolutions, setGovernanceResolutions] = useState<GovernanceReviewResolution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const latestHeartbeat = useMemo(() => heartbeatRuns[0] ?? null, [heartbeatRuns]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [loadedSessions, loadedSummary, loadedRunnerState, loadedRuns, loadedDecisions, loadedDispatches, loadedRecommendations, loadedHeartbeatSummary, loadedScheduleProfiles, loadedTimingSnapshots, loadedStopEvaluations, loadedTimingDecisions, loadedTimingRecommendations, loadedTimingSummary, loadedContextReviews, loadedProfileSwitchDecisions, loadedProfileSwitchRecords, loadedProfileRecommendations, loadedProfileSelectionSummary, loadedHealthSnapshots, loadedHealthAnomalies, loadedHealthDecisions, loadedHealthRecommendations, loadedHealthSummary, loadedRecoverySnapshots, loadedRecoveryBlockers, loadedResumeDecisions, loadedRecoveryRecommendations, loadedResumeRecords, loadedRecoverySummary, loadedCapacitySnapshots, loadedAdmissionReviews, loadedAdmissionDecisions, loadedAdmissionRecommendations, loadedAdmissionSummary, loadedGovernanceSummary, loadedGovernanceItems, loadedGovernanceRecommendations, loadedGovernanceResolutions] = await Promise.all([
        getAutonomousSessions(),
        getAutonomousSessionSummary(),
        getAutonomousRunnerState(),
        getAutonomousHeartbeatRuns(),
        getAutonomousHeartbeatDecisions(),
        getAutonomousTickDispatchAttempts(),
        getAutonomousHeartbeatRecommendations(),
        getAutonomousHeartbeatSummary(),
        getScheduleProfiles(),
        getSessionTimingSnapshots(),
        getStopConditionEvaluations(),
        getSessionTimingDecisions(),
        getSessionTimingRecommendations(),
        getSessionTimingSummary(),
        getSessionContextReviews(),
        getProfileSwitchDecisions(),
        getProfileSwitchRecords(),
        getProfileRecommendations(),
        getProfileSelectionSummary(),
        getSessionHealthSnapshots(),
        getSessionAnomalies(),
        getSessionInterventionDecisions(),
        getSessionHealthRecommendations(),
        getSessionHealthSummary(),
        getSessionRecoverySnapshots(),
        getSessionRecoveryBlockers(),
        getSessionResumeDecisions(),
        getSessionRecoveryRecommendations(),
        getSessionResumeRecords(),
        getSessionRecoverySummary(),
        getGlobalCapacitySnapshots(),
        getSessionAdmissionReviews(),
        getSessionAdmissionDecisions(),
        getSessionAdmissionRecommendations(),
        getSessionAdmissionSummary(),
        getGovernanceReviewSummary(),
        getGovernanceReviewItems(),
        getGovernanceReviewRecommendations(),
        getGovernanceReviewResolutions(),
      ]);
      setSessions(loadedSessions);
      setSummary(loadedSummary);
      setRunnerState(loadedRunnerState);
      setHeartbeatRuns(loadedRuns);
      setDecisions(loadedDecisions);
      setDispatchAttempts(loadedDispatches);
      setRecommendations(loadedRecommendations);
      setHeartbeatSummary(loadedHeartbeatSummary);
      setScheduleProfiles(loadedScheduleProfiles);
      setTimingSnapshots(loadedTimingSnapshots);
      setStopEvaluations(loadedStopEvaluations);
      setTimingDecisions(loadedTimingDecisions);
      setTimingRecommendations(loadedTimingRecommendations);
      setTimingSummary(loadedTimingSummary);
      setContextReviews(loadedContextReviews);
      setProfileSwitchDecisions(loadedProfileSwitchDecisions);
      setProfileSwitchRecords(loadedProfileSwitchRecords);
      setProfileRecommendations(loadedProfileRecommendations);
      setProfileSelectionSummary(loadedProfileSelectionSummary);
      setHealthSnapshots(loadedHealthSnapshots);
      setHealthAnomalies(loadedHealthAnomalies);
      setHealthDecisions(loadedHealthDecisions);
      setHealthRecommendations(loadedHealthRecommendations);
      setHealthSummary(loadedHealthSummary);
      setRecoverySnapshots(loadedRecoverySnapshots);
      setRecoveryBlockers(loadedRecoveryBlockers);
      setResumeDecisions(loadedResumeDecisions);
      setRecoveryRecommendations(loadedRecoveryRecommendations);
      setResumeRecords(loadedResumeRecords);
      setRecoverySummary(loadedRecoverySummary);
      setCapacitySnapshots(loadedCapacitySnapshots);
      setAdmissionReviews(loadedAdmissionReviews);
      setAdmissionDecisions(loadedAdmissionDecisions);
      setAdmissionRecommendations(loadedAdmissionRecommendations);
      setAdmissionSummary(loadedAdmissionSummary);
      setGovernanceSummary(loadedGovernanceSummary);
      setGovernanceItems(loadedGovernanceItems);
      setGovernanceRecommendations(loadedGovernanceRecommendations);
      setGovernanceResolutions(loadedGovernanceResolutions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load autonomous heartbeat runner state.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Mission control"
        title="Autonomous Runner"
        description="Local-first heartbeat runner that advances RUNNING autonomous sessions automatically when cadence is due, with cooldown/safety/runtime guardrails and paper-only execution boundaries."
        actions={<div className="button-row"><button type="button" className="primary-button" onClick={async () => { await startAutonomousRunner(); await load(); }}>Start runner</button><button type="button" className="secondary-button" onClick={async () => { await pauseAutonomousRunner(); await load(); }}>Pause runner</button><button type="button" className="secondary-button" onClick={async () => { await resumeAutonomousRunner(); await load(); }}>Resume runner</button><button type="button" className="secondary-button" onClick={async () => { await stopAutonomousRunner(); await load(); }}>Stop runner</button><button type="button" className="secondary-button" onClick={async () => { await runAutonomousHeartbeat(); await load(); }}>Run heartbeat now</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Autonomous runner" title="Heartbeat summary" description="Paper-only local heartbeat progression. No live broker/exchange execution.">
          <div className="system-metadata-grid">
            <div><strong>Runner status:</strong> {runnerState?.runner_status ?? 'n/a'}</div>
            <div><strong>Active sessions:</strong> {runnerState?.active_session_count ?? 0}</div>
            <div><strong>Considered sessions:</strong> {latestHeartbeat?.considered_session_count ?? 0}</div>
            <div><strong>Due ticks:</strong> {latestHeartbeat?.due_tick_count ?? 0}</div>
            <div><strong>Executed ticks:</strong> {latestHeartbeat?.executed_tick_count ?? 0}</div>
            <div><strong>Cooldown skips:</strong> {latestHeartbeat?.cooldown_skip_count ?? 0}</div>
            <div><strong>Blocked / paused / stopped:</strong> {(latestHeartbeat?.blocked_count ?? 0) + (latestHeartbeat?.paused_count ?? 0) + (latestHeartbeat?.stopped_count ?? 0)}</div>
            <div><strong>Total heartbeat runs:</strong> {heartbeatSummary?.totals.heartbeat_runs ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Session timing policy" title="Cadence governance summary" description="Configurable local-first timing policy (paper-only) governing when sessions run, wait, pause, or stop.">
          <div className="button-row">
            <button type="button" className="primary-button" onClick={async () => { await runSessionTimingReview(); await load(); }}>Run timing review</button>
          </div>
          <div className="system-metadata-grid">
            <div><strong>Sessions evaluated:</strong> {timingSummary?.summary.sessions_evaluated ?? 0}</div>
            <div><strong>Due now:</strong> {timingSummary?.summary.due_now ?? 0}</div>
            <div><strong>Waiting short:</strong> {timingSummary?.summary.waiting_short ?? 0}</div>
            <div><strong>Waiting long:</strong> {timingSummary?.summary.waiting_long ?? 0}</div>
            <div><strong>Monitor-only:</strong> {timingSummary?.summary.monitor_only ?? 0}</div>
            <div><strong>Pause recommended:</strong> {timingSummary?.summary.pause_recommended ?? 0}</div>
            <div><strong>Stop recommended:</strong> {timingSummary?.summary.stop_recommended ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Adaptive session profiles" title="Context-driven profile switching" description="Conservative local-first profile selection layer. It recommends or applies schedule profile shifts without replacing timing policy or heartbeat authorities. Paper-only and no live execution.">
          <div className="button-row">
            <button type="button" className="primary-button" onClick={async () => { await runProfileSelectionReview(); await load(); }}>Run profile selection review</button>
          </div>
          <div className="system-metadata-grid">
            <div><strong>Sessions reviewed:</strong> {profileSelectionSummary?.summary.sessions_reviewed ?? 0}</div>
            <div><strong>Keep current:</strong> {profileSelectionSummary?.summary.keep_current ?? 0}</div>
            <div><strong>Switch recommended:</strong> {profileSelectionSummary?.summary.switch_recommended ?? 0}</div>
            <div><strong>Switched:</strong> {profileSelectionSummary?.summary.switched ?? 0}</div>
            <div><strong>Blocked:</strong> {profileSelectionSummary?.summary.blocked ?? 0}</div>
            <div><strong>Manual review:</strong> {profileSelectionSummary?.summary.manual_review ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Adaptive session profiles" title="Context reviews" description="Per-session context posture used to decide whether to hold or switch profile.">
          <ul>{contextReviews.slice(0, 10).map((review) => <li key={review.id}><strong>session={review.linked_session}</strong> profile={review.linked_current_profile ?? 'n/a'} portfolio={review.portfolio_pressure_state} runtime={review.runtime_posture} safety={review.safety_posture} signal={review.signal_pressure_state} activity={review.activity_state} status={review.context_status} summary={review.context_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Adaptive session profiles" title="Switch decisions" description="Transparent keep/switch/manual/block decisions with source and target profiles.">
          <ul>{profileSwitchDecisions.slice(0, 10).map((decision) => <li key={decision.id}><strong>{decision.decision_type}</strong> — session={decision.linked_session} from={decision.from_profile ?? 'n/a'} to={decision.to_profile ?? 'n/a'} status={decision.decision_status} summary={decision.decision_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Adaptive session profiles" title="Switch records" description="Audit trail of applied profile switches.">
          <ul>{profileSwitchRecords.slice(0, 10).map((record) => <li key={record.id}><strong>{record.switch_status}</strong> — session={record.linked_session} previous={record.previous_profile ?? 'n/a'} applied={record.applied_profile} summary={record.switch_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Adaptive session profiles" title="Profile recommendations" description="Conservative rationale, blockers, and confidence for profile selection outcomes.">
          <ul>{profileRecommendations.slice(0, 10).map((recommendation) => <li key={recommendation.id}><strong>{recommendation.recommendation_type}</strong> — {recommendation.rationale} blockers=[{recommendation.blockers.join(', ')}] confidence={recommendation.confidence}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session health & interventions" title="Operational health governance" description="Health monitor for local-first paper sessions. Conservative self-healing only, with explicit guardrails and no live execution.">
          <div className="button-row">
            <button type="button" className="primary-button" onClick={async () => { await runSessionHealthReview(); await load(); }}>Run health review</button>
          </div>
          <div className="system-metadata-grid">
            <div><strong>Sessions reviewed:</strong> {healthSummary?.summary.sessions_reviewed ?? 0}</div>
            <div><strong>Healthy:</strong> {healthSummary?.summary.healthy ?? 0}</div>
            <div><strong>Anomalies:</strong> {healthSummary?.summary.anomalies ?? 0}</div>
            <div><strong>Pause recommended:</strong> {healthSummary?.summary.pause_recommended ?? 0}</div>
            <div><strong>Stop recommended:</strong> {healthSummary?.summary.stop_recommended ?? 0}</div>
            <div><strong>Resume recommended:</strong> {healthSummary?.summary.resume_recommended ?? 0}</div>
            <div><strong>Manual review/escalation:</strong> {healthSummary?.summary.manual_review_or_escalation ?? 0}</div>
            <div><strong>Interventions applied:</strong> {healthSummary?.summary.interventions_applied ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Session health & interventions" title="Health snapshots" description="Per-session operational health snapshot and reason codes.">
          <ul>{healthSnapshots.slice(0, 12).map((snapshot) => <li key={snapshot.id}><strong>{snapshot.session_health_status}</strong> — session={snapshot.linked_session} failed={snapshot.consecutive_failed_ticks} blocked={snapshot.consecutive_blocked_ticks} no_progress={snapshot.consecutive_no_progress_ticks} cooldown={String(snapshot.has_active_cooldown)} mismatch={String(snapshot.runner_session_mismatch)} pressure={snapshot.incident_pressure_state} summary={snapshot.health_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session health & interventions" title="Anomalies" description="Explicit anomaly detection output with severity levels.">
          <ul>{healthAnomalies.slice(0, 12).map((anomaly) => <li key={anomaly.id}><strong>{anomaly.anomaly_type}</strong> — session={anomaly.linked_session} severity={anomaly.anomaly_severity} summary={anomaly.anomaly_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session health & interventions" title="Intervention decisions" description="Conservative keep/pause/resume/stop/manual/escalate decisions.">
          <ul>{healthDecisions.slice(0, 12).map((decision) => <li key={decision.id}><strong>{decision.decision_type}</strong> — session={decision.linked_session} status={decision.decision_status} auto={String(decision.auto_applicable)} summary={decision.decision_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session health & interventions" title="Health recommendations" description="Recommendations with rationale, blockers, and confidence.">
          <ul>{healthRecommendations.slice(0, 12).map((recommendation) => <li key={recommendation.id}><strong>{recommendation.recommendation_type}</strong> — {recommendation.rationale} blockers=[{recommendation.blockers.join(', ')}] confidence={recommendation.confidence}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session recovery review" title="Recovery eligibility and conservative resume recommendations" description="Post-pause/degraded review layer. It builds auditable recovery snapshots, blockers, and resume decisions and can optionally auto-apply only safe-ready resumes.">
          <div className="button-row">
            <button type="button" className="primary-button" onClick={async () => { await runSessionRecoveryReview(); await load(); }}>Run recovery review</button>
            <button type="button" className="secondary-button" onClick={async () => { await runSessionRecoveryReviewSafeAutoApply(); await load(); }}>Run recovery review (safe auto apply)</button>
          </div>
          <div className="system-metadata-grid">
            <div><strong>Sessions reviewed:</strong> {recoverySummary?.summary.sessions_reviewed ?? 0}</div>
            <div><strong>Ready to resume:</strong> {recoverySummary?.summary.ready_to_resume ?? 0}</div>
            <div><strong>Keep paused:</strong> {recoverySummary?.summary.keep_paused ?? 0}</div>
            <div><strong>Manual review:</strong> {recoverySummary?.summary.manual_review ?? 0}</div>
            <div><strong>Stop recommended:</strong> {recoverySummary?.summary.stop_recommended ?? 0}</div>
            <div><strong>Incident escalation:</strong> {recoverySummary?.summary.incident_escalation ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Session recovery review" title="Recovery snapshots" description="Stabilization snapshots with cleared/active blocks and recovery status.">
          <ul>{recoverySnapshots.slice(0, 12).map((snapshot) => <li key={snapshot.id}><strong>{snapshot.recovery_status}</strong> — session={snapshot.linked_session} safety_cleared={String(snapshot.safety_block_cleared)} runtime_cleared={String(snapshot.runtime_block_cleared)} incident_cleared={String(snapshot.incident_pressure_cleared)} portfolio={snapshot.portfolio_pressure_state} cooldown={String(snapshot.cooldown_active)} failed={snapshot.recent_failed_ticks} blocked={snapshot.recent_blocked_ticks} summary={snapshot.recovery_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session recovery review" title="Recovery blockers" description="Explicit blockers still preventing a safe resume recommendation.">
          <ul>{recoveryBlockers.slice(0, 12).map((blocker) => <li key={blocker.id}><strong>{blocker.blocker_type}</strong> — session={blocker.linked_session} severity={blocker.blocker_severity} summary={blocker.blocker_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session recovery review" title="Resume decisions" description="Transparent decisions: keep paused, ready, monitor-only, manual, stop, or incident escalation.">
          <ul>{resumeDecisions.slice(0, 12).map((decision) => (
            <li key={decision.id}>
              <strong>{decision.decision_type}</strong> — session={decision.linked_session} status={decision.decision_status} auto={String(decision.auto_applicable)} summary={decision.decision_summary}
              <div className="button-row" style={{ marginTop: 8 }}>
                <button type="button" className="secondary-button" onClick={async () => { await applySessionResume(decision.id, 'MANUAL_RESUME'); await load(); }}>Apply resume</button>
                {decision.decision_type === 'RESUME_IN_MONITOR_ONLY_MODE' ? (
                  <button type="button" className="ghost-button" onClick={async () => { await applySessionResume(decision.id, 'MONITOR_ONLY_RESUME'); await load(); }}>Apply monitor-only</button>
                ) : null}
              </div>
            </li>
          ))}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session recovery review" title="Resume records" description="Audit trail of manual, auto-safe, and monitor-only resume apply attempts.">
          <ul>{resumeRecords.slice(0, 12).map((record) => <li key={record.id}><strong>{record.resume_status}</strong> — session={record.linked_session} mode={record.applied_mode} summary={record.resume_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session recovery review" title="Recovery recommendations" description="Auditable recommendations with reason codes and blocker references.">
          <ul>{recoveryRecommendations.slice(0, 12).map((recommendation) => <li key={recommendation.id}><strong>{recommendation.recommendation_type}</strong> — {recommendation.rationale} blockers=[{recommendation.blockers.join(', ')}] confidence={recommendation.confidence}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Global Session Admission" title="Portfolio-aware runtime capacity control" description="Conservative global coordinator deciding which sessions are admitted, resumed, parked, deferred, paused, or retired. Local-first, paper-only, and no live execution.">
          <div className="button-row">
            <button type="button" className="primary-button" onClick={async () => { await runSessionAdmissionReview(); await load(); }}>Run admission review</button>
          </div>
          <div className="system-metadata-grid">
            <div><strong>Sessions considered:</strong> {admissionSummary?.summary.sessions_considered ?? 0}</div>
            <div><strong>Admitted:</strong> {admissionSummary?.summary.admitted ?? 0}</div>
            <div><strong>Resume allowed:</strong> {admissionSummary?.summary.resume_allowed ?? 0}</div>
            <div><strong>Parked:</strong> {admissionSummary?.summary.parked ?? 0}</div>
            <div><strong>Deferred:</strong> {admissionSummary?.summary.deferred ?? 0}</div>
            <div><strong>Paused:</strong> {admissionSummary?.summary.paused ?? 0}</div>
            <div><strong>Retired:</strong> {admissionSummary?.summary.retired ?? 0}</div>
            <div><strong>Manual review:</strong> {admissionSummary?.summary.manual_review ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Global Session Admission" title="Capacity snapshots" description="Global runtime posture and capacity status consumed by session admission control.">
          <ul>{capacitySnapshots.slice(0, 6).map((snapshot) => <li key={snapshot.id}><strong>{snapshot.capacity_status}</strong> — active={snapshot.current_running_sessions}/{snapshot.max_active_sessions} dispatch={snapshot.active_dispatch_load} portfolio={snapshot.open_position_pressure_state} runtime={snapshot.runtime_posture} safety={snapshot.safety_posture} incident={snapshot.incident_pressure_state} summary={snapshot.snapshot_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Global Session Admission" title="Session admission reviews" description="Per-session priority + operability review against global capacity.">
          <ul>{admissionReviews.slice(0, 12).map((review) => <li key={review.id}><strong>session={review.linked_session}</strong> priority={review.session_priority_state} operability={review.session_operability_state} admission={review.admission_status} summary={review.review_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Global Session Admission" title="Admission decisions" description="Final explicit admission decision per reviewed session.">
          <ul>{admissionDecisions.slice(0, 12).map((decision) => <li key={decision.id}><strong>{decision.decision_type}</strong> — session={decision.linked_session} status={decision.decision_status} auto={String(decision.auto_applicable)} summary={decision.decision_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Global Session Admission" title="Admission recommendations" description="Conservative recommendations with rationale, blockers and confidence.">
          <ul>{admissionRecommendations.slice(0, 12).map((recommendation) => <li key={recommendation.id}><strong>{recommendation.recommendation_type}</strong> — {recommendation.rationale} blockers=[{recommendation.blockers.join(', ')}] confidence={recommendation.confidence}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Governance Review Queue" title="Cross-layer review inbox" description="Unified blocked/manual/deferred/advisory queue across runtime_governor, mission_control, and portfolio_governor with explicit manual-safe resolution and audit trail. Paper-only scope.">
          <div className="button-row">
            <button type="button" className="primary-button" onClick={async () => { await runGovernanceReviewQueue(); await load(); }}>Run governance review queue</button>
          </div>
          <div className="system-metadata-grid">
            <div><strong>Open items:</strong> {governanceSummary?.open_count ?? 0}</div>
            <div><strong>Resolved:</strong> {governanceSummary?.resolved_count ?? 0}</div>
            <div><strong>High priority (P1):</strong> {governanceSummary?.high_priority_count ?? 0}</div>
            <div><strong>Blocked:</strong> {governanceSummary?.blocked_count ?? 0}</div>
            <div><strong>Deferred:</strong> {governanceSummary?.deferred_count ?? 0}</div>
            <div><strong>Manual review:</strong> {governanceSummary?.manual_review_count ?? 0}</div>
            <div><strong>Latest run:</strong> {governanceSummary?.latest_run ?? 'n/a'}</div>
          </div>
          <ul>{governanceItems.slice(0, 10).map((item) => <li key={item.id}><strong>{item.queue_priority}</strong> [{item.severity}] {item.title} — module={item.source_module} type={item.source_type} status={item.item_status} <span style={{ marginLeft: 8, fontWeight: 700 }}>{item.item_status === 'DISMISSED' ? 'dismissed' : item.item_status === 'RESOLVED' ? 'resolved' : 'open'}</span><div className="button-row" style={{ marginTop: 8 }}><button type="button" className="primary-button" onClick={async () => { await resolveGovernanceReviewItem(item.id, { resolution_type: 'APPLY_MANUAL_APPROVAL' }); await load(); }}>Resolve item</button><button type="button" className="secondary-button" onClick={async () => { await resolveGovernanceReviewItem(item.id, { resolution_type: 'DISMISS_AS_EXPECTED' }); await load(); }}>Dismissed</button><button type="button" className="secondary-button" onClick={async () => { await resolveGovernanceReviewItem(item.id, { resolution_type: 'KEEP_BLOCKED' }); await load(); }}>Blocked</button><button type="button" className="secondary-button" onClick={async () => { await resolveGovernanceReviewItem(item.id, { resolution_type: 'REQUIRE_FOLLOWUP' }); await load(); }}>Follow-up</button><button type="button" className="secondary-button" onClick={async () => { await resolveGovernanceReviewItem(item.id, { resolution_type: 'RETRY_SAFE_APPLY' }); await load(); }}>Retry safe</button></div></li>)}</ul>
          <ul>{governanceRecommendations.slice(0, 10).map((recommendation) => <li key={recommendation.id}><strong>{recommendation.recommendation_type}</strong> — item={recommendation.linked_review_item ?? 'n/a'} confidence={recommendation.confidence.toFixed(2)} rationale={recommendation.rationale}</li>)}</ul>
          <ul>{governanceResolutions.slice(0, 12).map((resolution) => <li key={resolution.id}><strong>{resolution.resolution_type}</strong> — item={resolution.linked_review_item} status={resolution.resolution_status} state={resolution.resolution_type === 'DISMISS_AS_EXPECTED' ? 'dismissed' : resolution.resolution_type === 'KEEP_BLOCKED' ? 'blocked' : resolution.resolution_type === 'REQUIRE_FOLLOWUP' ? 'follow-up' : 'resolved'} summary={resolution.resolution_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session timing policy" title="Schedule profiles" description="Reusable cadence profiles with explicit intervals and quiet/stop thresholds.">
          <ul>{scheduleProfiles.slice(0, 10).map((profile) => <li key={profile.id}><strong>{profile.slug}</strong> ({profile.display_name}) — base={profile.base_interval_seconds}s reduced={profile.reduced_interval_seconds}s monitor={profile.monitor_only_interval_seconds}s quiet_pause={profile.max_no_action_ticks_before_pause} blocked_stop={profile.max_consecutive_blocked_ticks_before_stop} active={String(profile.is_active)}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session timing policy" title="Timing snapshots" description="Per-session cadence snapshot with next_due_at and pressure state.">
          <ul>{timingSnapshots.slice(0, 10).map((snapshot) => <li key={snapshot.id}><strong>{snapshot.timing_status}</strong> — session={snapshot.linked_session} next_due={snapshot.next_due_at ?? 'n/a'} cooldowns={snapshot.active_cooldown_count} no_action={snapshot.consecutive_no_action_ticks} blocked={snapshot.consecutive_blocked_ticks} signal={snapshot.signal_pressure_state} summary={snapshot.timing_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session timing policy" title="Timing decisions" description="Explicit decisions consumed by heartbeat due-tick evaluation.">
          <ul>{timingDecisions.slice(0, 10).map((decision) => <li key={decision.id}><strong>{decision.decision_type}</strong> — session={decision.linked_session} next_due={decision.next_due_at ?? 'n/a'} status={decision.decision_status} summary={decision.decision_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session timing policy" title="Timing recommendations" description="Conservative recommendations with rationale, blockers, and confidence.">
          <ul>{timingRecommendations.slice(0, 10).map((recommendation) => <li key={recommendation.id}><strong>{recommendation.recommendation_type}</strong> — {recommendation.rationale} blockers=[{recommendation.blockers.join(', ')}] confidence={recommendation.confidence}</li>)}</ul>
          <p><strong>Stop condition evaluations:</strong> {stopEvaluations.length}</p>
        </SectionCard>

        <SectionCard eyebrow="Runner state" title="Local autonomous runner state" description="Single local runner state with audit timestamps.">
          <ul>
            <li><StatusBadge tone="ready">{runnerState?.runner_status ?? 'UNKNOWN'}</StatusBadge> runner={runnerState?.runner_name ?? 'n/a'} last_heartbeat={runnerState?.last_heartbeat_at ?? 'n/a'} last_success={runnerState?.last_successful_run_at ?? 'n/a'} active_sessions={runnerState?.active_session_count ?? 0}</li>
          </ul>
        </SectionCard>

        <SectionCard eyebrow="Heartbeat decisions" title="Due tick decisions by session" description="Transparent due/wait/cooldown/pause/stop/block decisions for every evaluated session.">
          <ul>{decisions.slice(0, 12).map((decision) => <li key={decision.id}><strong>{decision.decision_type}</strong> — session={decision.linked_session} due_now={String(decision.due_now)} next_due={decision.next_due_at ?? 'n/a'} status={decision.decision_status} summary={decision.decision_summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Tick dispatch attempts" title="Automatic dispatch traceability" description="Automatic/manual distinction and status for each heartbeat dispatch attempt.">
          <ul>{dispatchAttempts.slice(0, 12).map((attempt) => <li key={attempt.id}><strong>{attempt.dispatch_status}</strong> — session={attempt.linked_session} tick={attempt.linked_tick ?? 'n/a'} automatic={String(attempt.automatic)} summary={attempt.summary}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Recommendations" title="Heartbeat recommendations" description="Conservative recommendations emitted per heartbeat decision.">
          <ul>{recommendations.slice(0, 12).map((recommendation) => <li key={recommendation.id}><strong>{recommendation.recommendation_type}</strong> — {recommendation.rationale} blockers=[{recommendation.blockers.join(', ')}] confidence={recommendation.confidence}</li>)}</ul>
        </SectionCard>

        <SectionCard eyebrow="Session baseline" title="Autonomous session counters" description="Existing autonomous session counters remain available for manual/automatic coexistence.">
          <div className="system-metadata-grid">
            <div><strong>Total sessions:</strong> {summary?.session_count ?? 0}</div>
            <div><strong>Active sessions:</strong> {summary?.active_sessions ?? 0}</div>
            <div><strong>Paused sessions:</strong> {summary?.paused_sessions ?? 0}</div>
            <div><strong>Stopped sessions:</strong> {summary?.stopped_sessions ?? 0}</div>
            <div><strong>Ticks executed:</strong> {summary?.ticks_executed ?? 0}</div>
            <div><strong>Ticks skipped:</strong> {summary?.ticks_skipped ?? 0}</div>
            <div><strong>Dispatches:</strong> {summary?.dispatch_count ?? 0}</div>
            <div><strong>Closed outcomes:</strong> {summary?.closed_outcome_count ?? 0}</div>
          </div>
          <ul>{sessions.slice(0, 8).map((session) => <li key={session.id}><StatusBadge tone="pending">{session.session_status}</StatusBadge> session={session.id} mode={session.runtime_mode || 'unknown'} profile={session.profile_slug || 'default'} ticks={session.tick_count}</li>)}</ul>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
