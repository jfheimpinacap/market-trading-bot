import { requestJson } from './api/client';
import type { AutonomyRoadmapDependency, AutonomyRoadmapPlan, AutonomyRoadmapSummary, RoadmapRecommendation } from '../types/autonomyRoadmap';

export function getAutonomyRoadmapDependencies() {
  return requestJson<AutonomyRoadmapDependency[]>('/api/autonomy-roadmap/dependencies/');
}

export function runAutonomyRoadmapPlan(payload?: { requested_by?: string }) {
  return requestJson<AutonomyRoadmapPlan>('/api/autonomy-roadmap/run-plan/', {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export function getAutonomyRoadmapPlans() {
  return requestJson<AutonomyRoadmapPlan[]>('/api/autonomy-roadmap/plans/');
}

export function getAutonomyRoadmapPlan(id: number) {
  return requestJson<AutonomyRoadmapPlan>(`/api/autonomy-roadmap/plans/${id}/`);
}

export function getAutonomyRoadmapRecommendations() {
  return requestJson<RoadmapRecommendation[]>('/api/autonomy-roadmap/recommendations/');
}

export function getAutonomyRoadmapSummary() {
  return requestJson<AutonomyRoadmapSummary>('/api/autonomy-roadmap/summary/');
}
