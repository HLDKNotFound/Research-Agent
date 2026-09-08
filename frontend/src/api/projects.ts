import { ApiClient } from './client';
import type { Project } from '../types';

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export const projectsApi = {
  list: () => ApiClient.get<PaginatedResponse<Project>>('/api/v1/projects?page=1&limit=50'),
  get: (id: string) => ApiClient.get<Project>(`/api/v1/projects/${id}`),
  create: (name: string, description?: string) =>
    ApiClient.post<Project>('/api/v1/projects', { name, description }),
};
