'use client';
import { useCallback, useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import Outreach from './outreach';

const WorkflowGraph = dynamic(() => import('./workflow-graph'), { ssr: false, loading: () => <p>Loading workflow graph…</p> });
type AnyRow = Record<string, any>;
export type View = 'dashboard' | 'discover' | 'leads' | 'tasks' | 'workflows' | 'lab' | 'chat' | 'settings';
const sections: { id: View; label: string }[] = [
  { id: 'dashboard', label: 'Overview' }, { id: 'discover', label: 'Discover' },
  { id: 'leads', label: 'Leads' }, { id: 'tasks', label: 'Tasks' },
  { id: 'workflows', label: 'Workflows' }, { id: 'lab', label: 'Automation lab' },
  { id: 'chat', label: 'AI assistant' }, { id: 'settings', label: 'Connections' },
];

function Icon({ name }: { name: View }) {
  const common = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  const paths: Record<View, React.ReactNode> = {
    dashboard: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></>,
    discover: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></>,
    leads: <><circle cx="9" cy="8" r="3" /><path d="M3 20v-2a6 6 0 0 1 12 0v2M17 5a3 3 0 0 1 0 6M21 20v-2a5 5 0 0 0-3-4.6" /></>,
    tasks: <><rect x="4" y="3" width="16" height="18" rx="2" /><path d="m8 12 2.5 2.5L16 9" /></>,
    workflows: <><circle cx="5" cy="5" r="2" /><circle cx="19" cy="8" r="2" /><circle cx="12" cy="19" r="2" /><path d="M7 5h5a7 7 0 0 1 7 1M18 10v2a7 7 0 0 1-5 6M10 19H9a5 5 0 0 1-5-5V7" /></>,
    lab: <><circle cx="12" cy="12" r="9" /><path d="m10 8 6 4-6 4z" /></>,
    chat: <><path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8zM19 18l.5 1.5L21 20l-1.5.5L19 22l-.5-1.5L17 20l1.5-.5z" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  };
  return <svg width="21" height="21" viewBox="0 0 24 24" aria-hidden="true" {...common}>{paths[name]}</svg>;
}

async function api(path: string, init?: RequestInit): Promise<any> {
  const response = await fetch('/api/backend/' + path.replace(/^\//, ''), { cache: 'no-store', ...init });
  const type = response.headers.get('content-type') || '';
  const data = type.includes('json') ? await response.json() : await response.blob();
  if (!response.ok) throw Error(data?.error?.message || data?.error || `Request failed (${response.status})`);
  return data;
}
const json = (data: object): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
const date = (value?: string) => value ? new Date(value).toLocaleString() : 'Unknown';
function Badge({ children, tone = '' }: { children: React.ReactNode; tone?: string }) { return <span className={'badge ' + tone}>{children}</span>; }
function Empty({ text }: { text: string }) { return <div className="empty"><span className="empty-mark" aria-hidden="true">✦</span><span>{text}</span></div>; }
function Notice({ error }: { error: string }) { return error ? <div className="notice error" role="alert">{error}</div> : null; }

export default function Workspace({ initialView = 'dashboard' }: { initialView?: View }) {
  const [view, setView] = useState<View>(initialView); const [leadId, setLeadId] = useState('');
  const [search, setSearch] = useState(''); const [businesses, setBusinesses] = useState<AnyRow[]>([]);
  const [prospects, setProspects] = useState<AnyRow[]>([]); const [tasks, setTasks] = useState<AnyRow[]>([]);
  const [appointments, setAppointments] = useState<AnyRow[]>([]); const [workflows, setWorkflows] = useState<AnyRow[]>([]);
  const [jobs, setJobs] = useState<AnyRow[]>([]); const [cap, setCap] = useState<AnyRow | null>(null);
  const [collector, setCollector] = useState<AnyRow | null>(null); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [includeDemo, setIncludeDemo] = useState(false);

  const load = useCallback(async () => {
    setError('');
    try {
      const capability = await api('capabilities'); setCap(capability);
      const rows = await Promise.allSettled([
        api('businesses?limit=500'), api(`prospects?limit=500&include_demo=${includeDemo}`),
        capability.crm_history_supported ? api('tasks?limit=500') : Promise.resolve([]),
        capability.client_workflow_activation_supported ? api('appointments?limit=500') : Promise.resolve([]),
        api('workflows?limit=500'), api('discovery/jobs'), api('discovery/collector-status'),
      ]);
      const setters = [setBusinesses, setProspects, setTasks, setAppointments, setWorkflows, setJobs, setCollector];
      const problems: string[] = [];
      rows.forEach((row, i) => { if (row.status === 'fulfilled') setters[i](row.value); else problems.push(row.reason?.message || 'Could not load saved records'); });
      if (problems.length) setError([...new Set(problems)].join(' · '));
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not load workspace'); }
    finally { setInitialLoading(false); }
  }, [includeDemo]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const sync = () => { const part = location.pathname.slice(1) || 'dashboard'; if (sections.some(s => s.id === part)) setView(part as View); setLeadId(new URLSearchParams(location.search).get('lead') || ''); };
    sync(); window.addEventListener('popstate', sync); return () => window.removeEventListener('popstate', sync);
  }, []);
  const visible = useMemo(() => businesses.filter(r => (includeDemo || r.source !== 'mock') && (!search || [r.business?.name, r.business?.address, r.business?.website].join(' ').toLowerCase().includes(search.toLowerCase()))), [businesses, includeDemo, search]);
  const selected = businesses.find(r => r.id === leadId);
  const prospect = prospects.find(r => r.business_id === leadId);
  const headings: Record<View, string> = { dashboard: 'Workspace overview', discover: 'Discover & import', leads: 'Lead research', tasks: 'Follow-up tasks', workflows: 'Workflow drafts', lab: 'Automation lab', chat: 'AI assistant', settings: 'Connections' };
  function navigate(section: View) { setView(section); setLeadId(''); history.pushState({}, '', section === 'dashboard' ? '/' : '/' + section); }
  function openLead(id: string) { setLeadId(id); setView('leads'); history.pushState({}, '', '/leads?lead=' + encodeURIComponent(id)); }
  async function action(fn: () => Promise<void>) { setBusy(true); setError(''); try { await fn(); await load(); } catch (e) { setError(e instanceof Error ? e.message : 'Action failed'); } finally { setBusy(false); } }
  return <div className="shell">
    <aside className="rail"><div className="logo" aria-label="AIAutomation"><img src="/logo-color.png" alt="" /></div><nav aria-label="Sections">{sections.map(s => <button key={s.id} className={view === s.id ? 'active' : ''} title={s.label} aria-label={s.label} onClick={() => navigate(s.id)}><Icon name={s.id} /></button>)}</nav><button title="Lock workspace" aria-label="Lock workspace" onClick={async () => { await fetch('/api/access', { method: 'DELETE' }); location.href = '/login'; }}>⇥</button></aside>
    <aside className="side"><div className="brand"><span>AIAutomation</span><small>Med spa workspace</small></div><p className="side-label">WORKSPACE</p>{sections.map(s => <button key={s.id} className={view === s.id ? 'selected' : ''} onClick={() => navigate(s.id)}>{s.label}<span>↗</span></button>)}<div className="side-bottom"><span className="pulse" /> Research • Review • Sandbox</div></aside>
    <main className="content"><header className="topbar"><div><small>Workspace / {headings[view]}</small><h1>{leadId && selected ? selected.business.name : headings[view]}</h1></div><div className="top-actions"><input aria-label="Search saved leads" placeholder="Search saved leads…" value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') navigate('leads'); }} /><button className="icon-button" onClick={() => void load()} aria-label="Refresh">↻</button></div></header>
      <div className="mobile-nav"><select aria-label="Sections" value={view} onChange={e => navigate(e.target.value as View)}>{sections.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}</select></div>
      <div className="page">{initialLoading ? <div className="loading-state" role="status" aria-live="polite"><div className="loading-banner shimmer" /><div className="loading-row"><div className="loading-card shimmer" /><div className="loading-card shimmer" /></div><p>Loading saved workspace…</p></div> : <><Notice error={error} />
        {view === 'dashboard' && <Dashboard prospects={prospects} businesses={businesses} tasks={tasks} appointments={appointments} jobs={jobs} onLead={openLead} />}
        {view === 'discover' && <Discover collector={collector} jobs={jobs} busy={busy} action={action} refresh={load} />}
        {view === 'leads' && (leadId && selected ? <LeadDetail record={selected} prospect={prospect} cap={cap} busy={busy} action={action} back={() => navigate('leads')} /> : <Leads rows={visible} prospects={prospects} includeDemo={includeDemo} setIncludeDemo={setIncludeDemo} onLead={openLead} />)}
        {view === 'tasks' && <Tasks rows={tasks} businesses={businesses} onLead={openLead} />}
        {view === 'workflows' && <Workflows rows={workflows} businesses={businesses} />}
        {view === 'lab' && <Lab appointments={appointments} workflows={workflows} cap={cap} busy={busy} action={action} />}
        {view === 'chat' && <Chat configured={!!cap?.gemini_configured} />}
        {view === 'settings' && <Settings cap={cap} collector={collector} />}</>}
      </div>
    </main>
  </div>;
}

function Dashboard({ prospects, businesses, tasks, appointments, jobs, onLead }: { prospects: AnyRow[]; businesses: AnyRow[]; tasks: AnyRow[]; appointments: AnyRow[]; jobs: AnyRow[]; onLead: (id: string) => void }) {
  const top = prospects.filter(p => p.prospect_status === 'ready_for_review').slice(0, 3);
  const name = (id: string) => businesses.find(b => b.id === id)?.business?.name || 'Saved lead';
  const realIds = new Set(businesses.filter(b => b.source !== 'mock').map(b => b.id));
  const realTasks = tasks.filter(t => realIds.has(t.business_id));
  const realAppointments = appointments.filter(a => realIds.has(a.business_id));
  const timeline: AnyRow[] = [...realTasks.filter(t => t.status === 'pending').map(t => ({ ...t, at: t.due_at, label: t.title, sandbox: false })), ...realAppointments.filter(a => a.status !== 'cancelled').map(a => ({ ...a, at: a.starts_at, label: 'Appointment reminder', sandbox: true }))].sort((a, b) => String(a.at).localeCompare(String(b.at))).slice(0, 8);
  return <><div className="hero"><div><p className="eyebrow">RESEARCH → REVIEW → AUTOMATE</p><h2>Find the right med spas.<br />Keep every next step clear.</h2><p>Public evidence supports prospect review. Internal needs stay unconfirmed until a business confirms them.</p></div><div className="hero-orb">✦</div></div>
    <div className="stats"><div><strong>{realIds.size}</strong><span>Saved real listings</span></div><div><strong>{prospects.filter(p => p.prospect_status === 'ready_for_review').length}</strong><span>Ready for review</span></div><div><strong>{realTasks.filter(t => t.status === 'pending').length}</strong><span>Open tasks</span></div><div><strong>{jobs.filter(j => j.status === 'succeeded').length}</strong><span>Successful pilot runs</span></div></div>
    <div className="two-col"><section className="panel"><div className="panel-title"><div><p className="eyebrow">PUBLIC QUALIFICATION</p><h2>Top prospects</h2></div><Badge>Unconfirmed needs</Badge></div>{top.length ? top.map((p, i) => <button className={'prospect-card ' + (i === 0 ? 'featured' : '')} key={p.business_id} onClick={() => onLead(p.business_id)}><span><strong>{name(p.business_id)}</strong><small>{p.prospect_status?.replaceAll('_', ' ')}</small></span><span className="score"><strong>{p.prospect_score ?? 0}</strong><small>score · {Math.round(p.public_evidence_coverage ?? 0)}% coverage</small></span></button>) : <Empty text="No review-ready prospects yet. Confirm business category and add supported public evidence before ranking leads." />}</section>
    <section className="panel"><div className="panel-title"><div><p className="eyebrow">RECORDED FOLLOW-UPS</p><h2>Timeline</h2></div><Badge>Local time</Badge></div><div className="timeline"><div className="now-line"><span>NOW</span></div>{timeline.length ? timeline.map((item, i) => <div key={item.id || i} className="timeline-item"><time>{date(item.at)}</time><div><strong>{item.label}</strong><small>{name(item.business_id)} {item.sandbox && '· sandbox unsent preview'}</small></div></div>) : <Empty text="No recorded tasks or sandbox appointments yet." />}</div></section></div></>;
}

function Leads({ rows, prospects, includeDemo, setIncludeDemo, onLead }: { rows: AnyRow[]; prospects: AnyRow[]; includeDemo: boolean; setIncludeDemo: (v: boolean) => void; onLead: (id: string) => void }) {
  const [sort, setSort] = useState<'name' | 'score'>('score'); const [filter, setFilter] = useState('all');
  const pmap = new Map(prospects.map(p => [p.business_id, p]));
  const shown = rows.filter(r => filter === 'all' || pmap.get(r.id)?.prospect_status === filter).sort((a, b) => sort === 'name' ? a.business.name.localeCompare(b.business.name) : (pmap.get(b.id)?.prospect_score || 0) - (pmap.get(a.id)?.prospect_score || 0));
  return <section className="panel"><div className="panel-title"><div><p className="eyebrow">SAVED RECORDS</p><h2>Leads</h2></div><div className="controls"><label><input type="checkbox" checked={includeDemo} onChange={e => setIncludeDemo(e.target.checked)} /> Show demos</label><select aria-label="Filter leads" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All statuses</option><option value="ready_for_review">Ready for review</option><option value="research">Needs research</option><option value="not_analyzed">Not analyzed</option></select><select aria-label="Sort leads" value={sort} onChange={e => setSort(e.target.value as 'name' | 'score')}><option value="score">Prospect score</option><option value="name">Name</option></select></div></div>{shown.length ? <div className="table-wrap"><table><thead><tr><th>Business</th><th>Source</th><th>Public score</th><th>Coverage</th><th>Status</th></tr></thead><tbody>{shown.map(r => { const p = pmap.get(r.id); return <tr key={r.id} onClick={() => onLead(r.id)} tabIndex={0} onKeyDown={e => { if (e.key === 'Enter') onLead(r.id); }}><td><strong>{r.business.name}</strong><small>{r.business.address || 'Address unknown'}</small></td><td>{r.source === 'mock' ? <Badge tone="demo">DEMO</Badge> : r.source}</td><td>{p?.prospect_score ?? '—'}</td><td>{p ? Math.round(p.public_evidence_coverage) + '%' : '—'}</td><td><Badge>{p?.prospect_status?.replaceAll('_', ' ') || 'Not analyzed'}</Badge></td></tr>; })}</tbody></table></div> : <Empty text="No saved leads match this view. Use Discover to preview a CSV before import." />}</section>;
}

function LeadDetail({ record, prospect, cap, busy, action, back }: { record: AnyRow; prospect?: AnyRow; cap: AnyRow | null; busy: boolean; action: (fn: () => Promise<void>) => void; back: () => void }) {
  const [analysis, setAnalysis] = useState<AnyRow | null>(null); const [insights, setInsights] = useState<AnyRow[]>([]); const [draft, setDraft] = useState<AnyRow | null>(null); const [localError, setLocalError] = useState(''); const [activityRevision, setActivityRevision] = useState(0);
  const refresh = useCallback(async () => { const [a, i] = await Promise.all([api(`analyses?business_id=${encodeURIComponent(record.id)}&limit=1`), api(`ai/businesses/${record.id}/insights`)]); setAnalysis(a[0] || null); setInsights(i.filter((row: AnyRow) => !row.kind || row.kind === 'analysis')); }, [record.id]);
  useEffect(() => { void refresh().catch(e => setLocalError(e.message)); }, [refresh]);
  const b = record.business;
  async function run(path: string, setter: (v: AnyRow) => void) { setLocalError(''); try { setter(await api(path, json({}))); await refresh(); } catch (e) { setLocalError(e instanceof Error ? e.message : 'AI request failed'); } }
  return <><button className="text-button" onClick={back}>← All leads</button><Notice error={localError} /><div className="detail-grid"><section className="panel"><div className="panel-title"><h2>{b.name}</h2>{record.source === 'mock' ? <Badge tone="demo">DEMO</Badge> : <Badge>{record.source}</Badge>}</div><p>{b.address || 'Address unknown'}</p><div className="detail-list"><span>Website</span><strong>{b.website || 'Unknown'}</strong><span>Phone</span><strong>{b.phone || 'Unknown'}</strong><span>Rating</span><strong>{b.rating ?? 'Unknown'} · {b.review_count ?? 'Unknown'} reviews</strong><span>Imported</span><strong>{date(record.created_at)}</strong></div><p className="hint">Listing contact details are not proof of reachability. Verify category and source before outreach.</p></section>
  <section className="panel"><p className="eyebrow">PUBLIC QUALIFICATION</p><h2>Evidence snapshot</h2><div className="metric-row"><div><strong>{prospect?.prospect_score ?? '—'}</strong><small>Prospect score</small></div><div><strong>{prospect ? Math.round(prospect.public_evidence_coverage) + '%' : '—'}</strong><small>Public coverage</small></div></div><Badge>{prospect?.prospect_status?.replaceAll('_', ' ') || 'Not analyzed'}</Badge><p>Internal operational needs are unconfirmed unless recorded business evidence says otherwise.</p>{analysis ? <><h3>Latest analysis</h3><p>{analysis.summary}</p><small>Saved {date(analysis.created_at)} · {analysis.mode}</small><h3>Observed evidence</h3>{analysis.evidence?.length ? analysis.evidence.map((e: AnyRow, i: number) => <div className="evidence" key={i}><strong>{e.criterion.replaceAll('_', ' ')} · {e.assessment}</strong><p>{e.detail}</p><small>{e.source} · {date(e.observed_at)}</small></div>) : <Empty text="No criterion evidence saved." />}<h3>Unknowns</h3><p>{analysis.unknown_criteria?.join(', ') || 'None listed'}</p></> : <Empty text="No saved analysis. Run the rules-based analysis first." />}{!analysis && <button className="secondary" disabled={busy} onClick={() => action(async () => { await api(`businesses/${record.id}/analyze`, json({ fetch_website: false, use_ai: false, evidence: [] })); await refresh(); })}>Create rules analysis</button>}</section></div>
  <Outreach key={record.id} record={record} analysis={analysis} geminiConfigured={!!cap?.gemini_configured} onLogged={() => setActivityRevision(value => value + 1)} />
  <LeadActivity businessId={record.id} enabled={!!cap?.crm_history_supported} busy={busy} action={action} revision={activityRevision} />
  {analysis && <section className="panel"><p className="eyebrow">BUILD · REVIEWED DRAFT</p><h2>Workflow graph</h2><p>Create a generated JSON draft from this saved analysis. External automation execution is not available.</p><button className="secondary" disabled={busy || analysis.automation_type === 'research_required'} onClick={() => action(async () => { await api('workflows', json({ analysis_id: analysis.id })); })}>Create workflow draft</button>{analysis.automation_type === 'research_required' && <p className="hint">More supported evidence is needed before a workflow can be generated.</p>}</section>}
  <section className="panel"><div className="panel-title"><div><p className="eyebrow">GEMINI · RESEARCH ONLY</p><h2>AI research insight</h2></div><Badge>Estimate only</Badge></div>{cap?.gemini_configured ? <button className="secondary" disabled={!analysis || busy} onClick={() => void run(`ai/businesses/${record.id}/analysis`, setDraft)}>Analyze saved evidence</button> : <p>Gemini is not configured. Rule-based analysis remains available above.</p>}{draft && <pre className="output">{JSON.stringify(draft.insight || draft, null, 2)}</pre>}{insights.length > 0 && <div className="insight-list"><h3>Saved AI insights</h3>{insights.map(i => <div className="evidence" key={i.id}><Badge>AI estimate</Badge><p>{i.insight?.summary}</p><small>{date(i.created_at)} · {i.model} · separate from evidence score</small></div>)}</div>}</section></>;
}

function LeadActivity({ businessId, enabled, busy, action, revision }: { businessId: string; enabled: boolean; busy: boolean; action: (fn: () => Promise<void>) => void; revision: number }) {
  const [contact, setContact] = useState<AnyRow | null>(null); const [activities, setActivities] = useState<AnyRow[]>([]); const [tasks, setTasks] = useState<AnyRow[]>([]);
  const [title, setTitle] = useState(''); const [due, setDue] = useState(''); const [key, setKey] = useState(''); const [error, setError] = useState('');
  const refresh = useCallback(async () => { if (!enabled) return; try { const [c, a, t] = await Promise.all([api(`businesses/${businessId}/contact`), api(`businesses/${businessId}/activities`), api(`tasks?business_id=${encodeURIComponent(businessId)}`)]); setContact(c); setActivities(a); setTasks(t); } catch (e) { setError(e instanceof Error ? e.message : 'Could not load contact history'); } }, [businessId, enabled]);
  useEffect(() => { void refresh(); }, [refresh, revision]);
  async function save(e: React.FormEvent) { e.preventDefault(); const stable = key || crypto.randomUUID(); setKey(stable); await action(async () => { await api(`businesses/${businessId}/tasks`, json({ idempotency_key: stable, title, due_at: new Date(due).toISOString(), notes: '' })); setTitle(''); setDue(''); setKey(''); await refresh(); }); }
  return <section className="panel"><p className="eyebrow">CRM RECORD</p><h2>Contact & follow-up</h2>{enabled ? <><Notice error={error} /><p>Stage: <Badge>{contact?.stage || 'new'}</Badge> · Manual history does not prove an operational gap.</p><div className="two-col"><div><h3>Activities</h3>{activities.length ? activities.slice(0, 8).map((a, i) => <div className="evidence" key={a.id || i}><strong>{a.kind || 'Activity'} · {date(a.occurred_at)}</strong><p>{a.notes}</p></div>) : <Empty text="No contact activity recorded." />}</div><div><h3>Tasks</h3>{tasks.length ? tasks.slice(0, 8).map(t => <div className="evidence" key={t.id}><strong>{t.title} · {t.status}</strong><p>Due {date(t.due_at)}</p></div>) : <Empty text="No follow-up tasks recorded." />}</div></div><form onSubmit={save} className="task-form"><h3>Create manual follow-up</h3><label>Task title<input value={title} onChange={e => { setTitle(e.target.value); setKey(''); }} required maxLength={200} /></label><label>Due date and time<input type="datetime-local" value={due} onChange={e => { setDue(e.target.value); setKey(''); }} required /></label><button className="secondary" disabled={busy}>Save task</button></form></> : <Empty text="Task and contact history are unavailable on this storage backend." />}</section>;
}

function Discover({ collector, jobs, busy, action, refresh }: { collector: AnyRow | null; jobs: AnyRow[]; busy: boolean; action: (fn: () => Promise<void>) => void; refresh: () => Promise<void> }) {
  const [query, setQuery] = useState('medical spas in Islamabad, Pakistan'); const [limit, setLimit] = useState(5); const [file, setFile] = useState<File | null>(null); const [report, setReport] = useState<AnyRow | null>(null); const [jobReport, setJobReport] = useState<AnyRow | null>(null);
  const ready = !!collector?.ready || !!collector?.available;
  async function upload(dryRun: boolean) { if (!file) return; await action(async () => { const path = `businesses/import-csv?dry_run=${dryRun}&file_name=${encodeURIComponent(file.name)}`; setReport(await api(path, { method: 'POST', headers: { 'Content-Type': 'text/csv' }, body: await file.arrayBuffer() })); }); }
  return <><div className="two-col"><section className="panel"><p className="eyebrow">OPTION 01 · LOCAL COLLECTION</p><h2>Maps pilot</h2><p>Collect a small sample, preview source and category, then explicitly import. A live job never falls back to mock leads.</p><label>Business + location<input value={query} onChange={e => setQuery(e.target.value)} maxLength={180} /></label><label>Maximum listings<input type="number" value={limit} min={1} max={10} onChange={e => setLimit(Number(e.target.value))} /></label><div className="notice">{ready ? 'Collector appears ready. A live search still depends on Maps access and readable results.' : 'Live collection is unavailable here. Run the local Edge collector and import its CSV into this workspace.'}</div><button className="primary" disabled={!ready || busy || !query.trim()} onClick={() => action(async () => { await api('discovery/jobs', json({ query, limit })); })}>Start live pilot →</button><p className="hint">Google Maps opens only for local browser collection. The collected CSV and source pages stay in preview until you import.</p></section>
    <section className="panel"><p className="eyebrow">OPTION 02 · HOSTED PATH</p><h2>Import a reviewed CSV</h2><p>Export from the local collector or a browser extension. Review business type and each source before saving.</p><label>CSV file<input type="file" accept=".csv,text/csv" onChange={e => { setFile(e.target.files?.[0] || null); setReport(null); }} /></label><div className="controls"><button className="secondary" disabled={!file || busy} onClick={() => void upload(true)}>Preview CSV</button><button className="primary" disabled={!file || !report || busy} onClick={() => { if (confirm('Import only the reviewed rows in this CSV?')) void upload(false); }}>Import reviewed CSV</button></div>{report && <Report report={report} />}</section></div>
    <section className="panel"><div className="panel-title"><div><p className="eyebrow">COLLECTION HISTORY</p><h2>Recent pilots</h2></div><button className="secondary" onClick={() => void refresh()}>Refresh status</button></div>{jobs.length ? jobs.slice(0, 10).map(j => <div className="job" key={j.id}><div><strong>{j.query}</strong><small>{date(j.created_at)} · Limit {j.limit} · {j.collected_count ?? 0} collected</small></div><Badge tone={j.status === 'succeeded' ? 'success' : 'error'}>{j.status}</Badge>{j.status === 'succeeded' && <div className="controls"><button className="secondary" onClick={() => void action(async () => setJobReport(await api(`discovery/jobs/${j.id}/preview`, json({}))))}>Preview results</button><a className="secondary" href={`/api/backend/discovery/jobs/${j.id}/csv`}>Download CSV</a><button className="primary" onClick={() => { if (confirm('Import the reviewed pilot results?')) void action(async () => setJobReport(await api(`discovery/jobs/${j.id}/import`, json({})))); }}>Import reviewed</button></div>}{j.error && <p className="error">{j.error}</p>}</div>) : <Empty text="No pilot jobs yet. CSV import remains available." />}{jobReport && <Report report={jobReport} />}</section></>;
}

function Report({ report }: { report: AnyRow }) { return <div className="report"><h3>{report.dry_run ? 'Preview' : 'Import result'}</h3><p>{JSON.stringify({ total_rows: report.total_rows, imported: report.imported_rows, duplicates: report.duplicate_rows, invalid: report.invalid_rows }, null, 2)}</p>{Array.isArray(report.rows) && <div className="table-wrap"><table><thead><tr><th>Business</th><th>Status</th><th>Issues / category</th></tr></thead><tbody>{report.rows.map((r: AnyRow, i: number) => <tr key={i}><td>{r.business?.name || `Row ${r.row_number}`}</td><td>{r.status}</td><td>{[...(r.errors || []), ...(r.warnings || [])].join(', ')}</td></tr>)}</tbody></table></div>}</div>; }

function Tasks({ rows, businesses, onLead }: { rows: AnyRow[]; businesses: AnyRow[]; onLead: (id: string) => void }) {
  const [showDemo, setShowDemo] = useState(false);
  const demoIds = new Set(businesses.filter(b => b.source === 'mock').map(b => b.id));
  const visible = rows.filter(r => showDemo || !demoIds.has(r.business_id));
  return <section className="panel"><div className="panel-title"><div><p className="eyebrow">MANUAL FOLLOW-UP</p><h2>Recorded tasks</h2></div><label className="demo-toggle"><input type="checkbox" checked={showDemo} onChange={e => setShowDemo(e.target.checked)} /> Show demos</label></div>{visible.length ? visible.map(r => <button className="task-row" key={r.id} onClick={() => onLead(r.business_id)}><div><strong>{r.title}</strong><small>{businesses.find(b => b.id === r.business_id)?.business?.name || 'Lead'} · Due {date(r.due_at)}</small></div><div className="controls">{demoIds.has(r.business_id) && <Badge tone="demo">DEMO</Badge>}<Badge>{r.status}</Badge></div></button>) : <Empty text="No tasks in this view. Recorded tasks are manual follow-ups, not evidence of business operations." />}</section>;
}

function Workflows({ rows, businesses }: { rows: AnyRow[]; businesses: AnyRow[] }) {
  const [selected, setSelected] = useState(''); const [showDemo, setShowDemo] = useState(false);
  const [detail, setDetail] = useState<AnyRow | null>(null); const [detailError, setDetailError] = useState('');
  const demoIds = new Set(businesses.filter(b => b.source === 'mock').map(b => b.id));
  const visible = rows.filter(r => showDemo || !demoIds.has(r.business_id));
  const flow = visible.find(r => r.id === selected) || visible[0];
  const demoCount = rows.filter(r => demoIds.has(r.business_id)).length;
  useEffect(() => {
    if (!flow?.id) { setDetail(null); return; }
    let current = true; setDetail(null); setDetailError('');
    void api(`workflows/${flow.id}`).then(row => { if (current) setDetail(row); }).catch(e => { if (current) setDetailError(e instanceof Error ? e.message : 'Could not load workflow'); });
    return () => { current = false; };
  }, [flow?.id]);
  const currentFlow = detail?.id === flow?.id ? detail : null;
  return <section className="panel workflow-panel"><div className="panel-title"><div><p className="eyebrow">GENERATED JSON · REVIEW BEFORE USE</p><h2>Workflow drafts</h2></div><label className="demo-toggle"><input type="checkbox" checked={showDemo} onChange={e => setShowDemo(e.target.checked)} /> Show demos</label></div><p>Review the generated steps before a sandbox run. This graph does not execute external automation.</p>{visible.length ? <><select aria-label="Select workflow" value={flow?.id} onChange={e => setSelected(e.target.value)}>{visible.map(r => <option key={r.id} value={r.id}>{r.name} · {businesses.find(b => b.id === r.business_id)?.business?.name || 'Lead'}</option>)}</select>{flow && <><div className="workflow-meta"><Badge tone={demoIds.has(flow.business_id) ? 'demo' : ''}>{demoIds.has(flow.business_id) ? 'DEMO WORKFLOW' : 'SAVED WORKFLOW'}</Badge><span>{flow.status} · {date(flow.created_at)}</span></div><Notice error={detailError} />{currentFlow ? <div className="graph-wrap"><WorkflowGraph workflow={currentFlow as { nodes: { id: string; type: string }[]; connections: [string, string][] }} /></div> : !detailError && <div className="graph-wrap graph-loading shimmer" role="status">Loading graph…</div>}<p className="hint">Format: {flow.format}. External execution: {flow.execution_supported ? 'supported' : 'not supported'}.</p></>}</> : <div className="workflow-empty"><span className="workflow-empty-icon" aria-hidden="true"><Icon name="workflows" /></span><p className="eyebrow">START WITH REVIEWED EVIDENCE</p><h3>No real workflow drafts yet</h3><p>Open a lead, review its analysis, and create a supported draft. {demoCount > 0 ? `${demoCount} fictional demo drafts are hidden.` : ''}</p>{demoCount > 0 && <button className="secondary" onClick={() => setShowDemo(true)}>Explore demo graph →</button>}</div>}</section>;
}

function Lab({ appointments, workflows, cap, busy, action }: { appointments: AnyRow[]; workflows: AnyRow[]; cap: AnyRow | null; busy: boolean; action: (fn: () => Promise<void>) => void }) {
  const [result, setResult] = useState<AnyRow | null>(null); const [workflowId, setWorkflowId] = useState('');
  const [contactId, setContactId] = useState(''); const [message, setMessage] = useState('');
  const [starts, setStarts] = useState(''); const [remind, setRemind] = useState(''); const [permission, setPermission] = useState(false);
  const [eventKey, setEventKey] = useState(''); const [runs, setRuns] = useState<AnyRow[]>([]); const [outbox, setOutbox] = useState<AnyRow[]>([]);
  const eligible = workflows.filter(w => w.status === 'draft' && w.nodes?.[0]?.parameters?.event === 'appointment_reminders');
  useEffect(() => { if (cap?.workflow_runner_modes?.includes('sandbox')) void Promise.all([api('workflow-runs?limit=20'), api('workflow-outbox?limit=20')]).then(([r, o]) => { setRuns(r); setOutbox(o); }).catch(() => {}); }, [cap?.workflow_runner_modes]);
  async function schedule(e: React.FormEvent) {
    e.preventDefault();
    const key = eventKey || crypto.randomUUID(); setEventKey(key);
    await action(async () => {
      const scheduled = new Date(remind).toISOString(); const start = new Date(starts).toISOString();
      if (scheduled >= start || scheduled <= new Date().toISOString()) throw Error('Choose a future reminder time before the appointment.');
      const result = await api('appointments', json({ workflow_id: workflowId, starts_at: start, reminder: { mode: 'sandbox', confirm_sandbox: true, idempotency_key: key, event: { contact_id: contactId, contact_permission: permission, appointment_cancelled: false }, message_body: message, scheduled_at: scheduled } }));
      setResult(result); setEventKey('');
      const [r, o] = await Promise.all([api('workflow-runs?limit=20'), api('workflow-outbox?limit=20')]); setRuns(r); setOutbox(o);
    });
  }
  return <section className="panel"><p className="eyebrow">SANDBOX · NOTHING SENT</p><h2>Automation lab</h2><p>Appointments are supplied events, not calendar bookings. Sandbox reminders only create local unsent previews.</p>{cap?.workflow_runner_modes?.includes('sandbox') ? <><button className="secondary" disabled={busy} onClick={() => action(async () => { const r = await api('demo/reminder-workflow', json({})); setResult(r); setWorkflowId(r.workflow.id); })}>Create fictional reminder demo</button>
    <form onSubmit={schedule} className="lab-form"><h3>Schedule a sandbox reminder</h3><label>Reminder workflow<select value={workflowId} onChange={e => { setWorkflowId(e.target.value); setEventKey(''); }} required><option value="">Choose a reviewed draft</option>{eligible.map(w => <option key={w.id} value={w.id}>{w.name} · {w.business_id}</option>)}</select></label><label>Synthetic contact ID<input value={contactId} onChange={e => { setContactId(e.target.value); setEventKey(''); }} required pattern="[A-Za-z0-9_.:-]{1,100}" placeholder="fixture-contact-1" /></label><label>Appointment time<input type="datetime-local" value={starts} onChange={e => { setStarts(e.target.value); setEventKey(''); }} required /></label><label>Reminder time<input type="datetime-local" value={remind} onChange={e => { setRemind(e.target.value); setEventKey(''); }} required /></label><label>Message preview<input value={message} onChange={e => { setMessage(e.target.value); setEventKey(''); }} required maxLength={1000} placeholder="Synthetic reminder text" /></label><label><input type="checkbox" checked={permission} onChange={e => { setPermission(e.target.checked); setEventKey(''); }} required /> I confirm this synthetic contact permits this sandbox reminder</label><button className="primary" disabled={busy || !eligible.length}>Schedule unsent preview</button></form>
    {result && <pre className="output">{JSON.stringify(result, null, 2)}</pre>}<h3>Appointment history</h3>{appointments.length ? appointments.map(a => <div className="task-row" key={a.id}><div><strong>{date(a.starts_at)}</strong><small>{a.status} · sandbox unsent preview</small></div><div className="controls"><Badge tone="demo">SANDBOX</Badge>{a.status !== 'cancelled' && <button className="secondary" disabled={busy} onClick={() => action(async () => { await api(`appointments/${a.id}/cancel`, json({})); })}>Cancel</button>}</div></div>) : <Empty text="No sandbox appointments recorded yet." />}<h3>Run history</h3>{runs.length ? runs.map(r => <div className="task-row" key={r.id}><div><strong>{r.status} · {r.mode}</strong><small>{date(r.created_at)} · sent: {String(r.sent)}</small></div><Badge>{r.result || r.stop_reason || 'pending'}</Badge></div>) : <Empty text="No runs recorded." />}<h3>Unsent outbox previews</h3>{outbox.length ? outbox.filter(o => o.mode === 'sandbox').map(o => <div className="evidence" key={o.id}><strong>{o.status} · sent: {String(o.sent)}</strong><p>{o.message_body}</p></div>) : <Empty text="No sandbox previews yet." />}</> : <Empty text="Sandbox runner is unavailable on this storage backend." />}</section>;
}

function Chat({ configured }: { configured: boolean }) {
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; text: string }[]>([]); const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [proposal, setProposal] = useState<AnyRow | null>(null);
  const [title, setTitle] = useState(''); const [due, setDue] = useState(''); const [key, setKey] = useState('');
  async function send(e: React.FormEvent) { e.preventDefault(); if (!input.trim() || busy) return; const message = input.trim(); setInput(''); setBusy(true); setError(''); setProposal(null); try { const reply = await api('ai/chat', json({ message, history: messages.slice(-8) })); setMessages([...messages, { role: 'user', text: message }, { role: 'assistant', text: reply.answer }]); setProposal(reply.proposed_action); } catch (e) { setError(e instanceof Error ? e.message : 'AI unavailable'); setInput(message); } finally { setBusy(false); } }
  async function confirmAction(e: React.FormEvent) {
    e.preventDefault(); if (!proposal || busy) return; setBusy(true); setError('');
    try {
      let result: AnyRow;
      if (proposal.type === 'create_task') { const stable = key || crypto.randomUUID(); setKey(stable); result = await api(`businesses/${proposal.business_id}/tasks`, json({ idempotency_key: stable, title, due_at: new Date(due).toISOString(), notes: '' })); }
      else if (proposal.type === 'run_ai_analysis') result = await api(`ai/businesses/${proposal.business_id}/analysis`, json({}));
      else throw Error('Open the lead record and enter your sender profile to create this draft.');
      const summary = proposal.type === 'create_task' ? `Manual task saved: ${result.title}` : `AI insight saved: ${result.insight?.summary || 'Review the lead record'}`;
      setMessages(m => [...m, { role: 'assistant', text: summary }]); setProposal(null); setKey(''); setTitle(''); setDue('');
    } catch (e) { setError(e instanceof Error ? e.message : 'Action failed'); } finally { setBusy(false); }
  }
  if (!configured) return <section className="panel chat-panel ai-connect"><p className="eyebrow">AI ASSISTANT · SETUP REQUIRED</p><h2>Connect Gemini to ask about saved records</h2><p>Gemini is not configured in the current backend process. The lead detail page can still create rule-based email drafts.</p><p>Run <code>pwsh -File START-GEMINI-BACKEND.ps1</code> from this project folder and enter the key at its hidden prompt, then refresh the workspace.</p><p className="hint">The key stays out of the browser and project files.</p></section>;
  return <section className="panel chat-panel"><p className="eyebrow">READ-ONLY ASSISTANT</p><h2>Ask about saved records</h2><p>The assistant reads selected CRM data. Any task or AI draft requires your separate confirmation below.</p><Notice error={error} /><div className="chat-messages">{messages.length ? messages.map((m, i) => <div className={'bubble ' + m.role} key={i}><small>{m.role === 'user' ? 'You' : 'AI assistant'}</small><p>{m.text}</p></div>) : <Empty text="Ask about a saved prospect, qualification, analysis or pending task." />}</div>{proposal && <form className="proposal" onSubmit={confirmAction}><h3>Confirm proposed action</h3><p>{proposal.type.replaceAll('_', ' ')} for saved business {proposal.business_id}. Nothing has run yet.</p>{proposal.type === 'create_task' && <><label>Task title<input value={title} onChange={e => { setTitle(e.target.value); setKey(''); }} required maxLength={200} /></label><label>Due date and time<input type="datetime-local" value={due} onChange={e => { setDue(e.target.value); setKey(''); }} required /></label></>}{proposal.type === 'generate_pitch' && <p>Enter your sender profile on the lead detail page before generating a draft.</p>}<div className="controls">{proposal.type === 'generate_pitch' ? <a className="primary" href={`/leads?lead=${encodeURIComponent(proposal.business_id)}`}>Open lead</a> : <button className="primary" disabled={busy}>Confirm</button>}<button type="button" className="secondary" onClick={() => setProposal(null)}>Dismiss</button></div></form>}<form onSubmit={send} className="chat-form"><input aria-label="Message" value={input} onChange={e => setInput(e.target.value)} maxLength={2000} placeholder={configured ? 'Ask about saved leads…' : 'Gemini key required on backend'} disabled={!configured || busy} /><button className="primary" disabled={!configured || busy}>Send →</button></form></section>;
}

function Settings({ cap, collector }: { cap: AnyRow | null; collector: AnyRow | null }) { return <section className="panel"><p className="eyebrow">CAPABILITIES</p><h2>Connections</h2><p>Configuration status only. Credentials are never shown in the browser.</p><div className="settings-grid"><div><strong>Gemini drafts</strong><Badge tone={cap?.gemini_configured ? 'success' : ''}>{cap?.gemini_configured ? 'Key set; access unverified' : 'Needs key'}</Badge></div><div><strong>CSV import</strong><Badge tone="success">Available</Badge></div><div><strong>Local Maps collector</strong><Badge>{collector?.ready || collector?.available ? 'Ready check passed' : 'Unavailable here'}</Badge></div><div><strong>Sandbox runner</strong><Badge>{cap?.workflow_runner_modes?.includes('sandbox') ? 'Available' : 'Unavailable'}</Badge></div><div><strong>Email delivery</strong><Badge>{cap?.email_delivery_enabled ? 'Opt-in enabled' : 'Disabled'}</Badge></div><div><strong>Calls</strong><Badge>{cap?.calling_enabled ? 'Opt-in enabled' : 'Disabled'}</Badge></div></div><p className="hint">A configured provider is not proof of live delivery. Individual accounts and public-hosting hardening are future work.</p></section>; }
