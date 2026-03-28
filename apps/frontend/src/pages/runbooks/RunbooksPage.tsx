import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  completeRunbook,
  createRunbook,
  getRunbookAutopilotRuns,
  getRunbookAutopilotSummary,
  getRunbookRecommendations,
  getRunbookSummary,
  getRunbooks,
  getRunbookTemplates,
  resumeRunbookAutopilot,
  retryRunbookAutopilotStep,
  runRunbookAutopilot,
  runRunbookStep,
} from '../../services/runbooks';
import { getAutomationPolicySummary } from '../../services/automationPolicy';
import type { RunbookAutopilotRun, RunbookAutopilotSummary, RunbookInstance, RunbookStepActionKind, RunbookSummary, RunbookTemplate } from '../../types/runbooks';

function statusTone(status: string): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (['COMPLETED', 'DONE', 'AUTO_EXECUTED', 'SAFE_AUTOMATION', 'APPROVED'].includes(status)) return 'ready';
  if (['BLOCKED', 'FAILED', 'ESCALATED', 'AUTO_BLOCKED', 'REJECTED'].includes(status)) return 'offline';
  if (['IN_PROGRESS', 'RUNNING', 'READY', 'OPEN', 'PAUSED_FOR_APPROVAL', 'APPROVAL_REQUIRED', 'MANUAL_ONLY', 'PENDING'].includes(status)) return 'pending';
  return 'neutral';
}

function actionKindTone(action: RunbookStepActionKind): 'ready' | 'pending' | 'offline' | 'neutral' {
  if (action === 'api_action') return 'pending';
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
  const [autopilotRuns, setAutopilotRuns] = useState<RunbookAutopilotRun[]>([]);
  const [autopilotSummary, setAutopilotSummary] = useState<RunbookAutopilotSummary | null>(null);
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
      const [templatesData, runbooksData, summaryData, recommendationsData, automationSummary, autopilotRunsData, autopilotSummaryData] = await Promise.all([
        getRunbookTemplates(),
        getRunbooks(),
        getRunbookSummary(),
        getRunbookRecommendations(),
        getAutomationPolicySummary(),
        getRunbookAutopilotRuns(),
        getRunbookAutopilotSummary(),
      ]);
      setTemplates(templatesData);
      setRunbooks(runbooksData);
      setSummary(summaryData);
      setRecommendations(recommendationsData.results);
      setAutoEligibleActions(automationSummary.auto_eligible_action_types ?? []);
      setAutopilotRuns(autopilotRunsData);
      setAutopilotSummary(autopilotSummaryData);
      if (!selectedId && runbooksData.length > 0) setSelectedId(runbooksData[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load runbooks data.');
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => { void load(); }, [load]);

  const selected = useMemo(() => runbooks.find((item) => item.id === selectedId) ?? null, [runbooks, selectedId]);
  const selectedAutopilot = useMemo(() => (selected ? autopilotRuns.find((run) => run.runbook_instance === selected.id) ?? null : null), [selected, autopilotRuns]);

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
        description="Supervised runbook autopilot keeps manual-first paper/sandbox remediation: safe steps auto-execute, approval/manual/block states pause orchestration, and every step remains auditable."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/cockpit')}>Open Cockpit</button><button type="button" className="secondary-button" onClick={() => navigate('/incidents')}>Open Incidents</button><button type="button" className="secondary-button" onClick={() => navigate('/approvals')}>Open Approvals</button><button type="button" className="secondary-button" onClick={() => navigate('/automation-policy')}>Open Automation Policy</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Summary" title="Runbook + autopilot posture" description="Lifecycle counts and supervised autopilot status.">
          <div className="cockpit-metric-grid">
            <div><strong>Open</strong><div>{summary?.counts.open ?? 0}</div></div>
            <div><strong>In progress</strong><div>{summary?.counts.in_progress ?? 0}</div></div>
            <div><strong>Blocked</strong><div>{summary?.counts.blocked ?? 0}</div></div>
            <div><strong>Autopilot paused</strong><div>{autopilotSummary?.counts.paused_for_approval ?? 0}</div></div>
            <div><strong>Autopilot blocked</strong><div>{autopilotSummary?.counts.blocked ?? 0}</div></div>
            <div><strong>Auto-eligible actions</strong><div>{autoEligibleActions.length}</div></div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Autopilot runs" title="Recent supervised runs" description="Approval/manual/block are expected controlled states.">
          {autopilotRuns.length === 0 ? <EmptyState eyebrow="Autopilot" title="No runbook autopilot runs yet." description="Start one from a runbook detail using Run autopilot." /> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Run</th><th>Runbook</th><th>Status</th><th>Progress</th><th>Summary</th></tr></thead>
                <tbody>
                  {autopilotRuns.slice(0, 10).map((run) => (
                    <tr key={run.id}>
                      <td>#{run.id}</td>
                      <td><button type="button" className="link-button" onClick={() => setSelectedId(run.runbook_instance)}>#{run.runbook_instance}</button></td>
                      <td><StatusBadge tone={statusTone(run.status)}>{run.status}</StatusBadge></td>
                      <td>{run.steps_auto_executed}/{run.steps_evaluated} auto/evaluated</td>
                      <td>{run.summary || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Runbook detail" title={selected ? `Runbook #${selected.id} (${selected.template.slug})` : 'Select a runbook'} description="Step-by-step workflow and autopilot checkpoints.">
          {!selected ? <EmptyState eyebrow="Detail" title="Select a runbook" description="Pick a runbook to run supervised autopilot." /> : (
            <div className="page-stack">
              <p><strong>Status:</strong> <StatusBadge tone={statusTone(selected.status)}>{selected.status}</StatusBadge></p>
              {selectedAutopilot ? <p><strong>Autopilot:</strong> <StatusBadge tone={statusTone(selectedAutopilot.status)}>{selectedAutopilot.status}</StatusBadge> · {selectedAutopilot.summary}</p> : <p className="muted-text">No autopilot run for this runbook yet.</p>}
              <div className="button-row">
                <button type="button" className="primary-button" disabled={actionLoading} onClick={() => void runAction(() => runRunbookAutopilot(selected.id), `Autopilot run started for runbook #${selected.id}.`)}>Run autopilot</button>
                <button type="button" className="secondary-button" disabled={actionLoading || !selectedAutopilot} onClick={() => void runAction(() => resumeRunbookAutopilot(selectedAutopilot!.id), `Autopilot resumed for runbook #${selected.id}.`)}>Resume</button>
                <button type="button" className="ghost-button" disabled={actionLoading || !selectedAutopilot} onClick={() => void runAction(() => completeRunbook(selected.id), `Runbook #${selected.id} marked completed.`)}>Complete runbook</button>
              </div>

              <div className="table-wrapper">
                <table className="data-table">
                  <thead><tr><th>#</th><th>Step</th><th>Kind</th><th>Status</th><th>Actions</th></tr></thead>
                  <tbody>
                    {selected.steps.map((step) => (
                      <tr key={step.id}>
                        <td>{step.step_order}</td>
                        <td>{step.title}</td>
                        <td><StatusBadge tone={actionKindTone(step.action_kind)}>{step.action_kind.toUpperCase()}</StatusBadge></td>
                        <td><StatusBadge tone={statusTone(step.status)}>{step.status}</StatusBadge></td>
                        <td><button type="button" className="secondary-button" disabled={actionLoading || !['READY', 'PENDING'].includes(step.status)} onClick={() => void runAction(() => runRunbookStep(selected.id, step.id), `Step ${step.step_order} executed.`)}>Run step</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <SectionCard eyebrow="Autopilot checkpoints" title="Approval and retry controls" description="Reanuda o reintenta de forma explícita y auditable.">
                {!selectedAutopilot ? <p className="muted-text">No checkpoints yet.</p> : (
                  <>
                    {selectedAutopilot.approval_checkpoints.length === 0 ? <p className="muted-text">No approval checkpoints recorded for this run.</p> : (
                      <ul>
                        {selectedAutopilot.approval_checkpoints.map((checkpoint) => (
                          <li key={checkpoint.id}>
                            <StatusBadge tone={statusTone(checkpoint.status)}>{checkpoint.status}</StatusBadge> Step #{checkpoint.runbook_step} — {checkpoint.approval_reason}
                            {checkpoint.status === 'PENDING' ? <><button type="button" className="link-button" onClick={() => void runAction(() => resumeRunbookAutopilot(selectedAutopilot.id, checkpoint.id, true), `Checkpoint #${checkpoint.id} approved and resumed.`)}>Approve & resume</button><button type="button" className="link-button" onClick={() => navigate('/approvals')}>Open in approvals</button></> : null}
                          </li>
                        ))}
                      </ul>
                    )}

                    {selectedAutopilot.step_results.length === 0 ? <p className="muted-text">No step results yet.</p> : (
                      <ul>
                        {selectedAutopilot.step_results.map((result) => (
                          <li key={result.id}>
                            <StatusBadge tone={statusTone(result.outcome)}>{result.outcome}</StatusBadge> Step {result.runbook_step.step_order} attempt #{result.attempt}
                            {['FAILED', 'BLOCKED'].includes(result.outcome) ? <button type="button" className="link-button" onClick={() => void runAction(() => retryRunbookAutopilotStep(selectedAutopilot.id, result.runbook_step.id), `Retry requested for step ${result.runbook_step.step_order}.`)}>Retry step</button> : null}
                          </li>
                        ))}
                      </ul>
                    )}
                  </>
                )}
              </SectionCard>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Recommendations" title="Suggested runbooks" description="Deterministic matching by incidents, degraded posture, certification, rollout, parity and queue pressure.">
          {recommendations.length === 0 ? <EmptyState eyebrow="Recommendations" title="No recommendations" description="No matching trigger conditions found right now." /> : (
            <div className="page-stack">
              {recommendations.map((item) => (
                <article key={`${item.template_slug}-${item.source_object_type}-${item.source_object_id}`} className="cockpit-attention-item">
                  <div><p className="section-label">{item.priority}</p><h3>{item.template_slug}</h3><p>{item.reason}</p></div>
                  <button className="secondary-button" type="button" disabled={actionLoading} onClick={() => void runAction(() => createRunbook({ template_slug: item.template_slug, source_object_type: item.source_object_type, source_object_id: item.source_object_id, priority: item.priority }), `Runbook ${item.template_slug} created.`)}>Create runbook</button>
                </article>
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Template catalog" title="Available runbook templates" description="Reusable operational templates.">
          {templates.length === 0 ? <EmptyState eyebrow="Templates" title="No templates available" description="Template catalog is empty." /> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Name</th><th>Slug</th><th>Trigger</th><th>Severity</th><th>Action</th></tr></thead><tbody>
              {templates.map((template) => (
                <tr key={template.id}><td>{template.name}</td><td>{template.slug}</td><td>{template.trigger_type}</td><td><StatusBadge tone={statusTone(template.severity_hint)}>{template.severity_hint || 'n/a'}</StatusBadge></td><td><button type="button" className="ghost-button" disabled={actionLoading} onClick={() => void runAction(() => createRunbook({ template_slug: template.slug, source_object_type: template.trigger_type, source_object_id: 'manual' }), `Runbook created from ${template.slug}.`)}>Create runbook</button></td></tr>
              ))}
            </tbody></table></div>
          )}
        </SectionCard>
      </DataStateWrapper>

      {message ? <p className="success-text">{message}</p> : null}
    </div>
  );
}
