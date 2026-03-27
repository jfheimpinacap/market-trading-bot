import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import { completeRunbook, createRunbook, getRunbookRecommendations, getRunbookSummary, getRunbooks, getRunbookTemplates, runRunbookStep } from '../../services/runbooks';
import { getAutomationPolicySummary } from '../../services/automationPolicy';
import type { RunbookInstance, RunbookStepActionKind, RunbookSummary, RunbookTemplate } from '../../types/runbooks';

function statusTone(status: string): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (status === 'COMPLETED' || status === 'DONE') return 'ready';
  if (status === 'BLOCKED' || status === 'FAILED' || status === 'ESCALATED') return 'offline';
  if (status === 'IN_PROGRESS' || status === 'RUNNING' || status === 'READY' || status === 'OPEN') return 'pending';
  return 'neutral';
}

function actionKindTone(action: RunbookStepActionKind): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (action === 'api_action') return 'pending';
  if (action === 'manual' || action === 'review' || action === 'confirm') return 'neutral';
  return 'neutral';
}

function formatDate(value: string) {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(d);
}

export function RunbooksPage() {
  const [templates, setTemplates] = useState<RunbookTemplate[]>([]);
  const [runbooks, setRunbooks] = useState<RunbookInstance[]>([]);
  const [summary, setSummary] = useState<RunbookSummary | null>(null);
  const [recommendations, setRecommendations] = useState<Array<{ template_slug: string; reason: string; source_object_type: string; source_object_id: string; priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' }>>([]);
  const [autoEligibleActions, setAutoEligibleActions] = useState<string[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [templatesData, runbooksData, summaryData, recommendationsData, automationSummary] = await Promise.all([
        getRunbookTemplates(),
        getRunbooks(),
        getRunbookSummary(),
        getRunbookRecommendations(),
        getAutomationPolicySummary(),
      ]);
      setTemplates(templatesData);
      setRunbooks(runbooksData);
      setSummary(summaryData);
      setRecommendations(recommendationsData.results);
      setAutoEligibleActions(automationSummary.auto_eligible_action_types ?? []);
      if (!selectedId && runbooksData.length > 0) {
        setSelectedId(runbooksData[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load runbooks data.');
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    void load();
  }, [load]);

  const selected = useMemo(() => runbooks.find((item) => item.id === selectedId) ?? null, [runbooks, selectedId]);

  const runAction = useCallback(async (action: () => Promise<unknown>, okMessage: string) => {
    setActionLoading(true);
    setError(null);
    setMessage(null);
    try {
      await action();
      setMessage(okMessage);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Runbook action failed.');
    } finally {
      setActionLoading(false);
    }
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operator playbooks"
        title="/runbooks"
        description="Guided manual-first remediation workflows. Runbooks orchestrate existing module actions with step-by-step progress and auditable evidence; they do not introduce opaque automation or real execution."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/cockpit')}>Open Cockpit</button><button type="button" className="secondary-button" onClick={() => navigate('/incidents')}>Open Incidents</button><button type="button" className="secondary-button" onClick={() => navigate('/mission-control')}>Open Mission Control</button><button type="button" className="secondary-button" onClick={() => navigate('/operator-queue')}>Open Operator Queue</button><button type="button" className="secondary-button" onClick={() => navigate('/trace')}>Open Trace Explorer</button><button type="button" className="secondary-button" onClick={() => navigate('/automation-policy')}>Open Automation Policy</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Runbook status counts" description="Operational runbook posture by lifecycle state.">
          <div className="cockpit-metric-grid">
            <div><strong>Open</strong><div>{summary?.counts.open ?? 0}</div></div>
            <div><strong>In progress</strong><div>{summary?.counts.in_progress ?? 0}</div></div>
            <div><strong>Blocked</strong><div>{summary?.counts.blocked ?? 0}</div></div>
            <div><strong>Completed</strong><div>{summary?.counts.completed ?? 0}</div></div>
            <div><strong>Escalated</strong><div>{summary?.counts.escalated ?? 0}</div></div>
            <div><strong>Auto-eligible actions</strong><div>{autoEligibleActions.length}</div></div>
          </div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Active runbooks" title="Top by priority" description="Open/in-progress runbooks and next suggested step.">
            {!summary?.top_active.length ? (
              <EmptyState eyebrow="Runbooks" title="No active runbooks right now." description="Create one from a template or use a recommendation to start guided remediation." />
            ) : (
              <ul className="key-value-list">
                {summary.top_active.map((item) => (
                  <li key={item.id}>
                    <span>
                      <button type="button" className="link-button" onClick={() => setSelectedId(item.id)}>#{item.id} {item.template_slug}</button>
                    </span>
                    <strong>
                      <StatusBadge tone={statusTone(item.status)}>{item.status}</StatusBadge>
                      {' '}{item.progress.done}/{item.progress.total}
                    </strong>
                  </li>
                ))}
              </ul>
            )}
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Suggested runbooks" description="Deterministic matching by incidents, degraded posture, certification, rollout, parity and queue pressure.">
            {recommendations.length === 0 ? <EmptyState eyebrow="Recommendations" title="No recommendations" description="No matching trigger conditions found right now." /> : (
              <div className="page-stack">
                {recommendations.map((item) => (
                  <article key={`${item.template_slug}-${item.source_object_type}-${item.source_object_id}`} className="cockpit-attention-item">
                    <div>
                      <p className="section-label">{item.priority}</p>
                      <h3>{item.template_slug}</h3>
                      <p>{item.reason}</p>
                    </div>
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={actionLoading}
                      onClick={() => void runAction(
                        () => createRunbook({
                          template_slug: item.template_slug,
                          source_object_type: item.source_object_type,
                          source_object_id: item.source_object_id,
                          priority: item.priority,
                        }),
                        `Runbook ${item.template_slug} created.`,
                      )}
                    >
                      Create runbook
                    </button>
                  </article>
                ))}
              </div>
            )}
          </SectionCard>
        </div>

        <SectionCard eyebrow="Template catalog" title="Available runbook templates" description="Reusable operational templates. Creating a runbook does not duplicate module logic.">
          {templates.length === 0 ? <EmptyState eyebrow="Templates" title="No templates available" description="Template catalog is empty." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Name</th><th>Slug</th><th>Trigger</th><th>Severity</th><th>Action</th></tr></thead>
                <tbody>
                  {templates.map((template) => (
                    <tr key={template.id}>
                      <td>{template.name}</td>
                      <td>{template.slug}</td>
                      <td>{template.trigger_type}</td>
                      <td><StatusBadge tone={statusTone(template.severity_hint)}>{template.severity_hint || 'n/a'}</StatusBadge></td>
                      <td>
                        <button
                          type="button"
                          className="ghost-button"
                          disabled={actionLoading}
                          onClick={() => void runAction(
                            () => createRunbook({ template_slug: template.slug, source_object_type: template.trigger_type, source_object_id: 'manual' }),
                            `Runbook created from ${template.slug}.`,
                          )}
                        >
                          Create runbook
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Runbook detail" title={selected ? `Runbook #${selected.id} (${selected.template.slug})` : 'Select a runbook'} description="Step-by-step workflow with action history and related links.">
          {!selected ? <EmptyState eyebrow="Detail" title="Select a runbook" description="Pick an active runbook to inspect steps, run actions, and review result history." /> : (
            <div className="page-stack">
              <p><strong>Status:</strong> <StatusBadge tone={statusTone(selected.status)}>{selected.status}</StatusBadge></p>
              <p><strong>Priority:</strong> <StatusBadge tone={statusTone(selected.priority)}>{selected.priority}</StatusBadge></p>
              <p><strong>Source:</strong> {selected.source_object_type} / {selected.source_object_id}</p>
              <p><strong>Summary:</strong> {selected.summary || '—'}</p>
              <p><strong>Related links:</strong> <button type="button" className="link-button" onClick={() => navigate(`/trace?root_type=${encodeURIComponent(selected.source_object_type)}&root_id=${encodeURIComponent(selected.source_object_id)}`)}>Open trace</button> · <button type="button" className="link-button" onClick={() => navigate('/incidents')}>Incidents</button> · <button type="button" className="link-button" onClick={() => navigate('/operator-queue')}>Operator queue</button> · <button type="button" className="link-button" onClick={() => navigate('/mission-control')}>Mission control</button> · <button type="button" className="link-button" onClick={() => navigate('/automation-policy')}>Automation policy</button></p>

              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>#</th><th>Step</th><th>Kind</th><th>Status</th><th>Instructions</th><th>Actions</th></tr></thead>
                  <tbody>
                    {selected.steps.map((step) => (
                      <tr key={step.id}>
                        <td>{step.step_order}</td>
                        <td>{step.title}</td>
                        <td><StatusBadge tone={actionKindTone(step.action_kind)}>{step.action_kind.toUpperCase()}</StatusBadge></td>
                        <td><StatusBadge tone={statusTone(step.status)}>{step.status}</StatusBadge></td>
                        <td>{step.instructions}</td>
                        <td>
                          <button
                            type="button"
                            className="secondary-button"
                            disabled={actionLoading || !['READY', 'PENDING'].includes(step.status) || ['COMPLETED', 'ABORTED'].includes(selected.status)}
                            onClick={() => void runAction(() => runRunbookStep(selected.id, step.id), `Step ${step.step_order} executed.`)}
                          >
                            Run step
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div>
                <strong>Result history</strong>
                {selected.steps.every((step) => step.action_results.length === 0) ? <p className="muted-text">No action results recorded yet.</p> : (
                  <ul>
                    {selected.steps.flatMap((step) => step.action_results.map((result) => (
                      <li key={result.id}>
                        <StatusBadge tone={statusTone(result.action_status)}>{result.action_status}</StatusBadge> <strong>{result.action_name}</strong> — {result.result_summary} ({formatDate(result.created_at)})
                      </li>
                    )))}
                  </ul>
                )}
              </div>

              <div className="button-row">
                <button
                  type="button"
                  className="primary-button"
                  disabled={actionLoading || ['COMPLETED', 'ABORTED'].includes(selected.status)}
                  onClick={() => void runAction(() => completeRunbook(selected.id), `Runbook #${selected.id} marked completed.`)}
                >
                  Complete runbook
                </button>
              </div>
            </div>
          )}
        </SectionCard>
      </DataStateWrapper>

      {message ? <p className="success-text">{message}</p> : null}
    </div>
  );
}
