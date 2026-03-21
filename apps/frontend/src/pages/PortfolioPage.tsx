import { FeaturePageTemplate } from './FeaturePageTemplate';

export function PortfolioPage() {
  return (
    <FeaturePageTemplate
      title="Portfolio"
      eyebrow="Paper trading"
      description="Landing page for future paper positions, exposure monitoring, and simulated performance views."
      currentStatus="Placeholder page ready. The structure defines where paper positions, unrealized PnL, and exposure summaries will appear later."
      futureModule="A local paper-trading panel with portfolio summary cards, exposure snapshots, scenario tracking, and future position drilldowns."
      nextSteps={[
        'Introduce summary cards for paper positions and cash usage.',
        'Prepare a compact activity log for simulated entries and exits.',
        'Reserve space for future risk and exposure widgets.',
      ]}
      notes={[
        'No orders, executions, or real broker/provider connectivity exist yet.',
        'Real portfolio logic is intentionally out of scope for this phase.',
        'This page only sets the information architecture for future local simulations.',
      ]}
    />
  );
}
