/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { UserSession, LegalDocument, ExtractedClause } from './types';
import LoginView from './components/LoginView';
import DashboardView from './components/DashboardView';
import UploadView from './components/UploadView';
import ProcessingView from './components/ProcessingView';
import ResultsView from './components/ResultsView';
import ReportView from './components/ReportView';
import ReviewQueueView from './components/ReviewQueueView';
import { Shield, BookOpen, AlertTriangle } from 'lucide-react';

export default function App() {
  // Session State
  const [user, setUser] = useState<UserSession>({
    name: '',
    role: '',
    email: '',
    isLoggedIn: false,
  });

  // Screen Router State: 'login' | 'dashboard' | 'upload' | 'processing' | 'results' | 'report' | 'review_queue'
  const [screen, setScreen] = useState<'login' | 'dashboard' | 'upload' | 'processing' | 'results' | 'report' | 'review_queue'>('login');

  // Document Repository
  const [documents, setDocuments] = useState<LegalDocument[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [processingDocName, setProcessingDocName] = useState('');
  const [isFetchingDocs, setIsFetchingDocs] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Fetch document index from Express backend
  const fetchDocuments = async () => {
    setIsFetchingDocs(true);
    try {
      const res = await fetch('/api/documents');
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      } else {
        setApiError('Failed to synchronize legal records from server.');
      }
    } catch (err) {
      console.error('Error fetching documents:', err);
      setApiError('Could not connect to the contract analysis server.');
    } finally {
      setIsFetchingDocs(false);
    }
  };

  useEffect(() => {
    if (user.isLoggedIn) {
      fetchDocuments();
    }
  }, [user.isLoggedIn]);

  // Actions
  const handleLogin = (session: UserSession) => {
    setUser(session);
    setScreen('dashboard');
  };

  const handleLogout = () => {
    setUser({ name: '', role: '', email: '', isLoggedIn: false });
    setScreen('login');
  };

  const handleSelectDocument = (doc: LegalDocument) => {
    setSelectedDocId(doc.id);
    setScreen('results');
  };

  const handleDeleteDocument = async (id: string) => {
    try {
      const res = await fetch(`/api/documents/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setDocuments((prev) => prev.filter((d) => d.id !== id));
        if (selectedDocId === id) {
          setSelectedDocId(null);
        }
      } else {
        alert('Could not delete document. Please try again.');
      }
    } catch (err) {
      console.error('Error deleting document:', err);
    }
  };

  // Trigger server-side Gemini legal analysis
  const handleStartAnalysis = async (text: string, name: string) => {
    setProcessingDocName(name);
    setScreen('processing');
    setApiError(null);

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, name }),
      });

      if (!res.ok) {
        throw new Error('Analysis request failed on server.');
      }

      const analyzedDoc: LegalDocument = await res.json();
      
      // Update local repository & open the workspace immediately
      setDocuments((prev) => [analyzedDoc, ...prev]);
      setSelectedDocId(analyzedDoc.id);
      
      // Brief pause to allow the processing transitions to feel deliberate
      setTimeout(() => {
        setScreen('results');
      }, 800);

    } catch (err: any) {
      console.error('Error conducting legal analysis:', err);
      setApiError('An exception error occurred during clause extraction. Reverting to repository index.');
      setScreen('dashboard');
    }
  };

  // Update a clause's manual verification states (PATCH)
  const handleUpdateClause = async (clauseId: string, updates: Partial<ExtractedClause>) => {
    if (!selectedDocId) return;
    try {
      const res = await fetch(`/api/documents/${selectedDocId}/clauses/${clauseId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });

      if (res.ok) {
        const updatedDoc: LegalDocument = await res.json();
        // Sync local records
        setDocuments((prev) =>
          prev.map((d) => (d.id === selectedDocId ? updatedDoc : d))
        );
      }
    } catch (err) {
      console.error('Error updating clause verification state:', err);
    }
  };

  // Update a clause in review queue when not currently in the Results split-pane view
  const handleUpdateReviewQueueClause = async (docId: string, clauseId: string, updates: Partial<ExtractedClause>) => {
    try {
      const res = await fetch(`/api/documents/${docId}/clauses/${clauseId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });

      if (res.ok) {
        const updatedDoc: LegalDocument = await res.json();
        setDocuments((prev) =>
          prev.map((d) => (d.id === docId ? updatedDoc : d))
        );
      }
    } catch (err) {
      console.error('Error updating review queue clause:', err);
    }
  };

  // Update overall document notes / comments
  const handleUpdateDocumentNotes = async (notes: string) => {
    if (!selectedDocId) return;
    try {
      const res = await fetch(`/api/documents/${selectedDocId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewerNotes: notes }),
      });

      if (res.ok) {
        const updatedDoc: LegalDocument = await res.json();
        setDocuments((prev) =>
          prev.map((d) => (d.id === selectedDocId ? updatedDoc : d))
        );
      }
    } catch (err) {
      console.error('Error saving document commentary:', err);
    }
  };

  const activeDoc = documents.find((d) => d.id === selectedDocId);

  // Router dispatcher
  const renderContent = () => {
    switch (screen) {
      case 'login':
        return <LoginView onLogin={handleLogin} />;

      case 'dashboard':
        return (
          <DashboardView
            documents={documents}
            onSelectDocument={handleSelectDocument}
            onNavigateToUpload={() => setScreen('upload')}
            onNavigateToReviewQueue={() => setScreen('review_queue')}
            onLogout={handleLogout}
            user={user}
            onDeleteDocument={handleDeleteDocument}
          />
        );

      case 'upload':
        return (
          <UploadView
            onBackToDashboard={() => setScreen('dashboard')}
            onStartAnalysis={handleStartAnalysis}
          />
        );

      case 'processing':
        return <ProcessingView documentName={processingDocName} />;

      case 'results':
        if (!activeDoc) {
          setScreen('dashboard');
          return null;
        }
        return (
          <ResultsView
            document={activeDoc}
            onBackToDashboard={() => setScreen('dashboard')}
            onNavigateToReport={() => setScreen('report')}
            onUpdateClause={handleUpdateClause}
            onUpdateDocumentNotes={handleUpdateDocumentNotes}
          />
        );

      case 'report':
        if (!activeDoc) {
          setScreen('dashboard');
          return null;
        }
        return (
          <ReportView
            document={activeDoc}
            onBackToWorkspace={() => setScreen('results')}
          />
        );

      case 'review_queue':
        return (
          <ReviewQueueView
            documents={documents}
            onBackToDashboard={() => setScreen('dashboard')}
            onSelectDocument={(doc) => {
              setSelectedDocId(doc.id);
              setScreen('results');
            }}
            onUpdateClause={handleUpdateReviewQueueClause}
          />
        );

      default:
        return <LoginView onLogin={handleLogin} />;
    }
  };

  return (
    <div className="min-h-screen bg-bg-warm flex flex-col justify-between" id="app-root-container">
      {/* Global Application Nav Header, invisible on login or processing */}
      {screen !== 'login' && screen !== 'processing' && (
        <header className="border-b border-border-subtle bg-bg-warm print:hidden" id="app-global-nav">
          <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div 
              className="flex items-center space-x-2.5 cursor-pointer text-ink-dark" 
              onClick={() => setScreen('dashboard')}
              id="nav-logo-group"
            >
              <Shield className="w-5 h-5 text-accent-forest" />
              <h1 className="font-serif text-lg font-bold tracking-tight">Legal Analyzer</h1>
              <span className="font-mono text-[9px] uppercase tracking-wider bg-border-subtle text-ink-muted px-1.5 py-0.5 font-bold">Workspace PRO</span>
            </div>

            {/* Quick Stats Summary */}
            <div className="hidden sm:flex items-center space-x-6 text-xs font-mono text-ink-muted" id="nav-metadata-block">
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-accent-forest"></span>
                <span>DB: Synced</span>
              </span>
              <span>Review Queue: {documents.filter(d => d.status === 'flagged').length} flagged</span>
            </div>
          </div>
        </header>
      )}

      {/* API/Network Error Alert Header */}
      {apiError && (
        <div className="bg-risk-high-bg border-b border-risk-high/20 px-6 py-2 flex items-center justify-between text-xs text-risk-high font-mono print:hidden" id="api-error-banner">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>{apiError}</span>
          </div>
          <button onClick={() => setApiError(null)} className="hover:underline font-bold">Clear</button>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 w-full" id="app-main-content">
        {renderContent()}
      </main>

      {/* Global Footer Block */}
      {screen !== 'login' && screen !== 'processing' && (
        <footer className="border-t border-border-subtle py-6 bg-bg-warm text-center text-xs text-ink-muted font-mono print:hidden" id="app-global-footer">
          <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-3">
            <span>© 2026 Legal Analyzer Advisory Labs • All rights reserved.</span>
            <div className="flex space-x-4">
              <span className="hover:text-ink-dark cursor-pointer">Protocol Status: Certified</span>
              <span>•</span>
              <span className="hover:text-ink-dark cursor-pointer">Sovereign Data Storage</span>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
}

