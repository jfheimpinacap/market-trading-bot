import { FeaturePageTemplate } from './FeaturePageTemplate';

export function PostMortemPage() {
  return (
    <FeaturePageTemplate
      title="Post-Mortem"
      eyebrow="Learning loop"
      description="Home for future incident reviews, decision retrospectives, and operational lessons."
      currentStatus="Placeholder page ready. The structure already anticipates writeups, failure analysis, and iteration summaries."
      futureModule="A local retrospective workspace combining execution notes, system anomalies, missed signals, and improvement actions."
      nextSteps={[
        'Add a timeline-style layout for incidents and reviews.',
        'Link future signal and portfolio modules to retrospective notes.',
        'Create placeholders for lessons learned and action tracking.',
      ]}
      notes={[
        'There is no retrospective data model yet.',
        'No automated ingestion from agents or trading flows exists yet.',
        'The frontend structure now keeps a clear place for the post-mortem process.',
      ]}
    />
  );
}
