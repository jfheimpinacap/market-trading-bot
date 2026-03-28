import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import { createAutonomyCampaign, getAutonomyCampaigns, getAutonomyCampaignSummary, startAutonomyCampaign, resumeAutonomyCampaign, abortAutonomyCampaign } from '../../services/autonomyCampaign';
import { getAutonomyRoadmapPlans } from '../../services/autonomyRoadmap';
import { getAutonomyScenarioRuns } from '../../services/autonomyScenario';
import type { AutonomyCampaign } from '../../types/autonomyCampaign';

const toneForCampaign = (status: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (['COMPLETED', 'READY'].includes(status)) return 'ready';
  if (['RUNNING', 'PAUSED', 'BLOCKED', 'WAITING_APPROVAL', 'OBSERVING'].includes(status)) return 'pending';
  if (['FAILED', 'ABORTED'].includes(status)) return 'offline';
  return 'neutral';
};

export function AutonomyCampaignsPage() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [campaigns, setCampaigns] = useState<AutonomyCampaign[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutonomyCampaignSummary>> | null>(null);
  const [latestRoadmapId, setLatestRoadmapId] = useState<number | null>(null);
  const [latestScenarioId, setLatestScenarioId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [campaignsPayload, summaryPayload, roadmapPlans, scenarioRuns] = await Promise.all([
        getAutonomyCampaigns(),
        getAutonomyCampaignSummary(),
        getAutonomyRoadmapPlans(),
        getAutonomyScenarioRuns(),
      ]);
      setCampaigns(campaignsPayload);
      setSummary(summaryPayload);
      setSelected((prev) => prev ?? campaignsPayload[0]?.id ?? null);
      setLatestRoadmapId(roadmapPlans[0]?.id ?? null);
      setLatestScenarioId(scenarioRuns[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomy campaigns.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const selectedCampaign = useMemo(() => campaigns.find((item) => item.id === selected) ?? null, [campaigns, selected]);

  const runAction = useCallback(async (action: 'start' | 'resume' | 'abort', campaignId: number) => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      if (action === 'start') await startAutonomyCampaign(campaignId);
      if (action === 'resume') await resumeAutonomyCampaign(campaignId);
      if (action === 'abort') await abortAutonomyCampaign(campaignId, { reason: 'manual_abort_from_ui' });
      setMessage(`Campaign ${action} action executed.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not ${action} campaign.`);
    } finally {
      setBusy(false);
    }
  }, [load]);

  const createFromRoadmap = useCallback(async () => {
    if (!latestRoadmapId) return;
    setBusy(true);
    setError(null);
    try {
      const result = await createAutonomyCampaign({ source_type: 'roadmap_plan', source_object_id: String(latestRoadmapId), title: `Roadmap campaign #${latestRoadmapId}` });
      setSelected(result.id);
      setMessage(`Campaign #${result.id} created from roadmap plan #${latestRoadmapId}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create campaign from roadmap.');
    } finally {
      setBusy(false);
    }
  }, [latestRoadmapId, load]);

  const createFromScenario = useCallback(async () => {
    if (!latestScenarioId) return;
    setBusy(true);
    setError(null);
    try {
      const result = await createAutonomyCampaign({ source_type: 'scenario_run', source_object_id: String(latestScenarioId), title: `Scenario campaign #${latestScenarioId}` });
      setSelected(result.id);
      setMessage(`Campaign #${result.id} created from scenario run #${latestScenarioId}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create campaign from scenario.');
    } finally {
      setBusy(false);
    }
  }, [latestScenarioId, load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Autonomy campaign board"
        title="/autonomy-campaigns"
        description="Scenario/roadmap handoff into explicit staged execution programs. Manual-first, approval-gated, and sandbox-only."
        actions={<div className="button-row"><button className="primary-button" type="button" disabled={busy || !latestRoadmapId} onClick={() => void createFromRoadmap()}>Create from roadmap</button><button className="secondary-button" type="button" disabled={busy || !latestScenarioId} onClick={() => void createFromScenario()}>Create from scenario</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-program')}>Program tower</button><button className="secondary-button" type="button" onClick={() => navigate('/approvals')}>Approvals</button><button className="ghost-button" type="button" onClick={() => navigate('/trace')}>Trace</button></div>}
      />
      {message ? <p className="success-text">{message}</p> : null}

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Campaign posture" title="Staged domain transition programs" description="Waiting approval and blocked states are healthy checkpoints, not failures.">
          <div className="cockpit-metric-grid">
            <div><strong>Total campaigns</strong><div>{summary?.total_campaigns ?? 0}</div></div>
            <div><strong>Active campaigns</strong><div>{summary?.active_campaigns ?? 0}</div></div>
            <div><strong>Latest source</strong><div>{summary?.latest_source_type ?? 'n/a'}</div></div>
            <div><strong>Latest status</strong><div>{summary?.latest_status ?? 'n/a'}</div></div>
          </div>
        </SectionCard>

        {campaigns.length === 0 ? <EmptyState eyebrow="Autonomy campaign board" title="No campaigns yet" description="Create an autonomy campaign from a roadmap plan or scenario recommendation." /> : null}

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Campaigns" title="Recent campaigns" description="Select a campaign to inspect wave, steps, checkpoints and controls.">
            <div className="page-stack">
              {campaigns.slice(0, 20).map((campaign) => (
                <article key={campaign.id} className="status-card">
                  <p className="status-card__label">Campaign #{campaign.id}</p>
                  <h3>{campaign.title}</h3>
                  <p><StatusBadge tone={toneForCampaign(campaign.status)}>{campaign.status}</StatusBadge> <span className="muted-text">{campaign.source_type} · wave {campaign.current_wave}</span></p>
                  <p>{campaign.summary}</p>
                  <p className="muted-text">Progress: {campaign.completed_steps}/{campaign.total_steps} · blocked/waiting {campaign.blocked_steps}</p>
                  <div className="button-row"><button className="link-button" type="button" onClick={() => setSelected(campaign.id)}>Details</button></div>
                </article>
              ))}
            </div>
          </SectionCard>

          <SectionCard eyebrow="Campaign detail" title={selectedCampaign ? `Campaign #${selectedCampaign.id}` : 'Select a campaign'} description="Ordered wave/step execution with checkpoints and links to approvals/trace/rollout.">
            {!selectedCampaign ? <p className="muted-text">Select a campaign from the list.</p> : (
              <>
                <div className="button-row"><button className="primary-button" type="button" disabled={busy} onClick={() => void runAction('start', selectedCampaign.id)}>Start</button><button className="secondary-button" type="button" disabled={busy} onClick={() => void runAction('resume', selectedCampaign.id)}>Resume</button><button className="ghost-button" type="button" disabled={busy} onClick={() => void runAction('abort', selectedCampaign.id)}>Abort</button></div>
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead><tr><th>Order</th><th>Wave</th><th>Domain</th><th>Action</th><th>Status</th><th>Rationale</th></tr></thead>
                    <tbody>
                      {selectedCampaign.steps.map((step) => (
                        <tr key={step.id}>
                          <td>{step.step_order}</td>
                          <td>{step.wave}</td>
                          <td>{step.domain_slug ?? 'n/a'}</td>
                          <td>{step.action_type}</td>
                          <td><StatusBadge tone={toneForCampaign(step.status)}>{step.status}</StatusBadge></td>
                          <td>{step.rationale}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <h4>Checkpoints</h4>
                {!selectedCampaign.checkpoints.length ? <p className="muted-text">No checkpoints yet.</p> : (
                  <div className="table-wrapper">
                    <table className="data-table">
                      <thead><tr><th>Type</th><th>Status</th><th>Summary</th><th>Links</th></tr></thead>
                      <tbody>
                        {selectedCampaign.checkpoints.map((checkpoint) => (
                          <tr key={checkpoint.id}>
                            <td>{checkpoint.checkpoint_type}</td>
                            <td><StatusBadge tone={toneForCampaign(checkpoint.status)}>{checkpoint.status}</StatusBadge></td>
                            <td>{checkpoint.summary}</td>
                            <td><button className="link-button" type="button" onClick={() => navigate('/approvals')}>Approvals</button> <button className="link-button" type="button" onClick={() => navigate(`/trace?root_type=autonomy_campaign&root_id=${encodeURIComponent(String(selectedCampaign.id))}`)}>Trace</button></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
