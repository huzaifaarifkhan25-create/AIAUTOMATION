'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { api, json, date, errorMessage, Badge, Notice, Empty, Result, type Row } from './feature-ui';

export default function AIAgent({ businesses, onChanged }: { businesses: Row[]; onChanged: () => Promise<void> }) {
  const [status, setStatus] = useState<Row | null>(null); const [conversations, setConversations] = useState<Row[]>([]);
  const [conversation, setConversation] = useState<Row | null>(null); const [input, setInput] = useState('');
  const [includeDemo, setIncludeDemo] = useState(false); const [businessId, setBusinessId] = useState('');
  const [busy, setBusy] = useState(false); const [loading, setLoading] = useState(true); const [error, setError] = useState('');
  const [provider, setProvider] = useState('gemini'); const [model, setModel] = useState('gemini-3.5-flash-lite'); const [key, setKey] = useState('');
  const [approved, setApproved] = useState<Record<string, boolean>>({});
  const createKey = useRef(''); const pendingMessage = useRef<Row | null>(null);
  const [retryAvailable, setRetryAvailable] = useState(false);

  const refresh = useCallback(async () => {
    const [s, rows] = await Promise.all([api('agent/status'), api('agent/conversations')]); setStatus(s); setConversations(rows);
  }, []);
  useEffect(() => { void refresh().catch(e => setError(errorMessage(e))).finally(() => setLoading(false)); }, [refresh]);
  async function act(fn: () => Promise<void>) { setBusy(true); setError(''); try { await fn(); } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); } }
  async function open(id: string) { await act(async () => { setConversation(await api(`agent/conversations/${id}`)); pendingMessage.current = null; setRetryAvailable(false); }); }
  async function ensureConversation() {
    if (conversation) return conversation.id;
    createKey.current ||= crypto.randomUUID();
    const row = await api('agent/conversations', json({ idempotency_key: createKey.current }));
    setConversation({ ...row, turns: [], actions: [] }); createKey.current = ''; return row.id;
  }
  async function send(event: React.FormEvent) {
    event.preventDefault(); if (busy || (!input.trim() && !pendingMessage.current)) return;
    await act(async () => {
      const id = await ensureConversation();
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Karachi';
      pendingMessage.current ||= { conversation_id: id, request_id: crypto.randomUUID(), message: input.trim(), include_demo: includeDemo, business_id: businessId || null, timezone };
      const { conversation_id, ...body } = pendingMessage.current;
      try {
        const row = await api(`agent/conversations/${conversation_id}/messages`, json(body)); setConversation(row);
        pendingMessage.current = null; setRetryAvailable(false); setInput(''); await refresh(); await onChanged();
      } catch (e) { setRetryAvailable(true); throw e; }
    });
  }
  async function review(action: Row, decision: string) {
    if (!conversation) return;
    await act(async () => {
      await api(`agent/actions/${action.id}/review`, json({ conversation_id: conversation.id, decision, confirm_action: decision === 'approve' }));
      setConversation(await api(`agent/conversations/${conversation.id}`)); await refresh(); await onChanged();
    });
  }
  async function connect(event: React.FormEvent) {
    event.preventDefault(); await act(async () => { setStatus(await api('agent/connection', json({ provider, model: model || null, api_key: key }))); setKey(''); await onChanged(); });
  }
  if (loading) return <section className="panel" role="status">Loading saved AI conversations…</section>;
  const visibleBusinesses = businesses.filter(b => includeDemo || b.source !== 'mock');
  const verification = status?.verification;
  return <>
    <section className="panel"><div className="panel-title"><div><p className="eyebrow">GROUNDED READS · REVIEWED ACTIONS</p><h2>AI Agent</h2></div><Badge tone={status?.configured ? 'success' : ''}>{status?.configured ? `${status.provider} · ${status.model}` : 'Provider not connected'}</Badge></div>
      <p>Ask about saved evidence, prepare work, or propose an automation. Every change requires your review of the exact action. Conversations and results survive page reloads.</p>
      <Notice error={error} />
      <div className="agent-verification"><div><strong>Live AI verification</strong><p className="hint">Checks provider tool calling, a read of real workspace records, and an answer matching that read. It performs no writes and does not guarantee every future answer.</p>
        {verification && <><Badge tone={verification.passed ? 'success' : 'error'}>{verification.passed ? 'Round trip passed' : 'Verification failed'}</Badge><small className="record-time">{date(verification.checked_at)}{verification.passed && ` · ${verification.business_count} real businesses · 0 writes`}</small>{verification.error && <p className="error">{verification.error}</p>}<ul>{verification.checks?.map((c: Row) => <li key={c.name}>{c.name}: {c.passed ? 'passed' : 'failed'}</li>)}</ul></>}
        {!verification && <Badge>Not checked in this server session</Badge>}</div><button className="secondary" disabled={busy || !status?.configured} onClick={() => void act(async () => { await api('agent/verify', json({})); await refresh(); })}>Verify live AI</button></div>
      {!status?.configured && <div className="notice">Set <code>GEMINI_API_KEY</code> on the backend and restart it. Get a key from <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer">Google AI Studio ↗</a>. Do not paste credentials into chat.</div>}
      {status?.local_connection_allowed && <details className="setup-details"><summary>Local laptop provider connection</summary><p className="hint">For this running backend session only. For a hosted server, use private environment settings.</p><form className="feature-form" onSubmit={connect}><label>Provider<select value={provider} onChange={e => { setProvider(e.target.value); setModel(e.target.value === 'gemini' ? 'gemini-3.5-flash-lite' : 'gpt-4.1-mini'); }}><option value="gemini">Gemini</option><option value="openai">OpenAI</option></select></label><label>Model<input value={model} onChange={e => setModel(e.target.value)} maxLength={100} /></label><label className="wide">API key<input type="password" autoComplete="off" value={key} onChange={e => setKey(e.target.value)} required /></label><button className="primary" disabled={busy || !key}>Connect and check provider</button>{status.configured && <button type="button" className="secondary" disabled={busy} onClick={() => void act(async () => { setStatus(await api('agent/connection', { method: 'DELETE' })); await onChanged(); })}>Disconnect session</button>}</form></details>}
    </section>
    <div className="agent-layout"><section className="panel conversation-list"><div className="panel-title"><h3>Conversations</h3><button className="secondary" disabled={busy} onClick={() => { setConversation(null); createKey.current = ''; pendingMessage.current = null; setRetryAvailable(false); setInput(''); }}>New</button></div>{conversations.length ? conversations.map(c => <button key={c.id} className={'conversation-button ' + (conversation?.id === c.id ? 'selected' : '')} disabled={busy} onClick={() => void open(c.id)}><strong>{c.title}</strong><small>{date(c.updated_at)}</small></button>) : <Empty>Your first conversation is saved when you send a message.</Empty>}</section>
      <section className="panel chat-panel"><div className="controls agent-scope"><label><input type="checkbox" disabled={busy || retryAvailable} checked={includeDemo} onChange={e => { setIncludeDemo(e.target.checked); if (!e.target.checked && businesses.find(b => b.id === businessId)?.source === 'mock') setBusinessId(''); }} /> Include fictional demos</label><select aria-label="Agent business scope" disabled={busy || retryAvailable} value={businessId} onChange={e => setBusinessId(e.target.value)}><option value="">Whole workspace</option>{visibleBusinesses.map(b => <option key={b.id} value={b.id}>{b.business.name}{b.source === 'mock' ? ' · DEMO' : ''}</option>)}</select></div>
        <div className="chat-messages" aria-live="polite">{conversation?.turns?.length ? conversation.turns.map((turn: Row) => <div key={turn.id}><div className="bubble user"><small>You · {date(turn.created_at)}</small><p>{turn.message}</p>{turn.include_demo && <Badge tone="demo">Demo scope included</Badge>}</div><div className="bubble assistant"><small>AI Agent · {turn.status}</small><p>{turn.reply || (turn.status === 'running' ? 'This turn is in progress. Refresh this conversation to check its saved result.' : 'No completed reply was recorded.')}</p>{turn.error && <p className="error">{turn.error}</p>}{turn.events?.length > 0 && <details><summary>Tools used ({turn.events.length})</summary>{turn.events.map((e: Row, i: number) => <div className="evidence" key={i}><strong>{e.tool.replaceAll('_', ' ')} · {e.status.replaceAll('_', ' ')}</strong><Result value={e.result || {}} /></div>)}</details>}</div></div>) : <Empty>Try “Summarize my real leads and pending tasks” or “Check my n8n connection and suggest the next safe step.”</Empty>}</div>
        {retryAvailable && <div className="notice">The last request did not return a confirmed reply. Retry uses the same saved request ID and original inputs. Open this conversation to inspect it before starting a different request.</div>}
        <form className="chat-form" onSubmit={send}><input aria-label="Message to AI Agent" value={input} onChange={e => setInput(e.target.value)} maxLength={4000} disabled={busy || retryAvailable || !status?.configured} placeholder="Ask about saved leads or propose a reviewed action…" /><button className="primary" disabled={busy || !status?.configured || (!input.trim() && !retryAvailable)}>{busy ? 'Working…' : retryAvailable ? 'Retry original request' : 'Send →'}</button></form>
        {conversation && <button className="text-button conversation-refresh" disabled={busy} onClick={() => void open(conversation.id)}>Refresh saved conversation</button>}
      </section></div>
    {conversation && conversation.actions?.length > 0 && <section className="panel"><p className="eyebrow">EXACT ACTION REVIEW</p><h2>Proposals and recorded results</h2>{conversation.actions.map((action: Row) => <div className="proposal" key={action.id}><div className="panel-title"><h3>{action.tool.replaceAll('_', ' ')}</h3><Badge tone={action.status === 'succeeded' ? 'success' : action.status === 'uncertain' || action.status === 'failed' ? 'error' : ''}>{action.status.replaceAll('_', ' ')}</Badge></div><p>{action.summary || 'Review the saved arguments before approving.'}</p><pre className="output">{JSON.stringify(action.arguments, null, 2)}</pre>{action.error && <p className="error">{action.error}</p>}{action.status === 'pending_review' && <><small>Expires {date(action.expires_at)}</small><label><input type="checkbox" checked={!!approved[action.id]} disabled={busy} onChange={e => setApproved({ ...approved, [action.id]: e.target.checked })} /> I reviewed these exact inputs and authorize this action</label><div className="controls"><button className="primary" disabled={busy || !approved[action.id]} onClick={() => void review(action, 'approve')}>Approve and execute</button><button className="secondary" disabled={busy} onClick={() => void review(action, 'reject')}>Reject</button></div></>}{action.result && <Result value={action.result} />}{action.status === 'uncertain' && <p className="hint">Inspect the underlying workflow, task or delivery record before requesting another action.</p>}</div>)}</section>}
  </>;
}
