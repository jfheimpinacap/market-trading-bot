import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import {
  getPredictionHandoffs,
  getPursuitRecommendations,
  getPursuitScores,
  getPursuitSummary,
  getResearchCandidates,
  getResearchRecommendations,
  getResearchTriageDecisions,
  getResearchUniverseSummary,
  getStructuralAssessments,
  runPursuitReview,
  runResearchUniverseScan,
} from '../services/researchAgent';
import type {
  PredictionHandoffCandidate,
  ResearchPursuitRecommendation,
  ResearchPursuitScore,
  ResearchPursuitSummary,
  ResearchStructuralAssessment,
  MarketResearchCandidate,
  MarketResearchRecommendation,
  MarketTriageDecision,
  ResearchUniverseSummary,
} from '../types/researchAgent';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const normalized = value.toUpperCase();
  if (['SHORTLIST', 'SEND_TO_PREDICTION', 'READY', 'READY_FOR_PREDICTION', 'PREDICTION_READY'].includes(normalized)) return 'ready';
  if (['WATCHLIST', 'WATCH', 'DEFER', 'DEFERRED', 'KEEP_ON_RESEARCH_WATCHLIST', 'NEEDS_REVIEW'].includes(normalized)) return 'pending';
  if (['IGNORE', 'BLOCK', 'BLOCKED'].includes(normalized)) return 'offline';
  return 'neutral';
};

export function ResearchAgentPage() {
  const [summary, setSummary] = useState<ResearchUniverseSummary | null>(null);
  const [pursuitSummary, setPursuitSummary] = useState<ResearchPursuitSummary | null>(null);
  const [candidates, setCandidates] = useState<MarketResearchCandidate[]>([]);
  const [decisions, setDecisions] = useState<MarketTriageDecision[]>([]);
  const [recommendations, setRecommendations] = useState<MarketResearchRecommendation[]>([]);
  const [assessments, setAssessments] = useState<ResearchStructuralAssessment[]>([]);
  const [scores, setScores] = useState<ResearchPursuitScore[]>([]);
  const [handoffs, setHandoffs] = useState<PredictionHandoffCandidate[]>([]);
  const [pursuitRecommendations, setPursuitRecommendations] = useState<ResearchPursuitRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanLoading, setScanLoading] = useState(false);
  const [pursuitLoading, setPursuitLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, candidateRes, decisionRes, recommendationRes, pursuitSummaryRes, assessmentsRes, scoresRes, handoffsRes, pursuitRecommendationsRes] = await Promise.all([
        getResearchUniverseSummary(),
        getResearchCandidates(),
        getResearchTriageDecisions(),
        getResearchRecommendations(),
        getPursuitSummary(),
        getStructuralAssessments(),
        getPursuitScores(),
        getPredictionHandoffs(),
        getPursuitRecommendations(),
      ]);
      setSummary(summaryRes);
      setCandidates(candidateRes);
      setDecisions(decisionRes);
      setRecommendations(recommendationRes);
      setPursuitSummary(pursuitSummaryRes);
      setAssessments(assessmentsRes);
      setScores(scoresRes);
      setHandoffs(handoffsRes);
      setPursuitRecommendations(pursuitRecommendationsRes);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load research-agent board.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runScan = async () => {
    setScanLoading(true);
    try {
      await runResearchUniverseScan();
      await load();
    } finally {
      setScanLoading(false);
    }
  };

  const runPursuit = async () => {
    setPursuitLoading(true);
    try {
      await runPursuitReview();
      await load();
    } finally {
      setPursuitLoading(false);
    }
  };

  const topCandidates = useMemo(() => candidates.slice(0, 40), [candidates]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Research pursuit & prediction handoff"
        title="/research-agent"
        description="Paper-only, local-first structural triage layer for research→prediction bridge. This does not execute live orders and does not replace prediction/risk/runtime authorities."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/scan-agent')}>Open scan-agent</button><button type="button" className="secondary-button" onClick={() => navigate('/prediction')}>Open prediction</button><button type="button" className="secondary-button" onClick={() => navigate('/trace')}>Open trace</button><button type="button" className="primary-button" disabled={scanLoading} onClick={() => void runScan()}>{scanLoading ? 'Running universe scan...' : 'Run universe scan'}</button><button type="button" className="primary-button" disabled={pursuitLoading} onClick={() => void runPursuit()}>{pursuitLoading ? 'Running pursuit review...' : 'Run pursuit review'}</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <div className="content-grid content-grid--three-columns">
          <SectionCard eyebrow="Summary" title="Research pursuit summary" description="Structural triage status for prediction readiness.">
            <ul className="key-value-list">
              <li><span>Markets considered</span><strong>{pursuitSummary?.totals.markets_considered ?? 0}</strong></li>
              <li><span>Prediction-ready</span><strong>{pursuitSummary?.totals.prediction_ready ?? 0}</strong></li>
              <li><span>Watchlist</span><strong>{pursuitSummary?.totals.watchlist ?? 0}</strong></li>
              <li><span>Deferred</span><strong>{pursuitSummary?.totals.deferred ?? 0}</strong></li>
              <li><span>Blocked</span><strong>{pursuitSummary?.totals.blocked ?? 0}</strong></li>
              <li><span>High-priority divergence</span><strong>{pursuitSummary?.totals.high_priority_divergence ?? 0}</strong></li>
            </ul>
          </SectionCard>
          <SectionCard eyebrow="Universe" title="Universe coverage" description="Existing universe triage telemetry remains active.">
            <ul className="key-value-list">
              <li><span>Total markets seen</span><strong>{summary?.totals.total_markets_seen ?? 0}</strong></li>
              <li><span>Open markets</span><strong>{summary?.totals.open_markets_seen ?? 0}</strong></li>
              <li><span>Shortlisted</span><strong>{summary?.totals.shortlisted_count ?? 0}</strong></li>
              <li><span>Watchlist</span><strong>{summary?.totals.watchlist_count ?? 0}</strong></li>
              <li><span>Ignored</span><strong>{summary?.totals.ignored_count ?? 0}</strong></li>
            </ul>
          </SectionCard>
          <SectionCard eyebrow="Notes" title="Scope guardrails" description="Conservative research hardening for paper sandbox runtime.">
            <p style={{ margin: 0 }}>Prediction continues as the authority for probability/edge. This layer only improves candidate quality and traceability before prediction.</p>
          </SectionCard>
        </div>

        <SectionCard eyebrow="Structural assessments" title="Market structural triage" description="Liquidity, volume, time window, and activity checks.">
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Market</th><th>Liquidity</th><th>Volume</th><th>Time window</th><th>Activity</th><th>Status</th><th>Summary</th></tr></thead><tbody>
            {assessments.slice(0, 80).map((item) => (
              <tr key={item.id}><td>{item.market_title}</td><td>{item.liquidity_state}</td><td>{item.volume_state}</td><td>{item.time_to_resolution_state}</td><td>{item.market_activity_state}</td><td><StatusBadge tone={tone(item.structural_status)}>{item.structural_status.toUpperCase()}</StatusBadge></td><td>{item.assessment_summary}</td></tr>
            ))}
          </tbody></table></div>
        </SectionCard>

        <SectionCard eyebrow="Pursuit scores" title="Pursuit-worthiness scoring" description="Transparent component scoring; no opaque single-number authority.">
          <div className="table-wrapper"><table className="data-table"><thead><tr><th>Market</th><th>Score</th><th>Priority</th><th>Status</th><th>Components</th><th>Summary</th></tr></thead><tbody>
            {scores.slice(0, 80).map((item) => (
              <tr key={item.id}><td>{item.market_title}</td><td>{item.pursuit_score}</td><td>{item.priority_bucket}</td><td><StatusBadge tone={tone(item.score_status)}>{item.score_status.toUpperCase()}</StatusBadge></td><td>{Object.entries(item.score_components || {}).map(([key, value]) => `${key}:${value}`).join(' · ')}</td><td>{item.score_summary}</td></tr>
            ))}
          </tbody></table></div>
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Prediction handoff" title="Prediction-ready candidates" description="Research→prediction bridge candidates.">
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Market</th><th>Status</th><th>Confidence</th><th>Reason codes</th><th>Summary</th></tr></thead><tbody>
              {handoffs.slice(0, 80).map((item) => (
                <tr key={item.id}><td>{item.market_title}</td><td><StatusBadge tone={tone(item.handoff_status)}>{item.handoff_status.toUpperCase()}</StatusBadge></td><td>{item.handoff_confidence}</td><td>{item.handoff_reason_codes.join(', ') || '—'}</td><td>{item.handoff_summary}</td></tr>
              ))}
            </tbody></table></div>
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Pursuit recommendations" description="Conservative recommendation set with blockers and rationale.">
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Market</th><th>Confidence</th><th>Blockers</th><th>Rationale</th></tr></thead><tbody>
              {pursuitRecommendations.slice(0, 80).map((item) => (
                <tr key={item.id}><td><StatusBadge tone={tone(item.recommendation_type)}>{item.recommendation_type.toUpperCase()}</StatusBadge></td><td>{item.market_title || '—'}</td><td>{item.confidence}</td><td>{item.blockers.join(', ') || '—'}</td><td>{item.rationale}</td></tr>
              ))}
            </tbody></table></div>
          </SectionCard>
        </div>

        <SectionCard eyebrow="Legacy board" title="Universe pursue board" description="Existing research candidate board retained for backward compatibility.">
          {topCandidates.length === 0 ? <EmptyState eyebrow="No candidates" title="No research triage candidates are available yet." description="Run a universe scan to evaluate markets." /> : (
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Market</th><th>Pursue</th><th>Status</th></tr></thead><tbody>{topCandidates.map((candidate) => (
              <tr key={candidate.id}><td>{candidate.market_title}</td><td>{candidate.pursue_worthiness_score}</td><td><StatusBadge tone={tone(candidate.status)}>{candidate.status.toUpperCase()}</StatusBadge></td></tr>
            ))}</tbody></table></div>
          )}
          <p style={{ marginTop: 12 }}>Legacy decisions: {decisions.length} · Legacy recommendations: {recommendations.length}</p>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
