import { useCallback, useEffect, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  emitAutonomyAdvisory,
  getAutonomyAdvisoryArtifacts,
  getAutonomyAdvisoryCandidates,
  getAutonomyAdvisoryRecommendations,
  getAutonomyAdvisorySummary,
  runAutonomyAdvisoryReview,
} from '../../services/autonomyAdvisory';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['READY', 'EMITTED', 'ACKNOWLEDGED', 'EMIT_MEMORY_PRECEDENT_NOTE', 'EMIT_ROADMAP_GOVERNANCE_NOTE', 'EMIT_SCENARIO_CAUTION_NOTE', 'EMIT_PROGRAM_POLICY_NOTE', 'EMIT_MANAGER_REVIEW_NOTE'].includes(v)) return 'ready';
  if (['PENDING_REVIEW', 'REQUIRE_MANUAL_ADVISORY_REVIEW', 'REORDER_ADVISORY_PRIORITY'].includes(v)) return 'pending';
  if (['BLOCKED', 'DUPLICATE_SKIPPED', 'SKIP_DUPLICATE_ADVISORY'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyAdvisoryPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyAdvisoryCandidates>>>([]);
  const [artifacts, setArtifacts] = useState<Awaited<ReturnType<typeof getAutonomyAdvisoryArtifacts>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyAdvisoryRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyAdvisorySummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, artifactData, recommendationData, summaryData] = await Promise.all([
        getAutonomyAdvisoryCandidates(),
        getAutonomyAdvisoryArtifacts(),
        getAutonomyAdvisoryRecommendations(),
        getAutonomyAdvisorySummary(),
      ]);
      setCandidates(candidateData.slice(0, 300));
      setArtifacts(artifactData.slice(0, 300));
      setRecommendations(recommendationData.slice(0, 300));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy advisory board.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runReview = useCallback(async () => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const result = await runAutonomyAdvisoryReview({ actor: 'operator-ui' });
      setMessage(`Advisory run #${result.run} reviewed ${result.candidate_count} candidates and emitted ${result.emitted_count} artifacts.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run autonomy advisory review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const emit = useCallback(async (insightId: number) => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const result = await emitAutonomyAdvisory(insightId, { actor: 'operator-ui' });
      setMessage(`Advisory artifact #${result.artifact_id} is now ${result.artifact_status}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not emit advisory for insight #${insightId}.`);
    } finally {
      setBusy(false);
    }
  }, [load]);

  const readyCount = candidates.filter((item) => item.ready_for_emission).length;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy advisory board"
        title="/autonomy-advisory"
        description="Formal insight action emitter and governance note registry. Manual-first recommendation routing only: no opaque auto-apply, no auto-learning, no broker/exchange execution."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run advisory review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-insights')}>Autonomy insights</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-feedback')}>Autonomy feedback</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-closeout')}>Autonomy closeout</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Advisory emission posture" description="Tracks candidate readiness, blocked emissions, duplicate skips, and target routing counts.">
          <div className="cockpit-metric-grid">
            <div><strong>Advisory candidates</strong><div>{summary?.candidate_count ?? candidates.length}</div></div>
            <div><strong>Ready</strong><div>{summary?.ready_count ?? readyCount}</div></div>
            <div><strong>Blocked</strong><div>{summary?.blocked_count ?? 0}</div></div>
            <div><strong>Emitted</strong><div>{summary?.emitted_count ?? 0}</div></div>
            <div><strong>Duplicate skipped</strong><div>{summary?.duplicate_skipped_count ?? 0}</div></div>
            <div><strong>Memory notes</strong><div>{summary?.memory_note_count ?? 0}</div></div>
            <div><strong>Roadmap notes</strong><div>{summary?.roadmap_note_count ?? 0}</div></div>
            <div><strong>Scenario notes</strong><div>{summary?.scenario_note_count ?? 0}</div></div>
            <div><strong>Program notes</strong><div>{summary?.program_note_count ?? 0}</div></div>
            <div><strong>Manager notes</strong><div>{summary?.manager_note_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {!candidates.length ? <EmptyState eyebrow="No advisory candidates" title="No autonomy insights currently require advisory emission." description="Run autonomy insights review first, mark candidate insights as reviewed, and then run advisory review." /> : null}

        <SectionCard eyebrow="Candidates" title="Insight advisory candidates" description="Manual-first routing from reviewed insight recommendations toward memory/roadmap/scenario/program/manager outputs.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Insight</th><th>Campaign</th><th>Target</th><th>Recommendation</th><th>Status</th><th>Existing artifact</th><th>Blockers</th><th>Links</th><th>Actions</th></tr></thead>
              <tbody>
                {candidates.map((item) => (
                  <tr key={item.insight}>
                    <td>#{item.insight}</td>
                    <td>{item.campaign_title ?? (item.campaign ? `Campaign #${item.campaign}` : 'Cross-campaign')}</td>
                    <td>{item.recommendation_target}</td>
                    <td><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></td>
                    <td><StatusBadge tone={item.ready_for_emission ? 'ready' : 'pending'}>{item.ready_for_emission ? 'READY' : item.review_status}</StatusBadge></td>
                    <td>{item.existing_artifact ? `#${item.existing_artifact}` : 'None'}</td>
                    <td>{item.blockers.join(', ') || 'None'}</td>
                    <td><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=campaign_insight&root_id=${encodeURIComponent(String(item.insight))}`)}>Insight trace</button>{item.campaign ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Campaign trace</button> : null}</td>
                    <td><button className="secondary-button" type="button" disabled={busy || !item.ready_for_emission} onClick={() => void emit(item.insight)}>Emit advisory</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Artifacts" title="Advisory artifacts history" description="Formal auditable outputs produced from insights and recommendation routing.">
            {!artifacts.length ? <p className="muted-text">No advisory artifacts yet.</p> : <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Status</th><th>Target</th><th>Insight</th><th>Emitted by</th><th>Emitted at</th><th>Linked artifact</th><th>Rationale</th></tr></thead><tbody>{artifacts.map((item) => (<tr key={item.id}><td>{item.artifact_type}</td><td><StatusBadge tone={tone(item.artifact_status)}>{item.artifact_status}</StatusBadge></td><td>{item.target_scope}</td><td>#{item.insight}</td><td>{item.emitted_by || 'n/a'}</td><td>{item.emitted_at ?? 'n/a'}</td><td>{item.linked_memory_document ? `Memory #${item.linked_memory_document}` : item.linked_program_note || item.linked_feedback_artifact || 'stub-only'}</td><td>{item.rationale}</td></tr>))}</tbody></table></div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Advisory recommendation queue" description="Recommendation-first emission guidance with confidence and blocker visibility.">
            {!recommendations.length ? <p className="muted-text">No recommendations generated yet.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge> {item.artifact_type ? <StatusBadge tone={tone(item.artifact_type)}>{item.artifact_type}</StatusBadge> : null}</p><h3>{item.target_campaign ? `Campaign #${item.target_campaign}` : 'Cross-campaign'}</h3><p>{item.rationale}</p><p className="muted-text">Blockers: {item.blockers.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
