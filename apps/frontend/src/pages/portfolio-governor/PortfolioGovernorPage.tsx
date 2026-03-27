import { useCallback, useEffect, useMemo, useState } from 'react';

import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { navigate } from '../../lib/router';
import { getPortfolioExposure, getPortfolioGovernanceRuns, getPortfolioGovernanceSummary, getPortfolioThrottle, runPortfolioGovernance } from '../../services/portfolioGovernor';
import type { PortfolioExposureSnapshot, PortfolioGovernanceRun, PortfolioGovernanceSummary, PortfolioThrottleDecision } from '../../types/portfolioGovernor';

const badgeClass = (state: string) => {
  if (state === 'NORMAL') return 'signal-badge signal-badge--actionable';
  if (state === 'CAUTION') return 'signal-badge signal-badge--monitor';
  if (state === 'THROTTLED') return 'signal-badge signal-badge--bearish';
  return 'signal-badge signal-badge--bearish';
};

export function PortfolioGovernorPage() {
  const [summary, setSummary] = useState<PortfolioGovernanceSummary | null>(null);
  const [exposure, setExposure] = useState<PortfolioExposureSnapshot | null>(null);
  const [throttle, setThrottle] = useState<PortfolioThrottleDecision | null>(null);
  const [runs, setRuns] = useState<PortfolioGovernanceRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [profile, setProfile] = useState('balanced_portfolio_governor');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, r] = await Promise.all([getPortfolioGovernanceSummary(), getPortfolioGovernanceRuns()]);
      setSummary(s);
      setRuns(r);
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

  useEffect(() => { void load(); }, [load]);

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

  const cards = useMemo(() => [
    { label: 'Open positions', value: exposure?.open_positions ?? 0 },
    { label: 'Total exposure', value: exposure?.total_exposure ?? '0' },
    { label: 'Concentration (market)', value: exposure ? `${(Number(exposure.concentration_market_ratio) * 100).toFixed(1)}%` : '0%' },
    { label: 'Throttle', value: throttle?.state ?? summary?.latest_throttle_state ?? 'NORMAL' },
    { label: 'Drawdown signal', value: exposure ? `${(Number(exposure.recent_drawdown_pct) * 100).toFixed(2)}%` : '0.00%' },
  ], [exposure, throttle, summary]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Portfolio governor"
        title="/portfolio-governor"
        description="Aggregate portfolio governance and regime-aware throttling for paper/demo only operation. No real-money execution."
        actions={<div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/portfolio')}>Open Portfolio</button><button className="secondary-button" type="button" onClick={() => navigate('/mission-control')}>Open Mission Control</button><button className="secondary-button" type="button" onClick={() => navigate('/opportunities')}>Open Opportunities</button><button className="secondary-button" type="button" onClick={() => navigate('/profile-manager')}>Open Profile Manager</button></div>}
      />

      <SectionCard eyebrow="Governance controls" title="Run governance review" description="Run aggregate exposure analysis and refresh throttle decision.">
        <div className="markets-filters__actions">
          <label className="field-group"><span>Profile</span><select className="select-input" value={profile} onChange={(e) => setProfile(e.target.value)}>{(summary?.profiles ?? []).map((p) => <option key={p.slug} value={p.slug}>{p.label}</option>)}</select></label>
          <button className="primary-button" type="button" disabled={running} onClick={() => void run()}>{running ? 'Running…' : 'Run governance review'}</button>
          {message ? <span className="muted-text">{message}</span> : null}
        </div>
      </SectionCard>

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Portfolio governance summary" description="Current aggregate exposure and throttling stance.">
          <div className="dashboard-stat-grid">{cards.map((c) => <article key={c.label} className="dashboard-stat-card"><span>{c.label}</span><strong>{c.value}</strong></article>)}</div>
          {!exposure ? <p className="muted-text">Portfolio exposure is currently light.</p> : null}
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
          <SectionCard eyebrow="Exposure" title="By market/provider/category" description="Concentration view for aggregate governance decisions.">
            {!exposure ? <p className="muted-text">No exposure snapshot yet.</p> : (
              <div className="markets-table-wrapper">
                <table className="markets-table">
                  <thead><tr><th>Bucket</th><th>Label</th><th>Exposure</th><th>Ratio</th></tr></thead>
                  <tbody>
                    {[
                      ...exposure.exposure_by_market.map((x) => ({ ...x, bucket: 'Market' })),
                      ...exposure.exposure_by_provider.map((x) => ({ ...x, bucket: 'Provider' })),
                      ...exposure.exposure_by_category.map((x) => ({ ...x, bucket: 'Category' })),
                    ].slice(0, 20).map((item, idx) => <tr key={`${item.bucket}-${item.label}-${idx}`}><td>{item.bucket}</td><td>{item.label}</td><td>{item.exposure.toFixed(2)}</td><td>{(item.ratio * 100).toFixed(1)}%</td></tr>)}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>

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
        </div>
      </DataStateWrapper>
    </div>
  );
}
