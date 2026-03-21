import type { PropsWithChildren } from 'react';
import { getRouteByPath } from '../app/routes';
import type { NavRoute } from '../types/system';
import { Sidebar } from '../components/Sidebar';
import { Topbar } from '../components/Topbar';

type AppShellProps = PropsWithChildren<{
  currentPath: string;
  routes: NavRoute[];
}>;

export function AppShell({ children, currentPath, routes }: AppShellProps) {
  const currentRoute = getRouteByPath(currentPath);

  return (
    <div className="app-shell">
      <Sidebar routes={routes} currentPath={currentPath} />
      <div className="app-shell__main">
        <Topbar route={currentRoute} />
        <main className="app-shell__content">{children}</main>
      </div>
    </div>
  );
}
