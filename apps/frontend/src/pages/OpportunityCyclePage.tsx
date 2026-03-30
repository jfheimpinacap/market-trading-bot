import { useCallback, useEffect, useMemo, useState } from 'react';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { navigate } from '../lib/router';
import {
  getOpportunityCycleAssessments,
  getOpportunityCycleCandidates,
  getOpportunityCycleProposals,
  getOpportunityCycleRecommendations,
  getOpportunityCycleSummary,
  runOpportunityCycleReview,
} from '../services/opportunityCycle';
import type {
  OpportunityCycleSummary,
  OpportunityFusionAssessment,
  OpportunityFusionCandidate,
  OpportunityRecommendation,
  PaperOpportunityProposal,
} from '../types/opportunityCycle';

function statusBadge(value: string) {
  if (value.includes('READY') || value.includes('SEND_TO')) return 'signal-badge signal-badge--actionable';
  if (value.includes('WATCH')) return 'signal-badge signal-badge--monitor';
  if (value.includes('BLOCK')) return 'signal-badge signal-badge--bearish';
  return 'signal-badge signal-badge--muted';
}

export function OpportunityCyclePage() {
  const [summary, setSummary] = useState<OpportunityCycleSummary | null>(null);
  const [candidates, setCandidates] = useState<OpportunityFusionCandidate[]>([]);
  const [assessments, setAssessments] = useState<OpportunityFusionAssessment[]>([]);
  const [proposals, setProposals] = useState<PaperOpportunityProposal[]>([]);
  const [recommendations, setRecommendations] = useState<OpportunityRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, candidatesRes, assessmentsRes, proposalsRes, recommendationsRes] = await Promise.all([
        getOpportunityCycleSummary(),
        getOpportunityCycleCandidates(),
        getOpportunityCycleAssessments(),
        getOpportunityCycleProposals(),
        getOpportunityCycleRecommendations(),
      ]);
      setSummary(summaryRes);
      setCandidates(candidatesRes);
      setAssessments(assessmentsRes);
      setProposals(proposalsRes);
      setRecommendations(recommendationsRes);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load opportunity cycle data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadData(); }, [loadData]);

  const runReview = useCallback(async () => {
    setBusy(true);
    try {
      await runOpportunityCycleReview();
      await loadData();
    } finally {
      setBusy(false);
    }
  }, [loadData]);

  const cards = useMemo(() => [
    { label: 'Candidates seen', value: summary?.candidate_count ?? 0 },
    { label: 'Fused', value: summary?.fused_count ?? 0 },
    { label: 'Ready for proposal', value: summary?.ready_for_proposal_count ?? 0 },
    { label: 'Watch only', value: summary?.watch_count ?? 0 },
    { label: 'Blocked', value: summary?.blocked_count ?? 0 },
    { label: 'Sent to proposal', value: summary?.sent_to_proposal_count ?? 0 },
  ], [summary]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Opportunity cycle"
        title="/opportunity-cycle"
        description="Local-first, manual-first signal fusion runtime hardening. Consolidates research/prediction/risk/learning and emits auditable paper proposal recommendations."
        actions={<div className="button-row"><button type="button" className="primary-button" disabled={busy} onClick={() => void runReview()}>{busy ? 'Running...' : 'Run opportunity cycle review'}</button><button type="button" className="secondary-button" onClick={() => navigate('/risk-agent')}>Risk agent</button><button type="button" className="secondary-button" onClick={() => navigate('/cockpit')}>Cockpit</button><button type="button" className="secondary-button" onClick={() => navigate('/trace')}>Trace</button><button type="button" className="secondary-button" onClick={() => navigate('/evaluation')}>Evaluation</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined} loadingTitle="Loading opportunity cycle" errorTitle="Could not load opportunity cycle" loadingDescription="Collecting candidates, assessments, proposals and recommendations.">
        <SectionCard eyebrow="Summary" title="Cycle status" description="Manual-first and recommendation-first. No opaque autopilot and no real execution.">
          <div className="dashboard-stat-grid">{cards.map((item) => <article key={item.label} className="dashboard-stat-card"><span>{item.label}</span><strong>{item.value}</strong></article>)}</div>
        </SectionCard>

        <SectionCard eyebrow="Fusion assessments" title="Readiness evaluation" description="Narrative, probability, edge, risk, learning and portfolio fit fused per opportunity.">
          {assessments.length === 0 ? <p className="muted-text">No fused opportunity assessments are available yet. Run the opportunity cycle to evaluate paper proposals.</p> : (
            <div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Provider/Category</th><th>Cal. prob</th><th>Edge</th><th>Conviction</th><th>Risk clearance</th><th>Learning drag</th><th>Portfolio fit</th><th>Final score</th><th>Status</th><th>Links</th></tr></thead><tbody>
              {assessments.map((item) => <tr key={item.id}><td>{item.market_title}</td><td>{item.provider || '-'} / {item.category || '-'}</td><td>{item.calibrated_probability ?? '-'}</td><td>{item.adjusted_edge}</td><td>{item.conviction_score}</td><td>{item.risk_clearance || '-'}</td><td>{item.learning_drag_score}</td><td>{item.portfolio_fit_score}</td><td>{item.final_opportunity_score}</td><td><span className={statusBadge(item.fusion_status)}>{item.fusion_status}</span></td><td><button type="button" className="link-button" onClick={() => navigate('/scan-agent')}>Scan</button><button type="button" className="link-button" onClick={() => navigate('/research-agent')}>Research</button><button type="button" className="link-button" onClick={() => navigate('/prediction')}>Prediction</button><button type="button" className="link-button" onClick={() => navigate('/risk-agent')}>Risk</button><button type="button" className="link-button" onClick={() => navigate('/trace')}>Trace</button></td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Paper proposals" title="Proposal handoff" description="Proposed/ready/watch/blocked output before proposal engine and execution simulation handoffs.">
          {proposals.length === 0 ? <p className="muted-text">No paper opportunity proposals created yet.</p> : (
            <div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Status</th><th>Direction</th><th>Size fraction</th><th>Paper notional</th><th>Execution sim</th><th>Rationale</th></tr></thead><tbody>
              {proposals.map((item) => <tr key={item.id}><td>{item.market_title}</td><td><span className={statusBadge(item.proposal_status)}>{item.proposal_status}</span></td><td>{item.recommended_direction}</td><td>{item.approved_size_fraction ?? '-'}</td><td>{item.paper_notional_size ?? '-'}</td><td>{item.execution_sim_recommended ? 'YES' : 'NO'}</td><td>{item.rationale}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Recommendations" title="Action recommendations" description="Explicit recommendation-first handoffs and blocks.">
          {recommendations.length === 0 ? <p className="muted-text">No recommendations generated yet.</p> : (
            <div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Recommendation</th><th>Rationale</th><th>Reason codes</th><th>Confidence</th></tr></thead><tbody>
              {recommendations.map((item) => <tr key={item.id}><td>{item.market_title}</td><td><span className={statusBadge(item.recommendation_type)}>{item.recommendation_type}</span></td><td>{item.rationale}</td><td>{item.reason_codes.join(', ') || '-'}</td><td>{item.confidence}</td></tr>)}
            </tbody></table></div>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
