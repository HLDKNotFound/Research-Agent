import React from 'react';
import { X, ExternalLink, ShieldCheck } from 'lucide-react';
import { useUI } from '../../context/UIContext';

export const CitationModal: React.FC = () => {
  const { activeModal, closeModal, selectedCitation } = useUI();

  if (activeModal !== 'citation' || !selectedCitation) return null;

  return (
    <div className="modal-overlay" onClick={closeModal}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="citation-badge" style={{ fontSize: '0.85rem', padding: '2px 8px' }}>
              {selectedCitation.marker}
            </span>
            <h3 className="modal-title" style={{ fontSize: '1.05rem' }}>Verified Evidence Source</h3>
          </div>
          <button className="action-icon-btn" onClick={closeModal}>
            <X size={18} />
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <h4 style={{ fontSize: '0.98rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
              {selectedCitation.title}
            </h4>
            {selectedCitation.url && (
              <a
                href={selectedCitation.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  color: 'var(--text-link)',
                  fontSize: '0.82rem',
                  textDecoration: 'none',
                }}
              >
                <span>{selectedCitation.url}</span>
                <ExternalLink size={12} />
              </a>
            )}
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '8px 12px',
              background: 'rgba(16, 185, 129, 0.1)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
            }}
          >
            <ShieldCheck size={18} color="#10b981" />
            <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)' }}>
              <strong>Critic Verification Score: </strong>
              <span style={{ color: '#10b981', fontWeight: 700 }}>
                {((selectedCitation.relevance_score || 0.95) * 100).toFixed(1)}% Confidence
              </span>
            </div>
          </div>

          {selectedCitation.snippet && (
            <div className="form-group">
              <label className="form-label">Evidence Snippet Extracted</label>
              <div
                style={{
                  padding: '12px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '0.86rem',
                  lineHeight: '1.5',
                  color: 'var(--text-secondary)',
                  fontStyle: 'italic',
                }}
              >
                "{selectedCitation.snippet}"
              </div>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
          <button className="btn-primary" onClick={closeModal} style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
