import React from 'react';
import {
  PanelLeft,
  Sparkles,
  Zap,
  FileText,
} from 'lucide-react';
import { useUI } from '../../context/UIContext';
import { useProjects } from '../../hooks/useProjects';
import { useConversations } from '../../hooks/useConversations';

export const Topbar: React.FC = () => {
  const { toggleSidebar, isDeepResearch, toggleDeepResearch, openModal } = useUI();
  const { activeProject } = useProjects();
  const { activeConversation } = useConversations();

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button
          className="icon-btn"
          onClick={toggleSidebar}
          title="Toggle Navigation Sidebar"
        >
          <PanelLeft size={18} />
        </button>

        <div className="chat-header-title">
          <span>{activeConversation ? activeConversation.title : 'Deep Research Session'}</span>
          {activeProject && (
            <span
              style={{
                fontSize: '0.72rem',
                color: 'var(--text-muted)',
                background: 'var(--bg-tertiary)',
                padding: '2px 8px',
                borderRadius: 'var(--radius-full)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              {activeProject.name}
            </span>
          )}
        </div>
      </div>

      <div className="topbar-right">
        {/* Deep Research Mode Switch */}
        <button
          className={`mode-toggle-chip ${isDeepResearch ? 'active' : ''}`}
          onClick={toggleDeepResearch}
          title="Toggle Multi-Agent Deep Research (Planner, File & Web Retrieval, Critic Verification, Citations)"
        >
          {isDeepResearch ? <Sparkles size={14} color="#818cf8" /> : <Zap size={14} />}
          <span>{isDeepResearch ? 'Multi-Agent Deep Mode' : 'Quick Chat Mode'}</span>
        </button>

        {/* Project Files Button */}
        <button
          className="icon-btn"
          onClick={() => openModal('file')}
          title="Manage Project Documents & Ingestion"
        >
          <FileText size={18} />
        </button>
      </div>
    </header>
  );
};
