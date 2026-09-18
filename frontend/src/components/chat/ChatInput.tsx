import React, { useState, useRef, useEffect } from 'react';
import {
  ArrowUp,
  Paperclip,
  Sparkles,
  Zap,
  X,
  Loader2,
} from 'lucide-react';
import { useUI } from '../../context/UIContext';
import { useAuth } from '../../context/AuthContext';
import { useConversations } from '../../hooks/useConversations';

export const ChatInput: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [attachedFiles, setAttachedFiles] = useState<Array<{ name: string; size: string }>>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { isDeepResearch, toggleDeepResearch, openModal } = useUI();
  const { isAuthenticated } = useAuth();
  const { sendMessage, isSending } = useConversations();

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [prompt]);

  const handleSubmit = async () => {
    if (!isAuthenticated) {
      openModal('auth');
      return;
    }
    if (!prompt.trim() || isSending) return;
    const currentText = prompt;
    setPrompt('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      await sendMessage({ prompt: currentText });
      setAttachedFiles([]);
    } catch (err) {
      console.error('Failed to send message:', err);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files).map((f) => ({
        name: f.name,
        size: `${(f.size / (1024 * 1024)).toFixed(2)} MB`,
      }));
      setAttachedFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="floating-input-wrapper">
      <div className="input-container">
        {/* Attached Files Row */}
        {attachedFiles.length > 0 && (
          <div className="input-top-bar">
            {attachedFiles.map((file, idx) => (
              <div key={idx} className="file-chip">
                <Paperclip size={12} color="#818cf8" />
                <span>{file.name}</span>
                <button
                  className="file-chip-remove"
                  onClick={() => removeFile(idx)}
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="input-main-row">
          {/* File Upload Trigger */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.xlsx,.csv,.txt"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <button
            className="icon-btn"
            type="button"
            title="Attach Document (PDF, Word, Excel, CSV)"
            onClick={() => fileInputRef.current?.click()}
            style={{ borderRadius: 'var(--radius-full)', border: 'none', background: 'transparent' }}
          >
            <Paperclip size={18} />
          </button>

          {/* Prompt Textarea */}
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            placeholder={
              isDeepResearch
                ? 'Ask a complex research question (Multi-agent loop will synthesize with citations)...'
                : 'Send a quick message...'
            }
            rows={1}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
          />

          <div className="input-actions">
            {/* Mode Toggle Button */}
            <button
              type="button"
              className={`mode-toggle-chip ${isDeepResearch ? 'active' : ''}`}
              onClick={toggleDeepResearch}
              title="Toggle Deep Research Mode"
              style={{ padding: '6px 10px', fontSize: '0.74rem' }}
            >
              {isDeepResearch ? <Sparkles size={13} /> : <Zap size={13} />}
              <span>{isDeepResearch ? 'Deep Mode' : 'Fast'}</span>
            </button>

            {/* Send Button */}
            <button
              type="button"
              className="send-btn"
              disabled={!prompt.trim() || isSending}
              onClick={handleSubmit}
              title="Send Message (Enter)"
            >
              {isSending ? <Loader2 size={18} className="animate-spin" /> : <ArrowUp size={18} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
