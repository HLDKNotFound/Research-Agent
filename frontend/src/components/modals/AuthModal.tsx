import React, { useState } from 'react';
import { X, AlertCircle, Loader2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useUI } from '../../context/UIContext';

export const AuthModal: React.FC = () => {
  const { activeModal, closeModal } = useUI();
  const { login, register } = useAuth();

  const [isLoginMode, setIsLoginMode] = useState<boolean>(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (activeModal !== 'auth') return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isLoginMode) {
        await login({ email, password });
      } else {
        await register({ email, password, name });
      }
      closeModal();
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Authentication failed';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={closeModal}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">{isLoginMode ? 'Sign In' : 'Create Account'}</h3>
          <button className="action-icon-btn" onClick={closeModal}>
            <X size={18} />
          </button>
        </div>

        {error && (
          <div
            style={{
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#f87171',
              fontSize: '0.84rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {!isLoginMode && (
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input
                className="form-input"
                type="text"
                placeholder="Dr. John von Neumann"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input
              className="form-input"
              type="email"
              placeholder="researcher@institution.org"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              className="form-input"
              type="password"
              placeholder={isLoginMode ? '••••••••••••' : 'At least 8 characters'}
              minLength={isLoginMode ? undefined : 8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? (
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <Loader2 size={16} className="animate-spin" />
                <span>Processing...</span>
              </span>
            ) : isLoginMode ? (
              'Sign In'
            ) : (
              'Register Account'
            )}
          </button>
        </form>

        <div style={{ textAlign: 'center', fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
          {isLoginMode ? "Don't have an account? " : 'Already have an account? '}
          <button
            type="button"
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-link)',
              fontWeight: 600,
              cursor: 'pointer',
            }}
            onClick={() => {
              setIsLoginMode(!isLoginMode);
              setError(null);
            }}
          >
            {isLoginMode ? 'Sign up' : 'Sign in'}
          </button>
        </div>
      </div>
    </div>
  );
};
