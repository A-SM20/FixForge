import React, { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import mountainBg from '../assets/img1.jpg';

interface LandingPageProps {
  onStartRun: () => void;
  onViewDashboard: () => void;
  onViewEval?: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onStartRun, onViewDashboard }) => {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div className="relative min-h-[92vh] flex flex-col justify-between overflow-hidden">
      {/* 3D Mountain Atmospheric Background with subtle depth lighting */}
      <div className="absolute inset-0 -z-10 overflow-hidden">
        <img
          src={mountainBg}
          alt="Atmospheric Mountain Backdrop"
          className="w-full h-full object-cover object-[center_35%] scale-100 brightness-[0.88] contrast-[1.12] transition-transform duration-1000 ease-out"
        />
        {/* Subtle cinematic gradient overlays for depth and text legibility */}
        <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/40 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#080c14] via-transparent to-black/30" />
      </div>

      {/* Main Hero Content */}
      <div className="max-w-[1440px] w-full mx-auto px-6 sm:px-12 pt-12 sm:pt-20 pb-8 grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center flex-1">
        {/* Left Column: Editorial Headline & Actions */}
        <div className="lg:col-span-6 space-y-7 text-left z-10">
          <h1 className="editorial-serif text-5xl sm:text-7xl lg:text-8xl font-normal text-white leading-[1.02] tracking-tight drop-shadow-lg">
            Autonomous QA & bug-fixing for engineering teams
          </h1>

          <p className="text-base sm:text-lg text-neutral-300 font-light max-w-lg leading-relaxed drop-shadow">
            Your definition of quality is the only one that matters. FixForge is the autonomous state-machine agent built around it.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-4">
            <button
              onClick={onStartRun}
              className="btn-lime px-8 py-4 rounded-full text-sm font-bold flex items-center gap-2.5 shadow-2xl shadow-[#D4FF00]/30 hover:scale-105 active:scale-95 text-black transition-all"
            >
              <span>Launch Fix Run</span>
              <ArrowRight className="w-4 h-4 stroke-[2.5]" />
            </button>

            <button
              onClick={onViewDashboard}
              className="px-7 py-4 rounded-full text-sm font-medium text-white bg-black/40 hover:bg-black/60 backdrop-blur-xl border border-white/20 hover:border-white/30 transition-all shadow-xl"
            >
              <span>View Live Dashboard</span>
            </button>
          </div>
        </div>

        {/* Right Column: 3D Perspective Floating Evaluation Dashboard Card */}
        <div 
          className="lg:col-span-6 flex justify-center lg:justify-end z-10"
          style={{ perspective: '1200px' }}
        >
          <div
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            style={{
              transform: isHovered
                ? 'rotateY(-2deg) rotateX(1deg) translateY(-8px) scale(1.02)'
                : 'rotateY(-7deg) rotateX(4deg) translateZ(15px)',
              transition: 'transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.5s ease',
            }}
            className="w-full max-w-[540px] bg-white/95 rounded-[32px] p-7 sm:p-8 text-slate-900 border border-white/60 shadow-[0_30px_70px_rgba(0,0,0,0.65)] backdrop-blur-2xl relative overflow-hidden select-none"
          >
            {/* Header inside card */}
            <div className="flex items-center justify-between text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-5">
              <span>Support & Agent Evaluation</span>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            </div>

            {/* 3 Metric Columns */}
            <div className="grid grid-cols-3 gap-4 pb-6 border-b border-slate-200/80">
              <div>
                <div className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight font-sans">
                  951
                </div>
                <p className="text-[11px] text-slate-500 font-medium mt-0.5">Issues Scored</p>
              </div>
              <div>
                <div className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight font-sans">
                  24
                </div>
                <p className="text-[11px] text-slate-500 font-medium mt-0.5">Need attention</p>
              </div>
              <div>
                <div className="text-3xl sm:text-4xl font-extrabold text-emerald-600 tracking-tight font-sans">
                  80%
                </div>
                <p className="text-[11px] text-slate-500 font-medium mt-0.5">Avg Quality Score</p>
              </div>
            </div>

            {/* Live Table Preview */}
            <div className="mt-5 overflow-hidden text-xs">
              <table className="w-full text-left">
                <thead className="text-[10px] text-slate-400 uppercase font-bold border-b border-slate-100 pb-2">
                  <tr>
                    <th className="pb-2.5">Agent</th>
                    <th className="pb-2.5">Interaction / Task</th>
                    <th className="pb-2.5 text-right">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-sans">
                  <tr className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 font-semibold text-slate-800 flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold text-[10px]">
                        JJ
                      </div>
                      <span>Flask Runner</span>
                    </td>
                    <td className="py-3 text-slate-500 font-mono text-[11px]">
                      ID #174923487102739
                    </td>
                    <td className="py-3 text-right">
                      <span className="bg-emerald-100 text-emerald-800 font-extrabold px-2.5 py-1 rounded-md text-[11px]">
                        89
                      </span>
                    </td>
                  </tr>
                  <tr className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 font-semibold text-slate-800 flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-cyan-100 text-cyan-800 flex items-center justify-center font-bold text-[10px]">
                        SM
                      </div>
                      <span>Requests Timeout</span>
                    </td>
                    <td className="py-3 text-slate-500 font-mono text-[11px]">
                      ID #589004627102458
                    </td>
                    <td className="py-3 text-right">
                      <span className="bg-emerald-100 text-emerald-800 font-extrabold px-2.5 py-1 rounded-md text-[11px]">
                        100
                      </span>
                    </td>
                  </tr>
                  <tr className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 font-semibold text-slate-800 flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-800 flex items-center justify-center font-bold text-[10px]">
                        PW
                      </div>
                      <span>HTTPX Redirect</span>
                    </td>
                    <td className="py-3 text-slate-500 font-mono text-[11px]">
                      ID #762145839102013
                    </td>
                    <td className="py-3 text-right">
                      <span className="bg-emerald-100 text-emerald-800 font-extrabold px-2.5 py-1 rounded-md text-[11px]">
                        96
                      </span>
                    </td>
                  </tr>
                  <tr className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 font-semibold text-slate-800 flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-amber-100 text-amber-800 flex items-center justify-center font-bold text-[10px]">
                        LS
                      </div>
                      <span>FastAPI Query</span>
                    </td>
                    <td className="py-3 text-slate-500 font-mono text-[11px]">
                      ID #301478652109841
                    </td>
                    <td className="py-3 text-right">
                      <span className="bg-amber-100 text-amber-800 font-extrabold px-2.5 py-1 rounded-md text-[11px]">
                        68
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Decorative 3D Neon Lime Ribbon Trail */}
            <div className="absolute -bottom-8 -right-8 pointer-events-none opacity-90">
              <svg width="240" height="140" viewBox="0 0 240 140" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 130C70 100 130 140 190 40C210 5 235 15 235 15" stroke="#D4FF00" strokeWidth="10" strokeLinecap="round" filter="drop-shadow(0 4px 12px rgba(212,255,0,0.5))"/>
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Brand Logo Strip */}
      <div className="max-w-[1440px] w-full mx-auto px-6 sm:px-12 py-6 border-t border-white/10 flex flex-wrap items-center justify-between gap-6 text-white/60 font-semibold text-xs tracking-widest uppercase z-10">
        <span className="hover:text-white transition-colors cursor-default">Pallets / Flask</span>
        <span className="hover:text-white transition-colors cursor-default">PSF / Requests</span>
        <span className="hover:text-white transition-colors cursor-default">Encode / HTTPX</span>
        <span className="hover:text-white transition-colors cursor-default">FastAPI</span>
        <span className="hover:text-white transition-colors cursor-default">Pydantic</span>
        <span className="hover:text-white transition-colors cursor-default">Textualize / Rich</span>
        <span className="hover:text-white transition-colors cursor-default">Docker Sandbox</span>
      </div>
    </div>
  );
};
