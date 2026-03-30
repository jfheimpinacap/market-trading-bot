export type OpportunityFusionStatus =
  | 'READY_FOR_PROPOSAL'
  | 'WATCH_ONLY'
  | 'BLOCKED_BY_RISK'
  | 'BLOCKED_BY_LEARNING'
  | 'LOW_CONVICTION'
  | 'NEEDS_REVIEW'
  | string;

export type PaperOpportunityProposalStatus = 'PROPOSED' | 'READY' | 'WATCH' | 'BLOCKED' | 'SKIPPED' | string;

export type OpportunityCycleSummary = {
  id?: number;
  candidate_count: number;
  fused_count: number;
  ready_for_proposal_count: number;
  watch_count: number;
  blocked_count: number;
  sent_to_proposal_count: number;
  sent_to_execution_sim_context_count: number;
  recommendation_summary: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type OpportunityFusionAssessment = {
  id: number;
  linked_candidate: number;
  fusion_status: OpportunityFusionStatus;
  conviction_score: string;
  execution_feasibility_score: string;
  learning_drag_score: string;
  portfolio_fit_score: string;
  final_opportunity_score: string;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  market_title: string;
  provider: string;
  category: string;
  calibrated_probability: string | null;
  adjusted_edge: string;
  risk_clearance: string;
};

export type PaperOpportunityProposal = {
  id: number;
  linked_assessment: number;
  proposal_status: PaperOpportunityProposalStatus;
  recommended_direction: string;
  calibrated_probability: string | null;
  adjusted_edge: string;
  approved_size_fraction: string | null;
  paper_notional_size: string | null;
  watch_required: boolean;
  execution_sim_recommended: boolean;
  rationale: string;
  reason_codes: string[];
  blockers: string[];
  market_title: string;
};

export type OpportunityRecommendation = {
  id: number;
  recommendation_type: string;
  rationale: string;
  reason_codes: string[];
  confidence: string;
  blockers: string[];
  market_title: string;
};

export type OpportunityFusionCandidate = {
  id: number;
  provider: string;
  category: string;
  market_title: string;
  opportunity_quality_score: string;
};
