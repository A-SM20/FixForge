import React from 'react';
import { 
  FileSearch, 
  SearchCode, 
  Wrench, 
  PlaySquare, 
  GitPullRequest, 
  AlertOctagon, 
  CheckCircle2, 
  ArrowRight,
  RefreshCw
} from 'lucide-react';

interface FSMStepperProps {
  currentState: string;
  iterationCount: number;
  status: string;
}

interface StateStep {
  key: string;
  name: string;
  description: string;
  icon: React.ReactNode;
}

const STEPS: StateStep[] = [
  {
    key: 'READ_ISSUE',
    name: '1. Read Issue',
    description: 'Fetch & parse GitHub issue body',
    icon: <FileSearch className="w-5 h-5" />,
  },
  {
    key: 'LOCATE_CODE',
    name: '2. Locate Code',
    description: 'Ripgrep search & relevant file discovery',
    icon: <SearchCode className="w-5 h-5" />,
  },
  {
    key: 'GENERATE_PATCH',
    name: '3. Generate Patch',
    description: 'LLM synthesis of unified diff',
    icon: <Wrench className="w-5 h-5" />,
  },
  {
    key: 'RUN_TESTS',
    name: '4. Sandboxed Tests',
    description: 'Execute tests in Docker container',
    icon: <PlaySquare className="w-5 h-5" />,
  },
  {
    key: 'OPEN_PR',
    name: '5. Open PR',
    description: 'Create branch & submit Pull Request',
    icon: <GitPullRequest className="w-5 h-5" />,
  },
];

export const FSMStepper: React.FC<FSMStepperProps> = ({ currentState, iterationCount, status }) => {
  const getStepStatus = (stepKey: string, index: number) => {
    const stateOrder = ['READ_ISSUE', 'LOCATE_CODE', 'GENERATE_PATCH', 'RUN_TESTS', 'OPEN_PR'];
    const currentIndex = stateOrder.indexOf(currentState);

    if (status === 'success') {
      return 'completed';
    }
    if (status === 'failed' || status === 'error') {
      if (stepKey === currentState || (currentState === 'ESCALATE' && stepKey === 'RUN_TESTS')) {
        return 'failed';
      }
      if (currentIndex > index) return 'completed';
      return 'pending';
    }

    if (currentState === stepKey) return 'active';
    if (currentIndex > index) return 'completed';
    return 'pending';
  };

  return (
    <div className="w-full bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-md shadow-xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <span>Agent State Machine Workflow</span>
            {status === 'running' && (
              <span className="flex items-center gap-1 text-xs font-mono font-normal text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded-full border border-cyan-500/20">
                <RefreshCw className="w-3 h-3 animate-spin" />
                Live Execution
              </span>
            )}
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Explicit FSM loop: Locate &rarr; Diff &rarr; Test Sandbox &rarr; PR (max 5 iterations)
          </p>
        </div>

        {iterationCount > 0 && (
          <div className="flex items-center gap-2 px-3 py-1 rounded-xl bg-slate-800/80 border border-slate-700/60">
            <span className="text-xs text-slate-400">Loop Iteration:</span>
            <span className="text-sm font-bold text-emerald-400 font-mono">
              #{iterationCount} <span className="text-slate-500 text-xs font-normal">/ 5</span>
            </span>
          </div>
        )}
      </div>

      {/* Stepper Steps Grid */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 relative">
        {STEPS.map((step, idx) => {
          const stepStatus = getStepStatus(step.key, idx);

          let borderBg = 'border-slate-800 bg-slate-950/40 text-slate-500';
          let iconBg = 'bg-slate-900 text-slate-500 border-slate-800';

          if (stepStatus === 'active') {
            borderBg = 'border-cyan-500/50 bg-cyan-950/20 text-cyan-200 ring-1 ring-cyan-500/40 shadow-lg shadow-cyan-500/10';
            iconBg = 'bg-cyan-500 text-slate-950 border-cyan-400 shadow-md shadow-cyan-500/30 animate-pulse';
          } else if (stepStatus === 'completed') {
            borderBg = 'border-emerald-500/30 bg-emerald-950/20 text-slate-300';
            iconBg = 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
          } else if (stepStatus === 'failed') {
            borderBg = 'border-rose-500/50 bg-rose-950/20 text-rose-200';
            iconBg = 'bg-rose-500/20 text-rose-400 border-rose-500/40';
          }

          return (
            <div
              key={step.key}
              className={`flex flex-col p-4 rounded-xl border transition-all duration-300 ${borderBg}`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className={`w-9 h-9 rounded-lg border flex items-center justify-center ${iconBg}`}>
                  {stepStatus === 'completed' ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  ) : (
                    step.icon
                  )}
                </div>
                {idx < STEPS.length - 1 && (
                  <ArrowRight className="hidden md:block w-4 h-4 text-slate-700" />
                )}
              </div>

              <div className="font-semibold text-sm tracking-tight text-white mb-1">
                {step.name}
              </div>
              <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                {step.description}
              </p>

              {/* Loop indicator for RUN_TESTS */}
              {step.key === 'RUN_TESTS' && (
                <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center gap-1.5 text-[11px] text-amber-400/90 font-mono">
                  <RefreshCw className="w-3 h-3" />
                  <span>Loops on test failure</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Escalation banner if escalated */}
      {currentState === 'ESCALATE' && (
        <div className="mt-4 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center gap-3 text-rose-300 text-sm">
          <AlertOctagon className="w-5 h-5 text-rose-400 flex-shrink-0" />
          <div>
            <span className="font-semibold text-rose-200">Human Escalation Triggered: </span>
            The agent exhausted maximum retry iterations without tests passing.
          </div>
        </div>
      )}
    </div>
  );
};
