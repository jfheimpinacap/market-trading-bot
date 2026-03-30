import { useCallback, useEffect, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  acceptAutonomySeed,
  acknowledgeAutonomySeed,
  deferAutonomySeed,
  getAutonomySeedReviewCandidates,
  getAutonomySeedReviewRecommendations,
  getAutonomySeedReviewResolutions,
  getAutonomySeedReviewSummary,
  rejectAutonomySeed,
  runAutonomySeedReview,
} from '../../services/autonomySeedReview';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const normalized = value.toUpperCase();
  if (['ACKNOWLEDGED', 'ACCEPTED', 'CLOSED', 'MARK_SEED_ACCEPTED'].includes(normalized)) return 'ready';
  if (['PENDING', 'UNKNOWN', 'ACKNOWLEDGE_SEED', 'KEEP_SEED_PENDING', 'REORDER_SEED_REVIEW_PRIORITY'].includes(normalized)) return 'pending';
  if (['BLOCKED', 'REJECTED', 'DEFERRED', 'REQUIRE_MANUAL_SEED_REVIEW', 'MARK_SEED_REJECTED', 'MARK_SEED_DEFERRED'].includes(normalized)) return 'offline';
  return 'neutral';
};

export function AutonomySeedReviewPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomySeedReviewCandidates>>>([]);
  const [resolutions, setResolutions] = useState<Awaited<ReturnType<typeof getAutonomySeedReviewResolutions>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomySeedReviewRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomySeedReviewSummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, resolutionData, recommendationData, summaryData] = await Promise.all([
        getAutonomySeedReviewCandidates(),
        getAutonomySeedReviewResolutions(),
        getAutonomySeedReviewRecommendations(),
        getAutonomySeedReviewSummary(),
      ]);
      setCandidates(candidateData.slice(0, 500));
      setResolutions(resolutionData.slice(0, 500));
      setRecommendations(recommendationData.slice(0, 500));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy seed review board.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const withAction = useCallback(async (fn: () => Promise<unknown>, success: string) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await fn();
      setMessage(success);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action failed.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy seed review board"
        title="/autonomy-seed-review"
        description="Manual-first seed resolution tracker that consumes registered governance seeds and records explicit outcomes (acknowledged/accepted/deferred/rejected) without opaque auto-apply."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void withAction(() => runAutonomySeedReview({ actor: 'operator-ui' }), 'Seed review run completed.')}>Run seed review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-seed')}>Autonomy seed</button><button className="ghost-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />
      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Seed resolution posture" description="Closed-loop status for next-cycle seed handoff and manual governance auditability.">
          <div className="cockpit-metric-grid">
            <div><strong>Seeds registered</strong><div>{summary?.seed_count ?? 0}</div></div>
            <div><strong>Pending</strong><div>{summary?.pending_count ?? 0}</div></div>
            <div><strong>Acknowledged</strong><div>{summary?.acknowledged_count ?? 0}</div></div>
            <div><strong>Accepted</strong><div>{summary?.accepted_count ?? 0}</div></div>
            <div><strong>Deferred</strong><div>{summary?.deferred_count ?? 0}</div></div>
            <div><strong>Rejected</strong><div>{summary?.rejected_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {!candidates.length ? <EmptyState eyebrow="Seed review" title="No registered governance seeds currently require resolution tracking." description="Run autonomy seed registration from adopted packages, then run seed review to produce recommendations and statuses." /> : null}

        <SectionCard eyebrow="Candidates" title="Seed candidates and downstream status" description="Links seed/package/decision lineage with explicit manual actions.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Seed</th><th>Package</th><th>Linked decisions</th><th>Target</th><th>Seed status</th><th>Downstream</th><th>Blockers</th><th>Links</th><th>Actions</th></tr></thead>
              <tbody>
                {candidates.map((item) => (
                  <tr key={item.governance_seed}>
                    <td>#{item.governance_seed}</td>
                    <td>#{item.governance_package}</td>
                    <td>{item.linked_decisions.length ? item.linked_decisions.map((id) => `#${id}`).join(', ') : 'n/a'}</td>
                    <td>{item.target_scope}</td>
                    <td><StatusBadge tone={tone(item.seed_status)}>{item.seed_status}</StatusBadge></td>
                    <td><StatusBadge tone={tone(item.downstream_status)}>{item.downstream_status}</StatusBadge></td>
                    <td>{item.blockers.join(', ') || 'None'}</td>
                    <td><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=governance_seed&root_id=${encodeURIComponent(String(item.governance_seed))}`)}>Seed</button><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=governance_package&root_id=${encodeURIComponent(String(item.governance_package))}`)}>Package</button>{item.linked_decisions[0] ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=governance_decision&root_id=${encodeURIComponent(String(item.linked_decisions[0]))}`)}>Decision</button> : null}</td>
                    <td><div className="button-row"><button className="ghost-button" type="button" disabled={busy} onClick={() => void withAction(() => acknowledgeAutonomySeed(item.governance_seed, { actor: 'operator-ui' }), `Seed #${item.governance_seed} acknowledged.`)}>Acknowledge</button><button className="ghost-button" type="button" disabled={busy} onClick={() => void withAction(() => acceptAutonomySeed(item.governance_seed, { actor: 'operator-ui' }), `Seed #${item.governance_seed} accepted.`)}>Accept</button><button className="link-button" type="button" disabled={busy} onClick={() => void withAction(() => deferAutonomySeed(item.governance_seed, { actor: 'operator-ui' }), `Seed #${item.governance_seed} deferred.`)}>Defer</button><button className="link-button" type="button" disabled={busy} onClick={() => void withAction(() => rejectAutonomySeed(item.governance_seed, { actor: 'operator-ui' }), `Seed #${item.governance_seed} rejected.`)}>Reject</button></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Resolutions" title="Persisted seed resolutions" description="Auditable records of post-registration seed outcomes.">
            {!resolutions.length ? <p className="muted-text">No seed resolutions recorded yet.</p> : <div className="page-stack">{resolutions.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.resolution_status)}>{item.resolution_status}</StatusBadge></p><h3>Seed #{item.governance_seed}</h3><p>{item.rationale}</p><p className="muted-text">Type: {item.resolution_type} · Resolved by: {item.resolved_by || 'n/a'} · At: {item.resolved_at ?? 'n/a'}</p></article>))}</div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Manual-first seed review recommendations" description="Guidance to close pending seed loops with explicit rationale.">
            {!recommendations.length ? <p className="muted-text">No recommendations generated yet.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p><h3>{item.governance_seed ? `Seed #${item.governance_seed}` : 'Global queue'}</h3><p>{item.rationale}</p><p className="muted-text">Blockers: {item.blockers.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
