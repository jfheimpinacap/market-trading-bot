import { requestJson } from './api/client';
import type { LlmStatusResponse } from '../types/llm';

export function getLlmStatus() {
  return requestJson<LlmStatusResponse>('/api/llm/status/');
}
