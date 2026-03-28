import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  applyPolicyTuningCandidate,
  getPolicyTuningApplicationLogs,
  getPolicyTuningCandidates,
  getPolicyTuningSummary,
  reviewPolicyTuningCandidate,
} from '../../services/policyTuning';
import type { PolicyTuningReviewDecision } from '../../types/policyTuning';

const formatDate = (value: string | null | undefined) => (value ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—');

function tone(status: string): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (status === 'APPROVED' || status === 'APPLIED') return 'ready';
  if (status === 'PENDING_APPROVAL' || status === 'DRAFT') return 'pending';
  if (status === 'REJECTED' || status === 'SUPERSEDED') return 'offline';
  return 'neutral';
}

export function PolicyTuningPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getPolicyTuningSummary>> | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getPolicyTuningCandidates>>>([]);
  const [logs, setLogs] = useState<Awaited<ReturnType<typeof getPolicyTuningApplicationLogs>>>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryPayload, candidatesPayload, logsPayload] = await Promise.all([
        getPolicyTuningSummary(),
        getPolicyTuningCandidates(),
        getPolicyTuningApplicationLogs(),
      ]);
      setSummary(summaryPayload);
      setCandidates(candidatesPayload);
      setLogs(logsPayload);
      setSelectedId((current) => current ?? candidatesPayload[0]?.id ?? null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load policy tuning board.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const selected = useMemo(() => candidates.find((candidate) => candidate.id === selectedId) ?? null, [candidates, selectedId]);

  const runReview = useCallback(async (decision: PolicyTuningReviewDecision) => {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await reviewPolicyTuningCandidate(selected.id, { decision, reviewer_note: `Operator decision: ${decision}.` });
      setMessage(`Candidate #${selected.id} reviewed: ${decision}.`);
      await load();
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : 'Review action failed.');
    } finally {
      setBusy(false);
    }
  }, [load, selected]);

  const applySelected = useCallback(async () => {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await applyPolicyTuningCandidate(selected.id, { note: 'Manual-first apply via /policy-tuning.' });
      setMessage(`Candidate #${selected.id} applied to automation policy.`);
      await load();
    } catch (applyError) {
      setError(applyError instanceof Error ? applyError.message : 'Apply action failed.');
    } finally {
      setBusy(false);
    }
  }, [load, selected]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Supervised automation tuning"
        title="/policy-tuning"
        description="Policy tuning board for recommendation-to-approval workflow. Candidates are created from trust calibration evidence, reviewed explicitly, and applied manually with before/after audit snapshots. No auto-apply."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/trust-calibration')}>Trust calibration</button><button type="button" className="secondary-button" onClick={() => navigate('/automation-policy')}>Automation policy</button><button type="button" className="secondary-button" onClick={() => navigate('/policy-rollout')}>Policy rollout</button><button type="button" className="secondary-button" onClick={() => navigate('/approvals')}>Approvals</button><button type="button" className="ghost-button" onClick={() => navigate('/trace')}>Trace explorer</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Manual-first guardrail" title="No opaque policy mutation" description="Every change remains explicit: recommendation -> candidate -> review -> manual apply -> application log.">
          <div className="cockpit-metric-grid">
            <div><strong>Pending candidates</strong><div>{summary?.pending_candidates ?? 0}</div></div>
            <div><strong>Approved not applied</strong><div>{summary?.approved_not_applied ?? 0}</div></div>
            <div><strong>Applied recently</strong><div>{summary?.applied_recently ?? 0}</div></div>
            <div><strong>Rejected/deferred track</strong><div>{summary?.rejected_or_superseded ?? 0}</div></div>
          </div>
        </SectionCard>

        {candidates.length === 0 ? <EmptyState eyebrow="Policy tuning" title="No tuning candidates yet" description="Create a tuning candidate from a trust calibration recommendation." /> : null}

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Candidates" title="Review queue" description="Current tier vs proposed tier, confidence, status, and source recommendation.">
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>ID</th><th>Action</th><th>Tier diff</th><th>Confidence</th><th>Status</th><th>Source run</th></tr></thead>
                <tbody>
                  {candidates.map((candidate) => (
                    <tr key={candidate.id} className={selectedId === candidate.id ? 'is-selected-row' : ''} onClick={() => setSelectedId(candidate.id)}>
                      <td>#{candidate.id}</td>
                      <td>{candidate.action_type}</td>
                      <td>{candidate.current_trust_tier || 'n/a'} → {candidate.proposed_trust_tier || 'n/a'}</td>
                      <td>{candidate.confidence}</td>
                      <td><StatusBadge tone={tone(candidate.status)}>{candidate.status}</StatusBadge></td>
                      <td>{String(candidate.evidence_refs.find((ref) => ref.type === 'trust_calibration_run')?.id ?? 'n/a')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionCard>

          <SectionCard eyebrow="Candidate detail" title={selected ? `#${selected.id} diff + review` : 'Select a candidate'} description="Current vs proposed policy with rationale, evidence links, review controls, and manual apply.">
            {!selected ? <EmptyState eyebrow="Detail" title="Select a candidate" description="Pick one candidate to inspect diff, evidence, and review/apply controls." /> : (
              <div className="page-stack">
                <ul className="key-value-list">
                  <li><span>Action type</span><strong>{selected.action_type}</strong></li>
                  <li><span>Trust tier</span><strong>{selected.change_set?.old_trust_tier || selected.current_trust_tier || 'n/a'} → {selected.change_set?.new_trust_tier || selected.proposed_trust_tier || 'n/a'}</strong></li>
                  <li><span>Apply scope</span><strong>{selected.change_set?.apply_scope ?? 'RULE_ONLY'}</strong></li>
                  <li><span>Rationale</span><strong>{selected.rationale || '—'}</strong></li>
                  <li><span>Evidence refs</span><strong>{selected.evidence_refs.map((ref) => String(ref.type ?? '')).join(', ') || '—'}</strong></li>
                </ul>

                <div className="content-grid content-grid--two-columns">
                  <article className="status-card"><p className="status-card__label">Current conditions</p><pre>{JSON.stringify(selected.change_set?.old_conditions ?? {}, null, 2)}</pre></article>
                  <article className="status-card"><p className="status-card__label">Proposed conditions</p><pre>{JSON.stringify(selected.change_set?.new_conditions ?? selected.proposed_conditions ?? {}, null, 2)}</pre></article>
                </div>

                <div className="button-row">
                  <button type="button" className="secondary-button" disabled={busy} onClick={() => void runReview('APPROVE')}>Approve</button>
                  <button type="button" className="secondary-button" disabled={busy} onClick={() => void runReview('REJECT')}>Reject</button>
                  <button type="button" className="ghost-button" disabled={busy} onClick={() => void runReview('REQUIRE_MORE_EVIDENCE')}>Require more evidence</button>
                  <button type="button" className="ghost-button" disabled={busy} onClick={() => void runReview('DEFER')}>Defer</button>
                </div>

                <div className="button-row">
                  <button type="button" className="primary-button" disabled={busy || selected.status !== 'APPROVED'} onClick={() => void applySelected()}>Apply approved change</button>
                  <button type="button" className="secondary-button" disabled={selected.status !== 'APPLIED'} onClick={() => navigate('/policy-rollout')}>Open rollout monitor</button>
                  <button type="button" className="link-button" onClick={() => navigate(`/trace?root_type=trust_calibration_run&root_id=${encodeURIComponent(String(selected.evidence_refs.find((ref) => ref.type === 'trust_calibration_run')?.id ?? ''))}`)}>Open trace evidence</button>
                </div>

                {selected.application_logs.length === 0 ? <p className="muted-text">No application logs yet for this candidate.</p> : (
                  <div className="table-wrapper">
                    <table className="data-table">
                      <thead><tr><th>Applied at</th><th>Result</th><th>Before</th><th>After</th></tr></thead>
                      <tbody>
                        {selected.application_logs.map((log) => (
                          <tr key={log.id}>
                            <td>{formatDate(log.applied_at)}</td>
                            <td>{log.result_summary}</td>
                            <td><code>{JSON.stringify(log.before_snapshot)}</code></td>
                            <td><code>{JSON.stringify(log.after_snapshot)}</code></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </SectionCard>
        </div>

        <SectionCard eyebrow="Recent applications" title="Manual apply audit trail" description="Most recent before/after snapshots applied from approved candidates.">
          {logs.length === 0 ? <p className="muted-text">No policy tuning applications yet.</p> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Candidate</th><th>Applied at</th><th>Summary</th></tr></thead>
                <tbody>
                  {logs.slice(0, 10).map((log) => (
                    <tr key={log.id}>
                      <td>#{log.candidate}</td>
                      <td>{formatDate(log.applied_at)}</td>
                      <td>{log.result_summary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
