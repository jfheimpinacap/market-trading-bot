import { useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../../components/PageHeader';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { MarketActiveBadge } from '../../components/markets/MarketActiveBadge';
import { MarketProbabilityBadge } from '../../components/markets/MarketProbabilityBadge';
import { MarketRulesCard } from '../../components/markets/MarketRulesCard';
import { MarketSnapshotsTable } from '../../components/markets/MarketSnapshotsTable';
import { MarketStatusBadge } from '../../components/markets/MarketStatusBadge';
import { formatCompactCurrency, formatDateTime, formatNumber, titleize } from '../../components/markets/utils';
import { SectionCard } from '../../components/SectionCard';
import { navigate, usePathname } from '../../lib/router';
import { getMarketDetail } from '../../services/markets';
import type { MarketDetail } from '../../types/markets';

function getMarketIdFromPath(pathname: string) {
  const segments = pathname.split('/').filter(Boolean);
  return segments[1] ?? '';
}

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function MarketDetailPage() {
  const pathname = usePathname();
  const marketId = useMemo(() => getMarketIdFromPath(pathname), [pathname]);
  const [market, setMarket] = useState<MarketDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadMarketDetail() {
      if (!marketId) {
        setError('The market identifier is missing from the URL.');
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await getMarketDetail(marketId);
        if (!isMounted) {
          return;
        }
        setMarket(response);
      } catch (loadError) {
        if (!isMounted) {
          return;
        }
        setError(getErrorMessage(loadError, 'Could not load market detail.'));
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadMarketDetail();

    return () => {
      isMounted = false;
    };
  }, [marketId]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Market detail"
        title={market?.title ?? 'Market detail'}
        description="Inspect current market state, related event context, rule guidance, and the most recent snapshots returned by the backend demo API."
        actions={
          <button className="secondary-button" type="button" onClick={() => navigate('/markets')}>
            Back to markets
          </button>
        }
      />

      <DataStateWrapper
        isLoading={isLoading}
        isError={Boolean(error)}
        errorMessage={error ?? undefined}
        isEmpty={!isLoading && !error && !market}
        loadingTitle="Loading market detail"
        loadingDescription="Requesting the selected market, its rules, and recent snapshots from the local backend."
        errorTitle="Could not load market detail"
        emptyTitle="Market not found"
        emptyDescription="The selected market does not exist in the current local demo catalog."
        action={
          <button className="secondary-button" type="button" onClick={() => navigate('/markets')}>
            Return to markets
          </button>
        }
      >
        {market ? (
          <>
            <section className="content-grid content-grid--two-columns">
              <SectionCard
                eyebrow="Overview"
                title="Market header"
                description="Primary identifiers and related event context for this contract."
                aside={
                  <div className="market-header-badges">
                    <MarketStatusBadge status={market.status} />
                    <MarketActiveBadge isActive={market.is_active} />
                  </div>
                }
              >
                <dl className="market-detail-list">
                  <div>
                    <dt>Provider</dt>
                    <dd>{market.provider.name}</dd>
                  </div>
                  <div>
                    <dt>Category</dt>
                    <dd>{market.category || '—'}</dd>
                  </div>
                  <div>
                    <dt>Related event</dt>
                    <dd>{market.event?.title ?? market.event_title ?? 'No related event'}</dd>
                  </div>
                  <div>
                    <dt>Ticker</dt>
                    <dd>{market.ticker || '—'}</dd>
                  </div>
                  <div>
                    <dt>Market type</dt>
                    <dd>{titleize(market.market_type)}</dd>
                  </div>
                  <div>
                    <dt>Outcome type</dt>
                    <dd>{titleize(market.outcome_type)}</dd>
                  </div>
                </dl>
              </SectionCard>

              <SectionCard eyebrow="Summary" title="Current market metrics" description="Latest values stored directly on the market row for quick inspection.">
                <div className="market-metric-grid">
                  <article className="market-metric-card">
                    <span>Current probability</span>
                    <strong><MarketProbabilityBadge value={market.current_market_probability} /></strong>
                  </article>
                  <article className="market-metric-card">
                    <span>Yes / No</span>
                    <strong>
                      {market.current_yes_price ? `${(Number(market.current_yes_price) * 100).toFixed(1)}%` : '—'} /{' '}
                      {market.current_no_price ? `${(Number(market.current_no_price) * 100).toFixed(1)}%` : '—'}
                    </strong>
                  </article>
                  <article className="market-metric-card">
                    <span>Liquidity</span>
                    <strong>{formatCompactCurrency(market.liquidity)}</strong>
                  </article>
                  <article className="market-metric-card">
                    <span>24h volume</span>
                    <strong>{formatCompactCurrency(market.volume_24h)}</strong>
                  </article>
                  <article className="market-metric-card">
                    <span>Total volume</span>
                    <strong>{formatCompactCurrency(market.volume_total)}</strong>
                  </article>
                  <article className="market-metric-card">
                    <span>Spread (bps)</span>
                    <strong>{formatNumber(market.spread_bps)}</strong>
                  </article>
                  <article className="market-metric-card">
                    <span>Resolution time</span>
                    <strong>{formatDateTime(market.resolution_time)}</strong>
                  </article>
                  <article className="market-metric-card">
                    <span>Latest snapshot</span>
                    <strong>{formatDateTime(market.latest_snapshot_at)}</strong>
                  </article>
                </div>
              </SectionCard>
            </section>

            <section className="content-grid content-grid--two-columns">
              <MarketRulesCard shortRules={market.short_rules} rules={market.rules} />

              <SectionCard eyebrow="Metadata" title="Useful backend metadata" description="Operational fields that help inspect provenance and resolution details.">
                <dl className="market-detail-list">
                  <div>
                    <dt>Resolution source</dt>
                    <dd>{market.resolution_source || '—'}</dd>
                  </div>
                  <div>
                    <dt>Open time</dt>
                    <dd>{formatDateTime(market.open_time)}</dd>
                  </div>
                  <div>
                    <dt>Close time</dt>
                    <dd>{formatDateTime(market.close_time)}</dd>
                  </div>
                  <div>
                    <dt>Snapshot count</dt>
                    <dd>{formatNumber(market.snapshot_count)}</dd>
                  </div>
                  <div>
                    <dt>Market URL</dt>
                    <dd>
                      {market.url ? (
                        <a href={market.url} target="_blank" rel="noreferrer" className="external-link">
                          Open source market page
                        </a>
                      ) : (
                        '—'
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt>Metadata</dt>
                    <dd className="market-json-preview">{JSON.stringify(market.metadata ?? {}, null, 2)}</dd>
                  </div>
                </dl>
              </SectionCard>
            </section>

            <MarketSnapshotsTable snapshots={market.recent_snapshots} />
          </>
        ) : null}
      </DataStateWrapper>
    </div>
  );
}
