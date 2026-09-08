import { ApiClient } from './client';
import type { ReportItem } from '../types';

export const reportsApi = {
  async listReports(projectId: string): Promise<{ items: ReportItem[]; total: number }> {
    return ApiClient.get<{ items: ReportItem[]; total: number }>(`/api/v1/projects/${projectId}/reports`);
  },

  async getReport(reportId: string): Promise<ReportItem> {
    return ApiClient.get<ReportItem>(`/api/v1/reports/${reportId}`);
  },

  async deleteReport(reportId: string): Promise<void> {
    return ApiClient.delete<void>(`/api/v1/reports/${reportId}`);
  },
};
