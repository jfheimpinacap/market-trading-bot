import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';

export function NotFoundPage() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Navigation"
        title="Page not found"
        description="The requested route is not part of the current frontend scaffold. Use the sidebar to move to an available section."
      />
      <EmptyState
        title="Unavailable route"
        description="This minimal frontend shell only includes the planned product sections defined in the sidebar navigation."
      />
    </div>
  );
}
