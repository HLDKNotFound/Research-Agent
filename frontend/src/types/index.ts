export interface User {
  id: string;
  email: string;
  name?: string;
  is_superuser?: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  role?: 'owner' | 'admin' | 'member' | 'viewer';
  created_at: string;
}

export interface Conversation {
  id: string;
  project_id: string;
  title: string;
  langgraph_thread_id?: string;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  id: string;
  marker: string; // e.g. "[1]"
  title: string;
  url?: string;
  snippet?: string;
  relevance_score?: number;
  source_type?: 'web' | 'document';
}

export interface AgentStep {
  agent: string;
  step: string;
  status: 'running' | 'completed' | 'failed';
  message: string;
  progress_pct?: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system' | 'agent' | 'tool';
  content: string;
  model?: string;
  metadata?: {
    agent_steps?: AgentStep[];
    citations?: Citation[];
    deep_research?: boolean;
    duration_ms?: number;
  };
  created_at: string;
}

export interface FileItem {
  id: string;
  project_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  created_at: string;
}

export interface AnalysisRun {
  id: string;
  project_id: string;
  conversation_id?: string;
  prompt: string;
  status: 'queued' | 'planning' | 'researching' | 'analyzing' | 'writing' | 'reviewing' | 'completed' | 'failed';
  current_step?: string;
  progress_pct: number;
  created_at: string;
}

export interface ReportCitationItem {
  id: string;
  report_section_id: string;
  evidence_id: string;
  citation_text: string;
  position: number;
  created_at: string;
}

export interface ReportSectionItem {
  id: string;
  report_id: string;
  section_key: string;
  title: string;
  content: string;
  section_order: number;
  status: string;
  created_at: string;
  updated_at: string;
  citations?: ReportCitationItem[];
}

export interface ReportItem {
  id: string;
  run_id: string;
  project_id: string;
  created_by_user_id?: string;
  title: string;
  status: string;
  version: number;
  content: string;
  format: string;
  created_at: string;
  updated_at: string;
  sections?: ReportSectionItem[];
}
