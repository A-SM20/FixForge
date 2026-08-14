import { 
  ShieldCheck, 
  ArrowRight, 
  Sparkles,
  Lock,
  BarChart3
} from 'lucide-react';

interface LandingPageProps {
  onStartRun: () => void;
  onViewDashboard: () => void;
  onViewEval: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onStartRun, onViewDashboard, onViewEval }) => {
  return (
    <div className="space-y-20 pb-16">
      {/* Hero Section */}
      <section className="relative pt-12 pb-8 overflow-hidden text-center max-w-5xl mx-auto px-4">
        {/* Glow backdrop */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-gradient-to-tr from-emerald-500/15 via-cyan-500/15 to-indigo-500/15 blur-3xl rounded-full -z-10 pointer-events-none" />

        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-900/90 border border-slate-700/80 shadow-inner mb-6 text-xs text-slate-300">
          <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
          <span>Production-Grade Autonomous Bug Fixing & PR Agent</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight sm:leading-tight">
          From GitHub Issue to Verified PR,{' '}
          <span className="bg-gradient-to-r from-emerald-400 via-cyan-400 to-indigo-400 bg-clip-text text-transparent">
            100% Autonomously
          </span>
        </h1>

        <p className="mt-6 text-lg sm:text-xl text-slate-400 max-w-3xl mx-auto leading-relaxed">
          FixForge reads issues, locates affected files via keyword indexing, synthesizes precise unified diffs, runs test suites inside ephemeral isolated Docker sandboxes, and iterates until passing.
        </p>

        {/* CTA buttons */}
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <button
            onClick={onStartRun}
            className="flex items-center gap-2.5 px-6 py-3.5 rounded-2xl font-bold text-slate-950 bg-gradient-to-r from-emerald-400 to-cyan-400 hover:from-emerald-300 hover:to-cyan-300 shadow-xl shadow-emerald-500/25 active:scale-95 transition-all text-base"
          >
            <span>Launch Bug Fix Run</span>
            <ArrowRight className="w-5 h-5 stroke-[2.5]" />
          </button>

          <button
            onClick={onViewDashboard}
            className="flex items-center gap-2 px-6 py-3.5 rounded-2xl font-semibold text-slate-200 bg-slate-900/90 hover:bg-slate-800 border border-slate-700/80 hover:text-white transition-all text-base"
          >
            <span>View Past Runs</span>
          </button>

          <button
            onClick={onViewEval}
            className="flex items-center gap-2 px-6 py-3.5 rounded-2xl font-semibold text-slate-300 bg-slate-900/40 hover:bg-slate-800/80 border border-slate-800 hover:text-white transition-all text-base"
          >
            <BarChart3 className="w-4 h-4 text-indigo-400" />
            <span>SWE Benchmark</span>
          </button>
        </div>
      </section>

      {/* Architecture Highlights Banner */}
      <section className="max-w-6xl mx-auto px-4">
        <div className="bg-gradient-to-b from-slate-900/90 to-slate-950/90 border border-slate-800 rounded-3xl p-8 backdrop-blur-xl shadow-2xl">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <h2 className="text-2xl font-bold text-white tracking-tight">
              Deterministic 5-State Machine Architecture
            </h2>
            <p className="text-sm text-slate-400 mt-2">
              Unlike unpredictable monolithic ReAct loops, FixForge enforces strict state boundaries with zero raw shell access.
            </p>
          </div>

          {/* Workflow Diagram */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/90 flex flex-col justify-between">
              <div>
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold font-mono text-sm mb-3">
                  01
                </div>
                <h4 className="font-semibold text-white text-sm">READ_ISSUE</h4>
                <p className="text-xs text-slate-400 mt-1">
                  Fetches issue title, body, and error logs via GitHub API.
                </p>
              </div>
              <div className="mt-4 text-[11px] text-emerald-400/90 font-mono">PyGithub API</div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/90 flex flex-col justify-between">
              <div>
                <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center font-bold font-mono text-sm mb-3">
                  02
                </div>
                <h4 className="font-semibold text-white text-sm">LOCATE_CODE</h4>
                <p className="text-xs text-slate-400 mt-1">
                  Targeted keyword search using ripgrep (`rg`) & file reading.
                </p>
              </div>
              <div className="mt-4 text-[11px] text-cyan-400/90 font-mono">Ripgrep Indexer</div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/90 flex flex-col justify-between">
              <div>
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold font-mono text-sm mb-3">
                  03
                </div>
                <h4 className="font-semibold text-white text-sm">GENERATE_PATCH</h4>
                <p className="text-xs text-slate-400 mt-1">
                  Generates unified diff; validated via `git apply --check`.
                </p>
              </div>
              <div className="mt-4 text-[11px] text-indigo-400/90 font-mono">Git Apply Safety</div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/90 flex flex-col justify-between">
              <div>
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center font-bold font-mono text-sm mb-3">
                  04
                </div>
                <h4 className="font-semibold text-white text-sm">RUN_TESTS</h4>
                <p className="text-xs text-slate-400 mt-1">
                  Executes pytest suite in an ephemeral container (0 network).
                </p>
              </div>
              <div className="mt-4 text-[11px] text-amber-400/90 font-mono">Docker Sandbox</div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/90 flex flex-col justify-between">
              <div>
                <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center font-bold font-mono text-sm mb-3">
                  05
                </div>
                <h4 className="font-semibold text-white text-sm">OPEN_PR</h4>
                <p className="text-xs text-slate-400 mt-1">
                  Pushes branch and creates verified GitHub Pull Request.
                </p>
              </div>
              <div className="mt-4 text-[11px] text-purple-400/90 font-mono">Verified Fix</div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Pillar Cards */}
      <section className="max-w-6xl mx-auto px-4 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all">
          <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center mb-4">
            <Lock className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Zero Shell Access Sandbox</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            The LLM has exactly 5 function-calling tools. Test execution is confined to ephemeral Docker containers with <code className="text-xs bg-slate-800 px-1 py-0.5 rounded text-cyan-300">network_mode="none"</code>, 1GB RAM cap, and 1 CPU quota.
          </p>
        </div>

        <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-4">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Git Apply Patch Guard</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            Avoids hallucinated full-file overwrites. Patches are required in strict unified diff format and checked dry-run with <code className="text-xs bg-slate-800 px-1 py-0.5 rounded text-emerald-300">git apply --check</code> so bad diffs fail loudly.
          </p>
        </div>

        <div className="p-6 rounded-3xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all">
          <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mb-4">
            <BarChart3 className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Structured Postgres Telemetry</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            Every LLM invocation and tool call logs prompt/completion tokens, latency ms, and exact USD cost directly to relational tables for transparent auditability.
          </p>
        </div>
      </section>
    </div>
  );
};
