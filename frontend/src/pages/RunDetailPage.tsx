import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  ArrowLeft, 
  GitPullRequest, 
  ExternalLink, 
  Clock, 
  DollarSign, 
  Cpu, 
  Terminal, 
  AlertTriangle, 
  RefreshCw, 
  FileCode
} from 'lucide-react';
import { fetchRunDetail } from '../lib/api';
import type { RunDetail } from '../lib/api';
import { FSMStepper } from '../components/FSMStepper';
import { StatusBadge } from '../components/StatusBadge';
import { DiffViewer } from '../components/DiffViewer';

interface RunDetailPageProps {
  runId: string;
  onBack: () => void;
}

export const RunDetailPage: React.FC<RunDetailPageProps> = ({ runId, onBack }) => {
  const [selectedIteration, setSelectedIteration] = useState<number | null>(null);

  // TanStack Query polling
  const { data: run, refetch, error, isLoading, isError } = useQuery<RunDetail>({
    queryKey: ['run', runId],
    queryFn: () => fetchRunDetail(runId),
    retry: 3,
    refetchInterval: (query) => {
      const current = query.state.data;
      if (current && (current.status === 'success' || current.status === 'failed' || current.status === 'error')) {
        return false; // Stop polling when finished
      }
      return 1500; // Poll every 1.5s while active
    },
  });

  // WebSocket for instantaneous live state updates (with graceful fallback)
  useEffect(() => {
    let wsUrl: string;
    const customApiUrl = import.meta.env.VITE_API_URL;

    if (customApiUrl) {
      try {
        const url = new URL(customApiUrl);
        const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${wsProtocol}//${url.host}/ws/runs/${runId}`;
      } catch {
        return;
      }
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//${window.location.host}/ws/runs/${runId}`;
    }

    let ws: WebSocket | null = null;

    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload && !payload.error) {
            refetch(); // Refetch complete detail on WS push
          }
        } catch {}
      };
    } catch {}

    return () => {
      if (ws) ws.close();
    };
  }, [runId, refetch]);

  if (isLoading || (!run && !isError)) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-28 text-center text-neutral-400 space-y-4 animate-fadeIn">
        <div className="w-12 h-12 rounded-full bg-[#D4FF00]/10 border border-[#D4FF00]/30 flex items-center justify-center mx-auto text-[#D4FF00]">
          <RefreshCw className="w-6 h-6 animate-spin" />
        </div>
        <div className="space-y-1">
          <p className="text-base font-semibold text-white">Connecting to live agent session...</p>
          <p className="text-xs text-neutral-500 font-mono">Session: {runId}</p>
        </div>
      </div>
    );
  }

  if (isError || !run) {
    return (
      <div className="max-w-xl mx-auto px-4 py-24 text-center space-y-5 animate-fadeIn">
        <div className="w-14 h-14 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
          <AlertTriangle className="w-7 h-7" />
        </div>
        <div className="space-y-1">
          <h2 className="text-xl font-bold text-white">Could Not Load Agent Session</h2>
          <p className="text-xs text-neutral-400 max-w-sm mx-auto">
            {error instanceof Error ? error.message : 'The requested run record could not be found.'}
          </p>
        </div>
        <div className="flex items-center justify-center gap-3 pt-2">
          <button
            onClick={onBack}
            className="px-5 py-2.5 rounded-full text-xs font-semibold text-neutral-300 bg-white/5 hover:bg-white/10 border border-white/10 transition-all"
          >
            Back to Dashboard
          </button>
          <button
            onClick={() => refetch()}
            className="btn-lime px-5 py-2.5 rounded-full text-xs font-bold flex items-center gap-1.5 text-black"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Connection</span>
          </button>
        </div>
      </div>
    );
  }

  const patches = run.patches || [];
  // Default to the latest iteration patch if not explicitly selected
  const activePatch = selectedIteration !== null
    ? patches.find(p => p.iteration_number === selectedIteration)
    : patches[patches.length - 1];

  const repoName = run.repo_url.replace('https://github.com/', '');
  const issueNum = run.issue_url.split('/').pop();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 space-y-10 animate-fadeIn">
      {/* Top Header & Breadcrumb */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-white/10 pb-6">
        <div className="space-y-2">
          <button
            onClick={onBack}
            className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Runs Dashboard</span>
          </button>

          <div className="flex flex-wrap items-center gap-3">
            <h1 className="editorial-serif text-4xl sm:text-5xl font-normal text-white tracking-tight flex items-center gap-2">
              <span>{repoName}</span>
              <span className="text-neutral-500 font-mono font-normal text-2xl sm:text-3xl">#{issueNum}</span>
            </h1>
            <StatusBadge status={run.status} size="lg" />
          </div>

          <p className="text-xs text-neutral-500 font-mono">Session ID: {run.id}</p>
        </div>

        {/* Links / PR CTA */}
        <div className="flex flex-wrap items-center gap-3">
          <a
            href={run.issue_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 px-4 py-2.5 rounded-full text-xs font-medium text-neutral-200 bg-white/5 border border-white/10 hover:bg-white/10 hover:text-white transition-all"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>View GitHub Issue</span>
          </a>

          {run.pr_url && (
            <a
              href={run.pr_url}
              target="_blank"
              rel="noreferrer"
              className="btn-lime flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-bold shadow-xl shadow-[#D4FF00]/20 active:scale-95 text-black"
            >
              <GitPullRequest className="w-4 h-4" />
              <span>View Generated PR</span>
            </a>
          )}
        </div>
      </div>

      {/* Metrics Header Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-5 rounded-3xl bg-black/40 border border-white/10 backdrop-blur-xl">
          <div className="text-[11px] text-neutral-400 uppercase tracking-wider font-semibold mb-1 flex items-center gap-1.5">
            <DollarSign className="w-3.5 h-3.5 text-[#D4FF00]" />
            <span>Cumulative Cost</span>
          </div>
          <div className="text-xl font-extrabold text-[#D4FF00] font-mono">
            ${(run.total_cost || 0).toFixed(4)}
          </div>
        </div>

        <div className="p-5 rounded-3xl bg-black/40 border border-white/10 backdrop-blur-xl">
          <div className="text-[11px] text-neutral-400 uppercase tracking-wider font-semibold mb-1 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>Execution Latency</span>
          </div>
          <div className="text-xl font-extrabold text-cyan-300 font-mono">
            {((run.total_latency || 0) / 1000).toFixed(1)}s
          </div>
        </div>

        <div className="p-5 rounded-3xl bg-black/40 border border-white/10 backdrop-blur-xl">
          <div className="text-[11px] text-neutral-400 uppercase tracking-wider font-semibold mb-1 flex items-center gap-1.5">
            <RefreshCw className="w-3.5 h-3.5 text-emerald-400" />
            <span>Iterations</span>
          </div>
          <div className="text-xl font-extrabold text-emerald-400 font-mono">
            {run.iteration_count} <span className="text-xs text-neutral-500 font-normal">/ 5</span>
          </div>
        </div>

        <div className="p-5 rounded-3xl bg-black/40 border border-white/10 backdrop-blur-xl">
          <div className="text-[11px] text-neutral-400 uppercase tracking-wider font-semibold mb-1 flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
            <span>Sandbox Mode</span>
          </div>
          <div className="text-xl font-extrabold text-indigo-300 font-mono">
            Docker (0-Net)
          </div>
        </div>
      </div>

      {/* State Machine Stepper Component */}
      <FSMStepper 
        currentState={run.state}
        iterationCount={run.iteration_count}
        status={run.status}
      />

      {/* Error Message if Present */}
      {run.error_message && (
        <div className="p-5 rounded-3xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-3 backdrop-blur-xl">
          <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-semibold text-rose-200">Execution Escalation / Error:</div>
            <p className="font-mono">{run.error_message}</p>
          </div>
        </div>
      )}

      {/* Patches & Test Results Section */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-3">
          <div className="flex items-center gap-2">
            <FileCode className="w-5 h-5 text-[#D4FF00]" />
            <h3 className="text-lg font-semibold text-white">Generated Patches & Sandbox Results</h3>
          </div>

          {/* Iteration Tabs */}
          {patches.length > 1 && (
            <div className="flex items-center gap-1.5 bg-black/40 p-1 rounded-full border border-white/10">
              {patches.map((p) => {
                const isSelected = activePatch?.id === p.id;
                return (
                  <button
                    key={p.id}
                    onClick={() => setSelectedIteration(p.iteration_number)}
                    className={`px-4 py-1 text-xs font-semibold rounded-full font-mono transition-all ${
                      isSelected
                        ? 'bg-[#D4FF00] text-black shadow-md'
                        : 'text-neutral-400 hover:text-white'
                    }`}
                  >
                    Iteration #{p.iteration_number}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Patch Viewer */}
        {activePatch ? (
          <div className="space-y-6">
            <DiffViewer 
              diff={activePatch.diff_preview} 
              title={`Unified Diff (Iteration #${activePatch.iteration_number})`} 
            />

            {/* Test Output Console */}
            <div className="bg-black/60 border border-white/10 rounded-3xl overflow-hidden shadow-2xl backdrop-blur-xl">
              <div className="flex items-center justify-between px-6 py-3.5 bg-white/5 border-b border-white/10">
                <div className="flex items-center gap-2 text-xs font-medium text-neutral-200 font-mono">
                  <Terminal className="w-4 h-4 text-cyan-400" />
                  <span>Sandbox Test Suite Logs</span>
                </div>
                {activePatch.test_passed !== null && (
                  <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${
                    activePatch.test_passed ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                  }`}>
                    {activePatch.test_passed ? 'Tests Passed' : 'Tests Failed'}
                  </span>
                )}
              </div>
              <div className="p-5 font-mono text-xs text-neutral-300 max-h-60 overflow-y-auto leading-relaxed whitespace-pre-wrap">
                {run.status === 'running' && run.state === 'RUN_TESTS' ? (
                  <div className="flex items-center gap-2 text-cyan-400">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Executing test suite inside Docker sandbox...</span>
                  </div>
                ) : (
                  activePatch.test_result || 'No test output available.'
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-black/40 border border-white/10 rounded-3xl p-14 text-center text-neutral-400 space-y-2 backdrop-blur-xl">
            <Clock className="w-8 h-8 mx-auto text-neutral-600 animate-pulse" />
            <p className="text-base font-medium text-neutral-200">Awaiting patch generation</p>
            <p className="text-xs text-neutral-500 max-w-sm mx-auto font-light">
              The agent is currently analyzing the issue and locating relevant source code.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
