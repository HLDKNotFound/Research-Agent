import React, { createContext, useContext, useState } from 'react';
import type { Citation } from '../types';

interface UIContextType {
  activeProjectId: string | null;
  setActiveProjectId: (id: string | null) => void;
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  isDeepResearch: boolean;
  toggleDeepResearch: () => void;
  activeModal: 'auth' | 'project' | 'file' | 'citation' | null;
  openModal: (modal: 'auth' | 'project' | 'file' | 'citation') => void;
  closeModal: () => void;
  selectedCitation: Citation | null;
  setSelectedCitation: (citation: Citation | null) => void;
}

const UIContext = createContext<UIContextType | undefined>(undefined);

export const UIProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
  const [isDeepResearch, setIsDeepResearch] = useState<boolean>(true);
  const [activeModal, setActiveModal] = useState<'auth' | 'project' | 'file' | 'citation' | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  const toggleSidebar = () => setIsSidebarOpen((prev) => !prev);
  const toggleDeepResearch = () => setIsDeepResearch((prev) => !prev);
  const openModal = (modal: 'auth' | 'project' | 'file' | 'citation') => setActiveModal(modal);
  const closeModal = () => {
    setActiveModal(null);
    setSelectedCitation(null);
  };

  return (
    <UIContext.Provider
      value={{
        activeProjectId,
        setActiveProjectId,
        activeConversationId,
        setActiveConversationId,
        isSidebarOpen,
        toggleSidebar,
        isDeepResearch,
        toggleDeepResearch,
        activeModal,
        openModal,
        closeModal,
        selectedCitation,
        setSelectedCitation,
      }}
    >
      {children}
    </UIContext.Provider>
  );
};

export const useUI = () => {
  const context = useContext(UIContext);
  if (!context) {
    throw new Error('useUI must be used within a UIProvider');
  }
  return context;
};
