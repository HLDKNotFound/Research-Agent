import React, { useState, useEffect } from 'react';
import { X, UploadCloud, FileText, CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import { useUI } from '../../context/UIContext';
import { useProjects } from '../../hooks/useProjects';
import { filesApi } from '../../api/files';
import type { FileItem } from '../../types';

export const FileUploadModal: React.FC = () => {
  const { activeModal, closeModal } = useUI();
  const { activeProject } = useProjects();
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(false);

  useEffect(() => {
    if (activeModal === 'file' && activeProject?.id) {
      setLoadingFiles(true);
      setErrorMessage(null);
      filesApi
        .listFiles(activeProject.id)
        .then((res) => {
          setFiles(res.items || []);
        })
        .catch(() => {
          // If unauthenticated or no files, graceful fallback
        })
        .finally(() => {
          setLoadingFiles(false);
        });
    }
  }, [activeModal, activeProject?.id]);

  if (activeModal !== 'file') return null;

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!activeProject?.id) {
      setErrorMessage('Please create or select a project first.');
      return;
    }

    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setIsUploading(true);
      setErrorMessage(null);

      try {
        const uploaded = await filesApi.uploadFile(activeProject.id, file);
        setFiles((prev) => [uploaded, ...prev]);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Upload failed. Please verify file format and size.';
        setErrorMessage(msg);
      } finally {
        setIsUploading(false);
        e.target.value = '';
      }
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="modal-overlay" onClick={closeModal}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileText size={20} color="#818cf8" />
            <h3 className="modal-title">Project Knowledge Base</h3>
          </div>
          <button className="action-icon-btn" onClick={closeModal} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <div style={{ fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
          Workspace: <strong>{activeProject?.name || 'Default Project'}</strong>.
          Documents are parsed, chunked, and embedded into <code>pgvector</code> for similarity search.
        </div>

        {errorMessage && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 14px',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 'var(--radius-md)',
              color: '#f87171',
              fontSize: '0.82rem',
            }}
          >
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Upload Dropzone */}
        <label
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
            border: '2px dashed var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            cursor: isUploading ? 'not-allowed' : 'pointer',
            background: 'rgba(15, 23, 42, 0.5)',
            gap: '8px',
            transition: 'border-color 0.2s',
          }}
        >
          <input
            type="file"
            accept=".pdf,.docx,.xlsx,.csv,.txt"
            style={{ display: 'none' }}
            onChange={handleFileUpload}
            disabled={isUploading}
          />
          {isUploading ? (
            <Loader2 size={28} className="animate-spin" color="#818cf8" />
          ) : (
            <UploadCloud size={28} color="#818cf8" />
          )}
          <span style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            {isUploading ? 'Ingesting & Embedding Document...' : 'Click to Upload Document'}
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Supports PDF, Word (.docx), Excel (.xlsx), CSV, and TXT (Max 50MB)
          </span>
        </label>

        {/* Document List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label className="form-label">
            Indexed Documents ({files.length})
          </label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '180px', overflowY: 'auto' }}>
            {loadingFiles ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '16px', color: 'var(--text-muted)' }}>
                <Loader2 size={18} className="animate-spin" />
              </div>
            ) : files.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '16px', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                No documents uploaded yet. Upload a file above to index it for multi-agent analysis.
              </div>
            ) : (
              files.map((doc) => (
                <div
                  key={doc.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    background: 'var(--bg-tertiary)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.82rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                    <CheckCircle size={14} color="#10b981" />
                    <span
                      style={{
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        maxWidth: '260px',
                        color: 'var(--text-primary)',
                      }}
                      title={doc.filename}
                    >
                      {doc.filename}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                      {formatBytes(doc.size_bytes)}
                    </span>
                    <span
                      style={{
                        fontSize: '0.7rem',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: doc.status === 'ready' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                        color: doc.status === 'ready' ? '#34d399' : '#fbbf24',
                      }}
                    >
                      {doc.status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
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
