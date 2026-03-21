import { FeaturePageTemplate } from './FeaturePageTemplate';

export function AgentsPage() {
  return (
    <FeaturePageTemplate
      title="Agents"
      eyebrow="Automation"
      description="Control surface for future local agents, orchestration state, and execution visibility."
      currentStatus="Placeholder page ready. The frontend defines where agent health, schedules, and orchestration summaries will surface later."
      futureModule="This area will host agent runs, local automation controls, dependencies, and system-level diagnostics for orchestrated workflows."
      nextSteps={[
        'Add agent registry cards and execution timeline placeholders.',
        'Expose backend summaries for future orchestration status.',
        'Visualize dependencies between signals, agents, and paper trading actions.',
      ]}
      notes={[
        'No real agents or task execution are implemented yet.',
        'Celery, Redis, and provider runtime visibility will be added in later stages.',
        'This page is prepared to evolve without changing the global layout.',
      ]}
    />
  );
}
