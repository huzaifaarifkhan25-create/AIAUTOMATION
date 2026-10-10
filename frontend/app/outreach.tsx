'use client';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { mailtoHref, telHref } from '@/lib/outreach-links';

type Row = Record<string, any>;
type Language = 'en' | 'ur' | 'roman_ur';
type Sender = { name: string; company: string; offer: string };

async function api(path: string, init?: RequestInit): Promise<any> {
  const response = await fetch('/api/backend/' + path, { cache: 'no-store', ...init });
  const data = await response.json();
  if (!response.ok) throw Error(data?.error?.message || data?.error || `Request failed (${response.status})`);
  return data;
}

function download(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url; link.download = name; document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function readableCall(draft: Row) {
  return [draft.opening, draft.permission_question, '', 'Discovery questions:', ...(draft.discovery_questions || []).map((q: string) => `• ${q}`),
    '', 'Value statement:', draft.value_statement, '', 'Objections:', ...(draft.objections || []).map((o: Row) => `${o.objection}\n${o.response}`),
    '', 'Close:', draft.close, '', 'Voicemail:', draft.voicemail, '', 'If not interested:', draft.if_not_interested].join('\n');
}

export default function Outreach({ record, analysis, geminiConfigured, onLogged }: {
  record: Row; analysis: Row | null; geminiConfigured: boolean; onLogged: () => void;
}) {
  const [language, setLanguage] = useState<Language>('en');
  const [sender, setSender] = useState<Sender>({ name: '', company: '', offer: '' });
  const [saved, setSaved] = useState<Row[]>([]);
  const [pitch, setPitch] = useState<Row | null>(null);
  const [script, setScript] = useState<Row | null>(null);
  const [busy, setBusy] = useState<'pitch' | 'call_script' | 'log' | null>(null);
  const [error, setError] = useState(''); const [status, setStatus] = useState('');
  const [recipient, setRecipient] = useState(''); const [subjectIndex, setSubjectIndex] = useState(0);
  const [logKind, setLogKind] = useState<'email' | 'call'>('email');
  const [outcome, setOutcome] = useState(''); const [actualContact, setActualContact] = useState(false);
  const [logKey, setLogKey] = useState('');
  const [contactStage, setContactStage] = useState<string | null>(null);

  const load = useCallback(async () => {
    const rows = await api(`ai/businesses/${record.id}/insights`);
    setSaved(rows);
  }, [record.id]);
  useEffect(() => { let active = true; void api(`ai/businesses/${record.id}/insights`).then(rows => { if (active) setSaved(rows); }).catch(e => { if (active) setError(e.message); }); return () => { active = false; }; }, [record.id]);
  useEffect(() => { let active = true; void api(`businesses/${record.id}/contact`).then(row => { if (active) setContactStage(row.stage || 'new'); }).catch(() => { if (active) setContactStage(null); }); return () => { active = false; }; }, [record.id]);

  const currentPitch = pitch || saved.find(row => row.kind === 'pitch') || null;
  const currentScript = script || saved.find(row => row.kind === 'call_script') || null;
  const subjects: string[] = currentPitch?.subject_options || [];
  const chosenSubject = subjects[Math.min(subjectIndex, subjects.length - 1)] || '';
  const publicEmails: string[] = useMemo(() => (analysis?.website?.emails || []).filter((email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)).slice(0, 5), [analysis]);
  const senderReady = Object.values(sender).every(value => value.trim());
  const outreachBlocked = contactStage === null || contactStage === 'do_not_contact' || record.status === 'archived';
  const emailHref = currentPitch && !outreachBlocked ? mailtoHref(recipient, chosenSubject, currentPitch.body) : null;
  const phoneHref = record.source === 'mock' || outreachBlocked ? null : telHref(record.business?.phone || '');

  async function generate(kind: 'pitch' | 'call_script') {
    if (!senderReady || busy || outreachBlocked) return;
    setBusy(kind); setError(''); setStatus('');
    try {
      const result = await api(`ai/businesses/${record.id}/${kind === 'pitch' ? 'pitch' : 'call-script'}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ language, sender }),
      });
      if (kind === 'pitch') { setPitch(result); setSubjectIndex(0); } else setScript(result);
      await load();
      setStatus(`${kind === 'pitch' ? 'Email pitch' : 'Call script'} saved as a review-only draft. Nothing was sent.`);
    } catch (e) { setError(e instanceof Error ? e.message : 'Draft could not be generated'); }
    finally { setBusy(null); }
  }

  async function copy(text: string, label: string) {
    try { await navigator.clipboard.writeText(text); setStatus(`${label} copied.`); }
    catch { setError('Clipboard access was denied. Use Download .txt instead.'); }
  }

  async function logContact(e: React.FormEvent) {
    e.preventDefault();
    if (!actualContact || !outcome.trim() || busy) return;
    const stable = logKey || crypto.randomUUID(); setLogKey(stable);
    setBusy('log'); setError(''); setStatus('');
    try {
      await api(`businesses/${record.id}/activities`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idempotency_key: stable, kind: logKind, direction: 'outgoing',
          notes: `Operator reported ${logKind}: ${outcome.trim()}. Provider delivery and recipient response are unverified.`,
          occurred_at: new Date().toISOString() }),
      });
      setOutcome(''); setActualContact(false); setLogKey('');
      setStatus('Manual contact note saved. Delivery was not verified.'); onLogged();
    } catch (e) { setError(e instanceof Error ? e.message : 'Contact note could not be saved'); }
    finally { setBusy(null); }
  }

  return <section className="outreach-section"><div className="panel outreach-setup"><p className="eyebrow">LEVEL 1 · REVIEWED DRAFTS</p><h2>Email pitch & call script</h2><p>These drafts use saved listing and analysis facts. They do not send email or place calls. Review category, evidence and permission before using your own tools.</p><div className="outreach-inputs"><label>Language<select value={language} onChange={e => setLanguage(e.target.value as Language)}><option value="en">English</option><option value="ur">Urdu</option><option value="roman_ur">Roman Urdu</option></select></label><label>Your name<input value={sender.name} onChange={e => setSender(s => ({ ...s, name: e.target.value }))} maxLength={80} placeholder="Sender name" /></label><label>Company<input value={sender.company} onChange={e => setSender(s => ({ ...s, company: e.target.value }))} maxLength={120} placeholder="Company name" /></label><label>Offer, one sentence<input value={sender.offer} onChange={e => setSender(s => ({ ...s, offer: e.target.value }))} maxLength={240} placeholder="What you offer, without a results promise" /></label></div>{contactStage === "do_not_contact" && <p className="notice error">Do not contact: draft actions are disabled.</p>}<p className="hint">Sender details are included in saved drafts. Do not enter a recipient or private credential here.</p>{error && <p className="notice error" role="alert">{error}</p>}{status && <p className="notice" role="status">{status}</p>}</div>
    <div className="outreach-grid"><section className="panel"><p className="eyebrow">AI OR RULE-BASED · UNSENT</p><h2>Email pitch</h2><p>{geminiConfigured ? 'Gemini is attempted first. If access or validation fails, a rule-based discovery draft is saved.' : 'Gemini is unavailable. Generate uses the rule-based discovery fallback.'}</p><button className="primary" disabled={!senderReady || outreachBlocked || !!busy} onClick={() => void generate('pitch')}>{busy === 'pitch' ? 'Generating…' : currentPitch ? 'Regenerate email pitch' : 'Generate email pitch'}</button>{currentPitch && <><div className="outreach-meta"><span className="badge">{currentPitch.origin === 'rules' ? 'Rule-based fallback' : 'AI draft, review before use'}</span>{currentPitch.demo && <span className="badge demo">DEMO</span>}<span>Saved {new Date(currentPitch.created_at).toLocaleString()}</span></div><label>Subject<select value={subjectIndex} onChange={e => setSubjectIndex(Number(e.target.value))}>{subjects.map((subject, index) => <option key={index} value={index}>{subject}</option>)}</select></label><div className="draft-text" dir={currentPitch.language === 'ur' ? 'rtl' : 'ltr'}>{currentPitch.body}</div><div className="outreach-actions"><button className="secondary" disabled={outreachBlocked} onClick={() => void copy(chosenSubject, 'Subject')}>Copy subject</button><button className="secondary" disabled={outreachBlocked} onClick={() => void copy(currentPitch.body, 'Email body')}>Copy body</button><button className="secondary" disabled={outreachBlocked} onClick={() => download('email-pitch.txt', `Subject: ${chosenSubject}\n\n${currentPitch.body}`)}>Download .txt</button></div><label>Recipient in your email app<select value={recipient} onChange={e => setRecipient(e.target.value)}><option value="">Leave recipient empty</option>{publicEmails.map(email => <option key={email} value={email}>{email} · public website</option>)}</select></label>{record.source === 'mock' ? <p className="hint">DEMO lead: external email link is disabled.</p> : emailHref && <a className="secondary" href={emailHref}>Open in email app ↗</a>}<h3>Personalization sources</h3>{currentPitch.personalization_used?.length ? currentPitch.personalization_used.map((fact: Row, i: number) => <div className="evidence" key={i}><strong>{fact.fact}</strong><small>{fact.source} · {fact.observed_on}</small></div>) : <p className="hint">No personalized fact was used.</p>}<h3>Assumptions and unknowns</h3><ul>{(currentPitch.assumptions_and_unknowns || []).map((value: string, i: number) => <li key={i}>{value}</li>)}</ul><p className="hint">Follow-ups for days 3 and 7 are drafts only; nothing is scheduled or sent.</p></>}</section>
      <section className="panel"><p className="eyebrow">HUMAN CALL SCRIPT · UNSENT</p><h2>Call script</h2><p>{geminiConfigured ? 'Gemini creates a script for a human to review and use.' : 'AI unavailable: a call script requires a Gemini key on the backend.'}</p><button className="primary" disabled={!senderReady || outreachBlocked || !geminiConfigured || !!busy} onClick={() => void generate('call_script')}>{busy === 'call_script' ? 'Generating…' : currentScript ? 'Regenerate call script' : 'Generate call script'}</button>{currentScript && <><div className="outreach-meta"><span className="badge">AI draft, review before use</span>{currentScript.demo && <span className="badge demo">DEMO</span>}<span>Saved {new Date(currentScript.created_at).toLocaleString()}</span></div><div className="draft-text" dir={currentScript.language === 'ur' ? 'rtl' : 'ltr'}>{readableCall(currentScript)}</div><div className="outreach-actions"><button className="secondary" disabled={outreachBlocked} onClick={() => void copy(readableCall(currentScript), 'Call script')}>Copy script</button><button className="secondary" disabled={outreachBlocked} onClick={() => download('call-script.txt', readableCall(currentScript))}>Download .txt</button>{phoneHref && <a className="secondary" href={phoneHref}>Call on my phone ↗</a>}</div>{!phoneHref && <p className="hint">No usable public phone is saved, or this is a DEMO lead. The app will not dial.</p>}<h3>Assumptions and unknowns</h3><ul>{(currentScript.assumptions_and_unknowns || []).map((value: string, i: number) => <li key={i}>{value}</li>)}</ul></>}</section></div>
    <section className="panel"><p className="eyebrow">MANUAL HISTORY · NO DELIVERY CLAIM</p><h2>Log contact after using your own tool</h2><p>Opening an email or phone app does not prove that a message was sent or a call connected. Record only what actually happened.</p><form onSubmit={logContact} className="outreach-log"><label>Method<select value={logKind} onChange={e => { setLogKind(e.target.value as 'email' | 'call'); setLogKey(''); }}><option value="email">Email from my app</option><option value="call">Call from my phone</option></select></label><label>Observed outcome<input value={outcome} onChange={e => { setOutcome(e.target.value); setLogKey(''); }} required maxLength={350} placeholder="For example: dialed, no answer; email composed and sent" /></label><label className="outreach-confirm"><input type="checkbox" checked={actualContact} onChange={e => setActualContact(e.target.checked)} required /> I actually used my own email or phone tool</label><button className="secondary" disabled={!!busy || !actualContact || !outcome.trim()}>Save manual contact note</button></form></section>
  </section>;
}
