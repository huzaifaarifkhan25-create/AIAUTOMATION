'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function Login() {
  const router = useRouter();
  const [mode, setMode] = useState<'login' | 'register' | 'legacy'>('login');
  const [status, setStatus] = useState<{ supported: boolean; has_accounts: boolean; registration_available: boolean; access_code_required: boolean; legacy_available: boolean } | null>(null);
  const [code, setCode] = useState(''); const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [name, setName] = useState(''); const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    fetch('/api/auth/status', { cache: 'no-store' }).then(async response => {
      const result = await response.json();
      if (!response.ok) throw Error(typeof result.error === 'string' ? result.error : result.error?.message || 'Account setup could not be loaded');
      if (active) { setStatus(result); if (!result.has_accounts && result.registration_available) setMode('register'); }
    }).catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'Account setup could not be loaded'); });
    return () => { active = false; };
  }, []);
  async function enter(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const payload = mode === 'legacy' ? { code } : mode === 'register' ? { name, email, password, access_code: code, confirm_shared_workspace: confirmed } : { email, password };
      const response = await fetch(mode === 'legacy' ? '/api/access' : `/api/auth/${mode}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const result = await response.json();
      if (!response.ok) throw Error(typeof result.error === 'string' ? result.error : result.error?.message || result.detail?.[0]?.msg || 'Could not sign in');
      setCode(''); setPassword(''); router.replace('/'); router.refresh();
    }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not sign in'); setBusy(false); }
  }
  function choose(value: typeof mode) { setMode(value); setError(''); setPassword(''); setCode(''); }
  return <main className="gate"><section className="gate-card auth-card"><div className="gate-icon"><img src="/logo-color.png" alt="" /></div><p className="eyebrow">MED SPA WORKSPACE</p><h1>{mode === 'register' ? 'Create your account' : 'Welcome to AIAutomation'}</h1><p>{mode === 'legacy' ? 'Enter the shared pilot access code.' : 'Your own sign-in for this shared automation workspace.'}</p>
    <div className="auth-tabs" aria-label="Sign-in options"><button type="button" className="secondary" aria-pressed={mode === 'login'} onClick={() => choose('login')} disabled={busy || status?.supported === false}>Sign in</button>{status?.registration_available && <button type="button" className="secondary" aria-pressed={mode === 'register'} onClick={() => choose('register')} disabled={busy}>Register</button>}{status?.legacy_available && <button type="button" className="secondary" aria-pressed={mode === 'legacy'} onClick={() => choose('legacy')} disabled={busy}>Access code</button>}</div>
    <form onSubmit={enter}>
      {mode === 'register' && <><label htmlFor="name">Your name</label><input id="name" autoComplete="name" maxLength={80} value={name} onChange={event => setName(event.target.value)} required /></>}
      {mode !== 'legacy' && <><label htmlFor="email">Email</label><input id="email" type="email" autoComplete="username" maxLength={254} value={email} onChange={event => setEmail(event.target.value)} required /><label htmlFor="password">Password{mode === 'register' ? ' (at least 12 characters)' : ''}</label><input id="password" type="password" autoComplete={mode === 'register' ? 'new-password' : 'current-password'} minLength={mode === 'register' ? 12 : 1} maxLength={128} value={password} onChange={event => setPassword(event.target.value)} required /></>}
      {(mode === 'legacy' || (mode === 'register' && status?.access_code_required)) && <><label htmlFor="code">{mode === 'register' ? 'Workspace invitation code' : 'Access code'}</label><input id="code" type="password" autoComplete="off" maxLength={512} value={code} onChange={event => setCode(event.target.value)} required /></>}
      {mode === 'register' && <label className="auth-confirm"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} required />I understand this account joins the same shared workspace as other operators.</label>}
      <button className="primary" disabled={busy || !status || (mode !== 'legacy' && !status.supported)}>{busy ? 'Opening…' : mode === 'register' ? 'Create account →' : mode === 'legacy' ? 'Open workspace →' : 'Sign in →'}</button>
    </form>{error && <p className="error" role="alert">{error}</p>}<small>Individual sign-ins. Leads and automations are shared; separate company workspaces and password recovery are not included.</small></section></main>;
}
