import { useCallback, useEffect, useMemo, useState } from 'react';

import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { navigate } from '../../lib/router';
import {
  getExposureClusterSnapshots,
  getExposureConflictReviews,
  getExposureCoordinationSummary,
  getExposureDecisions,
  getExposureRecommendations,
  getPortfolioExposure,
  getPortfolioGovernanceRuns,
  getPortfolioGovernanceSummary,
  getPortfolioThrottle,
  runExposureCoordinationReview,
  runPortfolioGovernance,
} from '../../services/portfolioGovernor';
import type {
  PortfolioExposureClusterSnapshot,
  PortfolioExposureConflictReview,
  PortfolioExposureCoordinationSummary,
  PortfolioExposureDecision,
  PortfolioExposureRecommendation,
  PortfolioExposureSnapshot,
  PortfolioGovernanceRun,
  PortfolioGovernanceSummary,
  PortfolioThrottleDecision,
} from '../../types/portfolioGovernor';

const badgeClass = (state: string) => {
  if (state === 'NORMAL') return 'signal-badge signal-badge--actionable';
  if (state === 'CAUTION') return 'signal-badge signal-badge--monitor';
  if (state === 'THROTTLED') return 'signal-badge signal-badge--bearish';
  return 'signal-badge signal-badge--bearish';
};

export function PortfolioGovernorPage() {
  const [summary, setSummary] = useState<PortfolioGovernanceSummary | null>(null);
  const [exposureSummary, setExposureSummary] = useState<PortfolioExposureCoordinationSummary | null>(null);
  const [clusters, setClusters] = useState<PortfolioExposureClusterSnapshot[]>([]);
  const [conflicts, setConflicts] = useState<PortfolioExposureConflictReview[]>([]);
  const [decisions, setDecisions] = useState<PortfolioExposureDecision[]>([]);
  const [recommendations, setRecommendations] = useState<PortfolioExposureRecommendation[]>([]);
  const [exposure, setExposure] = useState<PortfolioExposureSnapshot | null>(null);
  const [throttle, setThrottle] = useState<PortfolioThrottleDecision | null>(null);
  const [runs, setRuns] = useState<PortfolioGovernanceRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [runningExposure, setRunningExposure] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [profile, setProfile] = useState('balanced_portfolio_governor');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, r, es, c, f, d, rec] = await Promise.all([
        getPortfolioGovernanceSummary(),
        getPortfolioGovernanceRuns(),
        getExposureCoordinationSummary(),
        getExposureClusterSnapshots(),
        getExposureConflictReviews(),
        getExposureDecisions(),
        getExposureRecommendations(),
      ]);
      setSummary(s);
      setRuns(r);
      setExposureSummary(es);
      setClusters(c);
      setConflicts(f);
      setDecisions(d);
      setRecommendations(rec);
      if (s.profiles[0] && !s.profiles.some((item) => item.slug === profile)) setProfile(s.profiles[0].slug);
      const [e, t] = await Promise.allSettled([getPortfolioExposure(), getPortfolioThrottle()]);
      setExposure(e.status === 'fulfilled' ? e.value : null);
      setThrottle(t.status === 'fulfilled' ? t.value : null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load portfolio governor state.');
    } finally {
      setLoading(false);
    }
  }, [profile]);

  useEffect(() => {
    void load();
  }, [load]);

  const run = useCallback(async () => {
    setRunning(true);
    setMessage(null);
    try {
      const response = await runPortfolioGovernance({ profile_slug: profile });
      setMessage(`Governance run #${response.id} completed.`);
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Governance run failed.');
    } finally {
      setRunning(false);
    }
  }, [load, profile]);

  const runExposure = useCallback(async () => {
    setRunningExposure(true);
    setMessage(null);
    try {
      const response = await runExposureCoordinationReview();
      setMessage(`Exposure coordination run #${response.id} completed.`);
      await load();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Exposure coordination run failed.');
    } finally {
      setRunningExposure(false);
    }
  }, [load]);

  const cards = useMemo(
    () => [
      { label: 'Open positions', value: exposure?.open_positions ?? 0 },
      { label: 'Total exposure', value: exposure?.total_exposure ?? '0' },
      { label: 'Concentration (market)', value: exposure ? `${(Number(exposure.concentration_market_ratio) * 100).toFixed(1)}%` : '0%' },
      { label: 'Throttle', value: throttle?.state ?? summary?.latest_throttle_state ?? 'NORMAL' },
      { label: 'Drawdown signal', value: exposure ? `${(Number(exposure.recent_drawdown_pct) * 100).toFixed(2)}%` : '0.00%' },
    ],
    [exposure, throttle, summary],
  );

  const exposureCards = useMemo(
    () => [
      { label: 'Clusters reviewed', value: exposureSummary?.clusters_reviewed ?? 0 },
      { label: 'Concentration alerts', value: exposureSummary?.concentration_alerts ?? 0 },
      { label: 'Conflict alerts', value: exposureSummary?.conflict_alerts ?? 0 },
      { label: 'Throttles', value: exposureSummary?.throttles ?? 0 },
      { label: 'Defers', value: exposureSummary?.defers ?? 0 },
      { label: 'Parks', value: exposureSummary?.parks ?? 0 },
      { label: 'Manual review', value: exposureSummary?.manual_reviews ?? 0 },
    ],
    [exposureSummary],
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Portfolio governor"
        title="/portfolio-governor"
        description="Aggregate portfolio governance and global exposure coordination for local-first paper operation only. No real-money execution."
        actions={
          <div className="button-row">
            <button className="secondary-button" type="button" onClick={() => navigate('/portfolio')}>Open Portfolio</button>
            <button className="secondary-button" type="button" onClick={() => navigate('/mission-control')}>Open Mission Control</button>
            <button className="secondary-button" type="button" onClick={() => navigate('/opportunities')}>Open Opportunities</button>
            <button className="secondary-button" type="button" onClick={() => navigate('/profile-manager')}>Open Profile Manager</button>
          </div>
        }
      />

      <SectionCard eyebrow="Governance controls" title="Run governance review" description="Run aggregate exposure analysis and refresh throttle decision.">
        <div className="markets-filters__actions">
          <label className="field-group">
            <span>Profile</span>
            <select className="select-input" value={profile} onChange={(e) => setProfile(e.target.value)}>
              {(summary?.profiles ?? []).map((p) => <option key={p.slug} value={p.slug}>{p.label}</option>)}
            </select>
          </label>
          <button className="primary-button" type="button" disabled={running} onClick={() => void run()}>{running ? 'Running…' : 'Run governance review'}</button>
          <button className="secondary-button" type="button" disabled={runningExposure} onClick={() => void runExposure()}>{runningExposure ? 'Running…' : 'Run exposure coordination review'}</button>
          {message ? <span className="muted-text">{message}</span> : null}
        </div>
      </SectionCard>

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Portfolio governance summary" description="Current aggregate exposure and throttling stance.">
          <div className="dashboard-stat-grid">{cards.map((c) => <article key={c.label} className="dashboard-stat-card"><span>{c.label}</span><strong>{c.value}</strong></article>)}</div>
          {!exposure ? <p className="muted-text">Portfolio exposure is currently light.</p> : null}
        </SectionCard>

        <SectionCard
          eyebrow="Global Exposure Coordination"
          title="Cross-session exposure harmonizer"
          description="Paper-only, local-first, portfolio-aware control layer. Coordinates cluster concentration/conflicts across sessions, open positions, and pending dispatches without live execution."
        >
          <div className="dashboard-stat-grid">{exposureCards.map((c) => <article key={c.label} className="dashboard-stat-card"><span>{c.label}</span><strong>{c.value}</strong></article>)}</div>
        </SectionCard>

        <SectionCard eyebrow="Throttle decision" title="Current gating" description="Controls how aggressively new opportunities can enter the portfolio.">
          {!throttle ? <p className="muted-text">No throttle decision yet. Run governance review.</p> : (
            <div className="system-metadata-grid">
              <div><strong>State:</strong> <span className={badgeClass(throttle.state)}>{throttle.state}</span></div>
              <div><strong>Size multiplier:</strong> {throttle.recommended_max_size_multiplier}</div>
              <div><strong>Max new entries:</strong> {throttle.recommended_max_new_positions}</div>
              <div><strong>Reason codes:</strong> {throttle.reason_codes.join(', ') || 'N/A'}</div>
              <div><strong>Regime signals:</strong> {throttle.regime_signals.join(', ') || 'normal'}</div>
              <div><strong>Rationale:</strong> {throttle.rationale}</div>
            </div>
          )}
          {throttle?.state === 'BLOCK_NEW_ENTRIES' ? <p><strong>New entries are blocked at portfolio level.</strong></p> : null}
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Cluster snapshots" title="Exposure clusters" description="Global cluster view of market/narrative/directional concentration.">
            {clusters.length === 0 ? <p className="muted-text">No cluster snapshots yet.</p> : (
              <div className="markets-table-wrapper">
                <table className="markets-table">
                  <thead><tr><th>Cluster</th><th>Type</th><th>Direction</th><th>Sessions</th><th>Pending dispatches</th><th>Concentration</th><th>Summary</th></tr></thead>
                  <tbody>{clusters.slice(0, 12).map((item) => <tr key={item.id}><td>{item.cluster_label}</td><td>{item.cluster_type}</td><td>{item.net_direction}</td><td>{item.session_count}</td><td>{item.pending_dispatch_count}</td><td>{item.concentration_status}</td><td>{item.cluster_summary}</td></tr>)}</tbody>
                </table>
              </div>
            )}
          </SectionCard>

          <SectionCard eyebrow="Conflict reviews" title="Concentration/conflict findings" description="Detected concentration, conflict, overload, and low-value stacking.">
            {conflicts.length === 0 ? <p className="muted-text">No conflict reviews yet.</p> : (
              <div className="markets-table-wrapper">
                <table className="markets-table">
                  <thead><tr><th>Cluster ID</th><th>Type</th><th>Severity</th><th>Summary</th></tr></thead>
                  <tbody>{conflicts.slice(0, 12).map((item) => <tr key={item.id}><td>#{item.linked_cluster_snapshot}</td><td>{item.review_type}</td><td>{item.review_severity}</td><td>{item.review_summary}</td></tr>)}</tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </div>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Decisions" title="Exposure decisions" description="Conservative throttle/defer/park/pause decisions with auditability.">
            {decisions.length === 0 ? <p className="muted-text">No exposure decisions yet.</p> : (
              <div className="markets-table-wrapper">
                <table className="markets-table">
                  <thead><tr><th>Cluster ID</th><th>Decision</th><th>Status</th><th>Auto</th><th>Summary</th></tr></thead>
                  <tbody>{decisions.slice(0, 12).map((item) => <tr key={item.id}><td>#{item.linked_cluster_snapshot}</td><td>{item.decision_type}</td><td>{item.decision_status}</td><td>{item.auto_applicable ? 'Yes' : 'No'}</td><td>{item.decision_summary}</td></tr>)}</tbody>
                </table>
              </div>
            )}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Exposure recommendations" description="Explicit portfolio-wide recommendations for cluster governance.">
            {recommendations.length === 0 ? <p className="muted-text">No recommendations yet.</p> : (
              <div className="markets-table-wrapper">
                <table className="markets-table">
                  <thead><tr><th>Type</th><th>Rationale</th><th>Blockers</th><th>Confidence</th></tr></thead>
                  <tbody>{recommendations.slice(0, 12).map((item) => <tr key={item.id}><td>{item.recommendation_type}</td><td>{item.rationale}</td><td>{item.blockers.join(', ') || 'None'}</td><td>{item.confidence.toFixed(2)}</td></tr>)}</tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </div>

        <SectionCard eyebrow="Governance runs" title="Recent runs" description="Audit trail of completed governance decisions.">
          {runs.length === 0 ? <p className="muted-text">No governance runs yet.</p> : (
            <div className="markets-table-wrapper">
              <table className="markets-table">
                <thead><tr><th>ID</th><th>Status</th><th>Throttle</th><th>Summary</th><th>Created</th></tr></thead>
                <tbody>{runs.slice(0, 10).map((runItem) => <tr key={runItem.id}><td>#{runItem.id}</td><td>{runItem.status}</td><td>{runItem.throttle_decision?.state ?? 'N/A'}</td><td>{runItem.summary}</td><td>{runItem.started_at}</td></tr>)}</tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
