import { useCallback, useEffect, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { navigate } from '../../lib/router';
import {
  applyPromotionCase,
  getPromotionAdoptionActions,
  getPromotionAdoptionCandidates,
  getPromotionAdoptionRecommendations,
  getPromotionAdoptionSummary,
  getPromotionRollbackPlans,
  runPromotionAdoptionReview,
} from '../../services/promotionAdoption';
import { getPromotionCases } from '../../services/promotionReview';
import type {
  AdoptionActionCandidate,
  AdoptionActionRecommendation,
  AdoptionRollbackPlan,
  ManualAdoptionAction,
  PromotionAdoptionSummary,
  PromotionCase,
} from '../../types/promotion';

const statusBadgeClass = (status: string) => {
  if (['RESOLVED', 'READY_TO_APPLY', 'APPLIED', 'ROLLBACK_AVAILABLE', 'APPLY_CHANGE_MANUALLY'].includes(status)) return 'signal-badge signal-badge--actionable';
  if (['BLOCKED', 'REQUIRE_TARGET_MAPPING', 'DEFER_ADOPTION'].includes(status)) return 'signal-badge signal-badge--bearish';
  if (['PARTIAL', 'PROPOSED', 'PREPARE_ROLLOUT_PLAN', 'PREPARE_ROLLBACK'].includes(status)) return 'signal-badge signal-badge--monitor';
  return 'signal-badge signal-badge--neutral';
};

export function PromotionPage() {
  const [summary, setSummary] = useState<PromotionAdoptionSummary | null>(null);
  const [approvedCases, setApprovedCases] = useState<PromotionCase[]>([]);
  const [candidates, setCandidates] = useState<AdoptionActionCandidate[]>([]);
  const [actions, setActions] = useState<ManualAdoptionAction[]>([]);
  const [rollbacks, setRollbacks] = useState<AdoptionRollbackPlan[]>([]);
  const [recommendations, setRecommendations] = useState<AdoptionActionRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, casesRes, candidatesRes, actionsRes, rollbackRes, recommendationRes] = await Promise.all([
        getPromotionAdoptionSummary(),
        getPromotionCases({ case_status: 'APPROVED_FOR_MANUAL_ADOPTION' }),
        getPromotionAdoptionCandidates(),
        getPromotionAdoptionActions(),
        getPromotionRollbackPlans(),
        getPromotionAdoptionRecommendations(),
      ]);
      setSummary(summaryRes);
      setApprovedCases(casesRes);
      setCandidates(candidatesRes);
      setActions(actionsRes);
      setRollbacks(rollbackRes);
      setRecommendations(recommendationRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load promotion adoption board state.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
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
        eyebrow="Promotion manual adoption board"
        title="/promotion"
        description="Local-first, manual-first and paper-only adoption bridge. Approved promotion cases are converted into auditable manual actions with target resolution, before/after snapshots, rollback readiness, and optional rollout handoff preparation."
        actions={<div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/experiments')}>Experiments</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="secondary-button" type="button" onClick={() => navigate('/tuning')}>Tuning</button><button className="secondary-button" type="button" onClick={() => navigate('/evaluation')}>Evaluation</button><button className="secondary-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Manual adoption readiness" description="Approval is not auto-apply. This board tracks explicit safe actions only.">
          <div className="dashboard-stat-grid">
            <article className="dashboard-stat-card"><span>Approved cases</span><strong>{summary?.approved_cases ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Ready to apply</span><strong>{summary?.ready_to_apply ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Blocked</span><strong>{summary?.blocked ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Applied</span><strong>{summary?.applied ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Rollback prepared</span><strong>{summary?.rollback_prepared ?? 0}</strong></article>
            <article className="dashboard-stat-card"><span>Rollout handoff ready</span><strong>{summary?.rollout_handoff_ready ?? 0}</strong></article>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Actions" title="Run adoption review" description="Runs explicit candidate resolution and manual action planning. No silent apply, no live execution.">
          <div className="button-row">
            <button className="primary-button" type="button" onClick={() => void onRunAdoptionReview()}>Run adoption review</button>
            {message ? <span className="muted-text">{message}</span> : null}
          </div>
        </SectionCard>

        <SectionCard eyebrow="Candidates" title="Adoption candidates" description="Approved cases resolved to actionable manual targets.">
          {!approvedCases.length ? (
            <EmptyState
              eyebrow="Promotion adoption"
              title="No approved promotion cases are ready for manual adoption yet"
              description="No approved promotion cases are ready for manual adoption yet. Run adoption review to prepare safe change actions."
            />
          ) : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Case</th><th>Component</th><th>Scope</th><th>Change</th><th>Current</th><th>Proposed</th><th>Resolution</th><th>Blockers</th></tr></thead><tbody>
              {candidates.map((item) => <tr key={item.id}><td>#{item.linked_promotion_case}</td><td>{item.target_component}</td><td>{item.target_scope}</td><td>{item.change_type}</td><td>{item.current_value || 'n/a'}</td><td>{item.proposed_value || 'n/a'}</td><td><span className={statusBadgeClass(item.target_resolution_status)}>{item.target_resolution_status}</span></td><td>{item.blockers.join(', ') || 'None'}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Manual actions" title="Adoption actions" description="Before/after snapshots and explicit operator apply records.">
          {!actions.length ? <p className="muted-text">No adoption actions prepared yet.</p> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Case</th><th>Action</th><th>Status</th><th>Current snapshot</th><th>Proposed snapshot</th><th>Applied by</th><th>Applied at</th><th>Rationale</th><th>Manual</th></tr></thead><tbody>
              {actions.map((item) => <tr key={item.id}><td>#{item.linked_promotion_case}</td><td>{item.action_type}</td><td><span className={statusBadgeClass(item.action_status)}>{item.action_status}</span></td><td><code>{JSON.stringify(item.current_value_snapshot)}</code></td><td><code>{JSON.stringify(item.proposed_value_snapshot)}</code></td><td>{item.applied_by || 'n/a'}</td><td>{item.applied_at || 'n/a'}</td><td>{item.rationale}</td><td>{item.action_status === 'READY_TO_APPLY' ? <button className="secondary-button" type="button" onClick={() => void onApplyCase(item.linked_promotion_case)}>Apply</button> : '—'}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Rollback" title="Rollback plans" description="Prepared reversal plans for paper/demo manual adoption.">
          {!rollbacks.length ? <p className="muted-text">No rollback plans prepared yet.</p> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Action</th><th>Type</th><th>Status</th><th>Rationale</th></tr></thead><tbody>
              {rollbacks.map((item) => <tr key={item.id}><td>#{item.linked_manual_action}</td><td>{item.rollback_type}</td><td><span className={statusBadgeClass(item.rollback_status)}>{item.rollback_status}</span></td><td>{item.rationale}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Recommendations" title="Adoption recommendations" description="Explicit conservative guidance for operator sequencing and safeguards.">
          {!recommendations.length ? <p className="muted-text">No adoption recommendations generated yet.</p> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Recommendation</th><th>Case</th><th>Rationale</th><th>Reason codes</th><th>Confidence</th></tr></thead><tbody>
              {recommendations.map((item) => <tr key={item.id}><td><span className={statusBadgeClass(item.recommendation_type)}>{item.recommendation_type}</span></td><td>{item.linked_promotion_case ? `#${item.linked_promotion_case}` : 'Run-level'}</td><td>{item.rationale}</td><td>{item.reason_codes.join(', ') || 'None'}</td><td>{item.confidence}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
