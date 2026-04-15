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
  emptyTitle = 'Sin datos por ahora',
  emptyDescription = 'Todavía no hay información para mostrar en este bloque.',
  loadingTitle = 'Cargando información',
  loadingDescription = 'Estamos consultando datos del sistema.',
  errorTitle = 'No se pudo cargar la información',
  action,
}: DataStateWrapperProps) {
  if (isLoading) {
    return <EmptyState title={loadingTitle} description={loadingDescription} action={action} eyebrow="Cargando" />;
  }

  if (isError) {
    return (
      <EmptyState
        title={errorTitle}
        description={errorMessage ?? 'El sistema no respondió como se esperaba. Intenta nuevamente en unos segundos.'}
        action={action}
        eyebrow="Error"
      />
    );
  }

  if (isEmpty) {
    return <EmptyState title={emptyTitle} description={emptyDescription} action={action} eyebrow="Sin datos" />;
  }

  return <>{children}</>;
}
