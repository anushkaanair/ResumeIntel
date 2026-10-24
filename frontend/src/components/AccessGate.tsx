import { useEffect, useState, type ReactNode } from 'react';
import { API_ORIGIN, getApiKey, setApiKey, clearApiKey, api } from '../lib/api';
import { DEMO } from '../lib/demo';

/**
 * Personal-deployment access gate. If the server reports `auth_required`, ask for the
 * access key once and keep it in this browser's localStorage. Open servers (local dev)
 * pass straight through.
 */
export function AccessGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<'checking' | 'open' | 'locked' | 'offline'>(DEMO ? 'open' : 'checking');
  const [key, setKey] = useState('');
  const [err, setErr] = useState('');

  const check = async () => {
    try {
      const h = await fetch(`${API_ORIGIN}/health`).then((r) => r.json());
      if (!h.auth_required) return setState('open');
      if (!getApiKey()) return setState('locked');
      await api.get('/optimize/ping/status');
      setState('open');
    } catch (e: any) {
      if (e?.response?.status === 401) { clearApiKey(); setState('locked'); }
      else setState('offline');
    }
  };

  useEffect(() => {
    if (DEMO) return;
    check();
    const onAuth = () => { clearApiKey(); setState('locked'); };
    window.addEventListener('ri-auth-required', onAuth);
    return () => window.removeEventListener('ri-auth-required', onAuth);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (state === 'open') return <>{children}</>;
  const box: React.CSSProperties = { maxWidth: 420, margin: '15vh auto', padding: 24, color: '#e5e7eb', textAlign: 'center' };
  if (state === 'checking') return <div style={box}>Connecting…</div>;
  if (state === 'offline') {
    return (
      <div style={box}>
        <h2>Can't reach the server</h2>
        <p style={{ opacity: 0.7 }}>Expected the API at {API_ORIGIN}. Is the backend running?</p>
        <button onClick={() => { setState('checking'); check(); }} style={{ marginTop: 12 }}>Retry</button>
      </div>
    );
  }
  return (
    <form
      style={box}
      onSubmit={async (e) => {
        e.preventDefault();
        setApiKey(key.trim());
        setErr('');
        try { await api.get('/optimize/ping/status'); setState('open'); }
        catch { clearApiKey(); setErr('That key was not accepted.'); }
      }}
    >
      <h2>ResumeIntel</h2>
      <p style={{ opacity: 0.7 }}>This is a private deployment. Enter your access key.</p>
      <input
        type="password" autoFocus value={key} onChange={(e) => setKey(e.target.value)} placeholder="Access key"
        style={{ width: '100%', padding: 10, marginTop: 12, borderRadius: 8, border: '1px solid #374151', background: '#0b0b17', color: 'inherit' }}
      />
      {err && <p style={{ color: '#f87171' }}>{err}</p>}
      <button type="submit" style={{ marginTop: 12, padding: '8px 18px' }}>Unlock</button>
    </form>
  );
}
