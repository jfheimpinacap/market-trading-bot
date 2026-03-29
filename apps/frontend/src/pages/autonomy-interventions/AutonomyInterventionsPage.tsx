<<<<<<< HEAD
import { useCallback, useEffect, useState } from 'react';
=======
import { useCallback, useEffect, useMemo, useState } from 'react';
>>>>>>> origin/main

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
<<<<<<< HEAD
  cancelAutonomyInterventionRequest,
=======
>>>>>>> origin/main
  createAutonomyInterventionRequest,
  executeAutonomyInterventionRequest,
  getAutonomyInterventionActions,
  getAutonomyInterventionRequests,
  getAutonomyInterventionSummary,
  runAutonomyInterventionReview,
} from '../../services/autonomyInterventions';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const v = value.toUpperCase();
<<<<<<< HEAD
  if (['READY', 'EXECUTED', 'CAMPAIGN_RESUMED', 'CONTINUE_CONFIRMED'].includes(v)) return 'ready';
=======
  if (['EXECUTED', 'READY', 'CLEAR_TO_CONTINUE', 'CONTINUE_CLEARANCE'].includes(v)) return 'ready';
>>>>>>> origin/main
  if (['OPEN', 'APPROVAL_REQUIRED', 'PENDING', 'EXECUTING'].includes(v)) return 'pending';
  if (['BLOCKED', 'FAILED', 'REJECTED', 'PAUSE_CAMPAIGN', 'REVIEW_FOR_ABORT'].includes(v)) return 'offline';
  return 'neutral';
};

<<<<<<< HEAD
const manualDefaultAction = 'PAUSE_CAMPAIGN';

=======
>>>>>>> origin/main
export function AutonomyInterventionsPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
<<<<<<< HEAD
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyInterventionSummary>> | null>(null);
  const [requests, setRequests] = useState<Awaited<ReturnType<typeof getAutonomyInterventionRequests>>>([]);
  const [actions, setActions] = useState<Awaited<ReturnType<typeof getAutonomyInterventionActions>>>([]);
=======
  const [requests, setRequests] = useState<Awaited<ReturnType<typeof getAutonomyInterventionRequests>>>([]);
  const [actions, setActions] = useState<Awaited<ReturnType<typeof getAutonomyInterventionActions>>>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyInterventionSummary>> | null>(null);
>>>>>>> origin/main

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
<<<<<<< HEAD
      const [summaryData, requestsData, actionsData] = await Promise.all([
        getAutonomyInterventionSummary(),
        getAutonomyInterventionRequests(),
        getAutonomyInterventionActions(),
      ]);
      setSummary(summaryData);
      setRequests(requestsData.slice(0, 80));
      setActions(actionsData.slice(0, 80));
=======
      const [reqData, actionData, summaryData] = await Promise.all([
        getAutonomyInterventionRequests(),
        getAutonomyInterventionActions(),
        getAutonomyInterventionSummary(),
      ]);
      setRequests(reqData.slice(0, 80));
      setActions(actionData.slice(0, 80));
      setSummary(summaryData);
>>>>>>> origin/main
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy interventions.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runReview = useCallback(async () => {
    setBusy(true);
<<<<<<< HEAD
    setError(null);
    setMessage(null);
    try {
      const result = await runAutonomyInterventionReview({ actor: 'operator-ui' });
      setMessage(`Intervention run #${result.run_id} created ${result.created_request_count} request(s).`);
=======
    setMessage(null);
    setError(null);
    try {
      const result = await runAutonomyInterventionReview({ actor: 'operator-ui' });
      setMessage(`Intervention review run #${result.run} created ${result.created_requests} requests.`);
>>>>>>> origin/main
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run intervention review.');
    } finally {
      setBusy(false);
    }
  }, [load]);

<<<<<<< HEAD
  const createManual = useCallback(async () => {
    const campaignRaw = window.prompt('Campaign ID to intervene');
    if (!campaignRaw) return;
    const campaignId = Number(campaignRaw);
    if (!Number.isFinite(campaignId) || campaignId <= 0) {
      setError('Campaign ID must be a positive number.');
      return;
    }
    const requestedAction = window.prompt('Requested action (PAUSE_CAMPAIGN|RESUME_CAMPAIGN|ESCALATE_TO_APPROVAL|REVIEW_FOR_ABORT|CLEAR_TO_CONTINUE)', manualDefaultAction) ?? manualDefaultAction;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const created = await createAutonomyInterventionRequest(campaignId, {
        source_type: 'manual',
        requested_action: requestedAction,
        rationale: `Manual request from /autonomy-interventions`,
        requested_by: 'operator-ui',
      });
      setMessage(`Created intervention request #${created.id}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create manual intervention request.');
    } finally {
      setBusy(false);
    }
  }, [load]);

  const execute = useCallback(async (requestId: number) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await executeAutonomyInterventionRequest(requestId, { actor: 'operator-ui' });
      setMessage(`Action #${result.id} executed with status ${result.action_status}.`);
=======
  const execute = useCallback(async (requestId: number) => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await executeAutonomyInterventionRequest(requestId, { actor: 'operator-ui' });
      setMessage(`Intervention request #${requestId} executed.`);
>>>>>>> origin/main
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not execute intervention request.');
    } finally {
      setBusy(false);
    }
  }, [load]);

<<<<<<< HEAD
  const cancel = useCallback(async (requestId: number) => {
=======
  const createManual = useCallback(async () => {
    const campaignId = requests.find((r) => r.request_status === 'OPEN')?.campaign ?? actions[0]?.campaign;
    if (!campaignId) {
      setError('No campaign available. Run review first or create active campaigns.');
      return;
    }
>>>>>>> origin/main
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
<<<<<<< HEAD
      await cancelAutonomyInterventionRequest(requestId);
      setMessage(`Request #${requestId} cancelled.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not cancel intervention request.');
    } finally {
      setBusy(false);
    }
  }, [load]);
=======
      await createAutonomyInterventionRequest(campaignId, {
        source_type: 'manual',
        requested_action: 'CLEAR_TO_CONTINUE',
        rationale: 'Manual acknowledgement from intervention board.',
        requested_by: 'operator-ui',
      });
      setMessage(`Manual request created for campaign #${campaignId}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create manual intervention request.');
    } finally {
      setBusy(false);
    }
  }, [requests, actions, load]);

  const openRequests = useMemo(() => requests.filter((item) => ['OPEN', 'APPROVAL_REQUIRED', 'READY', 'BLOCKED'].includes(item.request_status)), [requests]);
>>>>>>> origin/main

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy intervention control"
        title="/autonomy-interventions"
<<<<<<< HEAD
        description="Active campaign action board and manual remediation gateway. Manual-first only: no opaque auto-remediation, no real broker/exchange execution."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run intervention review</button><button className="secondary-button" type="button" disabled={busy} onClick={() => void createManual()}>Create manual request</button><button className="ghost-button" type="button" onClick={() => navigate('/autonomy-operations')}>Autonomy operations</button><button className="ghost-button" type="button" onClick={() => navigate('/autonomy-recovery')}>Autonomy recovery</button><button className="ghost-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button></div>}
      />

      {message ? <p className="success-text">{message}</p> : null}
      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Intervention summary" title="Manual action readiness" description="READY and EXECUTED are valid states. Actions stay explicit and auditable.">
=======
        description="Active campaign action board and manual remediation gateway. Manual-first interventions only: no opaque auto-remediation and no real broker/exchange execution."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runReview()}>Run intervention review</button><button className="secondary-button" type="button" disabled={busy} onClick={() => void createManual()}>Create manual request</button><button className="ghost-button" type="button" onClick={() => navigate('/autonomy-operations')}>Autonomy operations</button><button className="ghost-button" type="button" onClick={() => navigate('/autonomy-recovery')}>Autonomy recovery</button><button className="ghost-button" type="button" onClick={() => navigate('/cockpit')}>Cockpit</button></div>}
      />
      {message ? <p className="success-text">{message}</p> : null}
      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Intervention summary" title="Manual-first intervention posture" description="READY and EXECUTED are valid states. Blocked interventions remain visible with reason codes and blockers.">
>>>>>>> origin/main
          <div className="cockpit-metric-grid">
            <div><strong>Open requests</strong><div>{summary?.open_request_count ?? 0}</div></div>
            <div><strong>Approval required</strong><div>{summary?.approval_required_count ?? 0}</div></div>
            <div><strong>Ready to execute</strong><div>{summary?.ready_request_count ?? 0}</div></div>
            <div><strong>Blocked requests</strong><div>{summary?.blocked_request_count ?? 0}</div></div>
            <div><strong>Recent actions</strong><div>{summary?.executed_recent_count ?? 0}</div></div>
            <div><strong>Campaigns needing intervention</strong><div>{summary?.campaigns_needing_intervention ?? 0}</div></div>
          </div>
        </SectionCard>

<<<<<<< HEAD
        {requests.length === 0 ? <EmptyState eyebrow="Intervention requests" title="No active autonomy campaigns currently need manual intervention requests." description="Run intervention review to bridge operations recommendations into explicit requests, or create manual requests for targeted campaigns." /> : null}

        <SectionCard eyebrow="Requests panel" title="Active intervention requests" description="Campaign, action, source, severity, status, blockers, and traceable links.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Campaign</th><th>Requested action</th><th>Source</th><th>Severity</th><th>Status</th><th>Blockers</th><th>Rationale</th><th>Links</th><th>Actions</th></tr></thead>
=======
        {openRequests.length === 0 ? <EmptyState eyebrow="Interventions" title="No active autonomy campaigns currently need manual intervention requests." description="Run intervention review to ingest operations recommendations and create auditable intervention requests." /> : null}

        <SectionCard eyebrow="Requests" title="Campaign intervention requests" description="Links campaign, trace, and approvals with explicit action, source, severity, blockers, and rationale.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead><tr><th>Campaign</th><th>Action</th><th>Source</th><th>Severity</th><th>Status</th><th>Blockers</th><th>Rationale</th><th>Actions</th></tr></thead>
>>>>>>> origin/main
              <tbody>
                {requests.map((item) => (
                  <tr key={item.id}>
                    <td>{item.campaign_title ?? `#${item.campaign}`}</td>
                    <td><StatusBadge tone={tone(item.requested_action)}>{item.requested_action}</StatusBadge></td>
                    <td>{item.source_type}</td>
                    <td><StatusBadge tone={tone(item.severity)}>{item.severity}</StatusBadge></td>
                    <td><StatusBadge tone={tone(item.request_status)}>{item.request_status}</StatusBadge></td>
                    <td>{item.blockers.join(', ') || 'none'}</td>
                    <td>{item.rationale}<div className="muted-text">reason_codes: {item.reason_codes.join(', ') || 'none'}</div></td>
<<<<<<< HEAD
                    <td><button type="button" className="link-button" onClick={() => navigate('/autonomy-campaigns')}>Campaign</button><button type="button" className="link-button" onClick={() => navigate('/approvals')}>Approvals</button><button type="button" className="link-button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Trace</button></td>
                    <td><div className="button-row"><button type="button" className="secondary-button" disabled={busy || !['OPEN', 'READY', 'APPROVAL_REQUIRED', 'BLOCKED'].includes(item.request_status)} onClick={() => void execute(item.id)}>Execute</button><button type="button" className="ghost-button" disabled={busy || !['OPEN', 'READY', 'APPROVAL_REQUIRED', 'BLOCKED'].includes(item.request_status)} onClick={() => void cancel(item.id)}>Cancel</button></div></td>
=======
                    <td><div className="button-row"><button className="secondary-button" type="button" disabled={busy || !['OPEN', 'READY', 'APPROVAL_REQUIRED'].includes(item.request_status)} onClick={() => void execute(item.id)}>Execute</button><button className="link-button" type="button" onClick={() => navigate('/autonomy-campaigns')}>Campaign</button><button className="link-button" type="button" onClick={() => navigate('/approvals')}>Approvals</button><button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(item.campaign))}`)}>Trace</button></div></td>
>>>>>>> origin/main
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

<<<<<<< HEAD
        <SectionCard eyebrow="Actions history" title="Intervention action outcomes" description="Who executed what, when, and with what result.">
          {!actions.length ? <p className="muted-text">No intervention actions yet.</p> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Campaign</th><th>Action type</th><th>Status</th><th>Executed by</th><th>Executed at</th><th>Result summary</th><th>Failure message</th></tr></thead><tbody>
              {actions.map((item) => (
                <tr key={item.id}>
                  <td>{item.campaign_title ?? `#${item.campaign}`}</td>
                  <td><StatusBadge tone={tone(item.action_type)}>{item.action_type}</StatusBadge></td>
                  <td><StatusBadge tone={tone(item.action_status)}>{item.action_status}</StatusBadge></td>
                  <td>{item.executed_by || 'n/a'}</td>
                  <td>{item.executed_at ? new Date(item.executed_at).toLocaleString() : 'n/a'}</td>
                  <td>{item.result_summary || 'n/a'}</td>
                  <td>{item.failure_message || 'n/a'}</td>
                </tr>
              ))}
            </tbody></table></div>
=======
        <SectionCard eyebrow="Action history" title="Executed, blocked and failed actions" description="Auditable execution outcomes with actor and failure detail.">
          {!actions.length ? <p className="muted-text">No intervention actions yet.</p> : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Campaign</th><th>Action type</th><th>Status</th><th>Executed by</th><th>Executed at</th><th>Result</th><th>Failure</th></tr></thead>
                <tbody>
                  {actions.map((item) => (
                    <tr key={item.id}>
                      <td>{item.campaign_title ?? `#${item.campaign}`}</td>
                      <td><StatusBadge tone={tone(item.action_type)}>{item.action_type}</StatusBadge></td>
                      <td><StatusBadge tone={tone(item.action_status)}>{item.action_status}</StatusBadge></td>
                      <td>{item.executed_by || 'n/a'}</td>
                      <td>{item.executed_at ? new Date(item.executed_at).toLocaleString() : 'n/a'}</td>
                      <td>{item.result_summary || 'n/a'}</td>
                      <td>{item.failure_message || 'n/a'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
>>>>>>> origin/main
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
