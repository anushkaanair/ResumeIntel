/**
 * VersionTimeline — horizontal scrollable strip above the canvas.
 * Each snapshot is a clickable chip. Selecting two chips triggers a diff view.
 * Clicking one chip + "Revert" restores the canvas to that state.
 */

import { useState, useEffect } from 'react';
import { History, RotateCcw, GitCompare } from 'lucide-react';
import { api } from '../lib/api';

interface Snapshot {
  id: string;
  version_num: number;
  label: string;
  source: string;
  timestamp: string;
}

interface DiffToken {
  type: 'add' | 'remove' | 'same';
  text: string;
}

interface Props {
  jobId: string;
  onRevert: (content: string) => void;
}

export function VersionTimeline({ jobId, onRevert }: Props) {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [selected, setSelected] = useState<string[]>([]);  // up to 2 IDs
  const [diffTokens, setDiffTokens] = useState<DiffToken[] | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const [reverting, setReverting] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    api.get(`/api/v1/versions/${jobId}`)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .then((r: any) => setSnapshots(r.data?.data?.snapshots ?? []))
      .catch(() => {});
  }, [jobId]);

  const toggleSelect = (id: string) => {
    setSelected(prev => {
      if (prev.includes(id)) return prev.filter(s => s !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
    setDiffTokens(null);
    setShowDiff(false);
  };

  const handleDiff = async () => {
    if (selected.length !== 2) return;
    try {
      const res = await api.get(`/api/v1/versions/${jobId}/diff`, {
        params: { v1_id: selected[0], v2_id: selected[1] },
      });
      setDiffTokens(res.data?.data?.tokens ?? []);
      setShowDiff(true);
    } catch {
      // ignore
    }
  };

  const handleRevert = async (versionId: string) => {
    setReverting(true);
    try {
      const res = await api.post(`/api/v1/versions/${jobId}/revert`, null, {
        params: { version_id: versionId },
      });
      const content = res.data?.data?.content;
      if (content) {
        onRevert(content);
        // Refresh snapshot list
        const r2 = await api.get(`/api/v1/versions/${jobId}`);
        setSnapshots(r2.data?.data?.snapshots ?? []);
        setSelected([]);
      }
    } catch {
      // ignore
    } finally {
      setReverting(false);
    }
  };

  if (snapshots.length === 0) return null;

  const sourceIcon = (src: string) =>
    src === 'agent' ? '🤖' : src === 'revert' ? '↩' : src === 'user_edit' ? '✏️' : '💾';

  return (
    <div className="version-timeline">
      <div className="vt-header">
        <History size={13} />
        <span className="vt-label">Versions</span>
        {selected.length === 2 && (
          <button className="vt-diff-btn" onClick={handleDiff}>
            <GitCompare size={12} /> Diff
          </button>
        )}
        {selected.length === 1 && (
          <button
            className="vt-revert-btn"
            onClick={() => handleRevert(selected[0])}
            disabled={reverting}
          >
            <RotateCcw size={12} />
            {reverting ? 'Reverting…' : 'Revert'}
          </button>
        )}
      </div>

      {/* Scrollable snapshot strip */}
      <div className="vt-strip">
        {snapshots.map(snap => {
          const isSelected = selected.includes(snap.id);
          const selIdx = selected.indexOf(snap.id);
          return (
            <button
              key={snap.id}
              className={`vt-chip ${isSelected ? 'vt-chip-selected' : ''}`}
              onClick={() => toggleSelect(snap.id)}
              title={`${snap.label} — ${new Date(snap.timestamp).toLocaleString()}`}
            >
              <span className="vt-chip-icon">{sourceIcon(snap.source)}</span>
              <span className="vt-chip-num">v{snap.version_num}</span>
              {isSelected && (
                <span className="vt-chip-sel-idx">{selIdx + 1}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Inline diff view */}
      {showDiff && diffTokens && (
        <div className="vt-diff">
          <div className="vt-diff-header">
            <span>Diff: v{snapshots.find(s => s.id === selected[0])?.version_num} → v{snapshots.find(s => s.id === selected[1])?.version_num}</span>
            <button className="vt-diff-close" onClick={() => setShowDiff(false)}>×</button>
          </div>
          <pre className="vt-diff-body">
            {diffTokens.map((tok, i) => (
              <span
                key={i}
                className={
                  tok.type === 'add' ? 'vt-add' :
                  tok.type === 'remove' ? 'vt-remove' : 'vt-same'
                }
              >
                {tok.text}
              </span>
            ))}
          </pre>
        </div>
      )}
    </div>
  );
}
