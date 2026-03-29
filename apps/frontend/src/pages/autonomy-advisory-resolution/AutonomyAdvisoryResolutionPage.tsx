import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  acknowledgeAutonomyAdvisory,
  adoptAutonomyAdvisory,
  deferAutonomyAdvisory,
  getAutonomyAdvisoryResolutionCandidates,
  getAutonomyAdvisoryResolutionRecommendations,
  getAutonomyAdvisoryResolutionSummary,
  getAutonomyAdvisoryResolutions,
  rejectAutonomyAdvisory,
  runAutonomyAdvisoryResolutionReview,
} from '../../services/autonomyAdvisoryResolution';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['ACKNOWLEDGED', 'ADOPTED', 'CLOSED', 'ACKNOWLEDGE_ADVISORY', 'MARK_ADOPTED'].includes(v)) return 'ready';
  if (['PENDING', 'UNKNOWN', 'KEEP_PENDING', 'REORDER_ADVISORY_RESOLUTION_PRIORITY'].includes(v)) return 'pending';
  if (['BLOCKED', 'REJECTED', 'DEFERRED', 'REQUIRE_MANUAL_REVIEW', 'MARK_REJECTED', 'MARK_DEFERRED'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyAdvisoryResolutionPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyAdvisoryResolutionCandidates>>>([]);
  const [resolutions, setResolutions] = useState<Awaited<ReturnType<typeof getAutonomyAdvisoryResolutions>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyAdvisoryResolutionRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyAdvisoryResolutionSummary>> | null>(null);

  const resolutionByArtifact = useMemo(() => {
    const map = new Map<number, (typeof resolutions)[number]>();
    resolutions.forEach((row) => map.set(row.advisory_artifact, row));
    return map;
  }, [resolutions]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, resolutionData, recommendationData, summaryData] = await Promise.all([
        getAutonomyAdvisoryResolutionCandidates(),
        getAutonomyAdvisoryResolutions(),
        getAutonomyAdvisoryResolutionRecommendations(),
        getAutonomyAdvisoryResolutionSummary(),
      ]);
      setCandidates(candidateData.slice(0, 300));
      setResolutions(resolutionData.slice(0, 300));
      setRecommendations(recommendationData.slice(0, 300));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy advisory resolution board.');
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
      const result = await runAutonomyAdvisoryResolutionReview({ actor: 'operator-ui' });
      setMessage(`Resolution run #${result.run} reviewed ${result.candidate_count} artifacts and produced ${result.recommendation_count} recommendations.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run advisory resolution review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const applyAction = useCallback(async (action: 'ack' | 'adopt' | 'defer' | 'reject', artifactId: number) => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      if (action === 'ack') await acknowledgeAutonomyAdvisory(artifactId, { actor: 'operator-ui' });
      if (action === 'adopt') await adoptAutonomyAdvisory(artifactId, { actor: 'operator-ui' });
      if (action === 'defer') await deferAutonomyAdvisory(artifactId, { actor: 'operator-ui' });
      if (action === 'reject') await rejectAutonomyAdvisory(artifactId, { actor: 'operator-ui' });
      setMessage(`Artifact #${artifactId} updated via manual ${action} action.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not ${action} advisory artifact #${artifactId}.`);
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy advisory resolution board"
        title="/autonomy-advisory-resolution"
        description="Manual-first governance note acknowledgment/adoption tracker for already emitted advisory artifacts. No opaque auto-apply and no broker/exchange execution."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run advisory resolution review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-advisory')}>Autonomy advisory</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-insights')}>Autonomy insights</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Resolution governance posture" description="Tracks unresolved, acknowledged, adopted, deferred, and rejected advisory artifacts with explicit audit states.">
          <div className="cockpit-metric-grid">
            <div><strong>Advisory emitted</strong><div>{summary?.advisory_emitted_count ?? 0}</div></div>
            <div><strong>Pending</strong><div>{summary?.pending_count ?? 0}</div></div>
            <div><strong>Acknowledged</strong><div>{summary?.acknowledged_count ?? 0}</div></div>
            <div><strong>Adopted</strong><div>{summary?.adopted_count ?? 0}</div></div>
            <div><strong>Deferred</strong><div>{summary?.deferred_count ?? 0}</div></div>
            <div><strong>Rejected</strong><div>{summary?.rejected_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {!candidates.length ? <EmptyState eyebrow="No advisory resolution candidates" title="No emitted autonomy advisory notes currently require resolution tracking." description="Run autonomy advisory first to emit notes, then run advisory resolution review." /> : null}

        <SectionCard eyebrow="Candidates" title="Advisory artifacts and downstream status" description="Tracks emitted artifacts, their current resolution status, blockers, and linked trace navigation.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Artifact</th><th>Insight</th><th>Campaign</th><th>Target</th><th>Status</th><th>Blockers</th><th>Links</th><th>Actions</th></tr></thead>
              <tbody>
                {candidates.map((item) => {
                  const status = resolutionByArtifact.get(item.advisory_artifact)?.resolution_status ?? item.downstream_status;
                  return (
                    <tr key={item.advisory_artifact}>
                      <td>#{item.advisory_artifact} <StatusBadge tone={tone(item.artifact_status)}>{item.artifact_status}</StatusBadge></td>
                      <td>#{item.insight}</td>
                      <td>{item.campaign_title ?? (item.campaign ? `Campaign #${item.campaign}` : 'Cross-campaign')}</td>
                      <td>{item.target_scope}</td>
                      <td><StatusBadge tone={tone(status)}>{status}</StatusBadge></td>
                      <td>{item.blockers.join(', ') || 'None'}</td>
                      <td><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=advisory_artifact&root_id=${encodeURIComponent(String(item.advisory_artifact))}`)}>Artifact trace</button><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=campaign_insight&root_id=${encodeURIComponent(String(item.insight))}`)}>Insight trace</button>{item.campaign ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Campaign trace</button> : null}</td>
                      <td><div className="button-row"><button className="secondary-button" type="button" disabled={busy} onClick={() => void applyAction('ack', item.advisory_artifact)}>Acknowledge</button><button className="secondary-button" type="button" disabled={busy} onClick={() => void applyAction('adopt', item.advisory_artifact)}>Adopt</button><button className="ghost-button" type="button" disabled={busy} onClick={() => void applyAction('defer', item.advisory_artifact)}>Defer</button><button className="ghost-button" type="button" disabled={busy} onClick={() => void applyAction('reject', item.advisory_artifact)}>Reject</button></div></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Resolutions" title="Resolution history" description="Auditable manual-first actions for acknowledgment, adoption, defer, reject, and closure states.">
            {!resolutions.length ? <p className="muted-text">No resolution records yet.</p> : <div className="table-wrapper"><table className="data-table"><thead><tr><th>Artifact</th><th>Status</th><th>Type</th><th>Resolved by</th><th>Resolved at</th><th>Rationale</th></tr></thead><tbody>{resolutions.map((item) => (<tr key={item.id}><td>#{item.advisory_artifact}</td><td><StatusBadge tone={tone(item.resolution_status)}>{item.resolution_status}</StatusBadge></td><td>{item.resolution_type}</td><td>{item.resolved_by || 'n/a'}</td><td>{item.resolved_at ?? 'n/a'}</td><td>{item.rationale}</td></tr>))}</tbody></table></div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Resolution recommendations" description="Recommendation-first queue to keep governance note loop explicit and auditable.">
            {!recommendations.length ? <p className="muted-text">No recommendations generated yet.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p><h3>{item.advisory_artifact ? `Artifact #${item.advisory_artifact}` : 'Global queue'}</h3><p>{item.rationale}</p><p className="muted-text">Blockers: {item.blockers.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
