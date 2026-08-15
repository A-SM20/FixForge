import { 
  Bot, 
  LayoutDashboard, 
  LineChart, 
  Sparkles,
  GitBranch,
  ArrowRight
} from 'lucide-react';

interface NavbarProps {
  activeTab: 'landing' | 'dashboard' | 'eval';
  setActiveTab: (tab: 'landing' | 'dashboard' | 'eval') => void;
  onOpenNewRun: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab, onOpenNewRun }) => {
  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-black/40 border-b border-white/10 px-6 py-3.5 transition-all">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Left: Brand / Logo */}
        <div 
          onClick={() => setActiveTab('landing')}
          className="flex items-center gap-3 cursor-pointer group select-none"
        >
          <div className="w-9 h-9 rounded-xl bg-white/10 border border-white/20 flex items-center justify-center text-white group-hover:scale-105 group-hover:bg-white/15 transition-all">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight text-white font-sans">
                FixForge
              </span>
              <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-[#D4FF00]/15 text-[#D4FF00] border border-[#D4FF00]/30">
                Agent
              </span>
            </div>
          </div>
        </div>

        {/* Center: Navigation Links */}
        <nav className="hidden md:flex items-center gap-1 bg-white/5 p-1 rounded-full border border-white/10 backdrop-blur-md">
          <button
            onClick={() => setActiveTab('landing')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium transition-all ${
              activeTab === 'landing'
                ? 'bg-white/15 text-white shadow-sm'
                : 'text-neutral-300 hover:text-white hover:bg-white/5'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-[#D4FF00]" />
            Overview
          </button>

          <button
            onClick={() => setActiveTab('dashboard')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium transition-all ${
              activeTab === 'dashboard'
                ? 'bg-white/15 text-white shadow-sm'
                : 'text-neutral-300 hover:text-white hover:bg-white/5'
            }`}
          >
            <LayoutDashboard className="w-3.5 h-3.5 text-cyan-400" />
            Runs Dashboard
          </button>

          <button
            onClick={() => setActiveTab('eval')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium transition-all ${
              activeTab === 'eval'
                ? 'bg-white/15 text-white shadow-sm'
                : 'text-neutral-300 hover:text-white hover:bg-white/5'
            }`}
          >
            <LineChart className="w-3.5 h-3.5 text-indigo-400" />
            SWE Benchmark
          </button>
        </nav>

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          <a
            href="https://github.com/A-SM20/FixForge"
            target="_blank"
            rel="noreferrer"
            className="hidden sm:flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium text-neutral-300 bg-white/5 hover:bg-white/10 hover:text-white border border-white/10 transition-all"
          >
            <GitBranch className="w-3.5 h-3.5" />
            <span>GitHub</span>
          </a>

          <button
            onClick={onOpenNewRun}
            className="flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold bg-[#D4FF00] hover:bg-[#c2eb00] text-black shadow-lg shadow-[#D4FF00]/20 hover:scale-[1.02] active:scale-95 transition-all"
          >
            <span>Launch Fix Run</span>
            <ArrowRight className="w-3.5 h-3.5 stroke-[2.5]" />
          </button>
        </div>
      </div>
    </header>
  );
};
