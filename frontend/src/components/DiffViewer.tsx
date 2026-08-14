import { useState } from 'react';
import { Copy, Check, FileCode, SplitSquareVertical } from 'lucide-react';

interface DiffViewerProps {
  diff: string;
  title?: string;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({ diff, title = 'Unified Patch Diff' }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(diff);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!diff || diff.trim() === '') {
    return (
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-8 text-center text-slate-400">
        <FileCode className="w-8 h-8 mx-auto text-slate-600 mb-2" />
        <p className="text-sm">No patch diff generated yet for this iteration.</p>
      </div>
    );
  }

  const lines = diff.split('\n');

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 bg-slate-900/90 border-b border-slate-800">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
          <SplitSquareVertical className="w-4 h-4 text-emerald-400" />
          <span>{title}</span>
          <span className="text-xs text-slate-500 font-mono">({lines.length} lines)</span>
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white rounded-lg border border-slate-700 transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy Diff</span>
            </>
          )}
        </button>
      </div>

      {/* Diff Content */}
      <div className="font-mono text-xs overflow-x-auto max-h-[460px] p-2 leading-relaxed">
        <table className="w-full border-collapse">
          <tbody>
            {lines.map((line, index) => {
              let lineStyle = 'text-slate-400';
              let bgStyle = 'hover:bg-slate-900/40';

              if (line.startsWith('+++') || line.startsWith('---')) {
                lineStyle = 'text-slate-300 font-bold';
                bgStyle = 'bg-slate-900/80';
              } else if (line.startsWith('@@')) {
                lineStyle = 'text-indigo-400 font-semibold';
                bgStyle = 'bg-indigo-950/20';
              } else if (line.startsWith('+')) {
                lineStyle = 'text-emerald-300';
                bgStyle = 'bg-emerald-950/30';
              } else if (line.startsWith('-')) {
                lineStyle = 'text-rose-300';
                bgStyle = 'bg-rose-950/30';
              }

              return (
                <tr key={index} className={`${bgStyle} transition-colors`}>
                  <td className="w-12 text-right pr-3 select-none text-slate-600 text-[11px] border-r border-slate-800/60 py-0.5">
                    {index + 1}
                  </td>
                  <td className={`pl-4 pr-2 py-0.5 whitespace-pre ${lineStyle}`}>
                    {line}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
