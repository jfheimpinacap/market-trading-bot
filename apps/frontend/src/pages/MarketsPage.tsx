import { FeaturePageTemplate } from './FeaturePageTemplate';

export function MarketsPage() {
  return (
    <FeaturePageTemplate
      title="Markets"
      eyebrow="Discovery"
      description="Foundation for future market exploration, watchlists, and opportunity scanning."
      currentStatus="Placeholder page ready. This section is positioned to become the entry point for browsing local market datasets and curated watchlists."
      futureModule="A structured explorer for local market snapshots, filters, venue segmentation, and watchlist management."
      nextSteps={[
        'Design a market summary grid and watchlist cards.',
        'Prepare local API contracts for market discovery endpoints.',
        'Add placeholders for filters, categories, and quick navigation.',
      ]}
      notes={[
        'No real market provider integration exists yet.',
        'No live quotes, contracts, or order books are implemented in this phase.',
        'The page layout is ready for future data tables without overengineering now.',
      ]}
    />
  );
}
