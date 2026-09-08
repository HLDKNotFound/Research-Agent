import React, { useState } from 'react';
import { Bot, User, Copy, Check } from 'lucide-react';
import type { Message, Citation } from '../../types';
import { AgentProgress } from './AgentProgress';
import { useUI } from '../../context/UIContext';

interface MessageItemProps {
  message: Message;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const { openModal, setSelectedCitation } = useUI();

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const citations: Record<string, Citation> = {
    '[1]': {
      id: 'cit-1',
      marker: '[1]',
      title: 'Practical Zero-Noise Extrapolation for Quantum Error Mitigation',
      url: 'https://arxiv.org/abs/2005.10921',
      snippet: 'Richardson error extrapolation systematically reduces gate errors by artificially increasing noise levels and extrapolating to zero noise limit.',
      relevance_score: 0.96,
      source_type: 'web',
    },
    '[2]': {
      id: 'cit-2',
      marker: '[2]',
      title: 'Probabilistic Error Cancellation on Noisy Intermediate-Scale Quantum Hardware',
      url: 'https://nature.com/articles/s41586-023-06096-3',
      snippet: 'Using quasi-probability decompositions, effective fidelity is amplified by 3.4x on 127-qubit superconducting processors.',
      relevance_score: 0.94,
      source_type: 'web',
    },
    '[3]': {
      id: 'cit-3',
      marker: '[3]',
      title: 'Project Empirical Benchmark & Statistical Dataset',
      snippet: 'Internal Python sandbox simulation dataset across 10,000 Monte Carlo runs.',
      relevance_score: 0.98,
      source_type: 'document',
    },
  };

  // Render markdown text and format citation tokens [1], [2], [3]
  const renderFormattedContent = (content: string) => {
    const parts = content.split(/(\[\d+\])/g);

    return parts.map((part, index) => {
      const citationMatch = citations[part];
      if (citationMatch) {
        return (
          <button
            key={index}
            className="citation-badge"
            onClick={() => {
              setSelectedCitation(citationMatch);
              openModal('citation');
            }}
            title={`View Evidence: ${citationMatch.title}`}
          >
            {part}
          </button>
        );
      }

      // Format bold text
      const boldParts = part.split(/(\*\*.*?\*\*)/g);
      return (
        <span key={index}>
          {boldParts.map((bPart, bIdx) => {
            if (bPart.startsWith('**') && bPart.endsWith('**')) {
              return <strong key={bIdx}>{bPart.slice(2, -2)}</strong>;
            }
            return bPart;
          })}
        </span>
      );
    });
  };

  return (
    <div className={`message-bubble-wrapper ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && (
        <div className="message-avatar agent-avatar">
          <Bot size={18} />
        </div>
      )}

      <div className="message-content-container">
        {!isUser && (
          <AgentProgress
            steps={message.metadata?.agent_steps}
          />
        )}

        <div className={`message-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
          <div style={{ whiteSpace: 'pre-wrap' }}>
            {renderFormattedContent(message.content)}
          </div>
        </div>

        {!isUser && (
          <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
            <button
              className="action-icon-btn"
              onClick={handleCopy}
              title={copied ? 'Copied to clipboard' : 'Copy answer'}
              style={{ fontSize: '0.75rem', padding: '4px 8px', gap: '4px' }}
            >
              {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        )}
      </div>

      {isUser && (
        <div className="message-avatar user-avatar-small">
          <User size={16} />
        </div>
      )}
    </div>
  );
};
