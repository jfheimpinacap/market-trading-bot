import { useCallback, useEffect, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  completeAutonomyCloseout,
  getAutonomyCloseoutCandidates,
  getAutonomyCloseoutFindings,
  getAutonomyCloseoutRecommendations,
  getAutonomyCloseoutReports,
  getAutonomyCloseoutSummary,
  runAutonomyCloseoutReview,
} from '../../services/autonomyCloseout';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['READY', 'COMPLETED', 'COMPLETE_CLOSEOUT', 'INDEX_IN_MEMORY'].includes(v)) return 'ready';
  if (['PENDING_REVIEW', 'APPROVAL_REQUIRED', 'REQUIRE_MANUAL_CLOSEOUT_REVIEW', 'KEEP_OPEN_FOR_FOLLOWUP'].includes(v)) return 'pending';
  if (['BLOCKED', 'SEND_TO_POSTMORTEM', 'PREPARE_ROADMAP_FEEDBACK'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyCloseoutPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyCloseoutCandidates>>>([]);
  const [reports, setReports] = useState<Awaited<ReturnType<typeof getAutonomyCloseoutReports>>>([]);
  const [findings, setFindings] = useState<Awaited<ReturnType<typeof getAutonomyCloseoutFindings>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyCloseoutRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyCloseoutSummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, reportData, findingData, recommendationData, summaryData] = await Promise.all([
        getAutonomyCloseoutCandidates(),
        getAutonomyCloseoutReports(),
        getAutonomyCloseoutFindings(),
        getAutonomyCloseoutRecommendations(),
        getAutonomyCloseoutSummary(),
      ]);
      setCandidates(candidateData.slice(0, 100));
      setReports(reportData.slice(0, 100));
      setFindings(findingData.slice(0, 150));
      setRecommendations(recommendationData.slice(0, 150));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy closeout board.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runReview = useCallback(async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await runAutonomyCloseoutReview({ actor: 'operator-ui' });
      setMessage(`Closeout run #${result.run} created ${result.report_count} reports and ${result.recommendation_count} recommendations.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run closeout review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const complete = useCallback(async (campaignId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await completeAutonomyCloseout(campaignId, { actor: 'operator-ui' });
      setMessage(`Closeout report #${result.report_id} moved to ${result.closeout_status}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not complete closeout.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy closeout board"
        title="/autonomy-closeout"
        description="Campaign archive dossier and learning handoff governance. Manual-first only: explicit reports, findings, and handoff stubs without opaque auto-learning or auto-archive."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run closeout review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-disposition')}>Disposition</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-recovery')}>Recovery</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-interventions')}>Interventions</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-followup')}>Followup</button><button className="ghost-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Closeout summary" title="Campaign closeout posture" description="COMPLETED and KEEP_OPEN_FOR_FOLLOWUP are valid outcomes in this manual-first governance stage.">
          <div className="cockpit-metric-grid">
            <div><strong>Candidates</strong><div>{summary?.candidate_count ?? 0}</div></div>
            <div><strong>Ready</strong><div>{summary?.ready_count ?? 0}</div></div>
            <div><strong>Blocked</strong><div>{summary?.blocked_count ?? 0}</div></div>
            <div><strong>Requires postmortem</strong><div>{summary?.requires_postmortem_count ?? 0}</div></div>
            <div><strong>Requires memory index</strong><div>{summary?.requires_memory_index_count ?? 0}</div></div>
            <div><strong>Roadmap feedback</strong><div>{summary?.requires_roadmap_feedback_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {candidates.length === 0 ? <EmptyState eyebrow="Closeout candidates" title="No autonomy campaigns currently require closeout review." description="Run closeout review after disposition is applied or recovery/intervention histories are updated." /> : null}

        <SectionCard eyebrow="Reports" title="Campaign closeout reports" description="Lifecycle dossier with blockers, incidents, interventions, and final outcomes.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Campaign</th><th>Disposition</th><th>Closeout status</th><th>Outcome</th><th>Blockers</th><th>Links & actions</th></tr></thead>
              <tbody>
                {reports.map((item) => (
                  <tr key={item.id}>
                    <td>{item.campaign_title ?? `Campaign #${item.campaign}`}</td>
                    <td><StatusBadge tone={tone(item.disposition_type)}>{item.disposition_type}</StatusBadge></td>
                    <td><StatusBadge tone={tone(item.closeout_status)}>{item.closeout_status}</StatusBadge></td>
                    <td>{item.final_outcome_summary}</td>
                    <td>{item.major_blockers.join(', ') || 'none'}</td>
                    <td>
                      <div className="button-row">
                        <button className="link-button" type="button" onClick={() => navigate('/autonomy-campaigns')}>Campaign</button>
                        <button className="link-button" type="button" onClick={() => navigate('/approvals')}>Approvals</button>
                        <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Trace</button>
                        <button className="secondary-button" type="button" disabled={busy || item.closeout_status === 'COMPLETED'} onClick={() => void complete(item.campaign)}>Complete closeout</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Findings" title="Structured lessons" description="Success/failure factors, blockers, incidents, recovery and disposition lessons.">
            {!findings.length ? <p className="muted-text">No findings generated yet.</p> : <div className="page-stack">{findings.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.finding_type)}>{item.finding_type}</StatusBadge></p><h3>{item.campaign_title ?? `Campaign #${item.campaign}`}</h3><p>{item.summary}</p><p className="muted-text">Severity: {item.severity_or_weight} · Follow-up: {item.recommended_followup || 'n/a'}</p></article>))}</div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Closeout actions" description="Explicit recommendation catalog for manual decision-making and handoff governance.">
            {!recommendations.length ? <p className="muted-text">No recommendations yet. Run closeout review.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p><h3>{item.target_campaign_title ?? (item.target_campaign ? `Campaign #${item.target_campaign}` : 'Cross-campaign')}</h3><p>{item.rationale}</p><p className="muted-text">Blockers: {item.blockers.join(', ') || 'none'} · Domains: {item.impacted_domains.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
