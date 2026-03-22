import type { DashboardModuleStatus } from '../../types/dashboard';
import { StatusBadge } from './StatusBadge';

type ModuleStatusListProps = {
  modules: DashboardModuleStatus[];
};

export function ModuleStatusList({ modules }: ModuleStatusListProps) {
  return (
    <ul className="dashboard-module-list">
      {modules.map((module) => (
        <li key={module.name} className="dashboard-module-list__item">
          <div>
            <h3>{module.name}</h3>
            <p>{module.summary}</p>
          </div>
          <StatusBadge tone={module.status === 'ready' ? 'ready' : 'pending'}>
            {module.status === 'ready' ? 'Ready' : 'Pending'}
          </StatusBadge>
        </li>
      ))}
    </ul>
  );
}
