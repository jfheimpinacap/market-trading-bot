import { useCallback, useEffect, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  acknowledgeAutonomySeed,
  getAutonomySeedCandidates,
  getAutonomySeedRecommendations,
  getAutonomySeedSummary,
  getAutonomySeeds,
  registerAutonomySeed,
  runAutonomySeedReview,
} from '../../services/autonomySeed';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
  if (['READY', 'REGISTERED', 'ACKNOWLEDGED', 'REGISTER_ROADMAP_SEED', 'REGISTER_SCENARIO_SEED', 'REGISTER_PROGRAM_SEED', 'REGISTER_MANAGER_SEED'].includes(v)) return 'ready';
  if (['PENDING_REVIEW', 'REORDER_SEED_PRIORITY'].includes(v)) return 'pending';
  if (['BLOCKED', 'REQUIRE_MANUAL_SEED_REVIEW', 'DUPLICATE_SKIPPED', 'SKIP_DUPLICATE_SEED'].includes(v)) return 'offline';
  return 'neutral';
};

export function AutonomySeedPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Awaited<ReturnType<typeof getAutonomySeedCandidates>>>([]);
  const [seeds, setSeeds] = useState<Awaited<ReturnType<typeof getAutonomySeeds>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getAutonomySeedRecommendations>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomySeedSummary>> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [candidateData, seedData, recommendationData, summaryData] = await Promise.all([
        getAutonomySeedCandidates(),
        getAutonomySeeds(),
        getAutonomySeedRecommendations(),
        getAutonomySeedSummary(),
      ]);
      setCandidates(candidateData.slice(0, 400));
      setSeeds(seedData.slice(0, 400));
      setRecommendations(recommendationData.slice(0, 400));
      setSummary(summaryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy seed board.');
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
      const result = await runAutonomySeedReview({ actor: 'operator-ui' });
      setMessage(`Seed review run #${result.run} processed ${result.candidate_count} candidates and generated ${result.recommendation_count} recommendations.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run seed review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const registerSeed = useCallback(async (packageId: number) => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const result = await registerAutonomySeed(packageId, { actor: 'operator-ui' });
      setMessage(`Package #${packageId} seed status: ${result.seed_status}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not register seed for package #${packageId}.`);
    } finally {
      setBusy(false);
    }
  }, [load]);

  const acknowledgeSeed = useCallback(async (seedId: number) => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await acknowledgeAutonomySeed(seedId, { actor: 'operator-ui' });
      setMessage(`Seed #${seedId} acknowledged.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not acknowledge seed #${seedId}.`);
    } finally {
      setBusy(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy seed board"
        title="/autonomy-seed"
        description="Manual-first adopted package registry that converts ADOPTED package resolutions into auditable next-cycle planning seeds. Recommendation-first, no opaque auto-apply into roadmap/scenario/program/manager."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run seed review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-package-review')}>Package review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-package')}>Packages</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-decision')}>Decisions</button><button className="ghost-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Next-cycle seed posture" description="Tracks adopted package candidates, manual registration state, duplicates, and target distribution.">
          <div className="cockpit-metric-grid">
            <div><strong>Seed candidates</strong><div>{summary?.candidate_count ?? 0}</div></div>
            <div><strong>Ready</strong><div>{summary?.ready_count ?? 0}</div></div>
            <div><strong>Blocked</strong><div>{summary?.blocked_count ?? 0}</div></div>
            <div><strong>Registered</strong><div>{summary?.registered_count ?? 0}</div></div>
            <div><strong>Duplicate skipped</strong><div>{summary?.duplicate_skipped_count ?? 0}</div></div>
            <div><strong>Roadmap</strong><div>{summary?.roadmap_seed_count ?? 0}</div></div>
            <div><strong>Scenario</strong><div>{summary?.scenario_seed_count ?? 0}</div></div>
            <div><strong>Program</strong><div>{summary?.program_seed_count ?? 0}</div></div>
            <div><strong>Manager</strong><div>{summary?.manager_seed_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {!candidates.length ? <EmptyState eyebrow="No adopted packages" title="No adopted governance packages currently require seed registration." description="Once package review marks resolutions as ADOPTED, they appear here as seed candidates." /> : null}

        <SectionCard eyebrow="Candidates" title="Adopted package candidates" description="Traceable candidate queue with package/decision links and manual register action.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Package</th><th>Resolution</th><th>Decisions</th><th>Target</th><th>Priority</th><th>Ready</th><th>Existing seed</th><th>Blockers</th><th>Links</th><th>Actions</th></tr></thead>
              <tbody>
                {candidates.map((item) => (
                  <tr key={`${item.governance_package}-${item.package_resolution}`}>
                    <td>#{item.governance_package}</td>
                    <td>#{item.package_resolution}</td>
                    <td>{item.linked_decisions.length ? item.linked_decisions.map((id) => `#${id}`).join(', ') : 'n/a'}</td>
                    <td>{item.target_scope}</td>
                    <td>{item.priority_level}</td>
                    <td><StatusBadge tone={item.ready_for_seed ? 'ready' : 'offline'}>{item.ready_for_seed ? 'READY' : 'BLOCKED'}</StatusBadge></td>
                    <td>{item.existing_seed ? `#${item.existing_seed}` : '—'}</td>
                    <td>{item.blockers.join(', ') || 'None'}</td>
                    <td><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=governance_package&root_id=${encodeURIComponent(String(item.governance_package))}`)}>Package</button>{item.linked_decisions[0] ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=governance_decision&root_id=${encodeURIComponent(String(item.linked_decisions[0]))}`)}>Decision</button> : null}{typeof item.metadata['campaign_id'] === 'number' ? <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.metadata['campaign_id']))}`)}>Campaign</button> : null}</td>
                    <td><button className="ghost-button" type="button" disabled={busy} onClick={() => void registerSeed(item.governance_package)}>Register seed</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Seeds history" title="Persisted governance seeds" description="Formal seed artifacts for next-cycle roadmap/scenario/program/manager/operator-review planning inputs.">
            {!seeds.length ? <p className="muted-text">No governance seeds registered yet.</p> : <div className="page-stack">{seeds.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.seed_status)}>{item.seed_status}</StatusBadge></p><h3>{item.title}</h3><p>{item.summary}</p><p className="muted-text">Type: {item.seed_type} · Target: {item.target_scope} · Priority: {item.priority_level} · Registered: {item.registered_at ?? 'n/a'}</p><div className="button-row"><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=governance_seed&root_id=${encodeURIComponent(String(item.id))}`)}>Trace seed</button><button className="ghost-button" type="button" disabled={busy} onClick={() => void acknowledgeSeed(item.id)}>Acknowledge</button></div></article>))}</div>}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Seed registration recommendations" description="Recommendation-first outputs to guide transparent manual registration and queue prioritization.">
            {!recommendations.length ? <p className="muted-text">No recommendations generated yet.</p> : <div className="page-stack">{recommendations.map((item) => (<article key={item.id} className="status-card"><p className="status-card__label"><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></p><h3>{item.governance_package ? `Package #${item.governance_package}` : 'Global queue'}</h3><p>{item.rationale}</p><p className="muted-text">Seed type: {item.seed_type || 'n/a'} · Blockers: {item.blockers.join(', ') || 'none'} · Confidence: {item.confidence}</p></article>))}</div>}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
