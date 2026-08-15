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
    <div className="min-h-screen bg-[#080c14] text-slate-100 flex flex-col selection:bg-[#D4FF00]/30 selection:text-[#D4FF00] relative font-sans">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setSelectedRunId(null);
          setActiveTab(tab);
        }}
        onOpenNewRun={() => setIsNewRunModalOpen(true)}
      />

      {/* Main Content Area (Footer intentionally omitted per design requirement) */}
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

      {/* New Run Trigger Modal */}
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
