import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import { applyAutomationProfile, getAutomationActionLogs, getAutomationDecisions, getAutomationPolicySummary, getCurrentAutomationPolicy } from '../../services/automationPolicy';
import type { AutomationDecisionOutcome, AutomationTrustTier } from '../../types/automationPolicy';

const formatDate = (value: string) => new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));

function tierTone(tier: AutomationTrustTier): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (tier === 'SAFE_AUTOMATION') return 'ready';
  if (tier === 'APPROVAL_REQUIRED') return 'pending';
  if (tier === 'AUTO_BLOCKED') return 'offline';
  return 'neutral';
}

function outcomeTone(outcome: AutomationDecisionOutcome): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (outcome === 'ALLOWED') return 'ready';
  if (outcome === 'APPROVAL_REQUIRED' || outcome === 'MANUAL_ONLY') return 'pending';
  if (outcome === 'BLOCKED') return 'offline';
  return 'neutral';
}

export function AutomationPolicyPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [current, setCurrent] = useState<Awaited<ReturnType<typeof getCurrentAutomationPolicy>> | null>(null);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutomationPolicySummary>> | null>(null);
  const [decisions, setDecisions] = useState<Awaited<ReturnType<typeof getAutomationDecisions>>>([]);
  const [logs, setLogs] = useState<Awaited<ReturnType<typeof getAutomationActionLogs>>>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [currentData, summaryData, decisionsData, logsData] = await Promise.all([
        getCurrentAutomationPolicy(),
        getAutomationPolicySummary(),
        getAutomationDecisions(),
        getAutomationActionLogs(),
      ]);
      setCurrent(currentData);
      setSummary(summaryData);
      setDecisions(decisionsData);
      setLogs(logsData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load automation policy data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const topDecisions = useMemo(() => decisions.slice(0, 10), [decisions]);
  const topLogs = useMemo(() => logs.slice(0, 10), [logs]);

  const switchProfile = useCallback(async (slug: string) => {
    setMessage(null);
    setError(null);
    try {
      await applyAutomationProfile(slug);
      setMessage(`Active automation profile switched to ${slug}.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not apply automation profile.');
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Supervised runbook autopilot"
        title="/automation-policy"
        description="Trust-tiered automation matrix for manual-first, paper-only operations. This page classifies what can auto-run, what needs approval, and what stays blocked, with explicit audit logs."
        actions={<div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/runbooks')}>Runbooks</button><button className="secondary-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button><button className="secondary-button" type="button" onClick={() => navigate('/incidents')}>Incidents</button><button className="secondary-button" type="button" onClick={() => navigate('/mission-control')}>Mission control</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        {!current || !summary ? null : (
          <>
            <SectionCard eyebrow="Current policy" title="Active profile and effective trust posture" description="Automation policy is always subordinate to certification, runtime, and safety guardrails.">
              <div className="cockpit-metric-grid">
                <div><strong>Active profile</strong><div>{current.profile.slug}</div></div>
                <div><strong>Recommendation mode</strong><div>{current.profile.recommendation_mode ? 'Enabled' : 'Disabled'}</div></div>
                <div><strong>Runbook auto-advance</strong><div>{current.profile.allow_runbook_auto_advance ? 'Allowed' : 'Manual only'}</div></div>
                <div><strong>Runtime</strong><div>{current.guardrails.runtime_mode ?? 'n/a'} / {current.guardrails.runtime_status ?? 'n/a'}</div></div>
                <div><strong>Safety</strong><div>{current.guardrails.safety_status ?? 'n/a'}</div></div>
                <div><strong>Certification</strong><div>{current.guardrails.certification_level ?? 'n/a'}</div></div>
                <div><strong>Degraded mode</strong><div>{current.guardrails.degraded_mode_state ?? 'n/a'}</div></div>
                <div><strong>Recent auto-actions</strong><div>{summary.log_counts.EXECUTED ?? 0}</div></div>
                <div><strong>Blocked decisions</strong><div>{summary.decision_counts.BLOCKED ?? 0}</div></div>
              </div>
              <div className="button-row">
                <button type="button" className="ghost-button" onClick={() => void switchProfile('conservative_manual_first')}>Set conservative_manual_first</button>
                <button type="button" className="ghost-button" onClick={() => void switchProfile('balanced_assist')}>Set balanced_assist</button>
                <button type="button" className="ghost-button" onClick={() => void switchProfile('supervised_autopilot')}>Set supervised_autopilot</button>
              </div>
            </SectionCard>

            <div className="content-grid content-grid--two-columns">
              <SectionCard eyebrow="Policy matrix" title="Action trust tiers" description="Explicit rule set by action type and trust tier with conservative defaults.">
                {current.rules.length === 0 ? <EmptyState eyebrow="Rules" title="No policy rules" description="No automation policy rules found yet." /> : (
                  <div className="table-wrapper">
                    <table className="data-table">
                      <thead><tr><th>Action type</th><th>Tier</th><th>Rationale</th></tr></thead>
                      <tbody>
                        {current.rules.map((rule) => (
                          <tr key={rule.id}>
                            <td>{rule.action_type}</td>
                            <td><StatusBadge tone={tierTone(rule.trust_tier)}>{rule.trust_tier}</StatusBadge></td>
                            <td>{rule.rationale}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </SectionCard>

              <SectionCard eyebrow="Recommendation mode" title="Gradual opt-in automation" description="Blocked and approval-required outcomes are expected healthy results, not system failures.">
                <ul className="key-value-list">
                  <li><span>Auto-eligible actions</span><strong>{summary.auto_eligible_action_types.length}</strong></li>
                  <li><span>Hard-blocked actions</span><strong>{summary.blocked_action_types.length}</strong></li>
                  <li><span>Allowed decisions</span><strong>{summary.decision_counts.ALLOWED ?? 0}</strong></li>
                  <li><span>Approval required</span><strong>{summary.decision_counts.APPROVAL_REQUIRED ?? 0}</strong></li>
                  <li><span>Manual only</span><strong>{summary.decision_counts.MANUAL_ONLY ?? 0}</strong></li>
                  <li><span>Blocked</span><strong>{summary.decision_counts.BLOCKED ?? 0}</strong></li>
                </ul>
              </SectionCard>
            </div>

            <SectionCard eyebrow="Recent decisions" title="Allowed / approval-required / blocked history" description="Every decision captures trust tier, reasons, and source context for auditability.">
              {topDecisions.length === 0 ? <p className="muted-text">No automation decisions recorded yet.</p> : (
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead><tr><th>When</th><th>Action</th><th>Tier</th><th>Outcome</th><th>Reason codes</th></tr></thead>
                    <tbody>
                      {topDecisions.map((item) => (
                        <tr key={item.id}>
                          <td>{formatDate(item.created_at)}</td>
                          <td>{item.action_type}</td>
                          <td><StatusBadge tone={tierTone(item.effective_trust_tier)}>{item.effective_trust_tier}</StatusBadge></td>
                          <td><StatusBadge tone={outcomeTone(item.outcome)}>{item.outcome}</StatusBadge></td>
                          <td>{item.reason_codes.length ? item.reason_codes.join(', ') : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>

            <SectionCard eyebrow="Auto-action log" title="Executed/skipped action records" description="No automation occurs without an explicit log linked to a policy decision.">
              {topLogs.length === 0 ? <p className="muted-text">No automation action logs recorded yet.</p> : (
                <ul>
                  {topLogs.map((log) => (
                    <li key={log.id}><StatusBadge tone={log.execution_status === 'EXECUTED' ? 'ready' : log.execution_status === 'FAILED' ? 'offline' : 'pending'}>{log.execution_status}</StatusBadge> <strong>{log.action_name}</strong> — {log.result_summary} ({formatDate(log.created_at)})</li>
                  ))}
                </ul>
              )}
            </SectionCard>
          </>
        )}
      </DataStateWrapper>
    </div>
  );
}
