import type { PropsWithChildren, ReactNode } from 'react';
import { EmptyState } from '../EmptyState';

type DataStateWrapperProps = PropsWithChildren<{
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  isEmpty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  loadingTitle?: string;
  loadingDescription?: string;
  errorTitle?: string;
  action?: ReactNode;
}>;

export function DataStateWrapper({
  children,
  isLoading,
  isError,
  errorMessage,
  isEmpty = false,
  emptyTitle = 'No data available',
  emptyDescription = 'There is nothing to show right now.',
  loadingTitle = 'Loading data',
  loadingDescription = 'Please wait while the frontend requests the local backend.',
  errorTitle = 'Could not load data',
  action,
}: DataStateWrapperProps) {
  if (isLoading) {
    return <EmptyState title={loadingTitle} description={loadingDescription} action={action} eyebrow="Loading" />;
  }

  if (isError) {
    return (
      <EmptyState
        title={errorTitle}
        description={errorMessage ?? 'Backend is not available or returned an unexpected response.'}
        action={action}
        eyebrow="Error"
      />
    );
  }

  if (isEmpty) {
    return <EmptyState title={emptyTitle} description={emptyDescription} action={action} eyebrow="Empty" />;
  }

  return <>{children}</>;
}
