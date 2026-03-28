import type { OperatorAlert, OperatorAlertsSummary } from './alerts';
import type { BrokerBridgeSummary } from './brokerBridge';
import type { CertificationSummary } from './certification';
import type { ChampionChallengerSummary } from './championChallenger';
import type { IncidentCurrentState } from './incidents';
import type { MissionControlStatusResponse } from './missionControl';
import type { OpportunityCycleItem, OpportunitySummary } from './opportunities';
import type { OperatorQueueItem, OperatorQueueSummary } from './operatorQueue';
import type { PortfolioGovernanceSummary, PortfolioThrottleDecision } from './portfolioGovernor';
import type { PositionLifecycleDecision, PositionLifecycleSummary } from './positions';
import type { ProfileGovernanceSummary } from './profileManager';
import type { PromotionSummary } from './promotion';
import type { RolloutSummary } from './rollout';
import type { RuntimeStatusResponse } from './runtime';
import type { ApprovalRequest, ApprovalSummary } from './approvals';
import type { RunbookAutopilotSummary, RunbookSummary } from './runbooks';
import type { TraceQueryRun, TraceSummary } from './trace';
import type { VenueSummary } from './executionVenue';
import type { VenueAccountSummary } from './venueAccount';
import type { PolicyTuningSummary } from './policyTuning';
import type { PolicyRolloutSummary } from './policyRollout';
import type { AutonomySummary } from './autonomy';
import type { AutonomyRolloutSummary } from './autonomyRollout';
import type { AutonomyRoadmapSummary } from './autonomyRoadmap';

export type CockpitPanelKey =
  | 'runtime'
  | 'incidents'
  | 'missionControl'
  | 'rollout'
  | 'certification'
  | 'profile'
  | 'portfolioGovernor'
  | 'portfolioThrottle'
  | 'brokerBridge'
  | 'executionVenue'
  | 'venueAccount'
  | 'operatorQueueSummary'
  | 'operatorQueueItems'
  | 'alertsSummary'
  | 'alerts'
  | 'opportunitiesSummary'
  | 'opportunityItems'
  | 'positionsSummary'
  | 'positionDecisions'
  | 'traceSummary'
  | 'traceRuns'
  | 'promotionSummary'
  | 'championChallengerSummary'
  | 'runbookSummary'
  | 'runbookAutopilotSummary'
  | 'approvalSummary'
  | 'pendingApprovals'
  | 'policyTuningSummary'
  | 'policyRolloutSummary'
  | 'autonomySummary'
  | 'autonomyRolloutSummary'
  | 'autonomyRoadmapSummary';

export type CockpitPanelFailures = Partial<Record<CockpitPanelKey, string>>;

export type CockpitSnapshot = {
  runtime: RuntimeStatusResponse | null;
  incidents: IncidentCurrentState | null;
  missionControl: MissionControlStatusResponse | null;
  rollout: RolloutSummary | null;
  certification: CertificationSummary | null;
  profile: ProfileGovernanceSummary | null;
  portfolioGovernor: PortfolioGovernanceSummary | null;
  portfolioThrottle: PortfolioThrottleDecision | null;
  brokerBridge: BrokerBridgeSummary | null;
  executionVenue: VenueSummary | null;
  venueAccount: VenueAccountSummary | null;
  operatorQueueSummary: OperatorQueueSummary | null;
  operatorQueueItems: OperatorQueueItem[];
  alertsSummary: OperatorAlertsSummary | null;
  alerts: OperatorAlert[];
  opportunitiesSummary: OpportunitySummary | null;
  opportunityItems: OpportunityCycleItem[];
  positionsSummary: PositionLifecycleSummary | null;
  positionDecisions: PositionLifecycleDecision[];
  traceSummary: TraceSummary | null;
  traceRuns: TraceQueryRun[];
  promotionSummary: PromotionSummary | null;
  championChallengerSummary: ChampionChallengerSummary | null;
  runbookSummary: RunbookSummary | null;
  runbookAutopilotSummary: RunbookAutopilotSummary | null;
  approvalSummary: ApprovalSummary | null;
  pendingApprovals: ApprovalRequest[];
  policyTuningSummary: PolicyTuningSummary | null;
  policyRolloutSummary: PolicyRolloutSummary | null;
  autonomySummary: AutonomySummary | null;
  autonomyRolloutSummary: AutonomyRolloutSummary | null;
  autonomyRoadmapSummary: AutonomyRoadmapSummary | null;
  failures: CockpitPanelFailures;
  lastUpdatedAt: string;
};

export type CockpitAttentionSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type CockpitAttentionItem = {
  id: string;
  severity: CockpitAttentionSeverity;
  title: string;
  summary: string;
  route: string;
  traceRootType?: string;
  traceRootId?: string;
};

export type CockpitQuickActionId =
  | 'MISSION_CONTROL_START'
  | 'MISSION_CONTROL_PAUSE'
  | 'MISSION_CONTROL_RESUME'
  | 'INCIDENT_DETECTION'
  | 'CERTIFICATION_REVIEW'
  | 'PORTFOLIO_GOVERNANCE'
  | 'PROFILE_GOVERNANCE'
  | 'ROLLOUT_PAUSE'
  | 'ROLLOUT_ROLLBACK';
