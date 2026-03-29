import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  createAutonomyBacklogItem,
  deferAutonomyBacklogItem,
  getAutonomyBacklogCandidates,
  getAutonomyBacklogItems,
  getAutonomyBacklogRecommendations,
  getAutonomyBacklogSummary,
  prioritizeAutonomyBacklogItem,
  runAutonomyBacklogReview,
} from '../../services/autonomyBacklog';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['READY', 'PRIORITIZED', 'CREATE_BACKLOG_ITEM', 'PRIORITIZE_BACKLOG_ITEM'].includes(v)) return 'ready';
  if (['PENDING_REVIEW', 'MEDIUM', 'HIGH', 'REORDER_BACKLOG_PRIORITY'].includes(v)) return 'pending';
  if (['BLOCKED', 'DEFERRED', 'CLOSED', 'SKIP_DUPLICATE_BACKLOG', 'REQUIRE_MANUAL_BACKLOG_REVIEW'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyBacklogPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyBacklogCandidates>>>([]);
  const [items, setItems] = useState<Awaited<ReturnType<typeof getAutonomyBacklogItems>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyBacklogRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyBacklogSummary>> | null>(null);

  const itemByArtifact = useMemo(() => {
    const map = new Map<number, (typeof items)[number]>();
    items.forEach((row) => map.set(row.advisory_artifact, row));
    return map;
  }, [items]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, itemData, recommendationData, summaryData] = await Promise.all([
        getAutonomyBacklogCandidates(),
        getAutonomyBacklogItems(),
        getAutonomyBacklogRecommendations(),
        getAutonomyBacklogSummary(),
      ]);
      setCandidates(candidateData.slice(0, 300));
      setItems(itemData.slice(0, 300));
      setRecommendations(recommendationData.slice(0, 300));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy backlog board.');
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
      const result = await runAutonomyBacklogReview({ actor: 'operator-ui' });
      setMessage(`Backlog run #${result.run} reviewed ${result.candidate_count} candidates and created ${result.created_count} items.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run backlog review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const createItem = useCallback(async (artifactId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await createAutonomyBacklogItem(artifactId, { actor: 'operator-ui' });
      setMessage(`Backlog item created/confirmed for advisory artifact #${artifactId}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not create backlog item for #${artifactId}.`);
    } finally {
      setBusy(false);
    }
  }, [load]);

  const prioritizeItem = useCallback(async (itemId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await prioritizeAutonomyBacklogItem(itemId, { actor: 'operator-ui' });
      setMessage(`Backlog item #${itemId} prioritized.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not prioritize backlog item #${itemId}.`);
    } finally {
      setBusy(false);
    }
  }, [load]);

  const deferItem = useCallback(async (itemId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await deferAutonomyBacklogItem(itemId, { actor: 'operator-ui' });
      setMessage(`Backlog item #${itemId} deferred.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not defer backlog item #${itemId}.`);
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy backlog board"
        title="/autonomy-backlog"
        description="Manual-first adopted governance candidate registry that transforms adopted/acknowledged advisories into structured future-cycle backlog items. Recommendation-first, auditable, and no opaque auto-apply."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run backlog review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-intake')}>Intake board</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-advisory-resolution')}>Advisory resolution</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-advisory')}>Advisory</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Governance backlog posture" description="Candidate readiness, blockers, creation outcomes, duplicate skips, and prioritization pressure for manual future-cycle planning handoff.">
          <div className="cockpit-metric-grid">
            <div><strong>Candidates</strong><div>{summary?.candidate_count ?? 0}</div></div>
            <div><strong>Ready</strong><div>{summary?.ready_count ?? 0}</div></div>
            <div><strong>Blocked</strong><div>{summary?.blocked_count ?? 0}</div></div>
            <div><strong>Created</strong><div>{summary?.created_count ?? 0}</div></div>
            <div><strong>Prioritized</strong><div>{summary?.prioritized_count ?? 0}</div></div>
            <div><strong>Duplicate skipped</strong><div>{summary?.duplicate_skipped_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {!candidates.length ? <EmptyState eyebrow="No backlog candidates" title="No adopted autonomy advisories currently require backlog registration." description="Adopt or acknowledge advisories in /autonomy-advisory-resolution, then run backlog review." /> : null}

        <SectionCard eyebrow="Candidates" title="Adopted governance candidates" description="Traceable conversion candidates from campaign → insight → advisory → advisory resolution into governance backlog items.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Artifact</th><th>Insight</th><th>Campaign</th><th>Target</th><th>Resolution</th><th>Readiness</th><th>Blockers</th><th>Links</th><th>Actions</th></tr></thead>
              <tbody>
                {candidates.map((item) => (
                  <tr key={`${item.advisory_artifact}-${item.advisory_resolution}`}>
                    <td>#{item.advisory_artifact}</td>
                    <td>#{item.insight}</td>
                    <td>{item.campaign_title ?? (item.campaign ? `Campaign #${item.campaign}` : 'Cross-campaign')}</td>
                    <td>{item.target_scope}</td>
                    <td><StatusBadge tone={tone(item.resolution_status)}>{item.resolution_status}</StatusBadge></td>
                    <td><StatusBadge tone={item.ready_for_backlog ? 'ready' : 'offline'}>{item.ready_for_backlog ? 'READY' : 'BLOCKED'}</StatusBadge></td>
                    <td>{item.blockers.join(', ') || 'None'}</td>
                    <td><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=advisory_artifact&root_id=${encodeURIComponent(String(item.advisory_artifact))}`)}>Advisory</button><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=campaign_insight&root_id=${encodeURIComponent(String(item.insight))}`)}>Insight</button>{item.campaign ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Campaign</button> : null}</td>
                    <td><div className="button-row"><button className="secondary-button" type="button" disabled={busy || Boolean(item.existing_backlog_item)} onClick={() => void createItem(item.advisory_artifact)}>{item.existing_backlog_item ? 'Exists' : 'Create'}</button>{item.existing_backlog_item ? <button className="secondary-button" type="button" disabled={busy} onClick={() => void prioritizeItem(item.existing_backlog_item!)}>Prioritize</button> : null}</div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Items" title="Backlog items history" description="Formal governance backlog artifacts with explicit target scope and manual-first backlog statuses.">
            {!items.length ? <p className="muted-text">No backlog items yet.</p> : <div className="table-wrapper"><table className="data-table"><thead><tr><th>Item</th><th>Type</th><th>Status</th><th>Priority</th><th>Target</th><th>Created</th><th>Summary</th><th>Actions</th></tr></thead><tbody>{items.map((item) => (<tr key={item.id}><td>#{item.id}</td><td>{item.backlog_type}</td><td><StatusBadge tone={tone(item.backlog_status)}>{item.backlog_status}</StatusBadge></td><td><StatusBadge tone={tone(item.priority_level)}>{item.priority_level}</StatusBadge></td><td>{item.target_scope}</td><td>{item.created_at}</td><td>{item.summary}</td><td><div className="button-row"><button className="secondary-button" type="button" disabled={busy || item.backlog_status === 'PRIORITIZED'} onClick={() => void prioritizeItem(item.id)}>Prioritize</button><button className="ghost-button" type="button" disabled={busy || item.backlog_status === 'DEFERRED'} onClick={() => void deferItem(item.id)}>Defer</button></div></td></tr>))}</tbody></table></div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Backlog recommendations" description="Recommendation-first CREATE / PRIORITIZE / DEFER / SKIP / REVIEW queue with rationale, blockers, and confidence.">
            {!recommendations.length ? <p className="muted-text">No recommendations generated yet.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p><h3>{item.advisory_artifact ? `Artifact #${item.advisory_artifact}` : 'Global queue'}</h3><p>{item.rationale}</p><p className="muted-text">Blockers: {item.blockers.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
