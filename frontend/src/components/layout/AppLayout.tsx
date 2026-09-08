import React from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { ChatContainer } from '../chat/ChatContainer';
import { ChatInput } from '../chat/ChatInput';
import { AuthModal } from '../modals/AuthModal';
import { NewProjectModal } from '../modals/NewProjectModal';
import { CitationModal } from '../modals/CitationModal';
import { FileUploadModal } from '../modals/FileUploadModal';

export const AppLayout: React.FC = () => {
  return (
    <div className="app-layout">
      {/* Navigation Sidebar */}
      <Sidebar />

      {/* Main Research Chat View */}
      <main className="main-content">
        <Topbar />
        <ChatContainer />
        <ChatInput />
      </main>

      {/* Modals & Popovers */}
      <AuthModal />
      <NewProjectModal />
      <CitationModal />
      <FileUploadModal />
    </div>
  );
};
