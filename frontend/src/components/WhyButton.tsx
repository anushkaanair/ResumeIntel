/**
 * WhyButton — small info button that opens a provenance popover for a bullet.
 * Shows: agent name, retrieved chunks, rationale, confidence, and a "Disagree" action.
 */

import { useState } from 'react';
import { HelpCircle, X, ThumbsDown } from 'lucide-react';
import { api } from '../lib/api';

export interface Provenance {
  agent_name: string;
  input_summary: string;
  retrieved_chunks: string[];
  decision_rationale: string;
  confidence: number;
}

interface Props {
  bulletId: string;
  bulletText: string;
  provenance: Provenance | null;
  onDisputeResolved?: (newContent: string, newScore: number) => void;
}

export function WhyButton({ bulletId, bulletText, provenance, onDisputeResolved }: Props) {
  const [open, setOpen] = useState(false);
  const [disputing, setDisputing] = useState(false);
  const [disputed, setDisputed] = useState(false);

  if (!provenance) return null;

  const confidencePct = Math.round(provenance.confidence * 100);
  const confidenceColor =
    provenance.confidence >= 0.7 ? 'text-green-400' :
    provenance.confidence >= 0.5 ? 'text-yellow-400' : 'text-red-400';

  const handleDisagree = async () => {
    setDisputing(true);
    try {
      const res = await api.post(`/api/v1/canvas/dispute/${bulletId}`, {
        bullet_text: bulletText,
        reason: 'User disagreed with AI suggestion',
      });
      const data = res.data?.data;
      if (data && onDisputeResolved) {
        onDisputeResolved(data.new_content, data.quality_score);
      }
      setDisputed(true);
    } catch {
      // silently ignore network errors
    } finally {
      setDisputing(false);
    }
  };

  return (
    <div className="why-btn-root">
      <button
        className="why-btn"
        onClick={() => setOpen(o => !o)}
        title="Why did the AI suggest this?"
        aria-label="Show AI reasoning"
      >
        <HelpCircle size={12} />
      </button>

      {open && (
        <>
          {/* Backdrop */}
          <div className="why-backdrop" onClick={() => setOpen(false)} />

          {/* Popover */}
          <div className="why-popover" role="dialog" aria-modal>
            <div className="why-popover-header">
              <span className="why-agent-badge">{provenance.agent_name} agent</span>
              <button className="why-close" onClick={() => setOpen(false)} aria-label="Close">
                <X size={12} />
              </button>
            </div>

            <div className="why-section">
              <p className="why-label">Rationale</p>
              <p className="why-rationale">{provenance.decision_rationale}</p>
            </div>

            {provenance.retrieved_chunks.length > 0 && (
              <div className="why-section">
                <p className="why-label">Source chunks used</p>
                <div className="why-chunks">
                  {provenance.retrieved_chunks.slice(0, 4).map(id => (
                    <span key={id} className="why-chunk-id">{id}</span>
                  ))}
                  {provenance.retrieved_chunks.length > 4 && (
                    <span className="why-chunk-more">+{provenance.retrieved_chunks.length - 4} more</span>
                  )}
                </div>
              </div>
            )}

            <div className="why-footer">
              <span className={`why-confidence ${confidenceColor}`}>
                Confidence: {confidencePct}%
              </span>
              {!disputed ? (
                <button
                  className="why-disagree-btn"
                  onClick={handleDisagree}
                  disabled={disputing}
                >
                  <ThumbsDown size={11} />
                  {disputing ? 'Re-evaluating…' : 'Disagree'}
                </button>
              ) : (
                <span className="why-disputed-label">Re-evaluated ✓</span>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
