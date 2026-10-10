'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function Login() {
  const router = useRouter();
  const [code, setCode] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function enter(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError('');
    try { const r = await fetch('/api/access', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code }) }); if (!r.ok) throw Error('Access code was not accepted'); router.replace('/'); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not sign in'); setBusy(false); }
  }
  return <main className="gate"><section className="gate-card"><div className="gate-icon"><img src="/logo-color.png" alt="" /></div><p className="eyebrow">MED SPA WORKSPACE</p><h1>Welcome to AIAutomation</h1><p>Enter the shared demo access code to review leads and sandbox workflows.</p><form onSubmit={enter}><label htmlFor="code">Access code</label><input id="code" type="password" autoComplete="off" value={code} onChange={e => setCode(e.target.value)} required /><button className="primary" disabled={busy}>{busy ? 'Opening…' : 'Open workspace →'}</button></form>{error && <p className="error">{error}</p>}<small>Shared pilot access. Individual accounts are planned.</small></section></main>;
}
