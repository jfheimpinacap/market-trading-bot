import type { PropsWithChildren, ReactNode } from 'react';
import { EmptyState } from '../EmptyState';

type DataStateWrapperProps = PropsWithChildren<{
  isLoading: boolean;
  isError: boolean;
  hasData?: boolean;
  staleWhileRevalidate?: boolean;
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
  hasData = false,
  staleWhileRevalidate = false,
  errorMessage,
  isEmpty = false,
  emptyTitle = 'Sin datos por ahora',
  emptyDescription = 'Todavía no hay información para mostrar en este bloque.',
  loadingTitle = 'Cargando información',
  loadingDescription = 'Estamos consultando datos del sistema.',
  errorTitle = 'No se pudo cargar la información',
  action,
}: DataStateWrapperProps) {
  const showStaleContent = staleWhileRevalidate && hasData;

  if (isLoading && !showStaleContent) {
    return <EmptyState title={loadingTitle} description={loadingDescription} action={action} eyebrow="Cargando" />;
  }

  if (isError && !showStaleContent) {
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

  return (
    <>
      {showStaleContent && isLoading ? <p className="muted-text">Actualizando datos en segundo plano…</p> : null}
      {showStaleContent && isError ? <p className="muted-text">Mostrando último dato válido mientras reconectamos.</p> : null}
      {children}
    </>
  );
}
