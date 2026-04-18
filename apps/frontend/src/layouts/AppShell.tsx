import type { PropsWithChildren } from 'react';
import type { NavRoute } from '../types/system';
import { Sidebar } from '../components/Sidebar';

type AppShellProps = PropsWithChildren<{
  currentPath: string;
  routes: NavRoute[];
}>;

export function AppShell({ children, currentPath, routes }: AppShellProps) {
  return (
    <div className="app-shell">
      <Sidebar routes={routes} currentPath={currentPath} />
      <div className="app-shell__main">
        <main className="app-shell__content">{children}</main>
      </div>
    </div>
  );
}
