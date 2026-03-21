import { AppShell } from '../layouts/AppShell';
import { appRoutes, getRouteByPath } from './routes';
import { SystemHealthProvider } from './SystemHealthProvider';
import { NotFoundPage } from '../pages/NotFoundPage';
import { usePathname } from '../lib/router';

export function App() {
  const pathname = usePathname();
  const currentRoute = getRouteByPath(pathname);
  const CurrentPage = currentRoute?.component ?? NotFoundPage;

  return (
    <SystemHealthProvider>
      <AppShell currentPath={pathname} routes={appRoutes}>
        <CurrentPage />
      </AppShell>
    </SystemHealthProvider>
  );
}
