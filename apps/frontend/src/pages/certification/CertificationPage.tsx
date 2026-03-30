import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { navigate } from '../../lib/router';
import {
  getCertificationCandidates,
  getCertificationDecisions,
  getCertificationEvidencePacks,
  getCertificationRecommendations,
  getCertificationSummary,
  runPostRolloutCertificationReview,
} from '../../services/certificationReview';
import type {
  CertificationCandidate,
  CertificationDecision,
  CertificationEvidencePack,
  CertificationRecommendationItem,
  PostRolloutCertificationSummary,
} from '../../types/certification';

const toneFromState = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const normalized = value.toUpperCase();
  if (['READY', 'CERTIFIED_FOR_PAPER_BASELINE', 'STRONG'].includes(normalized)) return 'ready';
  if (['NEEDS_OBSERVATION', 'KEEP_UNDER_OBSERVATION', 'MIXED', 'WEAK'].includes(normalized)) return 'pending';
  if (['ROLLBACK_RECOMMENDED', 'RECOMMEND_ROLLBACK', 'REJECT_CERTIFICATION', 'INSUFFICIENT', 'BLOCKED'].includes(normalized)) return 'offline';
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
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, candidatesRes, evidenceRes, decisionsRes, recommendationsRes] = await Promise.all([
        getCertificationSummary(),
        getCertificationCandidates(),
        getCertificationEvidencePacks(),
        getCertificationDecisions(),
        getCertificationRecommendations(),
      ]);
      setSummary(summaryRes);
      setCandidates(candidatesRes);
      setEvidencePacks(evidenceRes);
      setDecisions(decisionsRes);
      setRecommendations(recommendationsRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load certification stabilization state.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
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
          </>
        )}
      </DataStateWrapper>
    </div>
  );
}
