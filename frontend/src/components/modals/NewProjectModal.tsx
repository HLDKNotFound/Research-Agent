import React, { useState } from 'react';
import { X, FolderPlus, Loader2 } from 'lucide-react';
import { useUI } from '../../context/UIContext';
import { useProjects } from '../../hooks/useProjects';

export const NewProjectModal: React.FC = () => {
  const { activeModal, closeModal } = useUI();
  const { createProject, isCreating, projects, activeProjectId, setActiveProjectId } = useProjects();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  if (activeModal !== 'project') return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      await createProject({ name, description });
      closeModal();
      setName('');
      setDescription('');
    } catch (err) {
      console.error('Failed to create project:', err);
    }
  };

  return (
    <div className="modal-overlay" onClick={closeModal}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FolderPlus size={20} color="#818cf8" />
            <h3 className="modal-title">Select or Create Project</h3>
          </div>
          <button className="action-icon-btn" onClick={closeModal}>
            <X size={18} />
          </button>
        </div>

        {/* Existing Projects Switcher */}
        {projects.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label className="form-label">Existing Workspaces</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '140px', overflowY: 'auto' }}>
              {projects.map((p) => (
                <div
                  key={p.id}
                  onClick={() => {
                    setActiveProjectId(p.id);
                    closeModal();
                  }}
                  style={{
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-md)',
                    background: p.id === activeProjectId ? 'rgba(99, 102, 241, 0.15)' : 'var(--bg-tertiary)',
                    border: `1px solid ${p.id === activeProjectId ? 'var(--border-focus)' : 'var(--border-subtle)'}`,
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: '0.86rem',
                  }}
                >
                  <span style={{ fontWeight: 500 }}>{p.name}</span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{p.role || 'member'}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <hr style={{ borderColor: 'var(--border-subtle)', margin: '4px 0' }} />

        {/* Create New Project Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="form-group">
            <label className="form-label">New Project Name</label>
            <input
              className="form-input"
              type="text"
              placeholder="e.g., Quantum Computing Benchmarks"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description (Optional)</label>
            <input
              className="form-input"
              type="text"
              placeholder="Empirical analysis on NISQ error mitigation"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button className="btn-secondary" type="button" onClick={closeModal}>
              Cancel
            </button>
            <button className="btn-primary" type="submit" disabled={isCreating || !name.trim()}>
              {isCreating ? <Loader2 size={16} className="animate-spin" /> : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
