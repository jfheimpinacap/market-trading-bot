import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import {
  getConnectorCases,
  getConnectorRuns,
  getConnectorSummary,
  runConnectorQualification,
} from '../services/connectors';
import type {
  AdapterQualificationRun,
  AdapterReadinessRecommendationCode,
  ConnectorCaseDefinition,
  ConnectorFixtureProfileOption,
  ConnectorSummary,
} from '../types/connectors';

const TONE: Record<string, 'ready' | 'pending' | 'offline' | 'neutral'> = {
  SANDBOX_CERTIFIED: 'ready',
  READ_ONLY_PREPARED: 'ready',
  INCOMPLETE_MAPPING: 'pending',
  RECONCILIATION_GAPS: 'pending',
  MANUAL_REVIEW_REQUIRED: 'pending',
  NOT_READY: 'offline',
  RUNNING: 'pending',
  SUCCESS: 'ready',
  PARTIAL: 'pending',
  FAILED: 'offline',
  PARITY_OK: 'ready',
  PARITY_GAP: 'pending',
  UNSUPPORTED: 'pending',
  PASSED: 'ready',
  WARNING: 'pending',
};

export function ConnectorsPage() {
  const [cases, setCases] = useState<ConnectorCaseDefinition[]>([]);
  const [fixtures, setFixtures] = useState<ConnectorFixtureProfileOption[]>([]);
  const [runs, setRuns] = useState<AdapterQualificationRun[]>([]);
  const [summary, setSummary] = useState<ConnectorSummary | null>(null);
  const [selectedFixture, setSelectedFixture] = useState('generic_binary_market_fixture');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [casesData, runsData, summaryData] = await Promise.all([getConnectorCases(), getConnectorRuns(), getConnectorSummary()]);
      setCases(casesData.cases);
      setFixtures(casesData.fixtures);
      setRuns(runsData);
      setSummary(summaryData);
      if (casesData.fixtures.length > 0) {
        setSelectedFixture((prev) => prev || casesData.fixtures[0].slug);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load connector certification state.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleRunQualification() {
    setBusy(true);
    setError(null);
    try {
      await runConnectorQualification({ fixture_profile: selectedFixture, metadata: { triggered_from: 'connectors_page' } });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not run connector qualification suite.');
    } finally {
      setBusy(false);
    }
  }

  const latestRun = useMemo(() => runs[0] ?? null, [runs]);
  const readiness = summary?.current_readiness;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Adapter qualification harness"
        title="Connectors"
        description="Formal venue connector certification suite for payload mapping, response normalization, account mirror, and reconciliation readiness. Sandbox-only and local-first."
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard
          eyebrow="Safety boundary"
          title="No real broker connectivity in this phase"
          description="Qualification suites run only against sandbox/null adapter paths. No credentials, no live routes, no real orders, no real money."
        >
          <p>
            <StatusBadge tone="pending">SANDBOX_ONLY</StatusBadge> · Use <a href="/execution-venue">Execution Venue</a> for contract details and <a href="/venue-account">Venue Account</a> for parity evidence.
          </p>
        </SectionCard>

        <SectionCard eyebrow="Adapter readiness" title="Current recommendation" description="Latest readiness recommendation based on contract qualification evidence.">
          {!readiness ? (
            <EmptyState title="No readiness recommendation yet." description="Run an adapter qualification suite to assess connector readiness." />
          ) : (
            <div className="stack-sm">
              <p>
                <strong>Adapter:</strong> {summary?.latest_run?.adapter_name ?? 'null_sandbox'} ·{' '}
                <StatusBadge tone={TONE[readiness.recommendation] ?? 'neutral'}>{readiness.recommendation}</StatusBadge>
              </p>
              <p><strong>Rationale:</strong> {readiness.rationale}</p>
              <p><strong>Missing capabilities:</strong> {readiness.missing_capabilities.join(', ') || 'none'}</p>
              <p><strong>Unsupported paths:</strong> {readiness.unsupported_paths.join(', ') || 'none'}</p>
              <p><strong>Reason codes:</strong> {readiness.reason_codes.join(', ') || 'none'}</p>
              <p>
                <strong>Reconciliation readiness:</strong>{' '}
                <StatusBadge tone={latestRun?.results.some((result) => result.case_group === 'reconciliation' && result.result_status !== 'PASSED') ? 'pending' : 'ready'}>
                  {latestRun?.results.some((result) => result.case_group === 'reconciliation' && result.result_status !== 'PASSED') ? 'PARITY_GAP' : 'PARITY_OK'}
                </StatusBadge>
              </p>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Qualification controls" title="Run certification suite" description="Select a fixture profile to test mapping, normalization, and parity pathways.">
          <div className="button-row">
            <select value={selectedFixture} onChange={(event) => setSelectedFixture(event.target.value)}>
              {fixtures.map((fixture) => (
                <option key={fixture.slug} value={fixture.slug}>
                  {fixture.display_name}
                </option>
              ))}
            </select>
            <button type="button" className="primary-button" onClick={() => void handleRunQualification()} disabled={busy}>
              Run qualification
            </button>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Qualification results" title="Latest run case results" description="Technical mismatches and unsupported paths are valid outcomes, not UI errors.">
          {!latestRun ? (
            <EmptyState title="No qualification runs yet." description="Run an adapter qualification suite to assess connector readiness." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr><th>Case</th><th>Result</th><th>Issues</th><th>Warnings</th><th>Created</th></tr>
                </thead>
                <tbody>
                  {latestRun.results.map((result) => (
                    <tr key={result.id}>
                      <td>{result.case_code}</td>
                      <td><StatusBadge tone={TONE[result.result_status] ?? 'neutral'}>{result.result_status}</StatusBadge></td>
                      <td>{result.issues.join(' · ') || 'none'}</td>
                      <td>{result.warnings.join(' · ') || 'none'}</td>
                      <td>{result.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Recent runs" title="Qualification history" description="Recent adapter qualification runs and their readiness recommendations.">
          {runs.length === 0 ? (
            <EmptyState title="No runs available." description="Run an adapter qualification suite to assess connector readiness." />
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr><th>Run</th><th>Status</th><th>Adapter</th><th>Recommendation</th><th>Summary</th></tr>
                </thead>
                <tbody>
                  {runs.slice(0, 10).map((run) => (
                    <tr key={run.id}>
                      <td>#{run.id}</td>
                      <td><StatusBadge tone={TONE[run.qualification_status] ?? 'neutral'}>{run.qualification_status}</StatusBadge></td>
                      <td>{run.adapter_name}</td>
                      <td>
                        <StatusBadge tone={TONE[(run.readiness_recommendation?.recommendation as AdapterReadinessRecommendationCode) ?? 'NOT_READY'] ?? 'neutral'}>
                          {run.readiness_recommendation?.recommendation ?? 'NOT_READY'}
                        </StatusBadge>
                      </td>
                      <td>{run.summary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Qualification catalog" title="Cases baseline" description="Explicit case catalog used in adapter contract qualification runs.">
          {cases.length === 0 ? (
            <p>No qualification cases registered.</p>
          ) : (
            <ul>
              {cases.map((entry) => (
                <li key={entry.code}><strong>{entry.code}</strong> ({entry.group}) — {entry.description}</li>
              ))}
            </ul>
          )}
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
