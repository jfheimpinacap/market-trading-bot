import type { TestConsoleStatusResponse } from '../types/missionControl';

const TERMINAL_TEST_CONSOLE_STATUSES = new Set([
  'IDLE',
  'STOPPED',
  'COMPLETED',
  'COMPLETED_WITH_WARNINGS',
  'BLOCKED',
  'FAILED',
  'TIMED_OUT',
  'HUNG',
]);

export type TestConsoleLifecycleState = {
  normalizedStatus: string;
  runActive: boolean;
  hasLastCompletedRun: boolean;
  exists: boolean;
  contractStatus: string;
  reasonCode: string | null;
  currentSnapshot: TestConsoleStatusResponse | null;
  effectiveLastCompletedSnapshot: TestConsoleStatusResponse | null;
  canStop: boolean;
  canExport: boolean;
};

export function resolveTestConsoleLifecycleState(
  currentStatus: TestConsoleStatusResponse | null,
  historicalSnapshot: TestConsoleStatusResponse | null,
): TestConsoleLifecycleState {
  const normalizedStatus = (currentStatus?.test_status ?? '').toUpperCase();
  const runActive = currentStatus?.has_active_run
    ?? (Boolean(currentStatus?.test_status) && !TERMINAL_TEST_CONSOLE_STATUSES.has(normalizedStatus));
  const hasLastCompletedRun = currentStatus?.has_last_completed_run
    ?? Boolean(
      !runActive
      && currentStatus?.ended_at
      && TERMINAL_TEST_CONSOLE_STATUSES.has(normalizedStatus),
    );
  const exists = currentStatus?.exists ?? Boolean(currentStatus?.started_at);
  const contractStatus = (currentStatus?.status ?? (exists ? 'AVAILABLE' : 'NO_RUN_YET')).toUpperCase();
  const reasonCode = currentStatus?.reason_code ?? currentStatus?.last_reason_code ?? null;
  const canStop = runActive && Boolean(currentStatus?.stop_available ?? currentStatus?.can_stop ?? false);
  const canExport = Boolean(currentStatus?.export_available || runActive || hasLastCompletedRun);

  return {
    normalizedStatus,
    runActive,
    hasLastCompletedRun,
    exists,
    contractStatus,
    reasonCode,
    currentSnapshot: runActive ? currentStatus : null,
    effectiveLastCompletedSnapshot: hasLastCompletedRun
      ? (currentStatus ?? historicalSnapshot)
      : historicalSnapshot,
    canStop,
    canExport,
  };
}
