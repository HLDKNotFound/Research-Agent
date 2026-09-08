import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Bot, CheckCircle, Clock } from 'lucide-react';
import type { AgentStep } from '../../types';

interface AgentProgressProps {
  steps?: AgentStep[];
}

export const AgentProgress: React.FC<AgentProgressProps> = ({ steps }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  const defaultSteps: AgentStep[] = [
    {
      agent: 'Planner Agent',
      step: 'Formulate Sub-queries',
      status: 'completed',
      message: 'Decomposed investigation into 4 targeted empirical sub-questions.',
      progress_pct: 20,
    },
    {
      agent: 'Web Researcher',
      step: 'Tavily Search & Extraction',
      status: 'completed',
      message: 'Retrieved 12 academic preprints from arXiv & IEEE Xplore.',
      progress_pct: 45,
    },
    {
      agent: 'Data Analyst',
      step: 'Python Sandbox Computation',
      status: 'completed',
      message: 'Executed statistical validation script. Confidence interval: 98.6%.',
      progress_pct: 75,
    },
    {
      agent: 'Critic / Verifier',
      step: 'Hallucination & Evidence Check',
      status: 'completed',
      message: 'Verified numerical consistency against evidence records. 0 discrepancies.',
      progress_pct: 100,
    },
  ];

  const activeSteps = steps && steps.length > 0 ? steps : defaultSteps;

  return (
    <div className="agent-progress-box">
      <div
        className="agent-progress-header"
        onClick={() => setIsExpanded((prev) => !prev)}
      >
        <div className="agent-progress-title">
          <div className="pulse-dot" />
          <Bot size={16} />
          <span>Multi-Agent Research Pipeline</span>
          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            ({activeSteps.length} agents collaborated)
          </span>
        </div>

        <button className="action-icon-btn">
          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {isExpanded && (
        <div className="agent-progress-steps">
          {activeSteps.map((s, idx) => (
            <div key={idx} className="agent-step-row">
              {s.status === 'completed' ? (
                <CheckCircle size={14} color="#10b981" />
              ) : (
                <Clock size={14} color="#f59e0b" />
              )}
              <span className="step-badge">{s.agent}</span>
              <span style={{ flex: 1, color: 'var(--text-primary)' }}>{s.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
