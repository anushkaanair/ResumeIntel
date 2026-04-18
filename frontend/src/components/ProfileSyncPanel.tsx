/**
 * ProfileSyncPanel — slide-in right drawer that shows GitHub/LinkedIn sync status
 * and surfaces detected profile deltas as one-click "Apply to Resume" cards.
 */

import { useState, useEffect } from 'react';
import { StalenessIndicator } from './StalenessIndicator';
import { Github, Linkedin, RefreshCw, Plus, ChevronRight, ChevronLeft } from 'lucide-react';
import { api } from '../lib/api';

interface PlatformStatus {
  platform: string;
  last_sync_at: string | null;
  staleness_score: number;
  pending_deltas: number;
}

interface DeltaCard {
  id: string;
  platform: 'github' | 'linkedin';
  item_type: string;
  title: string;
  description: string;
  relevance_score: number;
  suggested_section: string;
}

interface Props {
  jobId: string;
  userId?: string;
  onBulletApplied: (bullet: {
    bullet: string;
    quality_score: number;
    platform_badge: string;
    suggested_section: string;
    status: string;
  }) => void;
}

const PLATFORM_ICON: Record<string, React.ReactNode> = {
  github: <Github size={14} />,
  linkedin: <Linkedin size={14} />,
};

export function ProfileSyncPanel({ jobId, userId = 'demo-user', onBulletApplied }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [syncStatus, setSyncStatus] = useState<PlatformStatus[]>([]);
  const [deltas, setDeltas] = useState<DeltaCard[]>([]);
  const [refreshing, setRefreshing] = useState<string | null>(null);
  const [applying, setApplying] = useState<string | null>(null);

  const loadStatus = () =>
    api.get(`/api/v1/sync/status?user_id=${userId}`)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .then((r: any) => setSyncStatus(r.data?.data?.platforms ?? []))
      .catch(() => {});

  const loadDeltas = () =>
    api.get(`/api/v1/sync/deltas?user_id=${userId}`)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .then((r: any) => setDeltas(r.data?.data?.deltas ?? []))
      .catch(() => {});

  useEffect(() => {
    loadStatus();
    loadDeltas();
  }, [userId]);

  const handleRefresh = async (platform: string) => {
    setRefreshing(platform);
    try {
      await api.post(`/api/v1/sync/refresh?platform=${platform}&job_id=${jobId}&user_id=${userId}`);
      await Promise.all([loadStatus(), loadDeltas()]);
    } catch {
      // surface error silently — panel shows stale data
    } finally {
      setRefreshing(null);
    }
  };

  const handleApply = async (deltaId: string) => {
    setApplying(deltaId);
    try {
      const res = await api.post(`/api/v1/sync/apply/${deltaId}`, {
        job_id: jobId,
        user_id: userId,
      });
      onBulletApplied(res.data?.data);
      setDeltas(prev => prev.filter(d => d.id !== deltaId));
    } catch {
      // keep delta in list on error
    } finally {
      setApplying(null);
    }
  };

  const pendingCount = deltas.length;

  return (
    <div className="sync-panel-root">
      {/* Toggle tab */}
      <button
        className="sync-panel-tab"
        onClick={() => setIsOpen(o => !o)}
        aria-label={isOpen ? 'Close sync panel' : 'Open sync panel'}
      >
        {isOpen ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        <span className="sync-tab-label">Profile Sync</span>
        {pendingCount > 0 && !isOpen && (
          <span className="sync-tab-badge">{pendingCount}</span>
        )}
      </button>

      {/* Drawer */}
      {isOpen && (
        <div className="sync-panel-drawer">
          <div className="sync-panel-header">
            <h2 className="sync-panel-title">Profile Sync</h2>
            {pendingCount > 0 && (
              <span className="sync-panel-count">{pendingCount} new</span>
            )}
          </div>

          {/* Platform rows */}
          {(['github', 'linkedin'] as const).map(platform => {
            const s = syncStatus.find(p => p.platform === platform);
            const isRefreshing = refreshing === platform;
            return (
              <div key={platform} className="sync-platform-row">
                <div className="sync-platform-header">
                  <span className="sync-platform-name">
                    {PLATFORM_ICON[platform]}
                    <span className="capitalize">{platform}</span>
                  </span>
                  <button
                    className="sync-refresh-btn"
                    onClick={() => handleRefresh(platform)}
                    disabled={isRefreshing}
                  >
                    <RefreshCw size={12} className={isRefreshing ? 'animate-spin' : ''} />
                    {isRefreshing ? 'Refreshing…' : 'Refresh'}
                  </button>
                </div>
                {s ? (
                  <StalenessIndicator
                    stalenessScore={s.staleness_score}
                    lastSyncAt={s.last_sync_at}
                  />
                ) : (
                  <p className="sync-not-connected">Not connected</p>
                )}
                {(s?.pending_deltas ?? 0) > 0 && (
                  <span className="sync-pending-chip">{s!.pending_deltas} new items</span>
                )}
              </div>
            );
          })}

          {/* Delta cards */}
          <div className="sync-deltas-header">
            <h3 className="sync-deltas-title">Detected Updates</h3>
            <span className="sync-deltas-count">({deltas.length})</span>
          </div>

          {deltas.length === 0 ? (
            <p className="sync-empty">No new profile updates. Hit Refresh to check.</p>
          ) : (
            <div className="sync-delta-list">
              {deltas.map(delta => (
                <div key={delta.id} className="sync-delta-card">
                  <div className="sync-delta-meta">
                    <span className="sync-delta-platform">
                      {PLATFORM_ICON[delta.platform]} {delta.item_type}
                    </span>
                    <span className="sync-delta-score">
                      {Math.round(delta.relevance_score * 100)}% match
                    </span>
                  </div>
                  <p className="sync-delta-title">{delta.title}</p>
                  {delta.description && (
                    <p className="sync-delta-desc">{delta.description}</p>
                  )}
                  <div className="sync-delta-footer">
                    <span className="sync-delta-section">→ {delta.suggested_section}</span>
                    <button
                      className="sync-apply-btn"
                      onClick={() => handleApply(delta.id)}
                      disabled={applying === delta.id}
                    >
                      <Plus size={11} />
                      {applying === delta.id ? 'Applying…' : 'Apply'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
