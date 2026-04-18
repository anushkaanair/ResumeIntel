/**
 * MentorAnnotationPanel — collaborative review comments on canvas bullets.
 * Mentor comments render in purple, AI-generated notes render in indigo.
 * Requires a collab session ID (shared_token) to identify the session.
 */

import { useState, useEffect, useRef } from 'react';
import { MessageSquare, Send, X } from 'lucide-react';
import { api } from '../lib/api';

export interface Annotation {
  id: string;
  bullet_id: string;
  author_id: string;
  role: string;
  source: 'mentor' | 'ai';
  text: string;
  created_at: string;
}

interface Props {
  bulletId: string;
  bulletText: string;
  sessionToken: string;
  authorId?: string;
}

export function MentorAnnotationPanel({
  bulletId,
  bulletText,
  sessionToken,
  authorId = 'guest',
}: Props) {
  const [open, setOpen] = useState(false);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  const load = () => {
    if (!sessionToken) return;
    api.get(`/api/v1/collab/${sessionToken}/annotations/${bulletId}`)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .then((r: any) => setAnnotations(r.data?.data?.annotations ?? []))
      .catch(() => {});
  };

  useEffect(() => {
    if (open) load();
  }, [open, bulletId, sessionToken]);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [annotations]);

  const handleSend = async () => {
    if (!draft.trim() || !sessionToken) return;
    setSending(true);
    try {
      await api.post(`/api/v1/collab/${sessionToken}/annotations`, {
        bullet_id: bulletId,
        author_id: authorId,
        source: 'mentor',
        text: draft.trim(),
      });
      setDraft('');
      load();
    } catch {
      // ignore
    } finally {
      setSending(false);
    }
  };

  const annotationCount = annotations.length;

  return (
    <div className="mentor-panel-root">
      <button
        className="mentor-toggle"
        onClick={() => setOpen(o => !o)}
        title="View / add mentor notes"
        aria-label="Mentor annotations"
      >
        <MessageSquare size={12} />
        {annotationCount > 0 && (
          <span className="mentor-count">{annotationCount}</span>
        )}
      </button>

      {open && (
        <div className="mentor-popover" role="dialog">
          <div className="mentor-popover-header">
            <span className="mentor-popover-title">Mentor Notes</span>
            <button className="mentor-close" onClick={() => setOpen(false)} aria-label="Close">
              <X size={12} />
            </button>
          </div>

          <p className="mentor-bullet-preview">{bulletText.slice(0, 80)}{bulletText.length > 80 ? '…' : ''}</p>

          <div className="mentor-list" ref={listRef}>
            {annotations.length === 0 ? (
              <p className="mentor-empty">No notes yet. Be the first to comment.</p>
            ) : (
              annotations.map(ann => (
                <div
                  key={ann.id}
                  className={`mentor-annotation ${ann.source === 'ai' ? 'mentor-ai' : 'mentor-human'}`}
                >
                  <div className="mentor-ann-meta">
                    <span className="mentor-ann-author">
                      {ann.source === 'ai' ? '🤖 AI' : `👤 ${ann.author_id}`}
                    </span>
                    <span className="mentor-ann-time">
                      {new Date(ann.created_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="mentor-ann-text">{ann.text}</p>
                </div>
              ))
            )}
          </div>

          <div className="mentor-input-row">
            <input
              className="mentor-input"
              placeholder="Add a note…"
              value={draft}
              onChange={e => setDraft(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            />
            <button
              className="mentor-send"
              onClick={handleSend}
              disabled={sending || !draft.trim()}
              aria-label="Send"
            >
              <Send size={12} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
