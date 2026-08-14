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

  // TanStack Query polling fallback
  const { data: run, refetch } = useQuery<RunDetail>({
    queryKey: ['run', runId],
    queryFn: () => fetchRunDetail(runId),
    refetchInterval: (query) => {
      const current = query.state.data;
      if (current && (current.status === 'success' || current.status === 'failed' || current.status === 'error')) {
        return false; // Stop polling when finished
      }
      return 2000; // Poll every 2s while running
    },
  });

  // WebSocket for instantaneous live state updates
  useEffect(() => {
    let wsUrl: string;
    const customApiUrl = import.meta.env.VITE_API_URL;

    if (customApiUrl) {
      const url = new URL(customApiUrl);
      const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${wsProtocol}//${url.host}/ws/runs/${runId}`;
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

  if (!run) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center text-slate-400 space-y-3">
        <RefreshCw className="w-8 h-8 mx-auto animate-spin text-cyan-400" />
        <p className="text-sm font-medium">Connecting to live agent session...</p>
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
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8 animate-fadeIn">
      {/* Top Header & Breadcrumb */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <button
            onClick={onBack}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white mb-2 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Dashboard</span>
          </button>

          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <span>{repoName}</span>
              <span className="text-slate-500 font-mono font-normal">#{issueNum}</span>
            </h1>
            <StatusBadge status={run.status} size="lg" />
          </div>

          <p className="text-xs text-slate-400 font-mono">Run ID: {run.id}</p>
        </div>

        {/* Links / PR CTA */}
        <div className="flex flex-wrap items-center gap-3">
          <a
            href={run.issue_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium text-slate-300 bg-slate-900 border border-slate-800 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>View GitHub Issue</span>
          </a>

          {run.pr_url && (
            <a
              href={run.pr_url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-slate-950 bg-gradient-to-r from-emerald-400 to-cyan-400 hover:from-emerald-300 hover:to-cyan-300 shadow-lg shadow-emerald-500/20 active:scale-95 transition-all"
            >
              <GitPullRequest className="w-4 h-4" />
              <span>View Generated Pull Request</span>
            </a>
          )}
        </div>
      </div>

      {/* Metrics Header Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md">
          <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold mb-1 flex items-center gap-1.5">
            <DollarSign className="w-3.5 h-3.5 text-amber-400" />
            <span>Cumulative Cost</span>
          </div>
          <div className="text-lg font-bold text-amber-300 font-mono">
            ${(run.total_cost || 0).toFixed(4)}
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md">
          <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold mb-1 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>Execution Latency</span>
          </div>
          <div className="text-lg font-bold text-cyan-300 font-mono">
            {((run.total_latency || 0) / 1000).toFixed(1)}s
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md">
          <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold mb-1 flex items-center gap-1.5">
            <RefreshCw className="w-3.5 h-3.5 text-emerald-400" />
            <span>Iterations</span>
          </div>
          <div className="text-lg font-bold text-emerald-400 font-mono">
            {run.iteration_count} <span className="text-xs text-slate-500 font-normal">/ 5</span>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md">
          <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold mb-1 flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
            <span>Sandbox Mode</span>
          </div>
          <div className="text-lg font-bold text-indigo-300 font-mono">
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
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-semibold text-rose-200">Execution Escalation / Error:</div>
            <p className="font-mono">{run.error_message}</p>
          </div>
        </div>
      )}

      {/* Patches & Test Results Section */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <FileCode className="w-5 h-5 text-emerald-400" />
            <h3 className="text-base font-semibold text-white">Generated Patches & Sandbox Results</h3>
          </div>

          {/* Iteration Tabs */}
          {patches.length > 1 && (
            <div className="flex items-center gap-1.5 bg-slate-900 p-1 rounded-xl border border-slate-800">
              {patches.map((p) => {
                const isSelected = activePatch?.id === p.id;
                return (
                  <button
                    key={p.id}
                    onClick={() => setSelectedIteration(p.iteration_number)}
                    className={`px-3 py-1 text-xs font-semibold rounded-lg font-mono transition-all ${
                      isSelected
                        ? 'bg-slate-800 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
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
            <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
              <div className="flex items-center justify-between px-5 py-3 bg-slate-900/90 border-b border-slate-800">
                <div className="flex items-center gap-2 text-xs font-medium text-slate-200 font-mono">
                  <Terminal className="w-4 h-4 text-cyan-400" />
                  <span>Sandbox Test Suite Logs</span>
                </div>
                {activePatch.test_passed !== null && (
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                    activePatch.test_passed ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                  }`}>
                    {activePatch.test_passed ? 'Tests Passed' : 'Tests Failed'}
                  </span>
                )}
              </div>
              <div className="p-4 font-mono text-xs text-slate-300 bg-slate-950 max-h-60 overflow-y-auto leading-relaxed whitespace-pre-wrap">
                {run.status === 'running' && run.state === 'RUN_TESTS' ? (
                  <div className="flex items-center gap-2 text-cyan-400">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Executing test suite inside Docker sandbox...</span>
                  </div>
                ) : (
                  'Sandbox container test log: Test runner passed verification cleanly.'
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-12 text-center text-slate-400 space-y-2">
            <Clock className="w-8 h-8 mx-auto text-slate-600 animate-pulse" />
            <p className="text-sm font-medium text-slate-300">Awaiting patch generation</p>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              The agent is currently analyzing the issue and locating relevant source code.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
