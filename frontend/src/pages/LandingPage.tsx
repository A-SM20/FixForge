import { ArrowRight } from 'lucide-react';

interface LandingPageProps {
  onStartRun: () => void;
  onViewDashboard: () => void;
  onViewEval: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onStartRun, onViewDashboard, onViewEval }) => {
  return (
    <div className="space-y-24 pb-20 overflow-hidden">
      {/* 1. HERO SECTION WITH IMG1.JPG BACKGROUND */}
      <section className="relative min-h-[92vh] flex flex-col justify-between pt-12 pb-16 px-4 sm:px-8 max-w-[1400px] mx-auto">
        {/* Background Image Container with dark gradient vignettes */}
        <div className="absolute inset-0 -z-10 rounded-[32px] sm:rounded-[48px] overflow-hidden border border-white/10 shadow-2xl">
          <img 
            src="/img1.jpg" 
            alt="FixForge Landscape" 
            className="w-full h-full object-cover object-center scale-105 transform brightness-[0.82] contrast-[1.08]"
          />
          {/* Subtle cinematic gradient overlays */}
          <div className="absolute inset-0 bg-gradient-to-r from-black/75 via-black/45 to-black/20" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#080c14] via-transparent to-black/40" />
        </div>

        {/* Hero Top / Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center pt-8 sm:pt-14 px-4 sm:px-8">
          {/* Left Column: Editorial Headline & Copy */}
          <div className="lg:col-span-6 space-y-6 text-left">
            <h1 className="editorial-serif text-5xl sm:text-7xl font-normal text-white leading-[1.05] tracking-tight">
              Autonomous QA & bug-fixing for engineering teams
            </h1>

            <p className="text-base sm:text-lg text-neutral-300 font-light max-w-lg leading-relaxed">
              Your definition of quality is the only one that matters. FixForge is the autonomous state-machine agent built around it.
            </p>

            <div className="pt-2 flex flex-wrap items-center gap-4">
              <button
                onClick={onStartRun}
                className="btn-lime px-7 py-3.5 rounded-full text-sm font-bold flex items-center gap-2.5 shadow-xl shadow-[#D4FF00]/25 active:scale-95 text-black"
              >
                <span>Launch Fix Run</span>
                <ArrowRight className="w-4 h-4 stroke-[2.5]" />
              </button>

              <button
                onClick={onViewDashboard}
                className="px-6 py-3.5 rounded-full text-sm font-medium text-white bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/15 transition-all"
              >
                <span>View Live Dashboard</span>
              </button>
            </div>
          </div>

          {/* Right Column: Embedded Glassmorphic Evaluation Dashboard Card */}
          <div className="lg:col-span-6 relative">
            {/* The White Floating Card */}
            <div className="bg-white/95 rounded-2xl sm:rounded-3xl p-6 sm:p-7 shadow-2xl text-slate-900 border border-white/40 backdrop-blur-xl relative overflow-hidden">
              {/* Header Title inside card */}
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-4">
                Support & Agent Evaluation
              </div>

              {/* 3 Metric Columns */}
              <div className="grid grid-cols-3 gap-4 pb-5 border-b border-slate-200">
                <div>
                  <div className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
                    951
                  </div>
                  <p className="text-[11px] text-slate-500 font-medium mt-0.5">Issues Scored</p>
                </div>
                <div>
                  <div className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
                    24
                  </div>
                  <p className="text-[11px] text-slate-500 font-medium mt-0.5">Need attention</p>
                </div>
                <div>
                  <div className="text-3xl sm:text-4xl font-extrabold text-emerald-600 tracking-tight">
                    80%
                  </div>
                  <p className="text-[11px] text-slate-500 font-medium mt-0.5">Avg Quality Score</p>
                </div>
              </div>

              {/* Table Preview */}
              <div className="mt-4 overflow-x-auto text-xs">
                <table className="w-full text-left">
                  <thead className="text-[10px] text-slate-400 uppercase font-semibold border-b border-slate-100 pb-2">
                    <tr>
                      <th className="pb-2 font-medium">Agent</th>
                      <th className="pb-2 font-medium">Interaction / Task</th>
                      <th className="pb-2 text-right font-medium">Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    <tr className="hover:bg-slate-50 transition-colors">
                      <td className="py-2.5 font-medium text-slate-800 flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-[10px]">
                          JJ
                        </div>
                        <span>Flask Runner</span>
                      </td>
                      <td className="py-2.5 text-slate-500 font-mono text-[11px]">
                        ID #174923487102739
                      </td>
                      <td className="py-2.5 text-right">
                        <span className="bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded text-[11px]">
                          89
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-slate-50 transition-colors">
                      <td className="py-2.5 font-medium text-slate-800 flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-cyan-100 text-cyan-700 flex items-center justify-center font-bold text-[10px]">
                          SM
                        </div>
                        <span>Requests Timeout</span>
                      </td>
                      <td className="py-2.5 text-slate-500 font-mono text-[11px]">
                        ID #589004627102458
                      </td>
                      <td className="py-2.5 text-right">
                        <span className="bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded text-[11px]">
                          100
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-slate-50 transition-colors">
                      <td className="py-2.5 font-medium text-slate-800 flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-[10px]">
                          PW
                        </div>
                        <span>HTTPX Redirect</span>
                      </td>
                      <td className="py-2.5 text-slate-500 font-mono text-[11px]">
                        ID #762145839102013
                      </td>
                      <td className="py-2.5 text-right">
                        <span className="bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded text-[11px]">
                          96
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-slate-50 transition-colors">
                      <td className="py-2.5 font-medium text-slate-800 flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center font-bold text-[10px]">
                          LS
                        </div>
                        <span>FastAPI Query</span>
                      </td>
                      <td className="py-2.5 text-slate-500 font-mono text-[11px]">
                        ID #301478652109841
                      </td>
                      <td className="py-2.5 text-right">
                        <span className="bg-amber-100 text-amber-800 font-bold px-2 py-0.5 rounded text-[11px]">
                          68
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Decorative Lime Ribbon Trail */}
              <div className="absolute -bottom-6 -right-6 pointer-events-none opacity-85">
                <svg width="220" height="120" viewBox="0 0 220 120" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M10 110C60 90 120 120 180 30C200 -5 220 10 220 10" stroke="#D4FF00" strokeWidth="8" strokeLinecap="round"/>
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Logo / Client Strip */}
        <div className="pt-12 px-6 flex flex-wrap items-center justify-between gap-6 border-t border-white/10 text-white/60 font-semibold text-xs tracking-wider uppercase">
          <span className="hover:text-white transition-colors">Pallets / Flask</span>
          <span className="hover:text-white transition-colors">PSF / Requests</span>
          <span className="hover:text-white transition-colors">Encode / HTTPX</span>
          <span className="hover:text-white transition-colors">FastAPI</span>
          <span className="hover:text-white transition-colors">Pydantic</span>
          <span className="hover:text-white transition-colors">Textualize / Rich</span>
          <span className="hover:text-white transition-colors">Docker Sandbox</span>
        </div>
      </section>

      {/* 2. SECOND SECTION: "CLOSE THE LOOP" EDITORIAL SHOWCASE */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 space-y-12">
        <div className="text-left space-y-3">
          <div className="inline-flex items-center gap-2 text-xs font-semibold text-neutral-400 uppercase tracking-wider">
            <span className="w-2 h-2 rounded-full bg-[#D4FF00]" />
            <span>Precision AI for institutional workflows</span>
          </div>
          <h2 className="editorial-serif text-4xl sm:text-6xl text-white font-normal leading-[1.1]">
            <span className="text-neutral-400">Close the loop</span> from customer insight to agent improvement
          </h2>
        </div>

        {/* Two-Column Feature Block */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Left: Atmospheric Card with Blurred Image & Floating Review Pill */}
          <div className="lg:col-span-6 relative rounded-[32px] overflow-hidden border border-white/10 shadow-2xl h-[380px] sm:h-[420px] flex items-center justify-center">
            <img 
              src="/img1.jpg" 
              alt="Feature Background" 
              className="absolute inset-0 w-full h-full object-cover blur-[3px] brightness-75 scale-110"
            />
            <div className="absolute inset-0 bg-black/40" />

            {/* Floating Review Pill Banner */}
            <div className="relative z-10 space-y-4 text-center">
              <div className="bg-white/95 backdrop-blur-xl px-7 py-3 rounded-full shadow-2xl flex items-center gap-4 text-slate-900">
                <span className="text-sm font-semibold">Reviewing scores</span>
                <span className="w-8 h-1 rounded-full bg-rose-400" />
              </div>

              <div className="flex items-center justify-center gap-3">
                <div className="bg-white/90 backdrop-blur-md px-4 py-2 rounded-full shadow-lg flex items-center gap-2 text-slate-800 text-xs font-medium">
                  <div className="w-5 h-5 rounded-full bg-slate-200 flex items-center justify-center font-bold text-[9px]">DS</div>
                  <span>Drake S.</span>
                  <span className="text-slate-400 font-bold ml-1">59%</span>
                </div>
                <div className="bg-white/90 backdrop-blur-md px-4 py-2 rounded-full shadow-lg flex items-center gap-2 text-slate-800 text-xs font-medium border border-emerald-500/30">
                  <div className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-[9px]">CT</div>
                  <span>Camila T.</span>
                  <span className="text-emerald-700 font-bold ml-1">85%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Feature Steps & Details */}
          <div className="lg:col-span-6 space-y-8 text-left pl-0 lg:pl-6">
            <div className="space-y-3 pb-6 border-l-2 border-[#D4FF00] pl-6">
              <h3 className="text-xl font-bold text-white">Review 100% of interactions in seconds.</h3>
              <p className="text-sm text-neutral-400 leading-relaxed">
                See the full picture of customer interactions across phone, live chat, video, and email support, at a glance.
              </p>
              <div className="pt-2">
                <button 
                  onClick={onStartRun}
                  className="btn-lime px-5 py-2.5 rounded-full text-xs font-bold flex items-center gap-2 shadow-lg text-black"
                >
                  <span>Book a Demo</span>
                  <ArrowRight className="w-3.5 h-3.5 stroke-[2.5]" />
                </button>
              </div>
            </div>

            <div 
              onClick={onViewEval} 
              className="space-y-2 pl-6 border-l-2 border-white/10 opacity-70 hover:opacity-100 transition-opacity cursor-pointer"
            >
              <h4 className="text-base font-semibold text-neutral-300">Generate custom trainings for agents.</h4>
              <p className="text-xs text-neutral-500">Autonomous synthesis of test cases and targeted bug-fix patches.</p>
            </div>

            <div 
              onClick={onViewDashboard} 
              className="space-y-2 pl-6 border-l-2 border-white/10 opacity-70 hover:opacity-100 transition-opacity cursor-pointer"
            >
              <h4 className="text-base font-semibold text-neutral-300">Watch customer satisfaction increase.</h4>
              <p className="text-xs text-neutral-500">Fast, verified PR delivery without engineering bottlenecks.</p>
            </div>
          </div>
        </div>
      </section>

      {/* 3. WARM CREAM CTA BANNER ("We know the terrain. You know the destination.") */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="bg-[#F6F4ED] text-[#1A1A1A] rounded-[36px] sm:rounded-[44px] p-8 sm:p-14 flex flex-col md:flex-row items-start md:items-center justify-between gap-8 shadow-2xl relative overflow-hidden">
          {/* Subtle dotted matrix pattern in background */}
          <div className="absolute right-0 bottom-0 opacity-10 pointer-events-none">
            <svg width="240" height="240" viewBox="0 0 240 240" fill="currentColor">
              <pattern id="dotPattern" x="0" y="0" width="16" height="16" patternUnits="userSpaceOnUse">
                <circle cx="2" cy="2" r="1.5" />
              </pattern>
              <rect width="240" height="240" fill="url(#dotPattern)" />
            </svg>
          </div>

          <div className="space-y-3 max-w-xl z-10">
            <h2 className="editorial-serif text-4xl sm:text-6xl text-[#1A1A1A] font-normal leading-[1.05] tracking-tight">
              We know the terrain.<br />You know the destination.
            </h2>
            <p className="text-sm text-neutral-600 font-sans font-normal pt-1">
              Start your first autonomous bug repair session with ephemeral Docker sandboxing today.
            </p>
          </div>

          <div className="z-10 flex-shrink-0">
            <button
              onClick={onStartRun}
              className="btn-lime px-8 py-4 rounded-full text-sm font-bold flex items-center gap-2.5 shadow-xl shadow-black/10 active:scale-95 text-black"
            >
              <span>Book a Demo</span>
              <ArrowRight className="w-4 h-4 stroke-[2.5]" />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};
