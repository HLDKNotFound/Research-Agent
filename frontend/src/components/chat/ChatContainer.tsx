import React, { useRef, useEffect } from 'react';
import { Atom, TrendingUp, Cpu, BookOpen } from 'lucide-react';
import { useConversations } from '../../hooks/useConversations';
import { MessageItem } from './MessageItem';

export const ChatContainer: React.FC = () => {
  const { messages, sendMessage } = useConversations();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const suggestions = [
    {
      icon: <Atom size={18} color="#818cf8" />,
      category: 'Quantum Computing',
      prompt: 'Compare zero-noise extrapolation vs probabilistic error cancellation in NISQ processors.',
    },
    {
      icon: <TrendingUp size={18} color="#10b981" />,
      category: 'Financial Analysis',
      prompt: 'Summarize Q3 revenue growth and cross-reference capital expenditures across uploaded spreadsheets.',
    },
    {
      icon: <Cpu size={18} color="#ec4899" />,
      category: 'Hardware & AI',
      prompt: 'Evaluate recent advancements in wafer-scale photonic computing with academic citations.',
    },
    {
      icon: <BookOpen size={18} color="#06b6d4" />,
      category: 'Literature Review',
      prompt: 'Synthesize research papers on LLM hallucination benchmarks and empirical verification techniques.',
    },
  ];

  return (
    <div className="chat-feed">
      {messages.length === 0 ? (
        <div className="welcome-container">
          <div className="welcome-title">
            Where knowledge meets deep reasoning.
          </div>
          <div className="welcome-subtitle">
            Autonomous multi-agent research orchestrated with LangGraph, pgvector similarity search, and automated academic citation verification.
          </div>

          <div className="suggestion-grid">
            {suggestions.map((s, idx) => (
              <div
                key={idx}
                className="suggestion-card"
                onClick={() => sendMessage({ prompt: s.prompt })}
              >
                <div className="suggestion-card-header">
                  {s.icon}
                  <span>{s.category}</span>
                </div>
                <div className="suggestion-card-text">{s.prompt}</div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        messages.map((msg) => <MessageItem key={msg.id} message={msg} />)
      )}

      <div ref={bottomRef} style={{ height: '20px' }} />
    </div>
  );
};
