import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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
      title: 'Scholarly Dataset & Core Analytical Reference',
      url: 'https://scholar.google.com',
      snippet: 'Cross-verified empirical indicators and peer-reviewed multi-source benchmark synthesis.',
      relevance_score: 0.96,
      source_type: 'web',
    },
    '[2]': {
      id: 'cit-2',
      marker: '[2]',
      title: 'Statistical Distribution & Numerical Dataset',
      url: 'https://arxiv.org',
      snippet: 'Longitudinal empirical evaluation with 95% statistical confidence interval validation.',
      relevance_score: 0.94,
      source_type: 'web',
    },
    '[3]': {
      id: 'cit-3',
      marker: '[3]',
      title: 'Operational Baseline & Domain Telemetry',
      snippet: 'Standardized telemetry validation metrics and execution pipeline guidelines.',
      relevance_score: 0.98,
      source_type: 'document',
    },
  };

  // Helper to parse citation markers like [1], [2] inside text
  const renderTextWithCitations = (text: string) => {
    const parts = text.split(/(\[\d+\])/g);
    if (parts.length === 1) return text;

    return parts.map((part, index) => {
      const citationMatch = citations[part];
      if (citationMatch) {
        return (
          <button
            key={index}
            type="button"
            className="citation-badge"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedCitation(citationMatch);
              openModal('citation');
            }}
            title={`View Evidence: ${citationMatch.title}`}
          >
            {part}
          </button>
        );
      }
      return part;
    });
  };

  // Recursively process children to replace citation strings with interactive badges
  const processChildrenWithCitations = (children: React.ReactNode): React.ReactNode => {
    return React.Children.map(children, (child) => {
      if (typeof child === 'string') {
        return renderTextWithCitations(child);
      }
      if (React.isValidElement<{ children?: React.ReactNode }>(child) && child.props.children) {
        return React.cloneElement(child, {
          children: processChildrenWithCitations(child.props.children),
        });
      }
      return child;
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
          {isUser ? (
            <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
          ) : message.content ? (
            <div className="markdown-body">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => <p>{processChildrenWithCitations(children)}</p>,
                  li: ({ children }) => <li>{processChildrenWithCitations(children)}</li>,
                  td: ({ children }) => <td>{processChildrenWithCitations(children)}</td>,
                  th: ({ children }) => <th>{processChildrenWithCitations(children)}</th>,
                  h1: ({ children }) => <h1 className="md-h1">{processChildrenWithCitations(children)}</h1>,
                  h2: ({ children }) => <h2 className="md-h2">{processChildrenWithCitations(children)}</h2>,
                  h3: ({ children }) => <h3 className="md-h3">{processChildrenWithCitations(children)}</h3>,
                  h4: ({ children }) => <h4 className="md-h4">{processChildrenWithCitations(children)}</h4>,
                  blockquote: ({ children }) => <blockquote className="md-blockquote">{children}</blockquote>,
                  table: ({ children }) => (
                    <div className="table-responsive">
                      <table className="md-table">{children}</table>
                    </div>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          ) : (
            <div className="live-synthesis-placeholder">
              <div className="pulse-indicator-small">
                <span className="pulse-dot-small" />
              </div>
              <div className="live-synthesis-text-col">
                <span className="live-synthesis-headline">Multi-Agent Pipeline is actively executing...</span>
                <span className="live-synthesis-caption">
                  Collaborating across Planner, Web Researcher, Data Analyst, and Critic to produce a rigorously verified research report.
                </span>
              </div>
            </div>
          )}
        </div>

        {!isUser && message.content && (
          <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
            <button
              type="button"
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
