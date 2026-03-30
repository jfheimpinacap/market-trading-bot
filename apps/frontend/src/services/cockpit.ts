import { getAlerts, getAlertsSummary } from './alerts';
import { getBrokerBridgeSummary } from './brokerBridge';
import { getCertificationSummary, runCertificationReview } from './certification';
import { getChampionChallengerSummary } from './championChallenger';
import { runIncidentDetection, getIncidentCurrentState } from './incidents';
import { getMissionControlStatus, pauseMissionControl, resumeMissionControl, startMissionControl } from './missionControl';
import { getOpportunityItems, getOpportunitySummary } from './opportunities';
import { getOperatorQueueItems, getOperatorQueueSummary } from './operatorQueue';
import { getPortfolioGovernanceSummary, getPortfolioThrottle, runPortfolioGovernance } from './portfolioGovernor';
import { getPositionDecisions, getPositionSummary } from './positions';
import { getProfileGovernanceSummary, runProfileGovernance } from './profileManager';
import { getPromotionSummary } from './promotion';
import { rollbackRollout, pauseRollout, getRolloutSummary } from './rollout';
import { getRuntimeStatus } from './runtime';
import { getApprovalSummary, getPendingApprovals } from './approvals';
import { getRunbookAutopilotSummary, getRunbookSummary } from './runbooks';
import { getTraceQueryRuns, getTraceSummary } from './trace';
import { getVenueSummary } from './executionVenue';
import { getVenueAccountSummary } from './venueAccount';
import { getPolicyTuningSummary } from './policyTuning';
import { getPolicyRolloutSummary } from './policyRollout';
import { getAutonomySummary } from './autonomy';
import { getAutonomyRolloutSummary } from './autonomyRollout';
import { getAutonomyRoadmapSummary } from './autonomyRoadmap';
import { getAutonomyCampaignSummary } from './autonomyCampaign';
import { getAutonomyBacklogSummary } from './autonomyBacklog';
import type { CockpitAttentionItem, CockpitPanelFailures, CockpitQuickActionId, CockpitSnapshot } from '../types/cockpit';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

async function withFallback<T>(
  key: keyof CockpitPanelFailures,
  request: () => Promise<T>,
  failures: CockpitPanelFailures,
  fallback: T,
  failureMessage: string,
) {
  try {
    return await request();
  } catch (error) {
    failures[key] = getErrorMessage(error, failureMessage);
    return fallback;
  }
}

export async function getCockpitSummary(): Promise<CockpitSnapshot> {
  const failures: CockpitPanelFailures = {};

  const [
    runtime,
    incidents,
    missionControl,
    rollout,
    certification,
    profile,
    portfolioGovernor,
    portfolioThrottle,
    brokerBridge,
    executionVenue,
    venueAccount,
    operatorQueueSummary,
    operatorQueueItems,
    alertsSummary,
    alerts,
    opportunitiesSummary,
    opportunityItems,
    positionsSummary,
    positionDecisions,
    traceSummary,
    traceRuns,
    promotionSummary,
    championChallengerSummary,
    runbookSummary,
    runbookAutopilotSummary,
    approvalSummary,
    pendingApprovals,
    policyTuningSummary,
    policyRolloutSummary,
    autonomySummary,
    autonomyRolloutSummary,
    autonomyRoadmapSummary,
    autonomyCampaignSummary,
    autonomyBacklogSummary,
  ] = await Promise.all([
    withFallback('runtime', () => getRuntimeStatus(), failures, null, 'Runtime status unavailable.'),
    withFallback('incidents', () => getIncidentCurrentState(), failures, null, 'Incident posture unavailable.'),
    withFallback('missionControl', () => getMissionControlStatus(), failures, null, 'Mission control status unavailable.'),
    withFallback('rollout', () => getRolloutSummary(), failures, null, 'Rollout summary unavailable.'),
    withFallback('certification', () => getCertificationSummary(), failures, null, 'Certification summary unavailable.'),
    withFallback('profile', () => getProfileGovernanceSummary(), failures, null, 'Profile manager summary unavailable.'),
    withFallback('portfolioGovernor', () => getPortfolioGovernanceSummary(), failures, null, 'Portfolio governor summary unavailable.'),
    withFallback('portfolioThrottle', () => getPortfolioThrottle(), failures, null, 'Portfolio throttle unavailable.'),
    withFallback('brokerBridge', () => getBrokerBridgeSummary(), failures, null, 'Broker bridge summary unavailable.'),
    withFallback('executionVenue', () => getVenueSummary(), failures, null, 'Execution venue summary unavailable.'),
    withFallback('venueAccount', () => getVenueAccountSummary(), failures, null, 'Venue account summary unavailable.'),
    withFallback('operatorQueueSummary', () => getOperatorQueueSummary(), failures, null, 'Operator queue summary unavailable.'),
    withFallback('operatorQueueItems', () => getOperatorQueueItems({ status: 'PENDING' }), failures, [], 'Operator queue items unavailable.'),
    withFallback('alertsSummary', () => getAlertsSummary(), failures, null, 'Alerts summary unavailable.'),
    withFallback('alerts', () => getAlerts({ status: 'OPEN' }), failures, [], 'Alerts unavailable.'),
    withFallback('opportunitiesSummary', () => getOpportunitySummary(), failures, null, 'Opportunities summary unavailable.'),
    withFallback('opportunityItems', () => getOpportunityItems(), failures, [], 'Opportunity items unavailable.'),
    withFallback('positionsSummary', () => getPositionSummary(), failures, null, 'Position summary unavailable.'),
    withFallback('positionDecisions', () => getPositionDecisions(), failures, [], 'Position decisions unavailable.'),
    withFallback('traceSummary', () => getTraceSummary(), failures, null, 'Trace summary unavailable.'),
    withFallback('traceRuns', () => getTraceQueryRuns(), failures, [], 'Trace runs unavailable.'),
    withFallback('promotionSummary', () => getPromotionSummary(), failures, null, 'Promotion summary unavailable.'),
    withFallback('championChallengerSummary', () => getChampionChallengerSummary(), failures, null, 'Champion/challenger summary unavailable.'),
    withFallback('runbookSummary', () => getRunbookSummary(), failures, null, 'Runbook summary unavailable.'),
    withFallback('runbookAutopilotSummary', () => getRunbookAutopilotSummary(), failures, null, 'Runbook autopilot summary unavailable.'),
    withFallback('approvalSummary', () => getApprovalSummary(), failures, null, 'Approval summary unavailable.'),
    withFallback('pendingApprovals', () => getPendingApprovals(), failures, [], 'Pending approvals unavailable.'),
    withFallback('policyTuningSummary', () => getPolicyTuningSummary(), failures, null, 'Policy tuning summary unavailable.'),
    withFallback('policyRolloutSummary', () => getPolicyRolloutSummary(), failures, null, 'Policy rollout summary unavailable.'),
    withFallback('autonomySummary', () => getAutonomySummary(), failures, null, 'Autonomy summary unavailable.'),
    withFallback('autonomyRolloutSummary', () => getAutonomyRolloutSummary(), failures, null, 'Autonomy rollout summary unavailable.'),
    withFallback('autonomyRoadmapSummary', () => getAutonomyRoadmapSummary(), failures, null, 'Autonomy roadmap summary unavailable.'),
    withFallback('autonomyCampaignSummary', () => getAutonomyCampaignSummary(), failures, null, 'Autonomy campaign summary unavailable.'),
    withFallback('autonomyBacklogSummary', () => getAutonomyBacklogSummary(), failures, null, 'Autonomy backlog summary unavailable.'),
  ]);

  return {
    runtime,
    incidents,
    missionControl,
    rollout,
    certification,
    profile,
    portfolioGovernor,
    portfolioThrottle,
    brokerBridge,
    executionVenue,
    venueAccount,
    operatorQueueSummary,
    operatorQueueItems,
    alertsSummary,
    alerts,
    opportunitiesSummary,
    opportunityItems,
    positionsSummary,
    positionDecisions,
    traceSummary,
    traceRuns,
    promotionSummary,
    championChallengerSummary,
    runbookSummary,
    runbookAutopilotSummary,
    approvalSummary,
    pendingApprovals,
    policyTuningSummary,
    policyRolloutSummary,
    autonomySummary,
    autonomyRolloutSummary,
    autonomyRoadmapSummary,
    autonomyCampaignSummary,
    autonomyBacklogSummary,
    failures,
    lastUpdatedAt: new Date().toISOString(),
  };
}

export function getCockpitAttention(snapshot: CockpitSnapshot): CockpitAttentionItem[] {
  const items: CockpitAttentionItem[] = [];

  if (snapshot.incidents?.summary.critical_active) {
    items.push({
      id: 'critical-incidents',
      severity: 'CRITICAL',
      title: 'Critical incidents open',
      summary: `${snapshot.incidents.summary.critical_active} critical incident(s) require immediate triage.`,
      route: '/incidents',
    });
  }

  if (snapshot.incidents?.degraded_mode.state === 'ACTIVE') {
    items.push({
      id: 'degraded-mode',
      severity: 'HIGH',
      title: 'Degraded mode active',
      summary: 'Some autonomous actions are restricted until degraded mode is cleared.',
      route: '/incidents',
    });
  }

  if ((snapshot.certification?.latest_run?.certification_level ?? '').includes('REMEDIATION') || (snapshot.certification?.latest_run?.certification_level ?? '').includes('RECERTIFICATION')) {
    items.push({
      id: 'cert-downgrade',
      severity: 'HIGH',
      title: 'Certification downgraded',
      summary: `Current level: ${snapshot.certification?.latest_run?.certification_level}.`,
      route: '/certification',
    });
  }

  if (snapshot.rollout?.latest_run?.status === 'ROLLED_BACK') {
    items.push({
      id: 'rollback-recent',
      severity: 'HIGH',
      title: 'Recent rollout rollback',
      summary: 'Last rollout ended in rollback and should be reviewed before new promotion activity.',
      route: '/rollout',
    });
  }

  if ((snapshot.operatorQueueSummary?.high_priority_count ?? 0) > 5) {
    items.push({
      id: 'queue-pressure',
      severity: 'HIGH',
      title: 'Queue pressure is high',
      summary: `${snapshot.operatorQueueSummary?.high_priority_count ?? 0} high-priority queue items are pending.`,
      route: '/operator-queue',
    });
  }

  if ((snapshot.executionVenue?.parity_gap ?? 0) > 0 || (snapshot.venueAccount?.latest_reconciliation?.mismatches_count ?? 0) > 0) {
    items.push({
      id: 'parity-gap',
      severity: 'MEDIUM',
      title: 'Venue parity gaps detected',
      summary: `Execution parity gaps: ${snapshot.executionVenue?.parity_gap ?? 0}, reconciliation mismatches: ${snapshot.venueAccount?.latest_reconciliation?.mismatches_count ?? 0}.`,
      route: '/execution-venue',
    });
  }

  const reviewsRequired = snapshot.positionDecisions.filter((decision) => decision.status === 'REVIEW_REQUIRED');
  if (reviewsRequired.length > 0) {
    const topDecision = reviewsRequired[0];
    items.push({
      id: 'positions-review',
      severity: 'MEDIUM',
      title: 'Positions need lifecycle review',
      summary: `${reviewsRequired.length} decision(s) are marked REVIEW_REQUIRED.`,
      route: '/positions',
      traceRootType: 'position',
      traceRootId: String(topDecision.id),
    });
  }

  const blockedOpportunities = snapshot.opportunityItems.filter((item) => item.execution_path === 'BLOCKED');
  if (blockedOpportunities.length > 0) {
    const topOpportunity = blockedOpportunities[0];
    items.push({
      id: 'blocked-opps',
      severity: 'LOW',
      title: 'Opportunities blocked by envelope',
      summary: `${blockedOpportunities.length} opportunities are currently blocked by policy or envelope constraints.`,
      route: '/opportunities',
      traceRootType: 'opportunity',
      traceRootId: String(topOpportunity.id),
    });
  }



  if ((snapshot.approvalSummary?.pending ?? 0) > 0) {
    items.push({
      id: 'approval-center-pending',
      severity: (snapshot.approvalSummary?.high_priority_pending ?? 0) > 0 ? 'HIGH' : 'MEDIUM',
      title: 'Approval center has pending decisions',
      summary: `${snapshot.approvalSummary?.pending ?? 0} approval request(s) are pending in /approvals.`,
      route: '/approvals',
      traceRootType: snapshot.pendingApprovals[0]?.metadata?.trace?.root_type as string | undefined,
      traceRootId: snapshot.pendingApprovals[0]?.metadata?.trace?.root_id as string | undefined,
    });
  }

  if ((snapshot.runbookAutopilotSummary?.counts.paused_for_approval ?? 0) > 0) {
    items.push({
      id: 'runbook-approval-paused',
      severity: 'MEDIUM',
      title: 'Runbook approvals pending',
      summary: `${snapshot.runbookAutopilotSummary?.counts.paused_for_approval ?? 0} autopilot run(s) are paused for approval.`,
      route: '/runbooks',
    });
  }

  if ((snapshot.runbookSummary?.counts.blocked ?? 0) > 0) {
    items.push({
      id: 'runbook-blocked',
      severity: 'HIGH',
      title: 'Blocked runbooks need operator resolution',
      summary: `${snapshot.runbookSummary?.counts.blocked ?? 0} runbook(s) are in BLOCKED state.`,
      route: '/runbooks',
    });
  }


  if ((snapshot.policyTuningSummary?.approved_not_applied ?? 0) > 0 || (snapshot.policyTuningSummary?.pending_candidates ?? 0) > 0) {
    const pending = snapshot.policyTuningSummary?.pending_candidates ?? 0;
    const approved = snapshot.policyTuningSummary?.approved_not_applied ?? 0;
    items.push({
      id: 'policy-tuning-pending',
      severity: approved > 0 ? 'HIGH' : 'MEDIUM',
      title: 'Policy tuning candidates require review/apply',
      summary: `${pending} pending and ${approved} approved-not-applied candidate(s) in /policy-tuning.`,
      route: '/policy-tuning',
      traceRootType: 'trust_calibration_run',
      traceRootId: '',
    });
  }

  if ((snapshot.policyRolloutSummary?.rollback_recommended_runs ?? 0) > 0) {
    items.push({
      id: 'policy-rollout-rollback-warning',
      severity: 'HIGH',
      title: 'Policy rollout recommends rollback',
      summary: `${snapshot.policyRolloutSummary?.rollback_recommended_runs ?? 0} rollout run(s) are marked rollback recommended.`,
      route: '/policy-rollout',
      traceRootType: 'policy_rollout_run',
      traceRootId: String(snapshot.policyRolloutSummary?.latest_run_id ?? ''),
    });
  }

  if ((snapshot.autonomySummary?.degraded_domains ?? 0) + (snapshot.autonomySummary?.blocked_domains ?? 0) > 0) {
    items.push({
      id: 'autonomy-degraded-domains',
      severity: 'HIGH',
      title: 'Autonomy domains degraded/blocked',
      summary: `${(snapshot.autonomySummary?.degraded_domains ?? 0) + (snapshot.autonomySummary?.blocked_domains ?? 0)} autonomy domain(s) are degraded or blocked.`,
      route: '/autonomy',
      traceRootType: 'autonomy_summary',
      traceRootId: 'latest',
    });
  }

  if ((snapshot.autonomySummary?.pending_stage_changes ?? 0) > 0) {
    items.push({
      id: 'autonomy-pending-changes',
      severity: 'MEDIUM',
      title: 'Autonomy stage changes pending',
      summary: `${snapshot.autonomySummary?.pending_stage_changes ?? 0} stage transition(s) pending approval/apply.`,
      route: '/autonomy',
      traceRootType: 'autonomy_transition',
      traceRootId: '',
    });
  }



  if ((snapshot.autonomyBacklogSummary?.critical_items ?? 0) > 0 || (snapshot.autonomyBacklogSummary?.ready_count ?? 0) > (snapshot.autonomyBacklogSummary?.prioritized_items ?? 0)) {
    const critical = snapshot.autonomyBacklogSummary?.critical_items ?? 0;
    const ready = snapshot.autonomyBacklogSummary?.ready_count ?? 0;
    const prioritized = snapshot.autonomyBacklogSummary?.prioritized_items ?? 0;
    items.push({
      id: 'autonomy-backlog-pressure',
      severity: critical > 0 ? 'HIGH' : 'MEDIUM',
      title: 'Autonomy backlog requires governance review',
      summary: `${critical} critical item(s), ${ready} ready candidate(s), ${prioritized} prioritized item(s) in /autonomy-backlog.`,
      route: '/autonomy-backlog',
      traceRootType: 'advisory_artifact',
      traceRootId: '',
    });
  }

  if ((snapshot.autonomyRoadmapSummary?.latest_blocked_domains.length ?? 0) > 0) {
    items.push({
      id: 'autonomy-roadmap-blocked',
      severity: 'MEDIUM',
      title: 'Roadmap has blocked domains',
      summary: `${snapshot.autonomyRoadmapSummary?.latest_blocked_domains.length ?? 0} domain(s) are blocked in the latest autonomy roadmap plan.`,
      route: '/autonomy-roadmap',
      traceRootType: 'autonomy_roadmap_plan',
      traceRootId: String(snapshot.autonomyRoadmapSummary?.latest_plan_id ?? ''),
    });
  }

  if (snapshot.missionControl?.state.status === 'PAUSED' && snapshot.incidents?.degraded_mode.state !== 'ACTIVE') {
    items.push({
      id: 'mission-paused',
      severity: 'MEDIUM',
      title: 'Mission control paused',
      summary: 'Mission control is paused without active degraded mode. Confirm if this is expected.',
      route: '/mission-control',
    });
  }

  return items.sort((left, right) => {
    const severityRank = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
    return severityRank[left.severity] - severityRank[right.severity];
  });
}

export function getCockpitQuickLinks() {
  return [
    { label: 'Mission control', path: '/mission-control' },
    { label: 'Incidents', path: '/incidents' },
    { label: 'Certification', path: '/certification' },
    { label: 'Rollout manager', path: '/rollout' },
    { label: 'Operator queue', path: '/operator-queue' },
    { label: 'Opportunity cycle', path: '/opportunity-cycle' },
    { label: 'Runbooks', path: '/runbooks' },
    { label: 'Approvals', path: '/approvals' },
    { label: 'Automation policy', path: '/automation-policy' },
    { label: 'Policy tuning', path: '/policy-tuning' },
    { label: 'Policy rollout', path: '/policy-rollout' },
    { label: 'Autonomy manager', path: '/autonomy' },
    { label: 'Autonomy roadmap', path: '/autonomy-roadmap' },
    { label: 'Autonomy campaigns', path: '/autonomy-campaigns' },
    { label: 'Autonomy backlog', path: '/autonomy-backlog' },
    { label: 'Autonomy intake', path: '/autonomy-intake' },
    { label: 'Planning review', path: '/autonomy-planning-review' },
    { label: 'Autonomy package', path: '/autonomy-package' },
    { label: 'Autonomy activation', path: '/autonomy-activation' },
    { label: 'Autonomy interventions', path: '/autonomy-interventions' },
    { label: 'Trace explorer', path: '/trace' },
    { label: 'Execution venue', path: '/execution-venue' },
    { label: 'Venue account', path: '/venue-account' },
  ];
}

export async function runCockpitAction(action: CockpitQuickActionId, payload?: Record<string, unknown>) {
  switch (action) {
    case 'MISSION_CONTROL_START':
      return startMissionControl(payload ?? {});
    case 'MISSION_CONTROL_PAUSE':
      return pauseMissionControl();
    case 'MISSION_CONTROL_RESUME':
      return resumeMissionControl();
    case 'INCIDENT_DETECTION':
      return runIncidentDetection();
    case 'CERTIFICATION_REVIEW':
      return runCertificationReview(payload ?? {});
    case 'PORTFOLIO_GOVERNANCE':
      return runPortfolioGovernance(payload ?? {});
    case 'PROFILE_GOVERNANCE':
      return runProfileGovernance(payload ?? {});
    case 'ROLLOUT_PAUSE': {
      if (!payload?.runId) {
        throw new Error('runId is required to pause rollout.');
      }
      return pauseRollout(Number(payload.runId));
    }
    case 'ROLLOUT_ROLLBACK': {
      if (!payload?.runId) {
        throw new Error('runId is required to rollback rollout.');
      }
      return rollbackRollout(Number(payload.runId), { reason: 'Operator cockpit rollback request.' });
    }
    default:
      throw new Error(`Unsupported cockpit action: ${String(action)}`);
  }
}
