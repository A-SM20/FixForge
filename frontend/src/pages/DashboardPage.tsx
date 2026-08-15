import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  PlusCircle, 
  Search, 
  Trash2, 
  ArrowUpRight, 
  Clock, 
  DollarSign, 
  Layers, 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  RefreshCw,
  ArrowRight
} from 'lucide-react';
import { fetchRuns, deleteRun } from '../lib/api';
import type { RunListItem } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';

interface DashboardPageProps {
  onSelectRun: (runId: string) => void;
  onOpenNewRun: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onSelectRun, onOpenNewRun }) => {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState('');
  const queryClient = useQueryClient();

  // TanStack Query for runs list with 3s auto-poll
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['runs', statusFilter],
    queryFn: () => fetchRuns(1, 50, statusFilter),
    refetchInterval: 3000,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteRun(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
  });

  const runs: RunListItem[] = data?.items || [];

  // Filter by search
  const filteredRuns = runs.filter(run => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return run.repo_url.toLowerCase().includes(q) || run.issue_url.toLowerCase().includes(q) || run.id.includes(q);
  });

  // Calculate metrics
  const totalRuns = runs.length;
  const successRuns = runs.filter(r => r.status === 'success').length;
  const successRate = totalRuns > 0 ? ((successRuns / totalRuns) * 100).toFixed(0) : '0';
  const totalCost = runs.reduce((acc, r) => acc + (r.total_cost || 0), 0);
  const avgCost = totalRuns > 0 ? (totalCost / totalRuns).toFixed(3) : '0.000';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 space-y-10">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-white/10 pb-6">
        <div>
          <div className="text-xs font-mono uppercase tracking-widest text-[#D4FF00] font-semibold mb-2">
            Telemetry & Execution
          </div>
          <h1 className="editorial-serif text-4xl sm:text-5xl text-white font-normal leading-tight">
            Autonomous Runs Dashboard
          </h1>
          <p className="text-sm text-neutral-400 font-light mt-1">
            Real-time state transitions, token cost telemetry, and verified pull request generation.
          </p>
        </div>

        <button
          onClick={onOpenNewRun}
          className="btn-lime px-6 py-3 rounded-full text-xs font-bold flex items-center gap-2 shadow-xl shadow-[#D4FF00]/20 active:scale-95 text-black self-start sm:self-auto"
        >
          <PlusCircle className="w-4 h-4 stroke-[2.5]" />
          <span>New Fix Run</span>
        </button>
      </div>

      {/* Top Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-6 rounded-3xl bg-black/40 border border-white/10 backdrop-blur-xl shadow-xl">
          <div className="flex items-center justify-between text-neutral-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Total Agent Runs</span>
            <Layers className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-3xl font-extrabold text-white font-sans">{totalRuns}</div>
          <p className="text-xs text-neutral-500 mt-1">Autonomous bug fix sessions</p>
        </div>

        <div className="p-6 rounded-3xl bg-black/40 border border-white/10 backdrop-blur-xl shadow-xl">
          <div className="flex items-center justify-between text-neutral-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Resolution Rate</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-400 font-sans">{successRate}%</div>
          <p className="text-xs text-neutral-500 mt-1">{successRuns} of {totalRuns} tasks resolved</p>
        </div>

        <div className="p-6 rounded-3xl bg-black/40 border border-white/10 backdrop-blur-xl shadow-xl">
          <div className="flex items-center justify-between text-neutral-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Average Cost / Run</span>
            <DollarSign className="w-4 h-4 text-[#D4FF00]" />
          </div>
          <div className="text-3xl font-extrabold text-[#D4FF00] font-mono">${avgCost}</div>
          <p className="text-xs text-neutral-500 mt-1">Token usage & inference</p>
        </div>

        <div className="p-6 rounded-3xl bg-black/40 border border-white/10 backdrop-blur-xl shadow-xl">
          <div className="flex items-center justify-between text-neutral-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Sandbox Mode</span>
            <Clock className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-3xl font-extrabold text-indigo-300 font-sans">100%</div>
          <p className="text-xs text-neutral-500 mt-1">Ephemeral container isolation</p>
        </div>
      </div>

      {/* Control Bar: Search & Status Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 bg-black/40 p-4 rounded-2xl border border-white/10 backdrop-blur-xl">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-neutral-500 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search by repo or issue URL..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white/5 border border-white/10 focus:border-[#D4FF00] focus:ring-1 focus:ring-[#D4FF00] rounded-full pl-10 pr-4 py-2 text-xs text-white placeholder-neutral-500 outline-none transition-all"
          />
        </div>

        {/* Status Filters & Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {['all', 'running', 'success', 'failed'].map((st) => {
            const isSelected = st === 'all' ? !statusFilter : statusFilter === st;
            return (
              <button
                key={st}
                onClick={() => setStatusFilter(st === 'all' ? undefined : st)}
                className={`px-4 py-1.5 rounded-full text-xs font-semibold capitalize transition-all ${
                  isSelected
                    ? 'bg-[#D4FF00] text-black shadow-md shadow-[#D4FF00]/20'
                    : 'text-neutral-400 hover:text-white hover:bg-white/5 border border-white/10'
                }`}
              >
                {st}
              </button>
            );
          })}

          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-2 rounded-full text-neutral-400 hover:text-white bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
            title="Refresh runs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Runs Table */}
      <div className="bg-black/40 border border-white/10 rounded-3xl overflow-hidden shadow-2xl backdrop-blur-xl">
        {isLoading ? (
          <div className="p-16 text-center text-neutral-400 space-y-3">
            <Loader2 className="w-8 h-8 mx-auto animate-spin text-[#D4FF00]" />
            <p className="text-sm font-medium">Loading agent runs...</p>
          </div>
        ) : error ? (
          <div className="p-16 text-center text-rose-400 space-y-2">
            <XCircle className="w-8 h-8 mx-auto" />
            <p className="text-sm font-semibold">Failed to fetch runs</p>
            <p className="text-xs text-neutral-500">{(error as any)?.message}</p>
          </div>
        ) : filteredRuns.length === 0 ? (
          <div className="p-20 text-center space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 text-neutral-400 flex items-center justify-center mx-auto">
              <Layers className="w-7 h-7" />
            </div>
            <div className="space-y-1">
              <h3 className="text-lg font-semibold text-white">No agent runs found</h3>
              <p className="text-xs text-neutral-400 max-w-sm mx-auto font-light">
                Trigger a new run with an issue and repo URL to let the agent start fixing bugs.
              </p>
            </div>
            <button
              onClick={onOpenNewRun}
              className="btn-lime px-6 py-2.5 rounded-full text-xs font-bold inline-flex items-center gap-2 shadow-lg text-black"
            >
              <span>Launch First Run</span>
              <ArrowRight className="w-3.5 h-3.5 stroke-[2.5]" />
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-white/5 text-neutral-400 border-b border-white/10 uppercase tracking-wider font-semibold text-[10px]">
                <tr>
                  <th className="px-6 py-4">Status & State</th>
                  <th className="px-6 py-4">Repository / Issue</th>
                  <th className="px-6 py-4">Iterations</th>
                  <th className="px-6 py-4">Cost (USD)</th>
                  <th className="px-6 py-4">Created At</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 font-mono">
                {filteredRuns.map((run) => {
                  const repoName = run.repo_url.replace('https://github.com/', '');
                  const issueNum = run.issue_url.split('/').pop();

                  return (
                    <tr
                      key={run.id}
                      onClick={() => onSelectRun(run.id)}
                      className="hover:bg-white/5 cursor-pointer transition-colors group"
                    >
                      {/* Status */}
                      <td className="px-6 py-4">
                        <div className="space-y-1 font-sans">
                          <StatusBadge status={run.status} size="sm" />
                          <div className="text-[11px] text-neutral-500 font-mono">
                            {run.state}
                          </div>
                        </div>
                      </td>

                      {/* Repo & Issue */}
                      <td className="px-6 py-4 font-sans">
                        <div className="font-semibold text-neutral-200 group-hover:text-[#D4FF00] transition-colors flex items-center gap-1.5">
                          <span>{repoName}</span>
                          <span className="text-xs text-neutral-500 font-mono">#{issueNum}</span>
                        </div>
                        <div className="text-xs text-neutral-500 font-mono truncate max-w-xs">
                          {run.id}
                        </div>
                      </td>

                      {/* Iterations */}
                      <td className="px-6 py-4 text-neutral-300">
                        <span className="font-bold text-emerald-400">{run.iteration_count}</span>
                        <span className="text-neutral-600"> / 5</span>
                      </td>

                      {/* Cost */}
                      <td className="px-6 py-4 text-[#D4FF00]">
                        ${(run.total_cost || 0).toFixed(4)}
                      </td>

                      {/* Created */}
                      <td className="px-6 py-4 text-neutral-500 text-[11px]">
                        {new Date(run.created_at).toLocaleString()}
                      </td>

                      {/* Actions */}
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => onSelectRun(run.id)}
                            className="p-2 rounded-full text-neutral-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
                            title="View Run Details"
                          >
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => {
                              if (confirm('Delete this run record?')) {
                                deleteMutation.mutate(run.id);
                              }
                            }}
                            className="p-2 rounded-full text-neutral-500 hover:text-rose-400 bg-white/5 hover:bg-rose-950/30 border border-white/10 transition-colors"
                            title="Delete Run"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
