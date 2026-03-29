import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  acknowledgeAutonomyPackage,
  getAutonomyPackageCandidates,
  getAutonomyPackageRecommendations,
  getAutonomyPackageSummary,
  getAutonomyPackages,
  registerAutonomyPackage,
  runAutonomyPackageReview,
} from '../../services/autonomyPackage';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['READY', 'REGISTERED', 'ACKNOWLEDGED', 'REGISTER_ROADMAP_PACKAGE', 'REGISTER_SCENARIO_PACKAGE', 'REGISTER_PROGRAM_PACKAGE', 'REGISTER_MANAGER_PACKAGE'].includes(v)) return 'ready';
  if (['PENDING_REVIEW', 'REORDER_PACKAGE_PRIORITY'].includes(v)) return 'pending';
  if (['BLOCKED', 'DUPLICATE_SKIPPED', 'REQUIRE_MANUAL_PACKAGE_REVIEW', 'SKIP_DUPLICATE_PACKAGE'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomyPackagePage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomyPackageCandidates>>>([]);
  const [packages, setPackages] = useState<Awaited<ReturnType<typeof getAutonomyPackages>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomyPackageRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyPackageSummary>> | null>(null);

  const packageByDecision = useMemo(() => {
    const map = new Map<number, (typeof packages)[number]>();
    packages.forEach((item) => item.linked_decision_ids.forEach((id) => map.set(id, item)));
    return map;
  }, [packages]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, packageData, recommendationData, summaryData] = await Promise.all([
        getAutonomyPackageCandidates(),
        getAutonomyPackages(),
        getAutonomyPackageRecommendations(),
        getAutonomyPackageSummary(),
      ]);
      setCandidates(candidateData.slice(0, 300));
      setPackages(packageData.slice(0, 300));
      setRecommendations(recommendationData.slice(0, 300));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy package board.');
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
      setMessage(`Package review run #${result.run} processed ${result.candidate_count} candidates and generated ${result.recommendation_count} recommendations.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run package review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy package board"
        title="/autonomy-package"
        description="Manual-first decision bundle registry that converts formal governance decisions into auditable next-cycle planning seeds. No opaque auto-apply into roadmap/scenario/program/manager."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run package review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-decision')}>Autonomy decision</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-planning-review')}>Planning review</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Package registration posture" description="Tracks bundle candidates, duplicates, and target scope distribution for next-cycle planning artifacts.">
          <div className="cockpit-metric-grid">
            <div><strong>Candidates</strong><div>{summary?.candidate_count ?? 0}</div></div>
            <div><strong>Ready</strong><div>{summary?.ready_count ?? 0}</div></div>
            <div><strong>Blocked</strong><div>{summary?.blocked_count ?? 0}</div></div>
            <div><strong>Registered</strong><div>{summary?.registered_count ?? 0}</div></div>
            <div><strong>Duplicate skipped</strong><div>{summary?.duplicate_skipped_count ?? 0}</div></div>
            <div><strong>Roadmap/Scenario/Program/Manager</strong><div>{summary?.roadmap_package_count ?? 0} / {summary?.scenario_package_count ?? 0} / {summary?.program_package_count ?? 0} / {summary?.manager_package_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {!candidates.length ? <EmptyState eyebrow="No package candidates" title="No registered governance decisions currently require package registration." description="Once decisions are REGISTERED/ACKNOWLEDGED in /autonomy-decision, they appear here for explicit package creation." /> : null}

        <SectionCard eyebrow="Candidates" title="Governance decisions pending package registration" description="Transparent decision candidate queue with source links and manual register action.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Decision</th><th>Proposal</th><th>Insight</th><th>Campaign</th><th>Target</th><th>Priority</th><th>Status</th><th>Blockers</th><th>Links</th><th>Actions</th></tr></thead>
              <tbody>
                {candidates.map((item) => {
                  const pkg = packageByDecision.get(item.governance_decision);
                  return (
                    <tr key={item.governance_decision}>
                      <td>#{item.governance_decision}</td>
                      <td>{item.planning_proposal ? `#${item.planning_proposal}` : 'n/a'}</td>
                      <td>{item.insight ? `#${item.insight}` : 'n/a'}</td>
                      <td>{typeof item.metadata.campaign_title === 'string' ? item.metadata.campaign_title : (item.campaign ? `Campaign #${item.campaign}` : 'Cross-campaign')}</td>
                      <td>{item.target_scope}</td>
                      <td>{item.priority_level}</td>
                      <td><StatusBadge tone={tone(pkg?.package_status ?? (item.ready_for_packaging ? 'READY' : 'BLOCKED'))}>{pkg?.package_status ?? (item.ready_for_packaging ? 'READY' : 'BLOCKED')}</StatusBadge></td>
                      <td>{item.blockers.join(', ') || 'None'}</td>
                      <td><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=governance_decision&root_id=${encodeURIComponent(String(item.governance_decision))}`)}>Decision</button>{item.planning_proposal ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=planning_proposal&root_id=${encodeURIComponent(String(item.planning_proposal))}`)}>Proposal</button> : null}{item.insight ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=campaign_insight&root_id=${encodeURIComponent(String(item.insight))}`)}>Insight</button> : null}{item.campaign ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Campaign</button> : null}</td>
                      <td><button className="secondary-button" type="button" disabled={busy || !item.ready_for_packaging} onClick={async () => { setBusy(true); setError(null); setMessage(null); try { const result = await registerAutonomyPackage(item.governance_decision, { actor: 'operator-ui' }); setMessage(`Package ${result.package_status} for decision #${item.governance_decision}.`); await load(); } catch (err) { setError(err instanceof Error ? err.message : `Could not register package for decision #${item.governance_decision}.`); } finally { setBusy(false); } }}>Register package</button></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Package history" title="Persisted governance packages" description="Formal reusable bundle registry with explicit target scope, status, and linked decision count.">
            {!packages.length ? <p className="muted-text">No packages registered yet.</p> : <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Status</th><th>Target</th><th>Priority</th><th>Decisions</th><th>Registered</th><th>Summary</th><th>Action</th></tr></thead><tbody>{packages.map((item) => (<tr key={item.id}><td>{item.package_type}</td><td><StatusBadge tone={tone(item.package_status)}>{item.package_status}</StatusBadge></td><td>{item.target_scope}</td><td>{item.priority_level}</td><td>{item.decision_count}</td><td>{item.registered_at ?? 'n/a'}</td><td>{item.summary}</td><td><button className="ghost-button" type="button" disabled={busy || item.package_status === 'ACKNOWLEDGED'} onClick={async () => { setBusy(true); setError(null); setMessage(null); try { await acknowledgeAutonomyPackage(item.id); setMessage(`Package #${item.id} acknowledged.`); await load(); } catch (err) { setError(err instanceof Error ? err.message : `Could not acknowledge package #${item.id}.`); } finally { setBusy(false); } }}>Acknowledge</button></td></tr>))}</tbody></table></div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Package recommendations" description="Recommendation-first queue for register, duplicate skip, manual review, and priority reorder actions.">
            {!recommendations.length ? <p className="muted-text">No recommendations generated yet.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p><h3>{item.governance_decision ? `Decision #${item.governance_decision}` : 'Global queue'}</h3><p>{item.rationale}</p><p className="muted-text">Blockers: {item.blockers.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
