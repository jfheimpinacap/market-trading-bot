import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { publishDemoFlowRefresh } from '../../lib/demoFlow';
import { navigate } from '../../lib/router';
import { getSafetyStatus } from '../../services/safety';
import type { SafetyStatus } from '../../types/safety';
import {
  approvePendingApproval,
  getPendingApprovals,
  getSemiAutoRuns,
  getSemiAutoSummary,
  rejectPendingApproval,
  runSemiAutoEvaluate,
  runSemiAutoExecution,
} from '../../services/semiAuto';
import type { PendingApproval, SemiAutoRun } from '../../types/semiAuto';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function formatDate(value: string | null) {
  if (!value) {
    return 'Pending';
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function badgeFromClassification(value: string) {
  if (value.includes('EXECUTED')) return 'ready';
  if (value.includes('APPROVAL')) return 'pending';
  if (value.includes('BLOCK')) return 'offline';
  if (value.includes('REJECT')) return 'offline';
  return 'neutral';
}

export function SemiAutoPage() {
  const [runs, setRuns] = useState<SemiAutoRun[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getSemiAutoSummary>> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [safety, setSafety] = useState<SafetyStatus | null>(null);

  const loadState = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [runsResponse, pendingResponse, summaryResponse, safetyResponse] = await Promise.all([getSemiAutoRuns(), getPendingApprovals(), getSemiAutoSummary(), getSafetyStatus()]);
      setRuns(runsResponse);
      setPendingApprovals(pendingResponse.filter((item) => item.status === 'PENDING'));
      setSummary(summaryResponse);
      setSafety(safetyResponse);
    } catch (loadError) {
      setError(getErrorMessage(loadError, 'Could not load semi-auto demo state.'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadState();
  }, [loadState]);

  const runAction = useCallback(async (handler: () => Promise<SemiAutoRun>) => {
    setIsActionLoading(true);
    setActionMessage(null);
    try {
      const run = await handler();
      setActionMessage(run.summary);
      publishDemoFlowRefresh('semi-auto-cycle');
      await loadState();
    } catch (runError) {
      setError(getErrorMessage(runError, 'Semi-auto action failed.'));
    } finally {
      setIsActionLoading(false);
    }
  }, [loadState]);

  const handleApprovalDecision = useCallback(async (id: number, decision: 'approve' | 'reject') => {
    setIsActionLoading(true);
    try {
      if (decision === 'approve') {
        await approvePendingApproval(id);
      } else {
        await rejectPendingApproval(id);
      }
      await loadState();
    } catch (decisionError) {
      setError(getErrorMessage(decisionError, `Could not ${decision} pending approval.`));
    } finally {
      setIsActionLoading(false);
    }
  }, [loadState]);

  const latestRun = useMemo(() => runs[0] ?? summary?.latest_run ?? null, [runs, summary]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Semi-autonomous demo"
        title="Semi-Auto"
        description="Controlled semi-autonomous mode for proposal evaluation and conservative paper auto-execution. Paper/demo only. No real execution."
        actions={
          <button type="button" className="secondary-button" onClick={() => navigate('/automation')}>
            Open automation
          </button>
        }
      />

      <SectionCard eyebrow="Control panel" title="Run semi-auto cycle" description="Use evaluate-only to classify proposals, or run semi-auto to execute only strict AUTO_APPROVE paper candidates.">
        <div className="button-row">
          <button type="button" className="secondary-button" disabled={isActionLoading} onClick={() => runAction(runSemiAutoEvaluate)}>
            Evaluate only
          </button>
          <button type="button" className="primary-button" disabled={isActionLoading || Boolean(safety?.kill_switch_enabled || safety?.hard_stop_active || safety?.cooldown_until_cycle)} onClick={() => runAction(runSemiAutoExecution)}>
            Run semi-auto cycle
          </button>
        </div>
        {actionMessage ? <p>{actionMessage}</p> : null}
        <p>This semi-auto mode never places real trades.</p>
        {safety?.status ? <p><strong>Safety status:</strong> {safety.status} {safety.status_message ? `· ${safety.status_message}` : ''}</p> : null}
      </SectionCard>

      <DataStateWrapper isLoading={isLoading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Safety" title="Safety overview" description="Conservative guardrails always apply before auto-execution.">
            <ul>
              <li>Max auto quantity: 3.0000</li>
              <li>Max auto trades per run: 2</li>
              <li>APPROVAL_REQUIRED → pending approval</li>
              <li>HARD_BLOCK → never executed</li>
              <li>BUY-only for auto execution</li>
              <li>Kill switch active: {safety?.kill_switch_enabled ? 'yes' : 'no'}</li>
              <li>Cooldown active: {safety?.cooldown_until_cycle ? `until cycle ${safety.cooldown_until_cycle}` : 'no'}</li>
            </ul>
          </SectionCard>

          <SectionCard eyebrow="Latest run" title="Last run summary" description={latestRun ? latestRun.summary : 'Run an evaluation cycle to detect candidate proposals.'}>
            {latestRun ? (
              <div className="system-metadata-grid">
                <div><strong>Markets evaluated:</strong> {latestRun.markets_evaluated}</div>
                <div><strong>Proposals generated:</strong> {latestRun.proposals_generated}</div>
                <div><strong>Auto executed:</strong> {latestRun.auto_executed_count}</div>
                <div><strong>Approval required:</strong> {latestRun.approval_required_count}</div>
                <div><strong>Blocked:</strong> {latestRun.blocked_count}</div>
              </div>
            ) : (
              <EmptyState title="No runs yet" description="Run an evaluation cycle to detect candidate proposals." eyebrow="Runs" />
            )}
          </SectionCard>
        </div>

        <SectionCard eyebrow="Manual queue" title="Pending approvals" description="APPROVAL_REQUIRED proposals are queued here for explicit operator decisions.">
          {pendingApprovals.length === 0 ? (
            <EmptyState title="No pending approvals right now." description="New pending items appear after a semi-auto or evaluate cycle classifies manual approvals." eyebrow="Queue" />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Market</th>
                    <th>Headline</th>
                    <th>Direction</th>
                    <th>Qty</th>
                    <th>Rationale</th>
                    <th>Policy</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingApprovals.map((item) => (
                    <tr key={item.id}>
                      <td>{item.market_title}</td>
                      <td>{item.proposal_headline}</td>
                      <td>{item.suggested_side}</td>
                      <td>{item.suggested_quantity}</td>
                      <td>{item.rationale || item.summary}</td>
                      <td><StatusBadge tone="pending">{item.policy_decision}</StatusBadge></td>
                      <td>
                        <div className="button-row">
                          <button type="button" className="secondary-button" disabled={isActionLoading} onClick={() => handleApprovalDecision(item.id, 'approve')}>Approve and execute</button>
                          <button type="button" className="ghost-button" disabled={isActionLoading} onClick={() => handleApprovalDecision(item.id, 'reject')}>Reject</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="History" title="Recent runs" description="Audit trail for evaluate and semi-auto execution cycles.">
          {runs.length === 0 ? (
            <EmptyState title="No semi-auto runs yet" description="Trigger evaluate-only or semi-auto run to generate an audit trail." eyebrow="History" />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Summary</th>
                    <th>Started</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.slice(0, 10).map((run) => (
                    <tr key={run.id}>
                      <td>{run.id}</td>
                      <td>{run.run_type}</td>
                      <td><StatusBadge tone={badgeFromClassification(run.status)}>{run.status}</StatusBadge></td>
                      <td>{run.summary}</td>
                      <td>{formatDate(run.started_at)}</td>
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
