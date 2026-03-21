import { FeaturePageTemplate } from './FeaturePageTemplate';

export function SignalsPage() {
  return (
    <FeaturePageTemplate
      title="Signals"
      eyebrow="Decision support"
      description="Placeholder workspace for future signal generation, scoring, and research summaries."
      currentStatus="Placeholder page ready. The navigation and visual structure already define where signal outputs and analyst context will appear."
      futureModule="A future signal board combining model-free heuristics, scored opportunities, analyst notes, and confidence metadata."
      nextSteps={[
        'Create a signal summary layout with cards and priority sections.',
        'Prepare local contracts for future backend signal endpoints.',
        'Reserve space for confidence, rationale, and timing metadata.',
      ]}
      notes={[
        'There is no prediction engine, ML, or market-derived scoring yet.',
        'No live signals are generated in this phase.',
        'The current goal is to preserve a clean location for future signal workflows.',
      ]}
    />
  );
}
