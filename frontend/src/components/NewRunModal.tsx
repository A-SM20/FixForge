import { useState } from 'react';
import { 
  X, 
  Sparkles, 
  AlertCircle, 
  Loader2, 
  ArrowRight, 
  Zap,
  GitBranch
} from 'lucide-react';
import { createRun } from '../lib/api';

interface NewRunModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRunCreated: (runId: string) => void;
}

const PRESETS = [
  {
    name: 'Pallets / Flask: Blueprint URL default error',
    repo: 'https://github.com/pallets/flask',
    issue: 'https://github.com/pallets/flask/issues/5239',
    badge: 'Flask',
  },
  {
    name: 'PSF / Requests: Timeout None on urllib3 v2',
    repo: 'https://github.com/psf/requests',
    issue: 'https://github.com/psf/requests/issues/6443',
    badge: 'Requests',
  },
  {
    name: 'Encode / HTTPX: Content-Length redirect leak',
    repo: 'https://github.com/encode/httpx',
    issue: 'https://github.com/encode/httpx/issues/2890',
    badge: 'HTTPX',
  },
  {
    name: 'FastAPI: Query default parameter optionality',
    repo: 'https://github.com/fastapi/fastapi',
    issue: 'https://github.com/fastapi/fastapi/issues/11244',
    badge: 'FastAPI',
  },
];

export const NewRunModal: React.FC<NewRunModalProps> = ({ isOpen, onClose, onRunCreated }) => {
  const [repoUrl, setRepoUrl] = useState('');
  const [issueUrl, setIssueUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim() || !issueUrl.trim()) {
      setError('Please provide both GitHub repository URL and Issue URL');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const run = await createRun({ repo_url: repoUrl.trim(), issue_url: issueUrl.trim() });
      onClose();
      onRunCreated(run.id);
    } catch (err: any) {
      setError(err.message || 'Failed to trigger agent run');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPreset = (preset: typeof PRESETS[0]) => {
    setRepoUrl(preset.repo);
    setIssueUrl(preset.issue);
    setError(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-xl overflow-hidden shadow-2xl">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-800 bg-slate-950/40">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center text-slate-950 shadow-md shadow-emerald-500/20">
              <Sparkles className="w-5 h-5 stroke-[2.5]" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Trigger Autonomous Bug-Fix Run</h2>
              <p className="text-xs text-slate-400">Spawn sandboxed agent loop to locate, patch, and test code</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6">
          {/* Quick Presets */}
          <div>
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <span>Or Choose a 1-Click Benchmark Sample</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {PRESETS.map((preset, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSelectPreset(preset)}
                  className="flex flex-col text-left p-3 rounded-xl bg-slate-950/60 hover:bg-slate-800/80 border border-slate-800/80 hover:border-slate-700 transition-all text-xs group"
                >
                  <div className="flex items-center justify-between w-full mb-1">
                    <span className="font-semibold text-slate-200 group-hover:text-emerald-400 transition-colors">
                      {preset.badge}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">Click to fill</span>
                  </div>
                  <p className="text-slate-400 line-clamp-1">{preset.name}</p>
                </button>
              ))}
            </div>
          </div>

          <hr className="border-slate-800/80" />

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                GitHub Repository URL
              </label>
              <div className="relative">
                <GitBranch className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                <input
                  type="url"
                  placeholder="https://github.com/pallets/flask"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-600 outline-none transition-all"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                GitHub Issue URL
              </label>
              <input
                type="url"
                placeholder="https://github.com/pallets/flask/issues/1234"
                value={issueUrl}
                onChange={(e) => setIssueUrl(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-600 outline-none transition-all"
                required
              />
            </div>

            {/* Submission */}
            <div className="pt-2 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200 rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-slate-950 bg-gradient-to-r from-emerald-400 to-cyan-400 hover:from-emerald-300 hover:to-cyan-300 shadow-lg shadow-emerald-500/20 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Launching Agent...</span>
                  </>
                ) : (
                  <>
                    <span>Start Bug-Fix Agent</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
