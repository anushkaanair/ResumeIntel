/**
 * StalenessIndicator — traffic-light badge showing how fresh a platform sync is.
 * stalenessScore: 0.0 = fresh, 1.0 = never synced
 */

interface Props {
  stalenessScore: number;
  lastSyncAt: string | null;
}

export function StalenessIndicator({ stalenessScore, lastSyncAt }: Props) {
  const color =
    stalenessScore < 0.25 ? 'bg-green-500' :
    stalenessScore < 0.75 ? 'bg-yellow-400' : 'bg-red-500';

  const label =
    stalenessScore < 0.25 ? 'Synced' :
    stalenessScore < 0.75 ? 'Stale' : 'Outdated';

  const since = lastSyncAt
    ? new Date(lastSyncAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    : null;

  return (
    <div className="flex items-center gap-2">
      <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${color}`} />
      <span className="text-sm text-gray-400">{label}</span>
      {since && (
        <span className="text-xs text-gray-500">· {since}</span>
      )}
    </div>
  );
}
