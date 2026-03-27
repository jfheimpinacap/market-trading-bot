import { requestJson } from './api/client';
import type { ChampionChallengerRun, ChampionChallengerSummary, StackProfileBinding } from '../types/championChallenger';

export function runChampionChallenger(payload: Record<string, unknown>) {
  return requestJson<ChampionChallengerRun>('/api/champion-challenger/run/', { method: 'POST', body: JSON.stringify(payload) });
}

export function getChampionChallengerRuns() {
  return requestJson<ChampionChallengerRun[]>('/api/champion-challenger/runs/');
}

export function getChampionChallengerRun(id: number) {
  return requestJson<ChampionChallengerRun>(`/api/champion-challenger/runs/${id}/`);
}

export function getCurrentChampionBinding() {
  return requestJson<{ current_champion: StackProfileBinding }>('/api/champion-challenger/current-champion/');
}

export function getChampionChallengerSummary() {
  return requestJson<ChampionChallengerSummary>('/api/champion-challenger/summary/');
}
