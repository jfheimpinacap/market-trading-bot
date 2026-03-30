import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { navigate } from '../../lib/router';
import {
  activatePaperBaseline,
  getActivePaperBindings,
  getBaselineActivationCandidates,
  getBaselineActivationRecommendations,
  getBaselineActivationSummary,
  getBaselineActivations,
  rollbackActivation,
  runBaselineActivationReview,
} from '../../services/baselineActivation';
import {
  getBaselineResponseCases,
  getBaselineResponseEvidencePacks,
  getBaselineResponseRecommendations,
  getBaselineResponseRoutingDecisions,
  getBaselineResponseSummary,
  runBaselineResponseReview,
} from '../../services/baselineResponse';
import {
  getBaselineHealthCandidates,
  getBaselineHealthRecommendations,
  getBaselineHealthSignals,
  getBaselineHealthStatuses,
  getBaselineHealthSummary,
  runBaselineHealthReview,
} from '../../services/baselineHealth';
import {
  confirmPaperBaseline,
  getBaselineBindingSnapshots,
  getBaselineConfirmationCandidates,
  getBaselineConfirmations,
  getBaselineRecommendations,
  getBaselineSummary,
  rollbackPaperBaseline,
  runBaselineConfirmationReview,
} from '../../services/baselineConfirmation';
import {
  getCertificationCandidates,
  getCertificationDecisions,
  getCertificationEvidencePacks,
  getCertificationRecommendations,
  getCertificationSummary,
  runPostRolloutCertificationReview,
} from '../../services/certificationReview';
import type {
  ActivePaperBindingRecord,
  BaselineActivationCandidate,
  BaselineActivationRecommendationItem,
  BaselineActivationSummary,
  BaselineHealthCandidate,
  BaselineHealthRecommendationItem,
  BaselineHealthSignal,
  BaselineHealthStatus,
  BaselineHealthSummary,
  BaselineResponseCase,
  BaselineResponseRecommendationItem,
  BaselineResponseSummary,
  BaselineBindingSnapshot,
  BaselineConfirmationCandidate,
  BaselineConfirmationRecommendationItem,
  BaselineConfirmationSummary,
  CertificationCandidate,
  CertificationDecision,
  CertificationEvidencePack,
  CertificationRecommendationItem,
  PostRolloutCertificationSummary,
  PaperBaselineActivation,
  PaperBaselineConfirmation,
  ResponseEvidencePack,
  ResponseRoutingDecision,
} from '../../types/certification';

const toneFromState = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const normalized = value.toUpperCase();
  if (['READY', 'CERTIFIED_FOR_PAPER_BASELINE', 'STRONG'].includes(normalized)) return 'ready';
  if (['NEEDS_OBSERVATION', 'KEEP_UNDER_OBSERVATION', 'MIXED', 'WEAK', 'UNDER_REVIEW', 'ROUTED', 'MEDIUM'].includes(normalized)) return 'pending';
  if (['ROLLBACK_RECOMMENDED', 'RECOMMEND_ROLLBACK', 'REJECT_CERTIFICATION', 'INSUFFICIENT', 'BLOCKED', 'CRITICAL', 'HIGH', 'ESCALATED', 'PREPARE_ROLLBACK_REVIEW'].includes(normalized)) return 'offline';
  return 'neutral';
};

const formatDate = (value: string | null) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

export function CertificationPage() {
  const [summary, setSummary] = useState<PostRolloutCertificationSummary | null>(null);
  const [candidates, setCandidates] = useState<CertificationCandidate[]>([]);
  const [evidencePacks, setEvidencePacks] = useState<CertificationEvidencePack[]>([]);
  const [decisions, setDecisions] = useState<CertificationDecision[]>([]);
  const [recommendations, setRecommendations] = useState<CertificationRecommendationItem[]>([]);
  const [baselineSummary, setBaselineSummary] = useState<BaselineConfirmationSummary | null>(null);
  const [baselineCandidates, setBaselineCandidates] = useState<BaselineConfirmationCandidate[]>([]);
  const [baselineConfirmations, setBaselineConfirmations] = useState<PaperBaselineConfirmation[]>([]);
  const [bindingSnapshots, setBindingSnapshots] = useState<BaselineBindingSnapshot[]>([]);
  const [baselineRecommendations, setBaselineRecommendations] = useState<BaselineConfirmationRecommendationItem[]>([]);
  const [activationSummary, setActivationSummary] = useState<BaselineActivationSummary | null>(null);
  const [activationCandidates, setActivationCandidates] = useState<BaselineActivationCandidate[]>([]);
  const [baselineActivations, setBaselineActivations] = useState<PaperBaselineActivation[]>([]);
  const [activeBindings, setActiveBindings] = useState<ActivePaperBindingRecord[]>([]);
  const [activationRecommendations, setActivationRecommendations] = useState<BaselineActivationRecommendationItem[]>([]);
  const [healthSummary, setHealthSummary] = useState<BaselineHealthSummary | null>(null);
  const [healthCandidates, setHealthCandidates] = useState<BaselineHealthCandidate[]>([]);
  const [healthStatuses, setHealthStatuses] = useState<BaselineHealthStatus[]>([]);
  const [healthSignals, setHealthSignals] = useState<BaselineHealthSignal[]>([]);
  const [healthRecommendations, setHealthRecommendations] = useState<BaselineHealthRecommendationItem[]>([]);
  const [responseSummary, setResponseSummary] = useState<BaselineResponseSummary | null>(null);
  const [responseCases, setResponseCases] = useState<BaselineResponseCase[]>([]);
  const [responseEvidencePacks, setResponseEvidencePacks] = useState<ResponseEvidencePack[]>([]);
  const [responseRoutingDecisions, setResponseRoutingDecisions] = useState<ResponseRoutingDecision[]>([]);
  const [responseRecommendations, setResponseRecommendations] = useState<BaselineResponseRecommendationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [runningBaseline, setRunningBaseline] = useState(false);
  const [runningActivation, setRunningActivation] = useState(false);
  const [runningHealth, setRunningHealth] = useState(false);
  const [runningResponse, setRunningResponse] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, candidatesRes, evidenceRes, decisionsRes, recommendationsRes, baselineSummaryRes, baselineCandidatesRes, baselineConfirmationsRes, bindingSnapshotsRes, baselineRecommendationsRes, activationSummaryRes, activationCandidatesRes, baselineActivationsRes, activeBindingsRes, activationRecommendationsRes, healthSummaryRes, healthCandidatesRes, healthStatusesRes, healthSignalsRes, healthRecommendationsRes, responseSummaryRes, responseCasesRes, responseEvidencePacksRes, responseRoutingRes, responseRecommendationsRes] = await Promise.all([
        getCertificationSummary(),
        getCertificationCandidates(),
        getCertificationEvidencePacks(),
        getCertificationDecisions(),
        getCertificationRecommendations(),
        getBaselineSummary(),
        getBaselineConfirmationCandidates(),
        getBaselineConfirmations(),
        getBaselineBindingSnapshots(),
        getBaselineRecommendations(),
        getBaselineActivationSummary(),
        getBaselineActivationCandidates(),
        getBaselineActivations(),
        getActivePaperBindings(),
        getBaselineActivationRecommendations(),
        getBaselineHealthSummary(),
        getBaselineHealthCandidates(),
        getBaselineHealthStatuses(),
        getBaselineHealthSignals(),
        getBaselineHealthRecommendations(),
        getBaselineResponseSummary(),
        getBaselineResponseCases(),
        getBaselineResponseEvidencePacks(),
        getBaselineResponseRoutingDecisions(),
        getBaselineResponseRecommendations(),
      ]);
      setSummary(summaryRes);
      setCandidates(candidatesRes);
      setEvidencePacks(evidenceRes);
      setDecisions(decisionsRes);
      setRecommendations(recommendationsRes);
      setBaselineSummary(baselineSummaryRes);
      setBaselineCandidates(baselineCandidatesRes);
      setBaselineConfirmations(baselineConfirmationsRes);
      setBindingSnapshots(bindingSnapshotsRes);
      setBaselineRecommendations(baselineRecommendationsRes);
      setActivationSummary(activationSummaryRes);
      setActivationCandidates(activationCandidatesRes);
      setBaselineActivations(baselineActivationsRes);
      setActiveBindings(activeBindingsRes);
      setActivationRecommendations(activationRecommendationsRes);
      setHealthSummary(healthSummaryRes);
      setHealthCandidates(healthCandidatesRes);
      setHealthStatuses(healthStatusesRes);
      setHealthSignals(healthSignalsRes);
      setHealthRecommendations(healthRecommendationsRes);
      setResponseSummary(responseSummaryRes);
      setResponseCases(responseCasesRes);
      setResponseEvidencePacks(responseEvidencePacksRes);
      setResponseRoutingDecisions(responseRoutingRes);
      setResponseRecommendations(responseRecommendationsRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load certification stabilization state.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runBaselineReview = useCallback(async () => {
    setRunningBaseline(true);
    setError(null);
    try {
      await runBaselineConfirmationReview({ actor: 'certification_ui', metadata: { initiated_from: 'certification_ui' } });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run baseline confirmation review.');
    } finally {
      setRunningBaseline(false);
    }
  }, [load]);

  const confirmBaseline = useCallback(async (decisionId: number) => {
    try {
      await confirmPaperBaseline(decisionId, { actor: 'certification_ui' });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not confirm paper baseline.');
    }
  }, [load]);

  const rollbackBaseline = useCallback(async (confirmationId: number) => {
    try {
      await rollbackPaperBaseline(confirmationId, { actor: 'certification_ui' });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not prepare baseline rollback.');
    }
  }, [load]);

  const runReview = useCallback(async () => {
    setRunning(true);
    setError(null);
    try {
      await runPostRolloutCertificationReview({ actor: 'certification_ui', metadata: { initiated_from: 'certification_ui' } });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run post-rollout certification review.');
    } finally {
      setRunning(false);
    }
  }, [load]);



  const runActivationReview = useCallback(async () => {
    setRunningActivation(true);
    setError(null);
    try {
      await runBaselineActivationReview({ actor: 'certification_ui', metadata: { initiated_from: 'certification_ui' } });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run baseline activation review.');
    } finally {
      setRunningActivation(false);
    }
  }, [load]);

  const runHealthReview = useCallback(async () => {
    setRunningHealth(true);
    setError(null);
    try {
      await runBaselineHealthReview({ actor: 'certification_ui', metadata: { initiated_from: 'certification_ui' } });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run baseline health review.');
    } finally {
      setRunningHealth(false);
    }
  }, [load]);

  const runResponseReview = useCallback(async () => {
    setRunningResponse(true);
    setError(null);
    try {
      await runBaselineResponseReview({ actor: 'certification_ui', metadata: { initiated_from: 'certification_ui' } });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run baseline response review.');
    } finally {
      setRunningResponse(false);
    }
  }, [load]);

  const activateBaseline = useCallback(async (confirmationId: number) => {
    try {
      await activatePaperBaseline(confirmationId, { actor: 'certification_ui' });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not activate paper baseline.');
    }
  }, [load]);

  const rollbackActivatedBaseline = useCallback(async (activationId: number) => {
    try {
      await rollbackActivation(activationId, { actor: 'certification_ui' });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not rollback activation.');
    }
  }, [load]);

  const hasCandidates = useMemo(() => candidates.length > 0, [candidates.length]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Rollout certification board"
        title="/certification"
        description="Post-rollout stabilization gate for manual-first, local-first, paper-only governance. Execute ≠ certify: this board consolidates rollout evidence and recommends certify/observe/review/rollback without auto-apply."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/promotion')}>Open Promotion</button><button type="button" className="secondary-button" onClick={() => navigate('/evaluation')}>Open Evaluation</button><button type="button" className="secondary-button" onClick={() => navigate('/trace')}>Open Trace</button><button type="button" className="secondary-button" onClick={() => navigate('/cockpit')}>Open Cockpit</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Actions" title="Run post-rollout certification review" description="Manual operator trigger. No auto-certification, no auto-promotion, no automatic baseline switch.">
          <button type="button" className="primary-button" onClick={() => void runReview()} disabled={running}>{running ? 'Running…' : 'Run post-rollout review'}</button>
          <button type="button" className="secondary-button" onClick={() => void runBaselineReview()} disabled={runningBaseline} style={{ marginLeft: 8 }}>{runningBaseline ? 'Running…' : 'Run baseline confirmation'}</button>
          <button type="button" className="secondary-button" onClick={() => void runActivationReview()} disabled={runningActivation} style={{ marginLeft: 8 }}>{runningActivation ? 'Running…' : 'Run baseline activation'}</button>
          <button type="button" className="secondary-button" onClick={() => void runHealthReview()} disabled={runningHealth} style={{ marginLeft: 8 }}>{runningHealth ? 'Running…' : 'Run baseline health review'}</button>
          <button type="button" className="secondary-button" onClick={() => void runResponseReview()} disabled={runningResponse} style={{ marginLeft: 8 }}>{runningResponse ? 'Running…' : 'Run baseline response review'}</button>
        </SectionCard>

        <SectionCard eyebrow="Summary" title="Stabilization outcomes" description="Latest review counters for certification, observation, manual review, rollback recommendation, and rejection.">
          <div className="cockpit-metric-grid">
            <div><strong>Candidates reviewed:</strong> {summary?.candidate_count ?? 0}</div>
            <div><strong>Certified:</strong> {summary?.certified_count ?? 0}</div>
            <div><strong>Under observation:</strong> {summary?.observation_count ?? 0}</div>
            <div><strong>Review required:</strong> {summary?.review_required_count ?? 0}</div>
            <div><strong>Rollback recommended:</strong> {summary?.rollback_recommended_count ?? 0}</div>
            <div><strong>Rejected:</strong> {summary?.rejected_count ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Baseline activation board" title="Manual active paper baseline registry" description="Confirmed baselines are reviewed for manual activation into active paper bindings with explicit rollback and no auto-switch.">
          <div className="cockpit-metric-grid">
            <div><strong>Confirmed baselines:</strong> {activationSummary?.confirmed_baselines ?? 0}</div>
            <div><strong>Ready to activate:</strong> {activationSummary?.ready_to_activate_count ?? 0}</div>
            <div><strong>Blocked:</strong> {activationSummary?.blocked_count ?? 0}</div>
            <div><strong>Activated:</strong> {activationSummary?.activated_count ?? 0}</div>
            <div><strong>Rollback available:</strong> {activationSummary?.rollback_available_count ?? 0}</div>
            <div><strong>Binding recheck required:</strong> {activationSummary?.binding_recheck_required_count ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Active baseline health watch" title="Degradation watch & re-evaluation trigger loop" description="Active baseline health is monitored continuously with recommendation-first governance. No auto-deactivate, no auto-retune, no auto-switch.">
          <div className="cockpit-metric-grid">
            <div><strong>Active baselines reviewed:</strong> {healthSummary?.active_baselines_reviewed ?? 0}</div>
            <div><strong>Healthy:</strong> {healthSummary?.healthy_count ?? 0}</div>
            <div><strong>Under watch:</strong> {healthSummary?.under_watch_count ?? 0}</div>
            <div><strong>Degraded:</strong> {healthSummary?.degraded_count ?? 0}</div>
            <div><strong>Review required:</strong> {healthSummary?.review_required_count ?? 0}</div>
            <div><strong>Rollback review recommended:</strong> {healthSummary?.rollback_review_recommended_count ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Baseline response board" title="Health-to-retuning governance loop" description="Manual-first response case registry that converts baseline health pressure into auditable response cases, evidence packs, routing decisions and recommendations.">
          <div className="cockpit-metric-grid">
            <div><strong>Active baselines reviewed:</strong> {responseSummary?.active_baselines_reviewed ?? 0}</div>
            <div><strong>Open response cases:</strong> {responseSummary?.open_response_cases ?? 0}</div>
            <div><strong>Re-evaluation cases:</strong> {responseSummary?.reevaluation_case_count ?? 0}</div>
            <div><strong>Tuning cases:</strong> {responseSummary?.tuning_case_count ?? 0}</div>
            <div><strong>Rollback review cases:</strong> {responseSummary?.rollback_review_case_count ?? 0}</div>
            <div><strong>Cases under watch:</strong> {responseSummary?.watch_case_count ?? 0}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Baseline confirmation board" title="Manual paper baseline adoption" description="Certification decides readiness; this board confirms baseline manually with before/after snapshots, binding review, and rollback preparation. No auto-switch champion, no silent baseline apply.">
          <div className="cockpit-metric-grid">
            <div><strong>Certified decisions:</strong> {baselineSummary?.candidate_count ?? 0}</div>
            <div><strong>Ready to confirm:</strong> {baselineSummary?.ready_to_confirm_count ?? 0}</div>
            <div><strong>Blocked:</strong> {baselineSummary?.blocked_count ?? 0}</div>
            <div><strong>Confirmed:</strong> {baselineSummary?.confirmed_count ?? 0}</div>
            <div><strong>Rollback available:</strong> {baselineSummary?.rollback_ready_count ?? 0}</div>
            <div><strong>Binding review required:</strong> {baselineSummary?.binding_review_required_count ?? 0}</div>
          </div>
        </SectionCard>

        {baselineCandidates.length === 0 ? (
          <EmptyState
            eyebrow="No baseline candidates"
            title="No certified paper baseline candidates are available yet."
            description="Run baseline confirmation to prepare safe manual baseline adoption. BLOCKED and REQUIRE_BINDING_REVIEW are valid governance outcomes."
          />
        ) : null}
        {activeBindings.length === 0 ? (
          <EmptyState
            eyebrow="No active baselines yet"
            title="No active paper baselines are available yet."
            description="Run baseline health review to monitor stability and degradation signals."
          />
        ) : null}
        {responseCases.length === 0 ? (
          <EmptyState
            eyebrow="No baseline response cases"
            title="No baseline response cases are available yet."
            description="Run baseline response review to formalize degradation handling and re-evaluation paths."
          />
        ) : null}

        {!hasCandidates ? (
          <EmptyState
            eyebrow="No post-rollout candidates"
            title="No post-rollout certification candidates are available yet."
            description="Run certification review to evaluate stabilization and baseline readiness. KEEP_UNDER_OBSERVATION and REJECT_CERTIFICATION are valid governance outcomes, not errors."
          />
        ) : (
          <>
            <SectionCard eyebrow="Candidates" title="Certification candidates" description="Rollout executions mapped into explicit stabilization readiness states.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>ID</th><th>Target</th><th>Scope</th><th>Rollout status</th><th>Readiness</th><th>Blockers</th><th>Trace chain</th></tr></thead><tbody>
                {candidates.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.id}</td>
                    <td>{row.target_component}</td>
                    <td>{row.target_scope}</td>
                    <td>{row.rollout_status}</td>
                    <td><StatusBadge tone={toneFromState(row.stabilization_readiness)}>{row.stabilization_readiness}</StatusBadge></td>
                    <td>{row.blockers.join(', ') || '—'}</td>
                    <td>promotion_case:{String((row.metadata.trace_chain as Record<string, unknown> | undefined)?.promotion_case_id ?? '—')} / experiment:{String((row.metadata.trace_chain as Record<string, unknown> | undefined)?.experiment_candidate_id ?? '—')}</td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Evidence" title="Evidence packs" description="Checkpoint outcomes, post-rollout signals and evaluation context merged into auditable packs.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Candidate</th><th>Summary</th><th>Samples</th><th>Confidence</th><th>Stability</th><th>Regression risk</th><th>Status</th></tr></thead><tbody>
                {evidencePacks.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.linked_candidate}</td>
                    <td>{row.summary}</td>
                    <td>{row.sample_count}</td>
                    <td>{row.confidence_score}</td>
                    <td>{row.stability_score}</td>
                    <td>{row.regression_risk_score}</td>
                    <td><StatusBadge tone={toneFromState(row.evidence_status)}>{row.evidence_status}</StatusBadge></td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Decisions" title="Certification decisions" description="Final stabilization decisions (manual-first) with rationale and reason codes.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Candidate</th><th>Decision</th><th>Rationale</th><th>Reason codes</th><th>Decided by</th><th>Decided at</th></tr></thead><tbody>
                {decisions.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.linked_candidate}</td>
                    <td><StatusBadge tone={toneFromState(row.decision_status)}>{row.decision_status}</StatusBadge></td>
                    <td>{row.rationale}</td>
                    <td>{row.reason_codes.join(', ') || '—'}</td>
                    <td>{row.decided_by || 'manual_pending'}</td>
                    <td>{formatDate(row.decided_at)}</td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Recommendations" title="Certification recommendations" description="Conservative recommendations for certify/observe/review/rollback/reject, never auto-applied.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Candidate</th><th>Recommendation</th><th>Rationale</th><th>Reason codes</th><th>Confidence</th></tr></thead><tbody>
                {recommendations.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>{row.target_candidate ? `#${row.target_candidate}` : '—'}</td>
                    <td><StatusBadge tone={toneFromState(row.recommendation_type)}>{row.recommendation_type}</StatusBadge></td>
                    <td>{row.rationale}</td>
                    <td>{row.reason_codes.join(', ') || '—'}</td>
                    <td>{row.confidence}</td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Baseline candidates" title="Certified changes ready for baseline confirmation" description="Candidate lineage with previous/proposed baseline references and binding resolution status.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>ID</th><th>Component</th><th>Scope</th><th>Previous baseline</th><th>Proposed baseline</th><th>Binding resolution</th><th>Blockers</th><th>Actions</th></tr></thead><tbody>
                {baselineCandidates.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.id}</td>
                    <td>{row.target_component}</td>
                    <td>{row.target_scope}</td>
                    <td>{row.previous_baseline_reference || '—'}</td>
                    <td>{row.proposed_baseline_reference || '—'}</td>
                    <td><StatusBadge tone={toneFromState(row.binding_resolution_status)}>{row.binding_resolution_status}</StatusBadge></td>
                    <td>{row.blockers.join(', ') || '—'}</td>
                    <td><button type="button" className="secondary-button" disabled={!row.ready_for_confirmation} onClick={() => void confirmBaseline(row.linked_certification_decision)}>Confirm baseline</button></td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Baseline confirmations" title="Manual confirmation registry" description="Explicit baseline adoption logs with confirmed actor/time and rationale.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>ID</th><th>Status</th><th>Previous snapshot</th><th>Confirmed snapshot</th><th>Confirmed by</th><th>Confirmed at</th><th>Rationale</th><th>Rollback</th></tr></thead><tbody>
                {baselineConfirmations.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.id}</td>
                    <td><StatusBadge tone={toneFromState(row.confirmation_status)}>{row.confirmation_status}</StatusBadge></td>
                    <td>{String((row.previous_baseline_snapshot as Record<string, unknown>).reference ?? '—')}</td>
                    <td>{String((row.confirmed_baseline_snapshot as Record<string, unknown>).reference ?? '—')}</td>
                    <td>{row.confirmed_by || 'manual_pending'}</td>
                    <td>{formatDate(row.confirmed_at)}</td>
                    <td>{row.rationale}</td>
                    <td><button type="button" className="secondary-button" onClick={() => void rollbackBaseline(row.id)}>Prepare rollback</button></td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Binding snapshots" title="Before/after baseline references" description="Champion/stack/trust/policy/rollout snapshots captured for auditable baseline transitions.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Confirmation</th><th>Binding type</th><th>Status</th><th>Snapshot</th></tr></thead><tbody>
                {bindingSnapshots.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.linked_confirmation}</td>
                    <td>{row.binding_type}</td>
                    <td><StatusBadge tone={toneFromState(row.binding_status)}>{row.binding_status}</StatusBadge></td>
                    <td>{JSON.stringify(row.binding_snapshot).slice(0, 120)}</td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Baseline recommendations" title="Manual-first adoption recommendations" description="Recommendations for confirm/defer/recheck/binding review/rollback; never auto-applied.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Confirmation</th><th>Recommendation</th><th>Rationale</th><th>Reason codes</th><th>Confidence</th></tr></thead><tbody>
                {baselineRecommendations.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>{row.target_confirmation ? `#${row.target_confirmation}` : '—'}</td>
                    <td><StatusBadge tone={toneFromState(row.recommendation_type)}>{row.recommendation_type}</StatusBadge></td>
                    <td>{row.rationale}</td>
                    <td>{row.reason_codes.join(', ') || '—'}</td>
                    <td>{row.confidence}</td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Activation candidates" title="Confirmed baselines ready for manual activation" description="Activation candidates resolve previous active binding vs proposed active binding and keep blockers explicit.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>ID</th><th>Component</th><th>Scope</th><th>Previous active</th><th>Proposed active</th><th>Resolution</th><th>Blockers</th><th>Actions</th></tr></thead><tbody>
                {activationCandidates.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.id}</td>
                    <td>{row.target_component}</td>
                    <td>{row.target_scope}</td>
                    <td>{row.previous_active_reference || '—'}</td>
                    <td>{row.proposed_active_reference || '—'}</td>
                    <td><StatusBadge tone={toneFromState(row.activation_resolution_status)}>{row.activation_resolution_status}</StatusBadge></td>
                    <td>{row.blockers.join(', ') || '—'}</td>
                    <td><button type="button" className="secondary-button" disabled={!row.ready_for_activation} onClick={() => void activateBaseline(row.linked_paper_baseline_confirmation)}>Activate baseline</button></td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Baseline activations" title="Manual activation records" description="Before/after snapshots of active paper bindings with explicit actor and rollback pathway.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>ID</th><th>Status</th><th>Previous</th><th>Activated</th><th>By</th><th>At</th><th>Rationale</th><th>Rollback</th></tr></thead><tbody>
                {baselineActivations.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.id}</td>
                    <td><StatusBadge tone={toneFromState(row.activation_status)}>{row.activation_status}</StatusBadge></td>
                    <td>{String((row.previous_active_snapshot as Record<string, unknown>).reference ?? '—')}</td>
                    <td>{String((row.activated_snapshot as Record<string, unknown>).reference ?? '—')}</td>
                    <td>{row.activated_by || 'manual_pending'}</td>
                    <td>{formatDate(row.activated_at)}</td>
                    <td>{row.rationale}</td>
                    <td><button type="button" className="secondary-button" onClick={() => void rollbackActivatedBaseline(row.id)}>Rollback activation</button></td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Active paper bindings" title="Current active paper baseline/config by component" description="Explicit registry of current active binding references and status transitions (ACTIVE, SUPERSEDED, REVERTED).">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>ID</th><th>Component</th><th>Scope</th><th>Binding type</th><th>Status</th><th>Source activation</th><th>Snapshot</th></tr></thead><tbody>
                {activeBindings.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.id}</td>
                    <td>{row.target_component}</td>
                    <td>{row.target_scope}</td>
                    <td>{row.active_binding_type}</td>
                    <td><StatusBadge tone={toneFromState(row.status)}>{row.status}</StatusBadge></td>
                    <td>{row.source_activation ? `#${row.source_activation}` : '—'}</td>
                    <td>{JSON.stringify(row.active_snapshot).slice(0, 120)}</td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Activation recommendations" title="Manual-first activation recommendations" description="Activate/defer/recheck/rollback recommendations for paper baseline activation; never auto-applied.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Activation</th><th>Recommendation</th><th>Rationale</th><th>Reason codes</th><th>Confidence</th></tr></thead><tbody>
                {activationRecommendations.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>{row.target_activation ? `#${row.target_activation}` : '—'}</td>
                    <td><StatusBadge tone={toneFromState(row.recommendation_type)}>{row.recommendation_type}</StatusBadge></td>
                    <td>{row.rationale}</td>
                    <td>{row.reason_codes.join(', ') || '—'}</td>
                    <td>{row.confidence}</td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Health candidates" title="Active baseline health candidates" description="Active binding candidates and readiness status with baseline lineage and blockers.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>ID</th><th>Component</th><th>Scope</th><th>Active binding</th><th>Readiness</th><th>Blockers</th><th>Trace links</th></tr></thead><tbody>
                {healthCandidates.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.id}</td>
                    <td>{row.target_component}</td>
                    <td>{row.target_scope}</td>
                    <td>#{row.linked_active_binding}</td>
                    <td><StatusBadge tone={toneFromState(row.readiness_status)}>{row.readiness_status}</StatusBadge></td>
                    <td>{row.blockers.join(', ') || '—'}</td>
                    <td><button type="button" className="link-button" onClick={() => navigate('/evaluation')}>evaluation</button> · <button type="button" className="link-button" onClick={() => navigate('/tuning')}>tuning</button> · <button type="button" className="link-button" onClick={() => navigate('/experiments')}>experiments</button> · <button type="button" className="link-button" onClick={() => navigate('/trace')}>trace</button></td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Health status" title="Current baseline health status" description="Per-baseline health status with calibration/risk/opportunity quality and drift/regression risk scores.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Candidate</th><th>Status</th><th>Calibration</th><th>Risk gate</th><th>Opportunity quality</th><th>Drift risk</th><th>Regression risk</th><th>Rationale</th></tr></thead><tbody>
                {healthStatuses.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.linked_candidate}</td>
                    <td><StatusBadge tone={toneFromState(row.health_status)}>{row.health_status}</StatusBadge></td>
                    <td>{row.calibration_health_score}</td>
                    <td>{row.risk_gate_health_score}</td>
                    <td>{row.opportunity_quality_health_score}</td>
                    <td>{row.drift_risk_score}</td>
                    <td>{row.regression_risk_score}</td>
                    <td>{row.rationale}</td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Health signals" title="Degradation and watch signals" description="Concrete signals that explain why a baseline is healthy, under watch, degraded or pending rollback review.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Status</th><th>Signal</th><th>Severity</th><th>Direction</th><th>Rationale</th><th>Evidence</th></tr></thead><tbody>
                {healthSignals.slice(0, 150).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.linked_status}</td>
                    <td>{row.signal_type}</td>
                    <td><StatusBadge tone={toneFromState(row.signal_severity)}>{row.signal_severity}</StatusBadge></td>
                    <td>{row.signal_direction}</td>
                    <td>{row.rationale}</td>
                    <td>{JSON.stringify(row.evidence_summary).slice(0, 140)}</td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Health recommendations" title="Recommendation-first baseline health actions" description="Conservative recommendations to keep/watch/re-evaluate/tune/review rollback with manual apply only.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Status</th><th>Recommendation</th><th>Rationale</th><th>Reason codes</th><th>Confidence</th></tr></thead><tbody>
                {healthRecommendations.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>{row.target_status ? `#${row.target_status}` : '—'}</td>
                    <td><StatusBadge tone={toneFromState(row.recommendation_type)}>{row.recommendation_type}</StatusBadge></td>
                    <td>{row.rationale}</td>
                    <td>{row.reason_codes.join(', ') || '—'}</td>
                    <td>{row.confidence}</td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Response cases" title="Formal baseline response case registry" description="Each case maps active baseline health pressure to manual-first response type, priority, status and explicit lineage.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Case</th><th>Component</th><th>Scope</th><th>Response type</th><th>Priority</th><th>Status</th><th>Blockers</th><th>Links</th></tr></thead><tbody>
                {responseCases.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.id}</td>
                    <td>{row.target_component}</td>
                    <td>{row.target_scope}</td>
                    <td><StatusBadge tone={toneFromState(row.response_type)}>{row.response_type}</StatusBadge></td>
                    <td><StatusBadge tone={toneFromState(row.priority_level)}>{row.priority_level}</StatusBadge></td>
                    <td><StatusBadge tone={toneFromState(row.case_status)}>{row.case_status}</StatusBadge></td>
                    <td>{row.blockers.join(', ') || '—'}</td>
                    <td><button type="button" className="link-button" onClick={() => navigate('/evaluation')}>evaluation</button> · <button type="button" className="link-button" onClick={() => navigate('/tuning')}>tuning</button> · <button type="button" className="link-button" onClick={() => navigate('/trace')}>trace</button></td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Response evidence packs" title="Evidence quality for baseline response cases" description="Aggregated health/evaluation/risk/opportunity context with conservative confidence, severity and urgency scoring.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Case</th><th>Summary</th><th>Confidence</th><th>Severity</th><th>Urgency</th><th>Evidence status</th></tr></thead><tbody>
                {responseEvidencePacks.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.linked_response_case}</td>
                    <td>{row.summary}</td>
                    <td>{row.confidence_score}</td>
                    <td>{row.severity_score}</td>
                    <td>{row.urgency_score}</td>
                    <td><StatusBadge tone={toneFromState(row.evidence_status)}>{row.evidence_status}</StatusBadge></td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Routing decisions" title="Downstream routing for response governance" description="Routing remains manual-first: no auto-retune, no auto-rollback, no auto-deactivate.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Case</th><th>Target</th><th>Status</th><th>Rationale</th></tr></thead><tbody>
                {responseRoutingDecisions.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>#{row.linked_response_case}</td>
                    <td>{row.routing_target}</td>
                    <td><StatusBadge tone={toneFromState(row.routing_status)}>{row.routing_status}</StatusBadge></td>
                    <td>{row.routing_rationale}</td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Response recommendations" title="Manual-first next-step recommendations" description="Recommendations can keep monitoring, request more evidence, route re-evaluation/tuning/rollback review, or request committee-level recheck.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Case</th><th>Recommendation</th><th>Rationale</th><th>Reason codes</th><th>Confidence</th></tr></thead><tbody>
                {responseRecommendations.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>{row.target_case ? `#${row.target_case}` : '—'}</td>
                    <td><StatusBadge tone={toneFromState(row.recommendation_type)}>{row.recommendation_type}</StatusBadge></td>
                    <td>{row.rationale}</td>
                    <td>{row.reason_codes.join(', ') || '—'}</td>
                    <td>{row.confidence}</td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

          </>
        )}
      </DataStateWrapper>
    </div>
  );
}
