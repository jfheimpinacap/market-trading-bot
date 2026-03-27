import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { navigate } from '../../lib/router';
import { getCertificationRuns, getCertificationSummary, getCurrentCertification, runCertificationReview } from '../../services/certification';
import type { CertificationRun, CertificationSummary } from '../../types/certification';

const levelTone = (level: string) => {
  if (level === 'PAPER_CERTIFIED_HIGH_AUTONOMY' || level === 'PAPER_CERTIFIED_BALANCED') return 'ready';
  if (level === 'PAPER_CERTIFIED_DEFENSIVE' || level === 'RECERTIFICATION_REQUIRED') return 'pending';
  if (level === 'NOT_CERTIFIED' || level === 'REMEDIATION_REQUIRED') return 'offline';
  return 'neutral';
};

const formatDate = (value: string) => {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
};

const asText = (v: unknown) => (v === null || v === undefined ? '—' : String(v));

export function CertificationPage() {
  const [summary, setSummary] = useState<CertificationSummary | null>(null);
  const [current, setCurrent] = useState<CertificationRun | null>(null);
  const [runs, setRuns] = useState<CertificationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, runsRes, currentRes] = await Promise.all([
        getCertificationSummary(),
        getCertificationRuns(),
        getCurrentCertification(),
      ]);
      setSummary(summaryRes);
      setRuns(runsRes);
      setCurrent(currentRes.current_certification);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load certification board state.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onRun = useCallback(async () => {
    setRunning(true);
    setError(null);
    try {
      await runCertificationReview({ metadata: { initiated_from: 'certification_ui' } });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not run certification review.');
    } finally {
      setRunning(false);
    }
  }, [load]);

  const evidence = current?.evidence_snapshot;
  const envelope = current?.operating_envelope;
  const hasRuns = useMemo(() => (summary?.total_runs ?? 0) > 0, [summary?.total_runs]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operational certification board"
        title="/certification"
        description="Manual-first operational certification and go-live gate for paper autonomy. Consolidates readiness, resilience, incidents, rollout and execution realism into an explicit operating envelope. Paper/demo only."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/readiness')}>Open Readiness</button><button type="button" className="secondary-button" onClick={() => navigate('/chaos')}>Open Chaos</button><button type="button" className="secondary-button" onClick={() => navigate('/promotion')}>Open Promotion</button><button type="button" className="secondary-button" onClick={() => navigate('/mission-control')}>Open Mission Control</button><button type="button" className="secondary-button" onClick={() => navigate('/runtime')}>Open Runtime</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Review controls" title="Run operational certification" description="Run a conservative certification review to assess current paper stack limits and constraints.">
          <button type="button" className="primary-button" disabled={running} onClick={() => void onRun()}>{running ? 'Running review…' : 'Run certification review'}</button>
        </SectionCard>

        {!hasRuns || !current ? (
          <EmptyState eyebrow="No certification reviews" title="Run an operational certification review to assess the current paper stack." description="Inconclusive evidence is shown as manual-review/recertification required, not as an API error." />
        ) : (
          <>
            <SectionCard eyebrow="Current certification" title="Certification state and recommendation" description="Latest certification level, recommendation, confidence and envelope summary.">
              <div className="system-metadata-grid">
                <div><strong>Certification level:</strong> <StatusBadge tone={levelTone(current.certification_level)}>{current.certification_level}</StatusBadge></div>
                <div><strong>Recommendation:</strong> {current.recommendation_code}</div>
                <div><strong>Confidence:</strong> {current.confidence}</div>
                <div><strong>Rationale:</strong> {current.rationale}</div>
                <div><strong>Reason codes:</strong> {current.reason_codes.join(', ') || 'None'}</div>
                <div><strong>Blocking constraints:</strong> {current.blocking_constraints.join(', ') || 'None'}</div>
                <div><strong>Created:</strong> {formatDate(current.created_at)}</div>
              </div>
            </SectionCard>

            <SectionCard eyebrow="Evidence snapshot" title="Consolidated operational evidence" description="Readiness + chaos + evaluation + incidents + rollout + promotion, all in one formal snapshot.">
              <div className="table-wrapper">
                <table className="data-table"><thead><tr><th>Evidence source</th><th>Summary</th></tr></thead><tbody>
                  <tr><td>Readiness</td><td>Status: {asText(evidence?.readiness_summary.status)} | Score: {asText(evidence?.readiness_summary.score)}</td></tr>
                  <tr><td>Chaos resilience</td><td>Resilience: {asText(evidence?.chaos_benchmark_summary.latest_resilience_score)} | Recovery: {asText(evidence?.chaos_benchmark_summary.latest_recovery_success_rate)}</td></tr>
                  <tr><td>Execution-aware evaluation</td><td>Favorable rate: {asText(evidence?.execution_evaluation_summary.favorable_review_rate)} | Hard stops: {asText(evidence?.execution_evaluation_summary.hard_stop_count)}</td></tr>
                  <tr><td>Incidents</td><td>Open critical: {asText(evidence?.incident_summary.open_critical)} | Open high: {asText(evidence?.incident_summary.open_high)}</td></tr>
                  <tr><td>Rollout + Promotion</td><td>Rollout status: {asText(evidence?.rollout_summary.status)} | Promotion recommendation: {asText(evidence?.promotion_summary.recommendation_code)}</td></tr>
                </tbody></table>
              </div>
            </SectionCard>

            <SectionCard eyebrow="Operating envelope" title="Certified paper limits" description="Explicit operational bounds derived from certification output.">
              <div className="system-metadata-grid">
                <div><strong>Max autonomy mode:</strong> {envelope?.max_autonomy_mode_allowed}</div>
                <div><strong>Auto execution allowed:</strong> {envelope?.auto_execution_allowed ? 'Yes' : 'No'}</div>
                <div><strong>Canary rollout allowed:</strong> {envelope?.canary_rollout_allowed ? 'Yes' : 'No'}</div>
                <div><strong>Max new entries/cycle:</strong> {envelope?.max_new_entries_per_cycle}</div>
                <div><strong>Max size multiplier:</strong> {envelope?.max_size_multiplier_allowed}</div>
                <div><strong>Allowed profiles:</strong> {envelope?.allowed_profiles?.join(', ') || '—'}</div>
                <div><strong>Constrained modules:</strong> {envelope?.constrained_modules?.join(', ') || 'None'}</div>
                <div><strong>Defensive only:</strong> {envelope?.defensive_profiles_only ? 'Yes' : 'No'}</div>
              </div>
            </SectionCard>
          </>
        )}

        <SectionCard eyebrow="Recent certification runs" title="Audit trail" description="Recent certification decisions with level, recommendation and summary.">
          {!runs.length ? (
            <EmptyState eyebrow="No runs" title="No certification runs yet" description="Run an operational certification review to assess the current paper stack." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>ID</th><th>Status</th><th>Recommendation</th><th>Certification level</th><th>Created</th><th>Summary</th></tr></thead>
                <tbody>
                  {runs.slice(0, 15).map((run) => (
                    <tr key={run.id}>
                      <td>#{run.id}</td>
                      <td>{run.status}</td>
                      <td>{run.recommendation_code}</td>
                      <td><StatusBadge tone={levelTone(run.certification_level)}>{run.certification_level}</StatusBadge></td>
                      <td>{formatDate(run.created_at)}</td>
                      <td>{run.summary || '—'}</td>
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
