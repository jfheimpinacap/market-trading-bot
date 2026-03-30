import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import {
  getResearchCandidates,
  getResearchRecommendations,
  getResearchTriageDecisions,
  getResearchUniverseSummary,
  runResearchUniverseScan,
} from '../services/researchAgent';
import type { MarketResearchCandidate, MarketResearchRecommendation, MarketTriageDecision, ResearchUniverseSummary } from '../types/researchAgent';

const tone = (value: string): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const normalized = value.toUpperCase();
  if (['SHORTLIST', 'SEND_TO_PREDICTION'].includes(normalized)) return 'ready';
  if (['WATCHLIST', 'RESEARCH_FOLLOWUP', 'KEEP_ON_WATCHLIST', 'NEEDS_REVIEW', 'REQUIRE_MANUAL_REVIEW'].includes(normalized)) return 'pending';
  if (['IGNORE', 'IGNORE_LOW_QUALITY', 'IGNORE_LOW_LIQUIDITY', 'IGNORE_BAD_TIME_HORIZON'].includes(normalized)) return 'offline';
  return 'neutral';
};

export function ResearchAgentPage() {
  const [summary, setSummary] = useState<ResearchUniverseSummary | null>(null);
  const [candidates, setCandidates] = useState<MarketResearchCandidate[]>([]);
  const [decisions, setDecisions] = useState<MarketTriageDecision[]>([]);
  const [recommendations, setRecommendations] = useState<MarketResearchRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanLoading, setScanLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, candidateRes, decisionRes, recommendationRes] = await Promise.all([
        getResearchUniverseSummary(),
        getResearchCandidates(),
        getResearchTriageDecisions(),
        getResearchRecommendations(),
      ]);
      setSummary(summaryRes);
      setCandidates(candidateRes);
      setDecisions(decisionRes);
      setRecommendations(recommendationRes);
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

  const topCandidates = useMemo(() => candidates.slice(0, 100), [candidates]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Market universe triage"
        title="/research-agent"
        description="Local-first, manual-first pursue-worthiness board. Read-only market scan + explicit triage filters + narrative context from scan-agent. No opaque autopilot, no auto-trading."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => navigate('/scan-agent')}>Open scan-agent</button><button type="button" className="secondary-button" onClick={() => navigate('/prediction')}>Open prediction</button><button type="button" className="secondary-button" onClick={() => navigate('/markets')}>Open markets</button><button type="button" className="secondary-button" onClick={() => navigate('/cockpit')}>Open cockpit</button><button type="button" className="secondary-button" onClick={() => navigate('/trace')}>Open trace</button><button type="button" className="primary-button" disabled={scanLoading} onClick={() => void runScan()}>{scanLoading ? 'Running universe scan...' : 'Run universe scan'}</button></div>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <div className="content-grid content-grid--three-columns">
          <SectionCard eyebrow="Summary" title="Universe coverage" description="Auditable market universe run output.">
            <ul className="key-value-list">
              <li><span>Total markets seen</span><strong>{summary?.totals.total_markets_seen ?? 0}</strong></li>
              <li><span>Open markets</span><strong>{summary?.totals.open_markets_seen ?? 0}</strong></li>
              <li><span>Shortlisted</span><strong>{summary?.totals.shortlisted_count ?? 0}</strong></li>
              <li><span>Watchlist</span><strong>{summary?.totals.watchlist_count ?? 0}</strong></li>
              <li><span>Ignored</span><strong>{summary?.totals.ignored_count ?? 0}</strong></li>
              <li><span>Sent to prediction</span><strong>{summary?.totals.sent_to_prediction_count ?? 0}</strong></li>
            </ul>
          </SectionCard>
          <SectionCard eyebrow="State" title="Recommendation summary" description="Recommendation-first triage outputs.">
            <ul className="key-value-list">
              {Object.entries(summary?.recommendation_summary ?? {}).map(([key, value]) => (
                <li key={key}><span>{key}</span><strong>{value}</strong></li>
              ))}
            </ul>
          </SectionCard>
          <SectionCard eyebrow="Notes" title="Manual-first scope" description="Read-only scan + conservative scoring. WATCHLIST/IGNORE are valid, expected outcomes.">
            <p style={{ margin: 0 }}>No research triage candidates are available yet. Run a universe scan to evaluate markets.</p>
          </SectionCard>
        </div>

        <SectionCard eyebrow="Candidates" title="Pursue-worthiness board" description="Market structure + narrative support/divergence + explicit score components.">
          {topCandidates.length === 0 ? (
            <EmptyState eyebrow="No candidates" title="No research triage candidates are available yet." description="Run a universe scan to evaluate markets." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table"><thead><tr><th>Market</th><th>Provider/Category</th><th>Time to resolution</th><th>Liq</th><th>Vol</th><th>Fresh</th><th>Quality</th><th>Narrative</th><th>Divergence</th><th>Pursue</th><th>Status</th><th>Links</th></tr></thead><tbody>
                {topCandidates.map((candidate) => (
                  <tr key={candidate.id}><td>{candidate.market_title}</td><td>{candidate.market_provider} / {candidate.category || '—'}</td><td>{candidate.time_to_resolution_hours ?? '—'}h</td><td>{candidate.liquidity_score}</td><td>{candidate.volume_score}</td><td>{candidate.freshness_score}</td><td>{candidate.market_quality_score}</td><td>{candidate.narrative_support_score}</td><td>{candidate.divergence_score}</td><td>{candidate.pursue_worthiness_score}</td><td><StatusBadge tone={tone(candidate.status)}>{candidate.status.toUpperCase()}</StatusBadge></td><td><button className="link-button" type="button" onClick={() => navigate(`/markets/${candidate.market_slug}`)}>Market</button>{' · '}<button className="link-button" type="button" onClick={() => navigate('/scan-agent')}>Scan signal</button>{' · '}<button className="link-button" type="button" onClick={() => navigate(`/prediction?market_id=${candidate.linked_market}`)}>Prediction</button>{' · '}<button className="link-button" type="button" onClick={() => navigate('/trace')}>Trace</button></td></tr>
                ))}
              </tbody></table>
            </div>
          )}
        </SectionCard>

        <div className="content-grid content-grid--two-columns">
          <SectionCard eyebrow="Decisions" title="Triage decisions" description="Auditable decision type/status and blockers.">
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Market</th><th>Decision</th><th>Status</th><th>Reason codes</th><th>Blockers</th><th>Rationale</th></tr></thead><tbody>
              {decisions.slice(0, 80).map((decision) => (
                <tr key={decision.id}><td>{decision.market_title}</td><td><StatusBadge tone={tone(decision.decision_type)}>{decision.decision_type.toUpperCase()}</StatusBadge></td><td>{decision.decision_status}</td><td>{decision.reason_codes.join(', ') || '—'}</td><td>{decision.blockers.join(', ') || '—'}</td><td>{decision.rationale}</td></tr>
              ))}
            </tbody></table></div>
          </SectionCard>

          <SectionCard eyebrow="Recommendations" title="Recommendation board" description="SEND_TO_PREDICTION / WATCHLIST / IGNORE / REVIEW outputs.">
            <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Market</th><th>Confidence</th><th>Reason codes</th><th>Rationale</th></tr></thead><tbody>
              {recommendations.slice(0, 80).map((recommendation) => (
                <tr key={recommendation.id}><td><StatusBadge tone={tone(recommendation.recommendation_type)}>{recommendation.recommendation_type.toUpperCase()}</StatusBadge></td><td>{recommendation.market_title || '—'}</td><td>{recommendation.confidence}</td><td>{recommendation.reason_codes.join(', ') || '—'}</td><td>{recommendation.rationale}</td></tr>
              ))}
            </tbody></table></div>
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
