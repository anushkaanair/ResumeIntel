import { AlertTriangle, Info, ShieldAlert } from 'lucide-react';

export interface WeaknessCardProps {
  severity: 'high' | 'medium' | 'low';
  type: string;
  description: string;
  recommendation: string;
}

const SEVERITY_CONFIG = {
  high: { icon: ShieldAlert, bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
  medium: { icon: AlertTriangle, bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  low: { icon: Info, bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
};

export function WeaknessCard({ severity, type, description, recommendation }: WeaknessCardProps) {
  const config = SEVERITY_CONFIG[severity];
  const Icon = config.icon;

  return (
    <div className={`p-4 rounded-xl border ${config.bg} ${config.border}`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon size={16} className={config.text} />
        <span className={`text-xs font-bold uppercase tracking-wider ${config.text}`}>
          {type.replace(/_/g, ' ')}
        </span>
      </div>
      <p className="text-sm font-medium text-gray-900 mb-2">{description}</p>
      <div className="text-sm text-gray-700 bg-white/60 p-2.5 rounded-md border border-white/40">
        <span className="font-semibold block mb-0.5">Recommendation:</span>
        {recommendation}
      </div>
    </div>
  );
}
