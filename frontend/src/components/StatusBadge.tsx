import React from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  Clock, 
  AlertTriangle 
} from 'lucide-react';

interface StatusBadgeProps {
  status: 'pending' | 'running' | 'success' | 'failed' | 'error' | string;
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const getBadgeStyle = () => {
    switch (status.toLowerCase()) {
      case 'success':
        return {
          bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
          icon: <CheckCircle2 className="w-3.5 h-3.5" />,
          label: 'Success',
        };
      case 'running':
        return {
          bg: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400',
          icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
          label: 'Running',
        };
      case 'pending':
        return {
          bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
          icon: <Clock className="w-3.5 h-3.5" />,
          label: 'Pending',
        };
      case 'failed':
        return {
          bg: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
          icon: <XCircle className="w-3.5 h-3.5" />,
          label: 'Failed',
        };
      case 'error':
      default:
        return {
          bg: 'bg-red-500/10 border-red-500/30 text-red-400',
          icon: <AlertTriangle className="w-3.5 h-3.5" />,
          label: 'Error',
        };
    }
  };

  const { bg, icon, label } = getBadgeStyle();
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : size === 'lg' ? 'px-3 py-1.5 text-sm' : 'px-2.5 py-1 text-xs';

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${bg} ${sizeClasses}`}>
      {icon}
      <span className="capitalize">{label}</span>
    </span>
  );
};
