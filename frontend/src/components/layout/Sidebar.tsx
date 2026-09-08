import React from 'react';
import {
  Sparkles,
  Plus,
  MessageSquare,
  Trash2,
  FolderKanban,
  User,
  LogOut,
  ChevronDown,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useUI } from '../../context/UIContext';
import { useProjects } from '../../hooks/useProjects';
import { useConversations } from '../../hooks/useConversations';

export const Sidebar: React.FC = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const { isSidebarOpen, openModal } = useUI();
  const { activeProject } = useProjects();
  const {
    conversations,
    activeConversationId,
    setActiveConversationId,
    createConversation,
    deleteConversation,
  } = useConversations();

  const handleNewChat = () => {
    createConversation('New Research Chat');
  };

  return (
    <aside className={`sidebar ${!isSidebarOpen ? 'collapsed' : ''}`}>
      {/* Header & Brand */}
      <div className="sidebar-header">
        <div className="brand-badge">
          <Sparkles size={22} />
          <span>Nexus Research AI</span>
        </div>

        {/* Project Selector */}
        <div
          className="project-selector"
          onClick={() => openModal('project')}
          title="Switch or Create Project"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
            <FolderKanban size={16} color="#818cf8" />
            <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {activeProject ? activeProject.name : 'Select Project'}
            </span>
          </div>
          <ChevronDown size={14} color="#94a3b8" />
        </div>

        {/* New Chat Button */}
        <button className="new-chat-btn" onClick={handleNewChat}>
          <Plus size={18} />
          <span>New Research Chat</span>
        </button>
      </div>

      {/* Conversation List */}
      <div className="conversation-list">
        <div className="conversation-group-title">Research Conversations</div>

        {conversations.length === 0 ? (
          <div style={{ padding: '16px 12px', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            No research chats yet. Start a new session above!
          </div>
        ) : (
          conversations.map((conv) => {
            const isActive = conv.id === activeConversationId;
            return (
              <div
                key={conv.id}
                className={`conversation-item ${isActive ? 'active' : ''}`}
                onClick={() => setActiveConversationId(conv.id)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
                  <MessageSquare size={16} color={isActive ? '#818cf8' : '#64748b'} />
                  <span className="conversation-title">{conv.title}</span>
                </div>

                <div className="conversation-actions">
                  <button
                    className="action-icon-btn"
                    title="Delete Conversation"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm('Delete this conversation?')) {
                        deleteConversation(conv.id);
                      }
                    }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Sidebar Footer / User Profile */}
      <div className="sidebar-footer">
        {isAuthenticated && user ? (
          <>
            <div className="user-profile-badge">
              <div className="user-avatar">
                {user.name ? user.name.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="user-details">
                <span className="user-name">{user.name || user.email}</span>
                <span className="user-role">
                  {user.is_superuser ? 'Superuser' : activeProject?.role || 'Researcher'}
                </span>
              </div>
            </div>

            <button className="action-icon-btn" title="Sign Out" onClick={() => logout()}>
              <LogOut size={16} />
            </button>
          </>
        ) : (
          <button
            className="new-chat-btn"
            style={{ padding: '8px 12px', fontSize: '0.84rem' }}
            onClick={() => openModal('auth')}
          >
            <User size={16} />
            <span>Sign In / Register</span>
          </button>
        )}
      </div>
    </aside>
  );
};
