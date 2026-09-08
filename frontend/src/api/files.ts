import { ApiClient } from './client';
import type { FileItem } from '../types';

export const filesApi = {
  async listFiles(projectId: string): Promise<{ items: FileItem[]; total: number }> {
    return ApiClient.get<{ items: FileItem[]; total: number }>(`/api/v1/projects/${projectId}/files`);
  },

  async uploadFile(projectId: string, file: File): Promise<FileItem> {
    const formData = new FormData();
    formData.append('file', file);
    return ApiClient.post<FileItem>(`/api/v1/projects/${projectId}/files/upload`, formData);
  },
};
