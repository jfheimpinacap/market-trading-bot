import { useCallback, useEffect, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { navigate } from '../../lib/router';
import {
  applyPromotionCase,
  getPromotionAdoptionActions,
  getPromotionAdoptionSummary,
  runPromotionAdoptionReview,
} from '../../services/promotionAdoption';
import {
  closePromotionRollout,
  executePromotionRollout,
  getPromotionCheckpointOutcomes,
  getPromotionPostRolloutStatus,
  getPromotionRolloutExecutionRecommendations,
  getPromotionRolloutExecutionSummary,
  getPromotionRolloutExecutions,
  recordPromotionCheckpointOutcome,
  runPromotionRolloutExecutionReview,
} from '../../services/promotionRolloutExecution';
import {
  getPromotionCheckpointPlans,
  getPromotionRollbackExecutions,
  getPromotionRolloutCandidates,
  getPromotionRolloutPlans,
  getPromotionRolloutRecommendations,
  getPromotionRolloutSummary,
  preparePromotionRollout,
  rollbackPromotionAction,
  runPromotionRolloutPrep,
} from '../../services/promotionRollout';
import type {
  ManualAdoptionAction,
  ManualRollbackExecution,
  ManualRolloutPlan,
  PostRolloutStatus,
  PromotionAdoptionSummary,
  PromotionRolloutExecutionSummary,
  PromotionRolloutSummary,
  RolloutExecutionRecord,
  RolloutExecutionRecommendation,
  RolloutActionCandidate,
  CheckpointOutcomeRecord,
  RolloutCheckpointPlan,
  RolloutPreparationRecommendation,
} from '../../types/promotion';

const statusBadgeClass = (status: string) => {
  if (['RESOLVED', 'READY_TO_APPLY', 'READY', 'EXECUTED', 'ROLLBACK_AVAILABLE', 'APPLY_CHANGE_MANUALLY', 'ROLLBACK_READY', 'DIRECT_APPLY_OK'].includes(status)) return 'signal-badge signal-badge--actionable';
  if (['BLOCKED', 'REQUIRE_TARGET_MAPPING', 'DEFER_ADOPTION', 'REQUIRE_TARGET_RECHECK', 'ROLLOUT_REQUIRED'].includes(status)) return 'signal-badge signal-badge--bearish';
  if (['PARTIAL', 'PROPOSED', 'PREPARE_ROLLOUT_PLAN', 'PREPARE_ROLLBACK', 'REQUIRE_ROLLOUT_CHECKPOINTS', 'ROLLOUT_RECOMMENDED', 'CAUTION', 'REVIEW_REQUIRED', 'PAUSE_AND_REVIEW', 'REQUIRE_MORE_OBSERVATION'].includes(status)) return 'signal-badge signal-badge--monitor';
  return 'signal-badge signal-badge--neutral';
};

export function PromotionPage() {
  const [summary, setSummary] = useState<PromotionAdoptionSummary | null>(null);
  const [rolloutSummary, setRolloutSummary] = useState<PromotionRolloutSummary | null>(null);
  const [executionSummary, setExecutionSummary] = useState<PromotionRolloutExecutionSummary | null>(null);
  const [actions, setActions] = useState<ManualAdoptionAction[]>([]);
  const [rolloutCandidates, setRolloutCandidates] = useState<RolloutActionCandidate[]>([]);
  const [rolloutPlans, setRolloutPlans] = useState<ManualRolloutPlan[]>([]);
  const [checkpointPlans, setCheckpointPlans] = useState<RolloutCheckpointPlan[]>([]);
  const [rollbackExecutions, setRollbackExecutions] = useState<ManualRollbackExecution[]>([]);
  const [rolloutRecommendations, setRolloutRecommendations] = useState<RolloutPreparationRecommendation[]>([]);
  const [rolloutExecutions, setRolloutExecutions] = useState<RolloutExecutionRecord[]>([]);
  const [checkpointOutcomes, setCheckpointOutcomes] = useState<CheckpointOutcomeRecord[]>([]);
  const [postRolloutStatuses, setPostRolloutStatuses] = useState<PostRolloutStatus[]>([]);
  const [executionRecommendations, setExecutionRecommendations] = useState<RolloutExecutionRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, actionsRes, rolloutSummaryRes, rolloutCandidatesRes, rolloutPlansRes, checkpointRes, rollbackExecRes, rolloutRecommendationRes, executionSummaryRes, rolloutExecutionsRes, checkpointOutcomesRes, postRolloutStatusesRes, executionRecommendationsRes] = await Promise.all([
        getPromotionAdoptionSummary(),
        getPromotionAdoptionActions(),
        getPromotionRolloutSummary(),
        getPromotionRolloutCandidates(),
        getPromotionRolloutPlans(),
        getPromotionCheckpointPlans(),
        getPromotionRollbackExecutions(),
        getPromotionRolloutRecommendations(),
        getPromotionRolloutExecutionSummary(),
        getPromotionRolloutExecutions(),
        getPromotionCheckpointOutcomes(),
        getPromotionPostRolloutStatus(),
        getPromotionRolloutExecutionRecommendations(),
      ]);
      setSummary(summaryRes);
      setRolloutSummary(rolloutSummaryRes);
      setExecutionSummary(executionSummaryRes);
      setActions(actionsRes);
      setRolloutCandidates(rolloutCandidatesRes);
      setRolloutPlans(rolloutPlansRes);
      setCheckpointPlans(checkpointRes);
      setRollbackExecutions(rollbackExecRes);
      setRolloutRecommendations(rolloutRecommendationRes);
      setRolloutExecutions(rolloutExecutionsRes);
      setCheckpointOutcomes(checkpointOutcomesRes);
      setPostRolloutStatuses(postRolloutStatusesRes);
      setExecutionRecommendations(executionRecommendationsRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load promotion adoption board state.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onRunRolloutExecutionReview = useCallback(async () => {
    setMessage(null);
    setError(null);
    try {
      await runPromotionRolloutExecutionReview({ actor: 'promotion_ui', metadata: { initiated_from: 'promotion_ui' } });
      setMessage('Manual rollout execution review completed. Ready plans were mapped to execution records (no auto-execute).');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run rollout execution review.');
    }
  }, [load]);

  const onExecuteRollout = useCallback(async (planId: number) => {
    setMessage(null);
    setError(null);
    try {
      await executePromotionRollout(planId, { actor: 'operator', notes: 'Manual execution from promotion board.' });
      setMessage(`Rollout plan #${planId} execution recorded.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not execute rollout manually.');
    }
  }, [load]);

  const onRecordCheckpoint = useCallback(async (checkpointId: number) => {
    setMessage(null);
    setError(null);
    try {
      await recordPromotionCheckpointOutcome(checkpointId, {
        actor: 'operator',
        outcome_status: 'PASSED',
        outcome_rationale: 'Manual operator review confirms checkpoint passed.',
        observed_metrics: { source: 'manual_promotion_ui' },
      });
      setMessage(`Checkpoint #${checkpointId} outcome recorded.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not record checkpoint outcome.');
    }
  }, [load]);

  const onCloseRollout = useCallback(async (executionId: number) => {
    setMessage(null);
    setError(null);
    try {
      await closePromotionRollout(executionId, { actor: 'operator', notes: 'Manual closure from promotion board.' });
      setMessage(`Rollout execution #${executionId} was manually closed.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not close rollout execution.');
    }
  }, [load]);

  const onRunAdoptionReview = useCallback(async () => {
    setMessage(null);
    setError(null);
    try {
      await runPromotionAdoptionReview({ actor: 'promotion_ui', metadata: { initiated_from: 'promotion_ui' } });
      setMessage('Adoption review run completed. Manual actions were prepared (not auto-applied).');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run promotion adoption review.');
    }
  }, [load]);

  const onRunRolloutPrep = useCallback(async () => {
    setMessage(null);
    setError(null);
    try {
      await runPromotionRolloutPrep({ actor: 'promotion_ui', metadata: { initiated_from: 'promotion_ui' } });
      setMessage('Rollout preparation run completed. Plans/checkpoints/rollback controls were prepared (manual-only).');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run rollout preparation.');
    }
  }, [load]);

  const onPrepareRollout = useCallback(async (caseId: number) => {
    setMessage(null);
    setError(null);
    try {
      await preparePromotionRollout(caseId, { actor: 'operator' });
      setMessage(`Rollout plan prepared for case #${caseId}.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not prepare rollout.');
    }
  }, [load]);

  const onRollback = useCallback(async (actionId: number) => {
    setMessage(null);
    setError(null);
    try {
      await rollbackPromotionAction(actionId, { actor: 'operator' });
      setMessage(`Rollback execution recorded for action #${actionId}.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not execute manual rollback.');
    }
  }, [load]);

  const onApplyCase = useCallback(async (caseId: number) => {
    setMessage(null);
    setError(null);
    try {
      await applyPromotionCase(caseId, { actor: 'operator' });
      setMessage(`Case #${caseId} recorded as manually applied.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not apply promotion case manually.');
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Promotion rollout execution prep board"
        title="/promotion"
        description="Local-first, manual-first and paper-only governance. Approved adoption actions can be transformed into explicit rollout plans, checkpoints, monitoring intent, and dedicated auditable manual rollback controls. No auto-rollout."
        actions={<div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/experiments')}>Experiments</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="secondary-button" type="button" onClick={() => navigate('/certification')}>Certification</button><button className="secondary-button" type="button" onClick={() => navigate('/tuning')}>Tuning</button><button className="secondary-button" type="button" onClick={() => navigate('/evaluation')}>Evaluation</button><button className="secondary-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Rollout/rollback readiness" description="Approval ≠ automatic rollout. All actions stay explicit, auditable and reversible.">
          <div className="dashboard-stat-grid">
            <article className="dashboard-stat-card"><span>Rollout candidates</span><strong>{rolloutSummary?.candidates ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Ready</span><strong>{rolloutSummary?.ready ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Blocked</span><strong>{rolloutSummary?.blocked ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Checkpoint plans</span><strong>{rolloutSummary?.checkpoint_plans ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Rollback ready</span><strong>{rolloutSummary?.rollback_ready ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Rollback executed</span><strong>{rolloutSummary?.rollback_executed ?? 0}</strong></article>
          </div>
        </SectionCard>
        <SectionCard eyebrow="Execution summary" title="Manual post-rollout safety loop" description="Manual-first execution tracking, checkpoint outcomes, post-rollout safety status and bounded recommendations.">
          <div className="dashboard-stat-grid">
            <article className="dashboard-stat-card"><span>Rollout plans ready</span><strong>{executionSummary?.rollout_plans_ready ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Executions running</span><strong>{executionSummary?.executions_running ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Healthy rollouts</span><strong>{executionSummary?.healthy_rollouts ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Review required</span><strong>{executionSummary?.review_required ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Rollback recommended</span><strong>{executionSummary?.rollback_recommended ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Rollback executed</span><strong>{executionSummary?.rollback_executed ?? 0}</strong></article>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Actions" title="Manual controls" description="Operator actions only. No silent apply and no automatic rollout.">
          <div className="button-row">
            <button className="primary-button" type="button" onClick={() => void onRunAdoptionReview()}>Run adoption review</button>
            <button className="secondary-button" type="button" onClick={() => void onRunRolloutPrep()}>Run rollout prep</button>
            <button className="secondary-button" type="button" onClick={() => void onRunRolloutExecutionReview()}>Run rollout execution review</button>
            {message ? <span className="muted-text">{message}</span> : null}
          </div>
        </SectionCard>

        <SectionCard eyebrow="Rollout candidates" title="Sensitive change triage" description="Direct apply, recommended rollout, or required rollout is explicitly classified.">
          {!rolloutCandidates.length ? (
            <EmptyState
              eyebrow="Rollout prep"
              title="No rollout candidates yet"
              description="No approved manual adoption actions currently require rollout preparation. Run rollout prep to prepare safe paper-only rollout and rollback plans."
            />
          ) : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Case</th><th>Component</th><th>Scope</th><th>Action</th><th>Need</th><th>Target resolution</th><th>Blockers</th><th>Links</th><th>Prepare</th></tr></thead><tbody>
              {rolloutCandidates.map((item) => <tr key={item.id}><td>#{item.linked_promotion_case}</td><td>{item.target_component}</td><td>{item.target_scope}</td><td>{item.action_type}</td><td><span className={statusBadgeClass(item.rollout_need_level)}>{item.rollout_need_level}</span></td><td><span className={statusBadgeClass(item.target_resolution_status)}>{item.target_resolution_status}</span></td><td>{item.blockers.join(', ') || 'None'}</td><td><div className="button-row"><button className="chip-button" type="button" onClick={() => navigate('/experiments')}>Experiments</button><button className="chip-button" type="button" onClick={() => navigate('/tuning')}>Tuning</button><button className="chip-button" type="button" onClick={() => navigate('/evaluation')}>Evaluation</button><button className="chip-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div></td><td><button className="secondary-button" type="button" onClick={() => void onPrepareRollout(item.linked_promotion_case)}>Prepare rollout</button></td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Rollout plans" title="Manual rollout plans" description="Staged manual plans with monitoring intent and rollout-manager bridge metadata.">
          {!rolloutPlans.length ? <p className="muted-text">No rollout plans prepared yet.</p> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Plan type</th><th>Status</th><th>Staged steps</th><th>Monitoring intent</th><th>Executed by</th><th>Executed at</th><th>Rationale</th><th>Manual action</th></tr></thead><tbody>
              {rolloutPlans.map((item) => <tr key={item.id}><td>{item.rollout_plan_type}</td><td><span className={statusBadgeClass(item.rollout_status)}>{item.rollout_status}</span></td><td><code>{JSON.stringify(item.staged_steps)}</code></td><td><code>{JSON.stringify(item.monitoring_intent)}</code></td><td>{item.executed_by || 'n/a'}</td><td>{item.executed_at || 'n/a'}</td><td>{item.rollout_rationale}</td><td><button className="secondary-button" type="button" onClick={() => void onExecuteRollout(item.id)}>Execute rollout</button></td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Checkpoints" title="Rollout checkpoint plans" description="Pre/post checks, drift, calibration and rollback readiness are explicit.">
          {!checkpointPlans.length ? <p className="muted-text">No checkpoint plans generated yet.</p> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Plan</th><th>Checkpoint type</th><th>Status</th><th>Rationale</th><th>Record outcome</th></tr></thead><tbody>
              {checkpointPlans.map((item) => <tr key={item.id}><td>#{item.linked_rollout_plan}</td><td>{item.checkpoint_type}</td><td><span className={statusBadgeClass(item.checkpoint_status)}>{item.checkpoint_status}</span></td><td>{item.checkpoint_rationale}</td><td><button className="secondary-button" type="button" onClick={() => void onRecordCheckpoint(item.id)}>Record checkpoint outcome</button></td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>
        <SectionCard eyebrow="Rollout executions" title="Manual rollout execution records" description="Execution run records the real manual rollout path, notes, actor and staged progress.">
          {!rolloutExecutions.length ? <p className="muted-text">No manual rollout executions are available yet. Run rollout execution review to track checkpoint outcomes and post-rollout safety.</p> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Plan</th><th>Status</th><th>Steps</th><th>Executed by</th><th>Executed at</th><th>Notes</th><th>Links</th><th>Close</th></tr></thead><tbody>
              {rolloutExecutions.map((item) => <tr key={item.id}><td>#{item.linked_rollout_plan}</td><td><span className={statusBadgeClass(item.execution_status)}>{item.execution_status}</span></td><td>{item.executed_step_count}</td><td>{item.executed_by || 'n/a'}</td><td>{item.executed_at || 'n/a'}</td><td>{item.execution_notes || item.rationale}</td><td><div className="button-row"><button className="chip-button" type="button" onClick={() => navigate('/tuning')}>Tuning</button><button className="chip-button" type="button" onClick={() => navigate('/evaluation')}>Evaluation</button><button className="chip-button" type="button" onClick={() => navigate('/experiments')}>Experiments</button><button className="chip-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div></td><td><button className="secondary-button" type="button" onClick={() => void onCloseRollout(item.id)}>Close rollout</button></td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>
        <SectionCard eyebrow="Checkpoint outcomes" title="Recorded checkpoint outcomes" description="Checkpoint plans become auditable real outcomes with explicit triggered actions.">
          {!checkpointOutcomes.length ? <p className="muted-text">No checkpoint outcomes recorded yet.</p> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Execution</th><th>Checkpoint</th><th>Outcome</th><th>Triggered action</th><th>Rationale</th><th>Recorded by</th><th>Recorded at</th></tr></thead><tbody>
              {checkpointOutcomes.map((item) => <tr key={item.id}><td>#{item.linked_rollout_execution}</td><td>#{item.linked_checkpoint_plan}</td><td><span className={statusBadgeClass(item.outcome_status)}>{item.outcome_status}</span></td><td><span className={statusBadgeClass(item.triggered_action)}>{item.triggered_action}</span></td><td>{item.outcome_rationale}</td><td>{item.recorded_by || 'n/a'}</td><td>{item.recorded_at || 'n/a'}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>
        <SectionCard eyebrow="Post-rollout status" title="Safety state after manual execution" description="Bounded drift/risk/calibration signals are visible context only; rollback remains manual.">
          {!postRolloutStatuses.length ? <p className="muted-text">No post-rollout status snapshots yet.</p> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Execution</th><th>Status</th><th>Drift flags</th><th>Risk flags</th><th>Calibration flags</th><th>Rationale</th></tr></thead><tbody>
              {postRolloutStatuses.map((item) => <tr key={item.id}><td>#{item.linked_rollout_execution}</td><td><span className={statusBadgeClass(item.status)}>{item.status}</span></td><td>{item.observed_drift_flags.join(', ') || 'None'}</td><td>{item.observed_risk_flags.join(', ') || 'None'}</td><td>{item.observed_calibration_flags.join(', ') || 'None'}</td><td>{item.status_rationale}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>
        <SectionCard eyebrow="Execution recommendations" title="Manual execution recommendations" description="Conservative bounded guidance for continue/pause/review/rollback/close decisions.">
          {!executionRecommendations.length ? <p className="muted-text">No rollout execution recommendations yet.</p> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Recommendation</th><th>Execution</th><th>Rationale</th><th>Reason codes</th><th>Confidence</th></tr></thead><tbody>
              {executionRecommendations.map((item) => <tr key={item.id}><td><span className={statusBadgeClass(item.recommendation_type)}>{item.recommendation_type}</span></td><td>{item.target_execution ? `execution #${item.target_execution}` : 'global'}</td><td>{item.rationale}</td><td>{item.reason_codes.join(', ') || 'None'}</td><td>{item.confidence}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Rollback execution" title="Dedicated manual rollback control" description="Rollback can be prepared and explicitly executed with traceable actor/timestamp.">
          {!rollbackExecutions.length ? <p className="muted-text">No rollback executions tracked yet.</p> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Action</th><th>Type</th><th>Status</th><th>Snapshot</th><th>Executed by</th><th>Executed at</th><th>Manual</th></tr></thead><tbody>
              {rollbackExecutions.map((item) => <tr key={item.id}><td>#{item.linked_manual_action}</td><td>{item.rollback_type}</td><td><span className={statusBadgeClass(item.execution_status)}>{item.execution_status}</span></td><td><code>{JSON.stringify(item.rollback_target_snapshot)}</code></td><td>{item.executed_by || 'n/a'}</td><td>{item.executed_at || 'n/a'}</td><td><button className="secondary-button" type="button" onClick={() => void onRollback(item.linked_manual_action)}>Rollback</button></td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Recommendations" title="Rollout preparation recommendations" description="Conservative recommendations for rollout ordering, recheck and rollback readiness.">
          {!rolloutRecommendations.length ? <p className="muted-text">No rollout recommendations generated yet.</p> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Recommendation</th><th>Target</th><th>Rationale</th><th>Reason codes</th><th>Confidence</th></tr></thead><tbody>
              {rolloutRecommendations.map((item) => <tr key={item.id}><td><span className={statusBadgeClass(item.recommendation_type)}>{item.recommendation_type}</span></td><td>{item.target_candidate ? `candidate #${item.target_candidate}` : `plan #${item.target_plan}`}</td><td>{item.rationale}</td><td>{item.reason_codes.join(', ') || 'None'}</td><td>{item.confidence}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Adoption bridge" title="Existing adoption layer" description="Original adoption board remains active for direct manual apply flow.">
          <div className="dashboard-stat-grid">
            <article className="dashboard-stat-card"><span>Approved cases</span><strong>{summary?.approved_cases ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Ready to apply</span><strong>{summary?.ready_to_apply ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Blocked</span><strong>{summary?.blocked ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Rollback prepared</span><strong>{summary?.rollback_prepared ?? 0}</strong></article>
          </div>
          {!actions.length ? <p className="muted-text">No adoption actions prepared yet.</p> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Case</th><th>Action</th><th>Status</th><th>Rationale</th><th>Manual apply</th></tr></thead><tbody>
              {actions.map((item) => <tr key={item.id}><td>#{item.linked_promotion_case}</td><td>{item.action_type}</td><td><span className={statusBadgeClass(item.action_status)}>{item.action_status}</span></td><td>{item.rationale}</td><td>{item.action_status === 'READY_TO_APPLY' ? <button className="secondary-button" type="button" onClick={() => void onApplyCase(item.linked_promotion_case)}>Apply</button> : '—'}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
