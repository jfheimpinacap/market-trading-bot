import { useCallback, useEffect, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  emitAutonomyFollowup,
  getAutonomyFollowupCandidates,
  getAutonomyFollowupRecommendations,
  getAutonomyFollowups,
  getAutonomyFollowupSummary,
  runAutonomyFollowupReview,
} from '../../services/autonomyFollowup';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['READY', 'EMITTED', 'ALREADY_EMITTED', 'EMIT_MEMORY_INDEX', 'EMIT_POSTMORTEM_REQUEST', 'EMIT_ROADMAP_FEEDBACK'].includes(v)) return 'ready';
  if (['PARTIAL', 'PENDING_REVIEW', 'REQUIRE_MANUAL_REVIEW', 'KEEP_PENDING'].includes(v)) return 'pending';
  if (['BLOCKED', 'FAILED', 'DUPLICATE_SKIPPED', 'SKIP_DUPLICATE_FOLLOWUP'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyFollowupPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyFollowupCandidates>>>([]);
  const [followups, setFollowups] = useState<Awaited<ReturnType<typeof getAutonomyFollowups>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyFollowupRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyFollowupSummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, followupData, recommendationData, summaryData] = await Promise.all([
        getAutonomyFollowupCandidates(),
        getAutonomyFollowups(),
        getAutonomyFollowupRecommendations(),
        getAutonomyFollowupSummary(),
      ]);
      setCandidates(candidateData.slice(0, 150));
      setFollowups(followupData.slice(0, 200));
      setRecommendations(recommendationData.slice(0, 200));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy follow-up board.');
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
      const result = await runAutonomyFollowupReview({ actor: 'operator-ui' });
      setMessage(`Follow-up run #${result.run} reviewed ${result.candidate_count} candidates and generated ${result.recommendation_count} recommendations.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run follow-up review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const emit = useCallback(async (campaignId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await emitAutonomyFollowup(campaignId, { actor: 'operator-ui' });
      setMessage(`Campaign #${result.campaign} emitted ${result.emitted_count} follow-up records.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not emit follow-up.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy followup board"
        title="/autonomy-followup"
        description="Manual-first closeout handoff emitter and knowledge-routing governance. No opaque auto-learning, no auto-apply roadmap changes."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run followup review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-feedback')}>Feedback board</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-closeout')}>Closeout</button><button className="secondary-button" type="button" onClick={() => navigate('/approvals')}>Approvals</button><button className="ghost-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Follow-up summary" title="Knowledge routing posture" description="EMITTED and DUPLICATE_SKIPPED are valid auditable outcomes.">
          <div className="cockpit-metric-grid">
            <div><strong>Candidates</strong><div>{summary?.candidate_count ?? 0}</div></div>
            <div><strong>Ready</strong><div>{summary?.ready_count ?? 0}</div></div>
            <div><strong>Blocked</strong><div>{summary?.blocked_count ?? 0}</div></div>
            <div><strong>Already emitted</strong><div>{summary?.emitted_count ?? 0}</div></div>
            <div><strong>Duplicate skipped</strong><div>{summary?.duplicate_skipped_count ?? 0}</div></div>
            <div><strong>Memory / Postmortem / Roadmap</strong><div>{summary?.memory_followup_count ?? 0} / {summary?.postmortem_followup_count ?? 0} / {summary?.roadmap_feedback_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {candidates.length === 0 ? <EmptyState eyebrow="Followup candidates" title="No autonomy campaigns currently require follow-up emission." description="Run closeout and follow-up reviews again after campaign closeout reports are refreshed." /> : null}

        <SectionCard eyebrow="Candidates" title="Closeout followup candidates" description="Campaign-level readiness, blockers, and required handoffs.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Campaign</th><th>Closeout status</th><th>Readiness</th><th>Required followups</th><th>Linked artifacts</th><th>Blockers</th><th>Links & actions</th></tr></thead>
              <tbody>
                {candidates.map((item) => {
                  const required = [item.requires_memory_index ? 'MEMORY_INDEX' : null, item.requires_postmortem ? 'POSTMORTEM_REQUEST' : null, item.requires_roadmap_feedback ? 'ROADMAP_FEEDBACK' : null].filter(Boolean).join(', ') || 'none';
                  const artifacts = [item.existing_memory_document ? `memory#${item.existing_memory_document}` : null, item.existing_postmortem_request ? `postmortem#${item.existing_postmortem_request}` : null, item.existing_feedback_artifact ?? null].filter(Boolean).join(', ') || 'none';
                  return (
                    <tr key={`${item.campaign}-${item.closeout_report}`}>
                      <td>{item.campaign_title}</td>
                      <td><StatusBadge tone={tone(item.closeout_status)}>{item.closeout_status}</StatusBadge></td>
                      <td><StatusBadge tone={tone(item.followup_readiness)}>{item.followup_readiness}</StatusBadge></td>
                      <td>{required}</td>
                      <td>{artifacts}</td>
                      <td>{item.blockers.join(', ') || 'none'}</td>
                      <td>
                        <div className="button-row">
                          <button className="link-button" type="button" onClick={() => navigate('/autonomy-campaigns')}>Campaign</button>
                          <button className="link-button" type="button" onClick={() => navigate('/autonomy-closeout')}>Closeout</button>
                          <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Trace</button>
                          <button className="secondary-button" type="button" disabled={busy || item.followup_readiness === 'BLOCKED'} onClick={() => void emit(item.campaign)}>Emit followup</button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Followup history" title="Emission records" description="Auditable history of emitted, blocked, failed, and duplicate-skipped followups.">
            {!followups.length ? <p className="muted-text">No follow-up history yet.</p> : <div className="page-stack">{followups.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.followup_status)}>{item.followup_type}</StatusBadge> <StatusBadge tone={tone(item.followup_status)}>{item.followup_status}</StatusBadge></p><h3>{item.campaign_title ?? `Campaign #${item.campaign}`}</h3><p>{item.rationale}</p><p className="muted-text">By: {item.emitted_by || 'n/a'} · At: {item.emitted_at ?? 'n/a'} · Artifact: {(item.linked_memory_document ?? item.linked_postmortem_request ?? item.linked_feedback_artifact) || 'n/a'}</p></article>))}</div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Manual-first followup recommendations" description="Recommendation-first governance for emit/skip/manual review decisions.">
            {!recommendations.length ? <p className="muted-text">No recommendations yet. Run follow-up review.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p><h3>{item.target_campaign_title ?? (item.target_campaign ? `Campaign #${item.target_campaign}` : 'Cross-campaign')}</h3><p>{item.rationale}</p><p className="muted-text">Blockers: {item.blockers.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
