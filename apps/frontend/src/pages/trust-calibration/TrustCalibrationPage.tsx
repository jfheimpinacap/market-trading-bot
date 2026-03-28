import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  getTrustCalibrationFeedback,
  getTrustCalibrationRecommendations,
  getTrustCalibrationRuns,
  getTrustCalibrationSummary,
  runTrustCalibration,
} from '../../services/trustCalibration';
import type { TrustCalibrationRecommendationType } from '../../types/trustCalibration';

const formatDate = (value: string | null | undefined) => (value ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—');

function recommendationTone(code: TrustCalibrationRecommendationType): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (code === 'PROMOTE_TO_SAFE_AUTOMATION') return 'ready';
  if (code === 'DOWNGRADE_TO_MANUAL_ONLY' || code === 'BLOCK_AUTOMATION_FOR_ACTION') return 'offline';
  if (code === 'KEEP_APPROVAL_REQUIRED' || code === 'REVIEW_RULE_CONDITIONS') return 'pending';
  return 'neutral';
}

export function TrustCalibrationPage() {
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getTrustCalibrationSummary>> | null>(null);
  const [runs, setRuns] = useState<Awaited<ReturnType<typeof getTrustCalibrationRuns>>>([]);
  const [feedback, setFeedback] = useState<Awaited<ReturnType<typeof getTrustCalibrationFeedback>>>([]);
  const [recommendations, setRecommendations] = useState<Awaited<ReturnType<typeof getTrustCalibrationRecommendations>>>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryPayload, runsPayload] = await Promise.all([getTrustCalibrationSummary(), getTrustCalibrationRuns()]);
      const latestRunId = runsPayload[0]?.id;
      const [feedbackPayload, recommendationPayload] = await Promise.all([
        getTrustCalibrationFeedback(latestRunId),
        getTrustCalibrationRecommendations(latestRunId),
      ]);
      setSummary(summaryPayload);
      setRuns(runsPayload);
      setFeedback(feedbackPayload);
      setRecommendations(recommendationPayload);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load trust calibration analytics.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const latestRun = runs[0] ?? null;
  const notEnoughHistory = feedback.length === 0 || recommendations.every((row) => row.recommendation_type === 'REQUIRE_MORE_DATA');
  const recommendationByAction = useMemo(() => {
    const map = new Map<string, (typeof recommendations)[number]>();
    recommendations.forEach((item) => {
      if (!map.has(item.action_type)) map.set(item.action_type, item);
    });
    return map;
  }, [recommendations]);

  const runNow = useCallback(async () => {
    setRunning(true);
    setError(null);
    setMessage(null);
    try {
      const result = await runTrustCalibration({ window_days: 30, include_degraded: true });
      setMessage(`Trust calibration run #${result.run.id} completed with ${result.recommendation_count} recommendation(s).`);
      await load();
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : 'Trust calibration run failed.');
    } finally {
      setRunning(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Approval analytics & human-feedback governance"
        title="/trust-calibration"
        description="Recommendation-only trust calibration loop. This page analyzes approval outcomes, autopilot outcomes, and incident follow-through to propose conservative trust-tier tuning without auto-applying policy changes."
        actions={<div className="button-row"><button type="button" className="primary-button" disabled={running} onClick={() => void runNow()}>Run calibration</button><button type="button" className="secondary-button" onClick={() => navigate('/automation-policy')}>Automation policy</button><button type="button" className="secondary-button" onClick={() => navigate('/policy-tuning')}>Policy tuning</button><button type="button" className="secondary-button" onClick={() => navigate('/approvals')}>Approvals</button><button type="button" className="ghost-button" onClick={() => navigate('/trace')}>Trace explorer</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Manual-first guardrail" title="Recommendation-only by default" description="No policy mutation is auto-applied. Human approval remains required to tune trust tiers.">
          <div className="cockpit-metric-grid">
            <div><strong>Latest run</strong><div>{latestRun ? `#${latestRun.id}` : 'n/a'}</div></div>
            <div><strong>Actions analyzed</strong><div>{summary?.actions_analyzed ?? 0}</div></div>
            <div><strong>Approval friction</strong><div>{summary?.avg_approval_friction ?? '0'}</div></div>
            <div><strong>Recommendations</strong><div>{summary?.recommendations_count ?? 0}</div></div>
          </div>
        </SectionCard>

        {notEnoughHistory ? <EmptyState eyebrow="Calibration readiness" title="Not enough approval/autopilot history yet to calibrate trust tiers." description="REQUIRE_MORE_DATA is a healthy outcome until more manual decisions and autopilot evidence accumulate." /> : null}

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Top domains" title="Auto-success and caution hotspots" description="Fast domain scan to detect where policy may be too strict or too permissive.">
            <ul className="key-value-list">
              <li><span>Top auto-success domains</span><strong>{(summary?.top_auto_success_domains ?? []).map((item) => item.action_type).join(', ') || 'n/a'}</strong></li>
              <li><span>Top caution domains</span><strong>{(summary?.top_caution_domains ?? []).map((item) => item.action_type).join(', ') || 'n/a'}</strong></li>
              <li><span>PROMOTE_TO_SAFE_AUTOMATION</span><strong>{summary?.recommendation_breakdown?.PROMOTE_TO_SAFE_AUTOMATION ?? 0}</strong></li>
              <li><span>DOWNGRADE_TO_MANUAL_ONLY</span><strong>{summary?.recommendation_breakdown?.DOWNGRADE_TO_MANUAL_ONLY ?? 0}</strong></li>
              <li><span>REQUIRE_MORE_DATA</span><strong>{summary?.recommendation_breakdown?.REQUIRE_MORE_DATA ?? 0}</strong></li>
            </ul>
          </SectionCard>

          <SectionCard eyebrow="Recent runs" title="Auditable calibration history" description="Each run captures scope, summary, and recommendation evidence snapshots.">
            {runs.length === 0 ? <p className="muted-text">No trust calibration runs yet.</p> : (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>Run</th><th>Created</th><th>Scope</th><th>Status</th><th>Summary</th></tr></thead>
                  <tbody>
                    {runs.slice(0, 10).map((run) => (
                      <tr key={run.id}>
                        <td>#{run.id}</td>
                        <td>{formatDate(run.created_at)}</td>
                        <td>{run.window_days}d {run.profile_slug ? `· ${run.profile_slug}` : ''}</td>
                        <td><StatusBadge tone={run.status === 'READY' ? 'ready' : run.status === 'FAILED' ? 'offline' : 'pending'}>{run.status}</StatusBadge></td>
                        <td>{run.summary || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </div>

        <SectionCard eyebrow="Calibration metrics" title="Action-level trust evidence" description="Approval center and automation policy outcomes are consolidated into explicit, auditable metrics.">
          {feedback.length === 0 ? <p className="muted-text">No feedback snapshots available yet.</p> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Action type</th><th>Current tier</th><th>Approval rate</th><th>Rejection rate</th><th>Auto success</th><th>Incidents after auto</th><th>Recommendation</th></tr></thead>
                <tbody>
                  {feedback.map((row) => {
                    const recommendation = recommendationByAction.get(row.action_type);
                    return (
                      <tr key={row.id}>
                        <td>{row.action_type}</td>
                        <td>{row.current_trust_tier || 'n/a'}</td>
                        <td>{String(row.metrics.approval_rate ?? 0)}</td>
                        <td>{String(row.metrics.rejection_rate ?? 0)}</td>
                        <td>{String(row.metrics.auto_execution_success_rate ?? 0)}</td>
                        <td>{String(row.metrics.auto_action_followed_by_incident_rate ?? 0)}</td>
                        <td>{recommendation ? <StatusBadge tone={recommendationTone(recommendation.recommendation_type)}>{recommendation.recommendation_type}</StatusBadge> : '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Recommendations" title="Trust-tier tuning proposals" description="Conservative proposals with rationale, confidence, reason codes, and evidence links.">
          {recommendations.length === 0 ? <p className="muted-text">No recommendations generated yet.</p> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Action</th><th>Current → recommended</th><th>Recommendation</th><th>Reason codes</th><th>Confidence</th><th>Evidence links</th></tr></thead>
                <tbody>
                  {recommendations.slice(0, 25).map((item) => (
                    <tr key={item.id}>
                      <td><strong>{item.action_type}</strong><div className="muted-text">{item.rationale}</div></td>
                      <td>{item.current_trust_tier || 'n/a'} → {item.recommended_trust_tier || 'n/a'}</td>
                      <td><StatusBadge tone={recommendationTone(item.recommendation_type)}>{item.recommendation_type}</StatusBadge></td>
                      <td>{item.reason_codes.join(', ') || '—'}</td>
                      <td>{item.confidence}</td>
                      <td><button type="button" className="link-button" onClick={() => navigate('/trace')}>Trace</button> · <button type="button" className="link-button" onClick={() => navigate('/approvals')}>Approvals</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
