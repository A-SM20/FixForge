import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Navbar } from './components/Navbar';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { RunDetailPage } from './pages/RunDetailPage';
import { EvalPage } from './pages/EvalPage';
import { NewRunModal } from './components/NewRunModal';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export function FixForgeApp() {
  const [activeTab, setActiveTab] = useState<'landing' | 'dashboard' | 'eval'>('landing');
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [isNewRunModalOpen, setIsNewRunModalOpen] = useState(false);

  const handleOpenRun = (runId: string) => {
    setSelectedRunId(runId);
  };

  const handleBackToDashboard = () => {
    setSelectedRunId(null);
    setActiveTab('dashboard');
  };

  const handleRunCreated = (runId: string) => {
    setSelectedRunId(runId);
  };

  return (
    <div className="min-h-screen bg-[#0b0f17] text-slate-100 flex flex-col selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setSelectedRunId(null);
          setActiveTab(tab);
        }}
        onOpenNewRun={() => setIsNewRunModalOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1">
        {selectedRunId ? (
          <RunDetailPage runId={selectedRunId} onBack={handleBackToDashboard} />
        ) : activeTab === 'landing' ? (
          <LandingPage
            onStartRun={() => setIsNewRunModalOpen(true)}
            onViewDashboard={() => setActiveTab('dashboard')}
            onViewEval={() => setActiveTab('eval')}
          />
        ) : activeTab === 'dashboard' ? (
          <DashboardPage
            onSelectRun={handleOpenRun}
            onOpenNewRun={() => setIsNewRunModalOpen(true)}
          />
        ) : (
          <EvalPage />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950/60 py-6 px-4 text-center text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>FixForge &mdash; Autonomous AI Bug-Fix & PR Engine</span>
          <span className="text-slate-600">FastAPI &bull; Docker Sandbox &bull; React &bull; Tailwind &bull; TanStack Query</span>
        </div>
      </footer>

      {/* New Run Modal */}
      <NewRunModal
        isOpen={isNewRunModalOpen}
        onClose={() => setIsNewRunModalOpen(false)}
        onRunCreated={handleRunCreated}
      />
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <FixForgeApp />
    </QueryClientProvider>
  );
}
