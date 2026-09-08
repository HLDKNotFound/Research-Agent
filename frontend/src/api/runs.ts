import { ApiClient } from './client';
import type { AnalysisRun } from '../types';

export const runsApi = {
  create: (projectId: string, prompt: string, conversationId?: string) =>
    ApiClient.post<AnalysisRun>(`/api/v1/projects/${projectId}/runs`, {
      project_id: projectId,
      prompt,
      conversation_id: conversationId,
    }),

  get: (runId: string) => ApiClient.get<AnalysisRun>(`/api/v1/runs/${runId}`),

  streamProgress: (
    runId: string,
    onEvent: (data: { event: string; agent?: string; message?: string; progress_pct?: number }) => void,
    onError?: (err: unknown) => void,
    onComplete?: () => void,
  ) => {
    const token = ApiClient.getAccessToken();
    const url = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/runs/${runId}/stream`;

    const eventSource = new EventSource(`${url}?token=${token || ''}`);

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        onEvent(parsed);
        if (parsed.event === 'completed') {
          eventSource.close();
          onComplete?.();
        }
      } catch (e) {
        console.error('Failed to parse SSE event:', e);
      }
    };

    eventSource.onerror = (err) => {
      onError?.(err);
      eventSource.close();
    };

    return () => eventSource.close();
  },
};
