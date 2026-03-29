import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  acknowledgeAutonomyPackage,
  adoptAutonomyPackage,
  deferAutonomyPackage,
  getAutonomyPackageReviewCandidates,
  getAutonomyPackageReviewRecommendations,
  getAutonomyPackageReviewResolutions,
  getAutonomyPackageReviewSummary,
  rejectAutonomyPackage,
  runAutonomyPackageReview,
} from '../../services/autonomyPackageReview';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['ACKNOWLEDGED', 'ADOPTED', 'CLOSED', 'MARK_PACKAGE_ADOPTED'].includes(v)) return 'ready';
  if (['PENDING', 'ACKNOWLEDGE_PACKAGE', 'KEEP_PACKAGE_PENDING', 'REORDER_PACKAGE_REVIEW_PRIORITY'].includes(v)) return 'pending';
  if (['BLOCKED', 'REJECTED', 'DEFERRED', 'REQUIRE_MANUAL_PACKAGE_REVIEW', 'MARK_PACKAGE_REJECTED', 'MARK_PACKAGE_DEFERRED'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyPackageReviewPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyPackageReviewCandidates>>>([]);
  const [resolutions, setResolutions] = useState<Awaited<ReturnType<typeof getAutonomyPackageReviewResolutions>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyPackageReviewRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyPackageReviewSummary>> | null>(null);

  const resolutionByPackage = useMemo(() => new Map(resolutions.map((item) => [item.governance_package, item])), [resolutions]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, resolutionData, recommendationData, summaryData] = await Promise.all([
        getAutonomyPackageReviewCandidates(),
        getAutonomyPackageReviewResolutions(),
        getAutonomyPackageReviewRecommendations(),
        getAutonomyPackageReviewSummary(),
      ]);
      setCandidates(candidateData.slice(0, 300));
      setResolutions(resolutionData.slice(0, 300));
      setRecommendations(recommendationData.slice(0, 300));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy package review board.');
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
      const result = await runAutonomyPackageReview({ actor: 'operator-ui' });
      setMessage(`Package review run #${result.run} processed ${result.candidate_count} packages and generated ${result.recommendation_count} recommendations.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run package review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const applyAction = useCallback(async (packageId: number, action: 'ack' | 'adopt' | 'defer' | 'reject') => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      if (action === 'ack') await acknowledgeAutonomyPackage(packageId, { actor: 'operator-ui' });
      if (action === 'adopt') await adoptAutonomyPackage(packageId, { actor: 'operator-ui' });
      if (action === 'defer') await deferAutonomyPackage(packageId, { actor: 'operator-ui' });
      if (action === 'reject') await rejectAutonomyPackage(packageId, { actor: 'operator-ui' });
      setMessage(`Package #${packageId} updated via ${action.toUpperCase()} action.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not ${action} package #${packageId}.`);
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy package review board"
        title="/autonomy-package-review"
        description="Manual-first package resolution tracker for registered governance bundles. Tracks acknowledge/adopt/defer/reject outcomes explicitly and never performs opaque auto-apply into roadmap/scenario/program/manager."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run package review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-package')}>Autonomy package</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-seed')}>Autonomy seed</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-decision')}>Autonomy decision</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Package resolution posture" description="Tracks registered packages and explicit downstream resolution outcomes.">
          <div className="cockpit-metric-grid">
            <div><strong>Registered candidates</strong><div>{summary?.candidate_count ?? 0}</div></div>
            <div><strong>Pending</strong><div>{summary?.pending_count ?? 0}</div></div>
            <div><strong>Acknowledged</strong><div>{summary?.acknowledged_count ?? 0}</div></div>
            <div><strong>Adopted</strong><div>{summary?.adopted_count ?? 0}</div></div>
            <div><strong>Deferred</strong><div>{summary?.deferred_count ?? 0}</div></div>
            <div><strong>Rejected</strong><div>{summary?.rejected_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {!candidates.length ? <EmptyState eyebrow="No package candidates" title="No registered governance packages currently require resolution tracking." description="Packages appear here once they are registered/ready/acknowledged/blocked in /autonomy-package." /> : null}

        <SectionCard eyebrow="Candidates and resolutions" title="Registered packages with downstream state" description="Auditable package resolution table with manual-first controls and trace drill-down links.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Package</th><th>Decisions</th><th>Target</th><th>Package status</th><th>Downstream</th><th>Blockers</th><th>Links</th><th>Actions</th></tr></thead>
              <tbody>
                {candidates.map((item) => {
                  const resolution = resolutionByPackage.get(item.governance_package);
                  return (
                    <tr key={item.governance_package}>
                      <td>#{item.governance_package}</td>
                      <td>{item.linked_decisions.length ? item.linked_decisions.map((id) => `#${id}`).join(', ') : 'n/a'}</td>
                      <td>{item.target_scope}</td>
                      <td><StatusBadge tone={tone(item.package_status)}>{item.package_status}</StatusBadge></td>
                      <td><StatusBadge tone={tone(resolution?.resolution_status ?? item.downstream_status)}>{resolution?.resolution_status ?? item.downstream_status}</StatusBadge></td>
                      <td>{item.blockers.join(', ') || 'None'}</td>
                      <td><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=governance_package&root_id=${encodeURIComponent(String(item.governance_package))}`)}>Package</button>{item.linked_decisions[0] ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=governance_decision&root_id=${encodeURIComponent(String(item.linked_decisions[0]))}`)}>Decision</button> : null}</td>
                      <td><div className="button-row"><button className="ghost-button" type="button" disabled={busy} onClick={() => void applyAction(item.governance_package, 'ack')}>Acknowledge</button><button className="ghost-button" type="button" disabled={busy} onClick={() => void applyAction(item.governance_package, 'adopt')}>Adopt</button><button className="ghost-button" type="button" disabled={busy} onClick={() => void applyAction(item.governance_package, 'defer')}>Defer</button><button className="ghost-button" type="button" disabled={busy} onClick={() => void applyAction(item.governance_package, 'reject')}>Reject</button></div></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Resolution history" title="Persisted package resolutions" description="Formal auditable resolution records linked to governance packages.">
            {!resolutions.length ? <p className="muted-text">No package resolutions recorded yet.</p> : <div className="page-stack">{resolutions.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.resolution_status)}>{item.resolution_status}</StatusBadge></p><h3>Package #{item.governance_package}</h3><p>{item.rationale}</p><p className="muted-text">Type: {item.resolution_type} · Blockers: {item.blockers.join(', ') || 'none'}</p></article>))}</div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Package review recommendations" description="Recommendation-first outputs to guide manual acknowledge/adopt/defer/reject control actions.">
            {!recommendations.length ? <p className="muted-text">No recommendations generated yet.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p><h3>{item.governance_package ? `Package #${item.governance_package}` : 'Global queue'}</h3><p>{item.rationale}</p><p className="muted-text">Blockers: {item.blockers.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
