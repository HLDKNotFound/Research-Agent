import { ApiClient } from './client';
import type { Conversation, Message } from '../types';
import type { PaginatedResponse } from './projects';

export const conversationsApi = {
  listByProject: (projectId: string) =>
    ApiClient.get<PaginatedResponse<Conversation>>(`/api/v1/projects/${projectId}/conversations?page=1&limit=50`),

  create: (projectId: string, title: string = 'New Research Chat') =>
    ApiClient.post<Conversation>(`/api/v1/projects/${projectId}/conversations`, {
      project_id: projectId,
      title,
    }),

  get: (conversationId: string) =>
    ApiClient.get<Conversation>(`/api/v1/conversations/${conversationId}`),

  delete: (conversationId: string) =>
    ApiClient.delete(`/api/v1/conversations/${conversationId}`),

  listMessages: (conversationId: string) =>
    ApiClient.get<Message[]>(`/api/v1/conversations/${conversationId}/messages?page=1&limit=100`),

  sendMessage: (conversationId: string, content: string, role: string = 'user') =>
    ApiClient.post<Message>(`/api/v1/conversations/${conversationId}/messages`, {
      conversation_id: conversationId,
      role,
      content,
    }),
};
