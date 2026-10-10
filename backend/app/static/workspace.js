const $ = (selector, parent = document) => parent.querySelector(selector);
const content = $('#content');
const leadDialog = $('#lead-dialog');
const authDialog = $('#auth-dialog');
const state = { token: '', businesses: [], analyses: [], qualifications: [], workflows: [], jobs: [], appointments: [], runs: [], outbox: [], reminderIntent: null, clients: [], deployments: [], tasks: [], operations: null, intents: {}, managedChoice: '', proofChoice: '', collectorStatus: null, capabilities: {}, loaded: false, stale: false, demo: false, search: '', filter: 'all', sort: 'priority', selected: null, preview: null, pendingPilotId: null };
const titles = { overview: 'Overview', leads: 'Leads & research', discovery: 'Discover & import', workflows: 'Workflow drafts', connections: 'Connections', automation: 'Automation lab', clients: 'Clients', tasks: 'Follow-up tasks', operations: 'Operations' };
const criteria = { inquiry_followup: 'Inquiry follow-up', appointment_reminders: 'Appointment reminders', consultation_followup: 'Consultation follow-up', rebooking: 'Client rebooking', public_email: 'Public business email', business_phone: 'Business phone', inquiry_form: 'Inquiry form', operational_scale: 'Operational scale', recurring_services: 'Recurring services', booking_friction: 'Booking friction', inquiry_friction: 'Inquiry friction', intake_friction: 'Intake friction' };
const operational = new Set(['inquiry_followup', 'appointment_reminders', 'consultation_followup', 'rebooking']);
let loadGeneration = 0;
let sessionGeneration = 0;
const sources = { mock: 'Demo · fictional', csv: 'CSV import', gosom: 'Gosom CSV', instant_data_scraper: 'Instant Data Scraper', web_scraper: 'Web Scraper', manual: 'Entered manually', google_places: 'Google Places' };
const human = value => value === 'sqlite' ? 'SQLite' : String(value ?? '').replaceAll('_', ' ').replace(/^./, c => c.toUpperCase());
const date = value => value ? new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'Not recorded';
const view = () => titles[location.hash.slice(1)] ? location.hash.slice(1) : 'overview';

// All API values enter the page through textContent, never HTML interpolation.
function el(tag, className = '', text = '', children = []) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== '') node.textContent = String(text);
  for (const child of children) if (child) node.append(child);
  return node;
}
function badge(text, style = 'neutral') { return el('span', `badge ${style}`, text); }
function button(text, action, style = '') {
  const node = el('button', `button ${style}`, text); node.type = 'button';
  node.addEventListener('click', () => busy(node, action)); return node;
}
function link(text, href, style = '') { const node = el('a', style, text); node.href = href; return node; }
function external(text, href) {
  try {
    const url = new URL(href);
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) return el('span', 'muted', 'URL unavailable');
    const node = link(text, url.href); node.target = '_blank'; node.rel = 'noopener noreferrer'; return node;
  } catch { return el('span', 'muted', 'URL unavailable'); }
}
function notice(message, error = false) {
  const box = $('#notice'); box.replaceChildren(el('span', '', message)); box.className = `notice${error ? ' error' : ''}`; box.hidden = false;
  const dismiss = el('button', '', '×'); dismiss.type = 'button'; dismiss.setAttribute('aria-label', 'Dismiss message'); dismiss.onclick = () => { box.hidden = true; }; box.append(dismiss);
}
async function busy(node, action) {
  $('#notice').hidden = true;
  node.disabled = true; node.setAttribute('aria-busy', 'true');
  try { await action(); } catch (error) { notice(error.message, true); }
  finally { node.disabled = false; node.removeAttribute('aria-busy'); }
}
function lock() {
  loadGeneration++; sessionGeneration++;
  state.token = ''; state.loaded = false; state.selected = null; state.preview = null;
  for (const key of ['businesses', 'analyses', 'qualifications', 'workflows', 'jobs', 'appointments', 'runs', 'outbox', 'clients', 'deployments', 'tasks']) state[key] = [];
  state.reminderIntent = null; state.intents = {}; state.managedChoice = ''; state.proofChoice = ''; state.operations = null; state.pendingPilotId = null;
  state.capabilities = {}; state.collectorStatus = null; leadDialog.close(); $('#lead-content').replaceChildren();
  clearGlobalSearch(); $('#global-search').disabled = true;
  content.replaceChildren(el('div', 'empty-state', 'Unlock the workspace to load its data.'));
  $('#connection-status').textContent = 'Locked'; $('#lock').hidden = true;
  if (!authDialog.open) authDialog.showModal();
}
async function api(path, options = {}) {
  const usedToken = state.token, session = sessionGeneration;
  let response;
  try {
    response = await fetch(path, { ...options, signal: AbortSignal.timeout(120000), headers: { ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}), ...(options.headers || {}) } });
  } catch { throw new Error('The server could not be reached. Check the connection and try again.'); }
  if (session !== sessionGeneration) throw new Error('Workspace access changed. Unlock and refresh before continuing.');
  if (response.status === 401) { if (usedToken === state.token) lock(); throw new Error('A valid API token is required to unlock this workspace.'); }
  if (!response.ok) {
    let data = {}; try { data = await response.json(); } catch {}
    const message = data.error?.message || (Array.isArray(data.detail) ? data.detail.map(item => `${item.loc?.slice(1).join('.') || 'Input'}: ${item.msg}`).join('\n') : typeof data.detail === 'string' ? data.detail : `Request failed (HTTP ${response.status}).`);
    throw new Error(message);
  }
  const result = await (options.blob ? response.blob() : response.json());
  if (session !== sessionGeneration) throw new Error('Workspace access changed. Unlock and refresh before continuing.');
  return result;
}
const post = (path, body) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
async function pages(path) {
  const records = []; let offset = 0;
  while (true) {
    const page = await api(`${path}${path.includes('?') ? '&' : '?'}limit=500&offset=${offset}`);
    if (!Array.isArray(page)) throw new Error('The server returned an invalid list.');
    records.push(...page); if (page.length < 500) return records; offset += page.length;
  }
}
async function load() {
  const generation = ++loadGeneration;
  $('#connection-status').textContent = 'Connecting…';
  try {
    const [ready, capabilities, businesses, analyses, qualifications, workflows, jobs] = await Promise.all([api('/ready'), api('/capabilities'), pages('/businesses'), pages('/analyses'), pages('/prospects?include_demo=true&include_blocked=true'), pages('/workflows'), api('/discovery/jobs')]);
    if (generation !== loadGeneration) return;
    const [appointments, runs, outbox] = capabilities.workflow_runner_modes?.includes('sandbox') ? await Promise.all([pages('/appointments'), pages('/workflow-runs'), pages('/workflow-outbox')]) : [[], [], []];
    if (generation !== loadGeneration) return;
    const [clients, deployments, tasks, operations] = capabilities.client_workflow_activation_supported ? await Promise.all([pages('/clients'), pages('/deployments'), pages('/tasks'), api(`/operations/summary?include_demo=${state.demo}`)]) : [[], [], [], null];
    if (generation !== loadGeneration) return;
    Object.assign(state, { capabilities, businesses, analyses, qualifications, workflows, jobs, appointments, runs, outbox, clients, deployments, tasks, operations, collectorStatus: null, loaded: true, stale: false });
    $('#connection-status').textContent = `${human(ready.persistence)} connected`; $('#connection-status').className = 'badge good';
    $('#lock').hidden = !state.token; $('#global-search').disabled = false; render();
  } catch (error) {
    if (generation !== loadGeneration && state.loaded) return;
    state.stale = state.loaded;
    if (!authDialog.open) {
      $('#connection-status').textContent = 'Connection failed'; $('#connection-status').className = 'badge error';
      if (state.loaded) render(); else content.replaceChildren(empty('Unable to load the workspace', error.message, button('Try again', load, 'primary')));
      notice(error.message, true);
    }
    throw error;
  }
}
function records() { return state.businesses.filter(record => state.demo || record.source !== 'mock'); }
function clearGlobalSearch() { $('#global-search').value = ''; $('#global-search-results').replaceChildren(); $('#global-search-results').hidden = true; }
function updateGlobalSearch() {
  const region = $('#global-search-results'), query = $('#global-search').value.trim().toLowerCase();
  region.replaceChildren(); region.hidden = !query || !state.loaded;
  if (region.hidden) return;
  const matches = records().filter(r => `${r.business.name} ${r.business.address} ${r.business.phone || ''}`.toLowerCase().includes(query));
  region.append(el('div', 'search-caption', `${matches.length} matching ${matches.length === 1 ? 'business' : 'businesses'} · ${state.demo ? 'demos included' : 'demos excluded'}`));
  for (const record of matches.slice(0, 8)) {
    const result = button('', async () => { clearGlobalSearch(); await openLead(record.id); }, 'search-result');
    result.append(el('span', 'initials', record.business.name.slice(0, 2).toUpperCase()), el('span', '', '', [el('strong', '', record.business.name), el('small', '', record.business.address)]));
    region.append(result);
  }
  if (!matches.length) region.append(el('p', 'muted', 'No saved businesses match this search.'));
  if (matches.length > 8) region.append(button('View all matching leads →', () => { state.search = $('#global-search').value; state.filter = 'all'; clearGlobalSearch(); location.hash = '#leads'; if (view() === 'leads') render(); }, 'small'));
}
function latest(id) { return state.analyses.filter(a => a.business_id === id).sort((a, b) => b.created_at.localeCompare(a.created_at))[0]; }
function qualification(id) { return state.qualifications.find(item => item.business_id === id); }
function prospectReady(id) { return qualification(id)?.prospect_status === 'ready_for_review'; }
function compareProspects(a, b) {
  const order = { ready_for_review: 0, research: 1, not_analyzed: 2, do_not_contact: 3 };
  const qa = qualification(a.id), qb = qualification(b.id);
  return (order[qa?.prospect_status] ?? 2) - (order[qb?.prospect_status] ?? 2) || (qb?.prospect_score || 0) - (qa?.prospect_score || 0) || (qb?.public_evidence_coverage || 0) - (qa?.public_evidence_coverage || 0) || a.id.localeCompare(b.id);
}
function prospectStatus(q) { return !q || q.prospect_status === 'not_analyzed' ? badge('Not analyzed') : q.prospect_status === 'do_not_contact' ? badge('Do not contact', 'error') : q.prospect_status === 'ready_for_review' ? badge('Prospect review ready', 'good') : badge('Public research needed', 'research'); }
function needStatus(q) { return badge(({ unconfirmed: 'Need unconfirmed', confirmed_gap: 'Business-confirmed gap', observed_friction: 'Observed website friction', assessed_no_gap: 'Assessed · no gap' })[q?.need_status] || 'Need unconfirmed', q?.need_status === 'confirmed_gap' ? 'good' : q?.need_status === 'observed_friction' ? 'neutral' : 'research'); }
function empty(title, detail, action) { return el('div', 'empty-state', '', [el('h3', '', title), el('p', '', detail), action]); }
function heading(eyebrow, title, subtitle, action) { return el('div', 'page-heading', '', [el('div', '', '', [el('div', 'eyebrow', eyebrow), el('h1', '', title), el('p', 'subtitle', subtitle)]), action]); }
function stat(label, value, caption, icon = '↗') { return el('div', 'stat', '', [el('div', 'stat-label', '', [el('span', '', label), el('span', 'stat-icon', icon)]), el('strong', 'stat-value', value), el('span', 'stat-caption', caption)]); }
function cardHeader(title, subtitle, action) { return el('div', 'card-header', '', [el('div', '', '', [el('h2', '', title), el('p', '', subtitle)]), action]); }
function scrollTable(table) { return el('div', '', '', [el('div', 'mobile-table-hint', 'Swipe sideways to see more columns →'), el('div', 'table-scroll', '', [table])]); }
function status(analysis) { return !analysis ? badge('Not analyzed') : analysis.provisional ? badge('Need review provisional', 'research') : badge(`Need priority: ${human(analysis.priority)}`, analysis.priority === 'high' ? 'good' : 'neutral'); }
function leadTable(leads, full = false) {
  if (!leads.length) return empty('No leads in this view', 'Collect a small pilot or import a scraper CSV to start researching.', link('Discover leads →', '#discovery', 'button'));
  const table = el('table'); const head = el('tr');
  for (const title of ['BUSINESS', 'SOURCE', 'PROSPECT SCORE', 'PUBLIC COVERAGE', 'NEED']) head.append(el('th', '', title));
  table.append(el('thead', '', '', [head])); const body = el('tbody');
  for (const record of leads) {
    const business = record.business, analysis = latest(record.id), q = qualification(record.id);
    const name = el('button', 'lead-link', business.name); name.type = 'button'; name.onclick = () => openLead(record.id).catch(error => notice(error.message, true));
    const initials = business.name.split(/\s+/).slice(0, 2).map(x => x[0]).join('').toUpperCase();
    const cell = el('div', 'business-cell', '', [el('span', 'initials', initials), el('div', '', '', [name, el('small', '', full ? business.address : business.address.split(',').slice(-2).join(',').trim())])]);
    const coverage = el('div', '', analysis && q ? `${q.public_evidence_coverage}%` : '—');
    if (analysis && q) { const fill = el('span'); fill.style.width = `${q.public_evidence_coverage}%`; coverage.append(el('div', 'coverage-track', '', [fill])); }
    const score = el('span', 'score-value', analysis && q ? q.prospect_score : '—'); if (analysis && q) score.append(el('small', '', ' / 100'));
    body.append(el('tr', '', '', [el('td', '', '', [cell]), el('td', '', '', [badge(sources[record.source] || human(record.source), record.source === 'mock' ? 'demo' : 'neutral')]), el('td', '', '', [score, el('div', 'status-detail', '', [prospectStatus(q)])]), el('td', '', '', [coverage]), el('td', '', '', [needStatus(q)])]));
  }
  table.append(body); return scrollTable(table);
}
function render() {
  if (!state.loaded) return;
  const current = view(); $('#breadcrumb').textContent = titles[current]; document.title = `${titles[current]} · AIAutomation`;
  document.querySelectorAll('[data-view]').forEach(node => { const active = node.dataset.view === current; node.classList.toggle('active', active); if (active) node.setAttribute('aria-current', 'page'); else node.removeAttribute('aria-current'); });
  $('#mobile-section-current').textContent = titles[current];
  document.querySelectorAll('[data-mobile-view]').forEach(node => { const active = node.dataset.mobileView === current; node.classList.toggle('active', active); if (active) node.setAttribute('aria-current', 'page'); else node.removeAttribute('aria-current'); });
  content.replaceChildren(); updateGlobalSearch();
  if (state.stale) content.append(el('div', 'callout', 'Connection failed. The data below is from the last successful load and may be out of date. Refresh before making changes.'));
  if (state.demo) content.append(el('div', 'callout', 'Demo leads are included in this view. Their businesses and evidence are fictional.'));
  ({ overview: renderOverview, leads: renderLeads, discovery: renderDiscovery, workflows: renderWorkflows, connections: renderConnections, automation: renderAutomation, clients: renderClients, tasks: renderTasks, operations: renderOperations })[current]();
}
function renderOverview() {
  const leads = records(), ready = leads.filter(r => prospectReady(r.id)), confirmed = leads.filter(r => qualification(r.id)?.need_status === 'confirmed_gap');
  const workflows = state.workflows.filter(w => leads.some(r => r.id === w.business_id) && w.status === 'draft');
  const hero = heading('SALES WORKSPACE', 'Overview', 'Your med spa prospects, research and next actions.', link('+ Discover leads', '#discovery', 'button primary'));
  hero.classList.add('overview-hero'); content.append(hero);
  content.append(el('div', 'overview-context', '', [el('span', '', 'Sales overview'), el('span', 'context-note', 'Saved leads and recorded activity')]));
  content.append(el('div', 'stats', '', [stat('Saved leads', leads.length, state.demo ? 'Includes fictional demo records' : 'Demo records excluded', '▤'), stat('Prospects to review', ready.length, 'Public fit + contact evidence', '⌕'), stat('Confirmed gaps', confirmed.length, 'Business confirmation recorded', '✧'), stat('Workflow drafts', workflows.length, 'Saved definitions · not running', '→')]));
  const candidates = [...leads].sort(compareProspects).slice(0, 6);
  const table = el('section', 'card', '', [cardHeader('Your prospect queue', 'Public contact and business-fit evidence. Internal need is a separate stage.', badge(`${candidates.length} shown`)), leadTable(candidates), el('div', 'table-footer', '', [el('span', '', 'Prospect scores rank public fit; they do not establish a need or conversion probability.'), link('View all leads →', '#leads')])]);
  const next = el('section', 'card research-card card-body', '', [el('div', 'line-label', 'THE NEXT USEFUL STEP'), el('h2', '', ready.length ? 'Ask about the actual process.' : leads.length ? 'Build the public picture.' : 'Start with a small, real pilot.'), el('p', '', ready.length ? `${ready.length} prospect${ready.length === 1 ? '' : 's'} have enough public evidence for review. Check contact details and discrepancies, then ask about their process. A public-fit score does not confirm an automation gap.` : leads.length ? 'Research contact details, scale, and recurring offerings. Record unknowns while confirming the facts.' : 'Collect up to 10 visible listings or bring a CSV from your browser extension. Check the preview before saving.'), link(leads.length ? 'Open prospect queue →' : 'Discover & import →', leads.length ? '#leads' : '#discovery', 'button')]);
  const path = el('section', 'card card-body', '', [el('div', 'row space-between', '', [el('h2', '', 'Upcoming follow-up'), link('View tasks →', '#tasks')])]);
  const pending = state.tasks.filter(t => t.status === 'pending' && leads.some(r => r.id === t.business_id)).sort((a,b) => new Date(a.due_at) - new Date(b.due_at)).slice(0,3);
  if (!pending.length) path.append(el('div', 'task-empty', '', [el('span', 'task-empty-icon', '✓'), el('strong', '', 'No pending follow-up'), el('p', 'muted', 'Create a task when you have a next step to record.'), link('Create a follow-up task', '#tasks', 'button small')]));
  for (const task of pending) {
    const item = link('', '#tasks', 'task-preview');
    item.append(el('strong', '', task.title), el('small', '', leads.find(r => r.id === task.business_id)?.business.name || 'Saved business'), el('span', new Date(task.due_at) < new Date() ? 'task-due overdue' : 'task-due', date(task.due_at)));
    path.append(item);
  }
  content.append(el('div', 'dashboard-grid', '', [table, el('div', 'aside-stack', '', [next, path])]));
  content.append(el('div', 'formula-note', '', [el('strong', '', 'Two separate stages'), el('span', '', 'Prospect score = contact + value, normalized to 100. Review readiness needs ≥40 score, ≥40% public coverage, and a supported contact route. Need scoring keeps its ≥70% overall coverage gate. Neither score is a probability.')]));
}
function renderLeads() {
  content.append(heading('LEADS & RESEARCH', 'Leads & research', 'Sources, scores, and open questions for every saved business.', link('Import leads', '#discovery', 'button primary')));
  const search = el('input'); search.type = 'search'; search.placeholder = 'Search a business or address'; search.setAttribute('aria-label', 'Search leads'); search.value = state.search;
  const filter = select([['all', 'All leads'], ['research', 'Public research needed'], ['ready', 'Prospects to review'], ['confirmed', 'Business-confirmed gaps'], ['need_review', 'Needs ready for review'], ['blocked', 'Do not contact'], ['unanalysed', 'Not analyzed']], state.filter); filter.setAttribute('aria-label', 'Filter leads');
  const demo = el('input'); demo.type = 'checkbox'; demo.checked = state.demo;
  const label = el('label', 'check-label', '', [demo, el('span', '', 'Include fictional demo leads')]);
  const rows = el('div');
  const tabs = el('div', 'saved-views'); tabs.setAttribute('aria-label', 'Lead views');
  const sort = select([['priority','Review priority'], ['name','Business name A–Z'], ['score','Prospect score: highest first']], state.sort); sort.setAttribute('aria-label', 'Sort leads');
  const viewOptions = [['all','All leads'], ['ready','Ready for review'], ['confirmed','Confirmed needs'], ['blocked','Do not contact']];
  function update() {
    const term = state.search.trim().toLowerCase();
    const selected = records().filter(r => `${r.business.name} ${r.business.address}`.toLowerCase().includes(term)).filter(r => {
      const q = qualification(r.id);
      return state.filter === 'all' || (state.filter === 'ready' ? prospectReady(r.id) : state.filter === 'confirmed' ? q?.need_status === 'confirmed_gap' : state.filter === 'need_review' ? q?.need_review_ready : state.filter === 'blocked' ? q?.prospect_status === 'do_not_contact' : state.filter === 'unanalysed' ? !latest(r.id) : ['research', 'not_analyzed'].includes(q?.prospect_status));
    });
    selected.sort(state.sort === 'name' ? (a,b) => a.business.name.localeCompare(b.business.name) : state.sort === 'score' ? (a,b) => (qualification(b.id)?.prospect_score || 0) - (qualification(a.id)?.prospect_score || 0) || a.business.name.localeCompare(b.business.name) : compareProspects);
    for (const tab of tabs.querySelectorAll('button')) { const active = tab.dataset.filter === state.filter; tab.classList.toggle('active',active); tab.setAttribute('aria-pressed', String(active)); }
    rows.replaceChildren(leadTable(selected, true), el('div', 'table-footer', `${selected.length} of ${records().length} leads · ${state.demo ? 'Demo records included' : 'Demo records excluded'}`));
  }
  for (const [key,title] of viewOptions) { const tab = button(title, () => { state.filter = key; filter.value = key; update(); }, 'view-tab'); tab.dataset.filter = key; tabs.append(tab); }
  search.oninput = () => { state.search = search.value; update(); }; filter.onchange = () => { state.filter = filter.value; update(); }; sort.onchange = () => { state.sort = sort.value; update(); }; demo.onchange = () => { state.demo = demo.checked; update(); updateGlobalSearch(); };
  content.append(el('section', 'card records-card', '', [tabs, el('div', 'toolbar', '', [search, filter, sort, label]), rows])); update();
}
function select(options, value) {
  const node = el('select'); for (const [key, label] of options) { const item = el('option', '', label); item.value = key; node.append(item); } node.value = value; return node;
}
function field(labelText, control, help = '') {
  const id = `field-${crypto.randomUUID()}`; control.id = id; const label = el('label', '', labelText); label.htmlFor = id;
  return el('div', 'field', '', [label, control, help ? el('small', 'help', help) : null]);
}
function localTime(value = new Date().toISOString()) { const d = new Date(value); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16); }
function submit(form, text, action) {
  const node = el('button', 'button primary', text); node.type = 'submit';
  form.addEventListener('submit', event => { event.preventDefault(); if (form.reportValidity()) busy(node, action); }); form.append(node); return node;
}
function discoverySearchQuery(value) {
  const query = value.trim().replace(/\s+/g, ' ');
  const hasBusinessType = /\b(?:med\s*spas?|medical\s*spas?|spas?|clinics?|aesthetics?|dermatolog(?:y|ists?)|laser|cosmetic|beauty|massage|wellness|skin\s*care)\b/i.test(query);
  return hasBusinessType ? query : `medical spas in ${query}`;
}
function renderDiscovery() {
  content.append(heading('BUILD YOUR PIPELINE', 'Discover businesses', 'Collect a small sample or bring your own CSV. Review every result before saving.'));
  content.append(el('div', 'discovery-steps', '', [el('span', '', '01  Collect'), el('span', '', '02  Preview'), el('span', '', '03  Import')]));
  const pilot = el('form', 'card-body discovery-form');
  const query = el('input'); query.required = true; query.maxLength = 300; query.placeholder = 'Islamabad, Pakistan';
  const limit = el('input'); limit.type = 'number'; limit.min = '1'; limit.max = '10'; limit.value = '5'; limit.required = true;
  const collectorPanel = el('div', 'collector-panel'); collectorPanel.id = 'collector-status';
  const pilotSummary = el('div', 'pilot-result-summary'); pilotSummary.id = 'pilot-result-summary';
  const importCard = el('section', 'card discovery-card discovery-import'); importCard.id = 'discovery-import';
  pilot.append(el('div', 'discovery-card-kicker', 'OPTION 01 · LIVE COLLECTION'), el('h2', '', 'Find med spas on Maps'), el('p', 'muted', 'Collect up to ten visible listings with the local Edge or bundled browser. Results stay in a preview until you choose to import them.'), field('City or business + location', query, 'Enter a city such as “Islamabad, Pakistan”; the pilot searches for medical spas there. You can also enter a full business + location query.'), field('Maximum listings', limit, '1–10 listings; this is a small sample, not a complete directory.'), collectorPanel);
  const startPilot = submit(pilot, 'Start live pilot →', async () => {
    if (state.jobs.some(job => ['queued', 'running'].includes(job.status))) throw new Error('A live pilot is already running. Wait for its result before starting another.');
    const search = discoverySearchQuery(query.value);
    if (search.length > 300) throw new Error('The search is too long. Shorten the city or business name.');
    query.value = search;
    const job = await post('/discovery/jobs', { query: search, limit: Number(limit.value) }); state.pendingPilotId = job.id; state.preview = null; state.jobs.unshift(job); renderPreview(); renderJobs(); notice(`Searching Maps for “${search}”. Its result count and preview will appear here when it finishes.`);
  });
  startPilot.disabled = true;
  const manualMaps = link('Open Google Maps ↗', 'https://www.google.com/maps/', 'button discovery-maps-link');
  manualMaps.target = '_blank'; manualMaps.rel = 'noopener noreferrer';
  manualMaps.addEventListener('click', event => {
    if (!query.value.trim()) { event.preventDefault(); query.reportValidity(); return; }
    const search = discoverySearchQuery(query.value);
    if (search.length > 300) { event.preventDefault(); notice('The search is too long. Shorten the city or business name.', true); return; }
    query.value = search;
    manualMaps.href = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(search)}`;
  });
  pilot.append(el('div', 'discovery-actions', '', [manualMaps]));
  pilot.append(el('p', 'discovery-footnote', 'Open Maps for manual review without Docker. Use your own CSV export for import; opening Maps does not save leads.'));
  pilot.append(el('p', 'discovery-footnote', 'A successful pilot saves its source pages and CSV. Review category, address and contact details before import.'));
  pilot.append(pilotSummary);
  const session = sessionGeneration;
  const active = () => session === sessionGeneration && state.loaded && view() === 'discovery';
  const paintCollector = result => {
    if (!active()) return;
    collectorPanel.className = `collector-panel ${result.ready ? 'is-ready' : 'is-blocked'}`;
    collectorPanel.replaceChildren(el('span', 'collector-dot', ''), el('div', '', '', [el('strong', '', result.ready ? 'Browser setup ready' : result.code === 'checking' ? 'Checking browser' : 'Live pilot unavailable here'), el('p', '', result.message)]), button('Check again', checkCollector, 'small'));
    startPilot.disabled = !result.ready;
  };
  const checkCollector = async () => {
    const result = await api('/discovery/collector-status');
    if (active()) { state.collectorStatus = result; paintCollector(result); }
  };
  if (state.collectorStatus) paintCollector(state.collectorStatus);
  else {
    paintCollector({ ready: false, code: 'checking', message: 'Checking the local browser…' });
    checkCollector().catch(error => { if (active()) paintCollector({ ready: false, code: 'unavailable', message: error.message }); });
  }
  const upload = el('form', 'card-body discovery-form');
  const file = el('input'); file.type = 'file'; file.accept = '.csv,text/csv'; file.required = true;
  const source = select([['csv', 'Other CSV export'], ['instant_data_scraper', 'Instant Data Scraper'], ['web_scraper', 'Web Scraper extension'], ['gosom', 'Gosom scraper']], 'csv');
  const time = el('input'); time.type = 'datetime-local'; time.max = localTime();
  const mapping = el('textarea'); mapping.rows = 2; mapping.placeholder = '{"name":"Business name","address":"Full address"}';
  upload.append(el('div', 'discovery-card-kicker', 'OPTION 02 · CSV IMPORT'), el('h2', '', 'Import a prepared list'), el('p', 'muted', 'Use a browser extension or scraper export. The preview checks rows and duplicates before anything is saved.'), field('CSV file', file, 'UTF-8 CSV, at most 2 MB and 2,000 rows. Business name and address are required.'), el('div', 'discovery-form-pair', '', [field('Export source', source), field('Collection time (your local time)', time, 'If omitted, import time is recorded; this does not verify scrape time.')]), field('Column mapping (optional JSON)', mapping, 'Common headers are detected automatically. Use exact CSV headers for custom mapping.'));
  const invalidate = () => { if (state.preview?.kind === 'upload') { state.preview = null; $('#preview-region')?.replaceChildren(); } };
  for (const control of [file, source, time, mapping]) control.addEventListener('input', invalidate);
  submit(upload, 'Preview CSV →', async () => {
    const selected = file.files[0]; if (!selected || selected.size > 2 * 1024 * 1024) throw new Error('Choose a CSV file at most 2 MB.');
    const selection = { source: source.value, time: time.value, mapping: mapping.value };
    const parameters = new URLSearchParams({ source: source.value, file_name: selected.name.slice(0, 120), dry_run: 'true' });
    if (time.value) parameters.set('collected_at', new Date(time.value).toISOString());
    if (mapping.value.trim()) { let map; try { map = JSON.parse(mapping.value); } catch { throw new Error('Column mapping must be a valid JSON object.'); } parameters.set('column_map', JSON.stringify(map)); }
    const data = await selected.arrayBuffer();
    const report = await api(`/businesses/import-csv?${parameters}`, { method: 'POST', headers: { 'Content-Type': 'text/csv' }, body: data });
    if (file.files[0] !== selected || source.value !== selection.source || time.value !== selection.time || mapping.value !== selection.mapping) throw new Error('The file or import settings changed while the preview was loading. Preview the current selection again.');
    state.preview = { kind: 'upload', parameters, data, report, name: selected.name }; renderPreview();
  });
  importCard.append(upload);
  content.append(el('div', 'discovery-grid', '', [el('section', 'card discovery-card discovery-pilot', '', [pilot]), importCard]));
  const jobs = el('section', 'card discovery-jobs'); jobs.id = 'jobs-region';
  const preview = el('section', 'preview'); preview.id = 'preview-region'; content.append(jobs, preview); renderJobs(); renderPreview();
}
function renderJobs() {
  const region = $('#jobs-region'); if (!region) return;
  renderPilotSummary();
  region.replaceChildren(cardHeader('Recent pilot activity', 'Every run stays here. Preview a successful result before importing; failed runs save no leads.', badge('At most 10 listings')));
  if (!state.jobs.length) { region.append(empty('No pilots yet', 'Start a small query above, or use a CSV export.')); return; }
  for (const job of state.jobs.slice(0, 10)) {
    const row = el('div', 'job', '', [el('div', 'row space-between', '', [el('h3', '', job.query), badge(human(job.status), job.status === 'succeeded' ? 'good' : ['failed', 'interrupted'].includes(job.status) ? 'error' : 'research')]), el('div', 'muted', `${date(job.created_at)} · Limit ${job.limit}${job.collected_count != null ? ` · ${job.collected_count} collected` : ''}`)]);
    if (job.error) row.append(el('p', 'job-error', job.error));
    if (job.status === 'failed' && job.error?.startsWith('Live collection failed or produced invalid output.')) row.append(el('p', 'status-detail', 'This run saved only a generic failure message. Its exact cause cannot be recovered; a new pilot will show a more specific reason when the collector recognizes it.'));
    if (job.status === 'failed') row.append(button('Review pilot options ↑', () => $('#collector-status')?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 'small'));
    if (job.status === 'succeeded') row.append(el('div', 'row', '', [button('Preview results', () => showPilotPreview(job), 'small'), button('Download raw CSV', async () => saveBlob(await api(`/discovery/jobs/${job.id}/csv`, { blob: true }), 'results.csv'), 'small'), button('Download spreadsheet CSV', async () => saveBlob(await api(`/discovery/jobs/${job.id}/spreadsheet.csv`, { blob: true }), 'results-spreadsheet.csv'), 'small')]));
    if (['queued', 'running'].includes(job.status)) row.append(el('p', 'status-detail', 'The pilot may take up to several minutes. No leads have been imported.'));
    region.append(row);
  }
}
function renderPilotSummary() {
  const region = $('#pilot-result-summary'); if (!region) return;
  const job = state.jobs[0]; region.replaceChildren();
  if (!job) return;
  if (['queued', 'running'].includes(job.status)) {
    region.append(el('strong', '', 'Searching Maps…'), el('p', '', 'The collector opens listings one at a time. Its Edge window closes after the run; nothing is imported automatically.'));
  } else if (job.status === 'succeeded') {
    const count = job.collected_count || 0;
    region.append(el('strong', '', `${count} listing${count === 1 ? '' : 's'} captured`), el('p', '', 'Open the preview to see names, categories and details. These are search results, not verified med spas; no leads were imported automatically.'), button(`Show ${count} listing${count === 1 ? '' : 's'}`, () => showPilotPreview(job), 'small'));
  } else if (job.status === 'failed') {
    region.append(el('strong', '', 'Latest pilot did not produce a preview'), el('p', '', 'See the saved reason in Recent pilot activity below. No leads were imported.'));
  }
}
async function showPilotPreview(job) {
  const session = sessionGeneration;
  const report = await post(`/discovery/jobs/${job.id}/preview`, {});
  if (session !== sessionGeneration || !state.loaded || view() !== 'discovery') return;
  state.preview = { kind: 'pilot', jobId: job.id, report, name: job.query };
  renderPreview(); $('#preview-region')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function renderPreview() {
  const region = $('#preview-region'); if (!region) return; region.replaceChildren();
  const preview = state.preview; if (!preview) return;
  const r = preview.report;
  const card = el('div', 'card', '', [cardHeader(r.dry_run ? 'Review before importing' : 'Import result', preview.name, badge(r.dry_run ? 'Preview · not saved' : 'Import completed', r.dry_run ? 'research' : 'good'))]);
  const body = el('div', 'card-body', '', [el('div', 'stats', '', [stat('New valid rows', r.dry_run ? r.valid_rows : r.imported_rows, r.dry_run ? 'Ready to save' : 'Saved'), stat('Duplicates', r.duplicate_rows, 'Existing records kept'), stat('Invalid rows', r.invalid_rows, 'Will not be saved'), stat('Total rows', r.total_rows, 'File rows evaluated')]), el('p', 'muted long-wrap', `Detected mapping: ${Object.entries(r.column_map).map(([field, header]) => `${human(field)} → ${header}`).join(' · ')}`)]);
  if (r.ignored_columns.length) body.append(el('p', 'muted long-wrap', `Ignored columns: ${r.ignored_columns.join(', ')}`));
  if (r.dry_run) {
    body.append(el('p', 'muted', 'Confirm these are relevant med spas and inspect the fields. Import saves valid new rows, skips duplicates, and skips invalid rows. Source selection is your statement, not independent verification.'));
    let categoryReview = null;
    if (preview.kind === 'pilot') {
      categoryReview = el('input'); categoryReview.type = 'checkbox';
      body.append(el('label', 'discovery-review-confirmation', '', [categoryReview, el('span', '', 'I checked each Maps category and confirmed these are relevant med spas or medical aesthetics businesses.') ]));
    }
    const commit = button(`Import ${r.valid_rows} valid new lead${r.valid_rows === 1 ? '' : 's'}`, async () => {
      let result;
      if (preview.kind === 'pilot') result = await post(`/discovery/jobs/${preview.jobId}/import`, {});
      else { const params = new URLSearchParams(preview.parameters); params.set('dry_run', 'false'); result = await api(`/businesses/import-csv?${params}`, { method: 'POST', headers: { 'Content-Type': 'text/csv' }, body: preview.data }); }
      preview.report = result; await load(); notice(`${result.imported_rows} leads saved. ${result.duplicate_rows} duplicates and ${result.invalid_rows} invalid rows skipped.`);
    }, 'primary');
    commit.disabled = !r.valid_rows || Boolean(categoryReview);
    categoryReview?.addEventListener('change', () => { commit.disabled = !r.valid_rows || !categoryReview.checked; });
    body.append(commit);
  }
  card.append(body);
  const table = el('table'); const head = el('tr'); for (const title of ['ROW', 'BUSINESS', 'CATEGORY', 'STATUS', 'ISSUES']) head.append(el('th', '', title)); table.append(el('thead', '', '', [head]));
  const rows = el('tbody');
  for (const row of r.rows) {
    const category = row.warnings.find(warning => warning.startsWith('Source category: '));
    rows.append(el('tr', '', '', [el('td', '', row.row_number), el('td', '', '', [el('strong', '', row.business?.name || 'Invalid business'), el('div', 'muted', row.business?.address || ''), el('div', 'status-detail', [row.business?.phone, row.business?.website].filter(Boolean).join(' · '))]), el('td', '', category ? category.slice('Source category: '.length) : 'Not supplied'), el('td', '', '', [badge(human(row.status), row.status === 'invalid' ? 'error' : 'neutral')]), el('td', '', '', [el('div', 'error-text', row.errors.join(' · ')), el('div', 'muted', row.warnings.filter(warning => warning !== category).join(' · '))])]));
  }
  table.append(rows); card.append(scrollTable(table)); region.append(card);
}
function saveBlob(blob, name) { const url = URL.createObjectURL(blob), a = link('', url); a.download = name; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
function saveJSON(value, name) { saveBlob(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }), name); }

async function openLead(id) {
  state.selected = id; const region = $('#lead-content');
  region.replaceChildren(el('div', 'dialog-header', '', [el('h2', '', 'Loading lead…'), button('Close', () => leadDialog.close(), 'small')]), el('div', 'empty-state', 'Loading contact and analysis…'));
  if (!leadDialog.open) leadDialog.showModal();
  const [contact, q, history] = await Promise.all([api(`/businesses/${id}/contact`), api(`/businesses/${id}/qualification`), state.capabilities.crm_history_supported ? api(`/businesses/${id}/activities?limit=100`) : []]);
  if (state.selected !== id || !leadDialog.open) return;
  state.qualifications = [...state.qualifications.filter(item => item.business_id !== id), q];
  renderLead(id, contact, history);
}
async function refreshLead(id) {
  await load();
  if (leadDialog.open && state.selected === id) await openLead(id);
}
function renderLead(id, contact, history = []) {
  const record = state.businesses.find(r => r.id === id); if (!record) throw new Error('This lead is no longer loaded. Refresh the workspace.');
  const business = record.business, analysis = latest(id), q = qualification(id), region = $('#lead-content'); region.replaceChildren();
  region.append(el('div', 'dialog-header', '', [el('div', '', '', [el('div', 'eyebrow', 'BUSINESS RESEARCH'), el('h2', '', business.name), el('p', 'subtitle', business.address)]), button('Close', () => leadDialog.close(), 'small')])); $('#lead-content h2').id = 'lead-title';
  const body = el('div', 'dialog-body');
  const meta = el('div', 'detail-meta', '', [badge(sources[record.source] || human(record.source), record.source === 'mock' ? 'demo' : 'neutral'), el('span', '', business.phone || 'Phone unknown'), el('span', '', business.rating == null ? 'Rating unknown' : `${business.rating} rating · ${business.review_count ?? 'unknown'} reviews`)]);
  if (business.website) meta.append(external('Official website ↗', business.website));
  if (record.provenance?.listing_url) meta.append(external('Original listing ↗', record.provenance.listing_url));
  body.append(meta);
  if (record.source === 'mock') body.append(el('div', 'callout', 'Fictional demo lead. The business and any synthetic evidence are not real.'));
  const left = el('div'), right = el('div');
  if (analysis) {
    left.append(el('div', 'stats', '', [stat('Prospect score', `${q.prospect_score}/100`, 'Public contact + business fit'), stat('Public coverage', `${q.public_evidence_coverage}%`, 'Assessed C + V weight only'), stat('Need score', `${analysis.need_score}/100`, 'Unknowns can still exist')]));
    const reasons = el('ul', 'unknown-list'); q.prospect_reasons.forEach(reason => reasons.append(el('li', '', reason)));
    left.append(el('section', 'card card-body', '', [el('h2', '', 'Two-stage review'), el('div', 'row', '', [prospectStatus(q), needStatus(q)]), el('p', 'muted', q.next_step), reasons, el('p', 'status-detail', `Public unknowns: ${q.public_unknown_criteria.map(name => criteria[name]).join(', ') || 'None recorded'}. Contact presence does not prove reachability.`)]));
    left.append(el('div', 'card card-body', '', [el('div', 'row space-between', '', [el('h2', '', 'Need evidence overview'), status(analysis)]), el('p', 'muted', `${date(analysis.created_at)} · ${analysis.mode === 'rules' ? 'Deterministic scoring' : 'Deterministic scoring + AI narrative'}`), el('p', 'muted', `Overall evidence score ${analysis.total_score}/100 · Overall coverage ${analysis.evidence_coverage}% · ${q.need_review_ready ? 'Enough evidence for need review' : 'More confirmation or need research required'}`), el('p', 'muted long-wrap', analysis.summary), el('p', '', analysis.recommended_automation), el('div', 'callout', 'A promising prospect can still have unconfirmed needs. Zero need points does not prove there is no need. Internal gaps require business confirmation.') ]));
    const evidence = el('section', 'card', '', [cardHeader('Evidence & unknowns', 'Source statements are recorded; operator entries are not independently verified.')]);
    for (const name of Object.keys(criteria)) {
      const item = analysis.evidence.find(e => e.criterion === name);
      const origin = item?.origin === 'automatic' ? 'Automatic observation' : item?.origin === 'operator' ? 'Recorded by operator' : 'Origin not recorded';
      evidence.append(el('div', 'evidence-item', '', [el('div', 'row space-between', '', [el('span', 'evidence-name', criteria[name]), badge(!item || item.assessment === 'unknown' ? 'Unknown' : item.assessment === 'clear' ? 'Assessed · 0 points' : human(item.assessment), !item || item.assessment === 'unknown' ? 'research' : 'neutral')]), item ? el('p', '', item.detail) : el('p', '', 'No evidence has been recorded for this criterion.'), item ? el('div', 'evidence-meta', `${human(item.source)} · ${origin} · ${date(item.observed_at)}`) : null]));
    }
    left.append(evidence);
  } else left.append(empty('This lead needs its first analysis', 'Check the public website or record observations. Internal operations stay unknown until confirmed.'));
  const research = el('section', 'card card-body', '', [el('h2', '', 'Research this lead'), el('p', 'muted', 'Website refresh replaces automatic observations. Operator evidence keeps its source and date; review that it is still valid.')]);
  const ai = el('input'); ai.type = 'checkbox'; ai.disabled = !state.capabilities.ai_configured;
  research.append(el('label', 'check-label', '', [ai, el('span', '', state.capabilities.ai_configured ? 'Add AI narrative (configured; live availability not guaranteed)' : 'AI narrative not configured')]));
  const analyze = async fetchWebsite => {
    const evidence = (analysis?.evidence || []).filter(item => !fetchWebsite || item.origin !== 'automatic');
    await post(`/businesses/${id}/analyze`, { fetch_website: fetchWebsite, use_ai: ai.checked, evidence });
    await refreshLead(id); notice('A new analysis was saved. Review its evidence and unknowns.');
  };
  const fetchButton = button('Fetch website & analyze', () => analyze(true), 'primary'); fetchButton.disabled = !business.website || record.source === 'mock';
  research.append(el('div', 'row', '', [fetchButton, button(analysis ? 'Recalculate saved evidence' : 'Analyze listing only', () => analyze(false), 'small')]));
  research.append(el('p', 'status-detail', 'Fetching needs the website host allowed by this server. Static HTML checks do not test booking or submit forms.'));
  research.append(evidenceEditor(id, analysis)); right.append(research);
  const website = state.analyses.filter(a => a.business_id === id && a.website).sort((a, b) => b.created_at.localeCompare(a.created_at))[0]?.website;
  if (website) right.append(el('section', 'card card-body', '', [el('h2', '', 'Last website snapshot'), external(website.title || 'Source page ↗', website.url), el('p', 'status-detail', `${date(website.observed_at)} · This may predate the latest analysis.`), el('p', 'muted', `${website.has_booking_link ? 'Booking link observed' : 'Booking link not observed'} · ${website.has_inquiry_form ? 'Form detected, untested' : 'Form not observed'} · ${website.emails.length ? website.emails.join(', ') : 'No email link observed'}`), el('p', 'muted', website.limitations), el('div', 'website-excerpt', website.excerpt)]));
  right.append(contactEditor(id, contact));
  if (state.capabilities.crm_history_supported) {
    const activity = el('section', 'card card-body', '', [el('h2', '', 'Contact activity'), el('p', 'muted', 'Recorded activity does not establish delivery or an internal operational gap.')]);
    for (const item of history) activity.append(el('div', 'activity-entry', '', [el('strong', '', human(item.kind)), el('p', 'muted', item.notes || `${human(item.status)}${item.mode ? ' · ' + human(item.mode) : ''}`), el('p', 'status-detail', date(item.occurred_at))]));
    if (!history.length) activity.append(el('p', 'muted', 'No contact activity recorded.'));
    activity.append(link('Manage follow-up tasks →', '#tasks', 'button small')); right.append(activity);
  }
  if (analysis) {
    const draftCard = el('section', 'card card-body', '', [el('h2', '', 'Prepare outreach'), el('p', 'muted', 'Generate a draft for human review. This workspace does not send it.')]);
    const target = el('div');
    const draftButton = button('Generate outreach draft', async () => {
      const draft = await api(`/businesses/${id}/outreach-draft?analysis_id=${encodeURIComponent(analysis.id)}`);
      const text = el('textarea', 'draft-text'); text.readOnly = true; text.value = `Subject: ${draft.subject}\n\n${draft.body}`; text.setAttribute('aria-label', 'Outreach draft');
      target.replaceChildren(el('div', 'callout', draft.kind === 'discovery' ? 'Discovery draft: asks about the process without claiming an internal gap. Review before using.' : 'Based on recorded business confirmation. Review the source, wording, and scope before using.'), text, button('Download draft', () => saveBlob(new Blob([text.value], { type: 'text/plain' }), 'outreach-draft.txt'), 'small'));
    }, 'small');
    draftButton.disabled = contact.stage === 'do_not_contact';
    if (draftButton.disabled) draftCard.append(el('p', 'error-text', 'This lead is marked do not contact. Outreach drafts are blocked.'));
    draftCard.append(draftButton, target); right.append(draftCard);
    const generate = button('Create workflow draft', async () => { const workflow = await post('/workflows', { analysis_id: analysis.id }); await load(); notice('Workflow definition saved. It does not execute.'); saveJSON(workflow, `workflow-${workflow.id}.json`); }, 'small');
    generate.disabled = analysis.automation_type === 'research_required' || contact.stage === 'do_not_contact';
    right.append(el('section', 'card card-body', '', [el('h2', '', 'Workflow definition'), el('p', 'muted', contact.stage === 'do_not_contact' ? 'This lead is marked do not contact. New workflow drafts are blocked.' : generate.disabled ? 'Confirm an automation need in the evidence before generating a draft.' : 'A proposed definition based on this analysis. Review provisional evidence before testing or configuring live delivery.'), generate, el('p', 'status-detail', 'Internal JSON format. Live delivery and native n8n integration are not implemented.')]));
  }
  if (record.provenance) right.append(el('section', 'card card-body', '', [el('h2', '', 'Import provenance'), el('p', 'muted', `File: ${record.provenance.file_name}`), el('p', 'muted', `Recorded collection time: ${date(record.provenance.collected_at)}`), el('p', 'muted long-wrap', `Place ID: ${record.provenance.place_id || 'Not supplied'}`), button('Download saved lead & evidence', () => saveJSON({ record, latest_analysis: analysis || null }, 'lead-research.json'), 'small')]));
  body.append(el('div', 'detail-grid', '', [left, right])); region.append(body);
}
function evidenceEditor(id, analysis) {
  const details = el('details'), summary = el('summary', '', 'Record or update evidence'); details.append(summary);
  const form = el('form'); form.style.marginTop = '16px';
  const criterion = select(Object.entries(criteria), 'inquiry_followup');
  const assessment = select([['unknown', 'Unknown / unassessed'], ['strong', 'Strong evidence · full points'], ['partial', 'Partial evidence · half points'], ['clear', 'Assessed · no need / 0 points']], 'unknown');
  const source = select([['manual_research', 'Manual research'], ['public_website', 'Public website'], ['public_listing', 'Public listing'], ['business_confirmation', 'Business confirmation']], 'manual_research');
  const observed = el('input'); observed.type = 'datetime-local'; observed.required = true; observed.value = localTime(); observed.max = localTime();
  const detail = el('textarea'); detail.required = true; detail.maxLength = 2000; detail.placeholder = 'What did you observe? Include the source URL or who confirmed the process.';
  const confirm = el('input'); confirm.type = 'checkbox';
  const confirmation = el('label', 'check-label', '', [confirm, el('span', '', 'The business actually confirmed this process; the details identify the conversation or source.')]);
  function loadCriterion() {
    const item = analysis?.evidence.find(e => e.criterion === criterion.value);
    assessment.value = item?.assessment || 'unknown'; source.value = item?.source || 'manual_research'; detail.value = item?.detail || ''; observed.value = localTime(item?.observed_at); confirm.checked = false; updateRequirement();
  }
  function updateRequirement() {
    const requires = operational.has(criterion.value) && assessment.value !== 'unknown';
    confirmation.hidden = !requires; confirm.required = requires;
    if (requires) source.value = 'business_confirmation'; source.disabled = requires;
  }
  criterion.onchange = loadCriterion; assessment.onchange = updateRequirement;
  form.append(el('p', 'muted', 'Only enter observations you can support. Strong/partial refer to the scoring criteria below, not your confidence in a guess.'), field('Criterion', criterion), field('Assessment', assessment), field('Source', source), field('Observation time (your local time)', observed), field('Evidence details', detail), confirmation,
    el('div', 'callout', 'Need criteria: confirmed manual processes. Scale: 1 practitioner = 0, 2–3 = half, ≥4 or multiple locations = full. Recurrence: none = 0, one repeat offering = half, several or membership = full. Contact: usable channels; an untested form earns at most half. Friction: assess the actual customer journey, not just link presence.'));
  submit(form, 'Save evidence & recalculate', async () => {
    const evidence = (analysis?.evidence || []).filter(e => e.criterion !== criterion.value);
    evidence.push({ criterion: criterion.value, assessment: assessment.value, source: source.value, origin: 'operator', detail: detail.value.trim(), observed_at: new Date(observed.value).toISOString() });
    await post(`/businesses/${id}/analyze`, { fetch_website: false, use_ai: false, evidence }); await refreshLead(id); notice('Evidence recorded with its source and date. A new analysis was saved.');
  });
  details.append(form); loadCriterion(); return details;
}
function contactEditor(id, contact) {
  const form = el('form', 'card card-body');
  const stage = select(['new', 'contacted', 'interested', 'demo_booked', 'won', 'lost', 'do_not_contact'].map(x => [x, human(x)]), contact.stage);
  const notes = el('textarea'); notes.maxLength = 4000; notes.value = contact.notes;
  form.append(el('h2', '', 'Contact tracking'), el('p', 'muted', 'Record your actual conversations and outcomes. Saving a stage does not contact this business.'), field('Stage', stage), field('Notes', notes));
  submit(form, 'Save contact record', async () => { await api(`/businesses/${id}/contact`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stage: stage.value, notes: notes.value }) }); await refreshLead(id); notice('Contact stage and notes saved.'); });
  return form;
}
function renderWorkflows() {
  content.append(heading('WORKFLOW DRAFTS', 'Workflow drafts', 'Saved definitions for human review. They do not run automations.'));
  content.append(el('div', 'callout', 'Saving a workflow creates a definition. Supported message workflows can run in the Automation lab or through a reviewed client setup. Calendar and arbitrary graphs remain unsupported.'));
  content.append(link('Manage client setup →', '#clients', 'button small'));
  const visible = state.workflows.filter(w => records().some(r => r.id === w.business_id));
  if (!visible.length) { content.append(empty('No workflow drafts yet', 'Open a lead, confirm an automation need, then create a workflow draft.', link('Open leads →', '#leads', 'button'))); return; }
  for (const workflow of visible.sort((a, b) => b.created_at.localeCompare(a.created_at))) {
    const record = state.businesses.find(r => r.id === workflow.business_id), nodes = el('div');
    workflow.nodes.forEach((node, index) => { if (index) nodes.append(el('span', 'workflow-arrow', '→')); nodes.append(el('span', 'workflow-node', human(node.type))); });
    const configuration = el('ul'); workflow.required_configuration.forEach(item => configuration.append(el('li', '', item)));
    const actions = el('div', 'row', '', [button('Download JSON', async () => saveJSON(await api(`/workflows/${workflow.id}/export`), `workflow-${workflow.id}.json`), 'small')]);
    if (workflow.status !== 'archived') actions.append(button('Archive', async () => { await post(`/workflows/${workflow.id}/archive`, {}); await load(); notice('Workflow draft archived.'); }, 'small'));
    content.append(el('section', 'card workflow-card', '', [el('div', 'row space-between', '', [el('h2', '', workflow.name), badge(`${human(workflow.status)} · not running`)]), el('p', 'muted', `${record?.business.name || 'Unknown business'} · ${date(workflow.created_at)}`), nodes, el('p', 'status-detail', 'Configuration required before any future execution:'), configuration, actions]));
  }
}
function renderConnections() {
  content.append(heading('CONNECTIONS', 'Connections', 'Configuration presence and live operation are different checks.'));
  const c = state.capabilities;
  const items = [
    ['▤', 'Local / shared storage', c.persistence === 'sqlite' ? 'SQLite connected' : 'Supabase configured', `Readiness checked the selected ${human(c.persistence)} storage. Individual user accounts are not implemented.`, 'good'],
    ['⌕', 'Free browser collection', c.browser_collection_configured ? 'Prerequisites detected' : 'Not configured', 'Uses the bundled Google Maps browser collector. Each run reports success or failure; detected prerequisites do not guarantee network access or a successful query.', c.browser_collection_configured ? 'neutral' : 'research'],
    ['↗', 'Website research', c.website_fetching_configured ? 'Hosts configured' : 'Not configured', 'Only approved public HTTPS websites can be fetched. Static observations do not establish internal processes or prove a booking flow works.', c.website_fetching_configured ? 'neutral' : 'research'],
    ['G', 'Google Places API', c.discovery_configured ? 'Credential configured' : 'Optional · not configured', 'An optional paid-provider adapter. Key presence is not a live verification. The free collection and CSV path does not need it.', c.discovery_configured ? 'neutral' : 'research'],
    ['✧', 'AI narrative', c.ai_configured ? 'Credential configured' : 'Optional · not configured', 'Optional summary generation. Evidence points are calculated by fixed rules. API key presence does not prove the provider is reachable.', c.ai_configured ? 'neutral' : 'research'],
    ['☎', 'Human dialer', c.calling_enabled && c.calling_configured ? 'Enabled + configured' : 'Disabled or incomplete', 'The backend supports Twilio calling your sales agent first, then connecting to the business. It needs explicit confirmation and valid international numbers. This frontend has no call action; AI voice calling is not built.', c.calling_enabled && c.calling_configured ? 'neutral' : 'research'],
    ['→', 'Workflow execution', c.workflow_runner_modes?.includes('sandbox') ? 'Sandbox API available' : 'Sandbox requires SQLite', 'The automation lab runs reminders and saves unsent previews. Native calendar integration and n8n import remain to be built.', 'research'],
    ['✉', 'Reminder email', c.email_delivery_configured ? 'Enabled + configured' : 'Disabled or incomplete', 'Resend submission and signed delivery callbacks are implemented. Configuration presence does not establish successful live delivery. Sandbox reminders need no email account.', c.email_delivery_configured ? 'neutral' : 'research']
  ];
  const grid = el('div', 'two-columns');
  for (const [icon, title, label, detail, style] of items) grid.append(el('section', 'card connection-card', '', [el('div', 'connection-icon', icon), el('div', 'row space-between', '', [el('h2', '', title), badge(label, style)]), el('p', '', detail)]));
  content.append(grid);
}

function localDateTime(value) {
  const time = new Date(value); return new Date(time.getTime() - time.getTimezoneOffset() * 60000).toISOString().slice(0, 19);
}
function input(type, value = '') { const node = el('input'); node.type = type; node.value = value; return node; }
function renderAutomation() {
  content.append(heading('AUTOMATION LAB', 'Automation lab', 'Schedule a sandbox reminder, inspect its history, or cancel it before it runs.', button('Refresh run history', load, 'small')));
  content.append(el('div', 'callout', 'Sandbox only: messages stay in this workspace. No email, SMS, or calls are sent. The fictional demo is clearly labeled; real business needs remain separate.'));
  if (!state.capabilities.workflow_runner_modes?.includes('sandbox')) { content.append(empty('SQLite runner required', 'The research workspace remains available; this reminder lab currently requires SQLite.')); return; }
  const eligible = state.workflows.filter(w => w.status === 'draft' && w.nodes[0]?.parameters.event === 'appointment_reminders' && latest(w.business_id)?.id === w.analysis_id && qualification(w.business_id)?.prospect_status !== 'do_not_contact');
  const demoButton = button('Create fictional reminder demo', async () => { await post('/demo/reminder-workflow', {}); state.demo = true; await load(); notice('Fictional reminder workflow is ready. No real business was analyzed or contacted.'); }, 'small');
  content.append(demoButton);
  if (eligible.length) {
    const form = el('form', 'card card-body');
    const workflow = select(eligible.map(w => [w.id, `${state.businesses.find(b => b.id === w.business_id)?.business.name || w.name}`]), eligible.some(w => w.id === state.proofChoice) ? state.proofChoice : eligible[0].id); workflow.required = true;
    const contact = input('text', 'synthetic-contact-001'); contact.required = true; contact.maxLength = 100;
    const starts = input('datetime-local', localDateTime(Date.now() + 3600000)); starts.required = true; starts.step = '1';
    const scheduled = input('datetime-local', localDateTime(Date.now() + 15000)); scheduled.required = true; scheduled.step = '1';
    const message = el('textarea'); message.value = 'Synthetic appointment reminder. This preview is not sent.'; message.required = true; message.maxLength = 1000;
    const permission = input('checkbox'); permission.required = true;
    const confirmed = input('checkbox'); confirmed.required = true;
    const managed = state.deployments.filter(d => d.status === 'active' && d.channel === 'sandbox' && eligible.some(w => w.id === d.workflow_id) && state.clients.some(c => c.id === d.client_id && c.status === 'active'));
    const context = select([['', 'Standalone sandbox'], ...managed.map(d => [d.id, state.businesses.find(b => b.id === d.business_id)?.business.name || 'Client deployment'])], managed.some(d => d.id === state.managedChoice) ? state.managedChoice : '');
    const applyContext = () => { const chosen = managed.find(d => d.id === context.value); if (chosen) workflow.value = chosen.workflow_id; workflow.disabled = !!chosen; state.managedChoice = context.value; };
    context.addEventListener('change', applyContext); applyContext();
    form.append(el('h2', '', 'Schedule sandbox reminder'));
    form.append(field('Client deployment (optional)', context, 'An active sandbox deployment applies client pause and validation controls.'));
    form.append(field('Reminder workflow', workflow), field('Synthetic contact reference', contact), field('Appointment starts', starts), field('Reminder time', scheduled), field('Reminder preview text', message), el('label', 'check-label reminder-consent', '', [permission, el('span', '', 'Permission recorded for this synthetic contact')]), el('label', 'check-label reminder-consent', '', [confirmed, el('span', '', 'I understand this creates an unsent sandbox preview')]));
    const pending = state.reminderIntent;
    if (pending) {
      const body = pending.body; workflow.value = body.workflow_id; contact.value = body.reminder.event.contact_id;
      starts.value = localDateTime(body.starts_at); scheduled.value = localDateTime(body.reminder.scheduled_at); message.value = body.reminder.message_body;
      permission.checked = body.reminder.event.contact_permission; confirmed.checked = true;
      context.value = pending.path === '/appointments' ? '' : pending.path.split('/')[2]; applyContext();
    }
    form.addEventListener('input', () => { state.reminderIntent = null; });
    submit(form, 'Schedule sandbox reminder', async () => {
      if (state.stale) throw new Error('Refresh the workspace before scheduling a reminder.');
      const intent = state.reminderIntent || { path: context.value ? `/deployments/${context.value}/appointments` : '/appointments', body: { workflow_id: workflow.value, starts_at: new Date(starts.value).toISOString(), reminder: { mode: 'sandbox', confirm_sandbox: confirmed.checked, idempotency_key: crypto.randomUUID(), event: { contact_id: contact.value.trim(), contact_permission: permission.checked }, message_body: message.value.trim(), scheduled_at: new Date(scheduled.value).toISOString() } } };
      state.reminderIntent = intent;
      const appointment = await post(intent.path, intent.body);
      state.reminderIntent = null; await load(); notice(`Sandbox appointment ${appointment.id.slice(0, 8)} scheduled. Refresh run history to see its progress.`);
    });
    content.append(form);
  } else content.append(empty('No current reminder workflow', 'Create the fictional demo above, or record a supported reminder need and generate its workflow.'));
  content.append(el('h2', '', 'Appointments and run history'));
  if (!state.appointments.length) content.append(el('p', 'muted', 'No appointment events have been recorded.'));
  for (const appointment of state.appointments) {
    const run = state.runs.find(item => item.id === appointment.run_id), outbox = state.outbox.find(item => item.run_id === appointment.run_id);
    const business = state.businesses.find(item => item.id === appointment.business_id);
    const card = el('section', 'card card-body');
    card.dataset.appointmentId = appointment.id;
    card.append(el('div', 'row space-between', '', [el('h3', '', business?.business.name || 'Saved appointment'), badge(appointment.reminder.mode === 'sandbox' ? 'Sandbox · unsent' : 'Email · inspect delivery', 'neutral')]), el('p', 'muted', `Contact: ${appointment.reminder.event.contact_id} · Appointment: ${date(appointment.starts_at)}`), el('p', 'run-status', `Appointment: ${human(appointment.status)} · Run: ${run ? human(run.status) : 'Pending'}`));
    if (run?.stop_reason) card.append(el('p', 'status-detail', human(run.stop_reason)));
    if (outbox) card.append(el('p', 'status-detail', outbox.mode === 'sandbox' ? 'Unsent sandbox preview' : `Delivery: ${human(outbox.status)}${outbox.delivered ? ' · Provider reports delivered' : outbox.sent ? ' · Provider reports sent' : ' · Delivery unconfirmed'}`), el('pre', 'message-preview', outbox.message_body));
    if (run) {
      const history = el('details'); history.append(el('summary', '', 'Step history'));
      const entries = el('ul'); for (const item of run.history) entries.append(el('li', '', `${date(item.at)} · ${item.step ? human(item.step) + ': ' : ''}${human(item.outcome)}`));
      history.append(entries); card.append(history);
    }
    if (appointment.status !== 'cancelled') card.append(button('Cancel appointment', async () => { await post(`/appointments/${appointment.id}/cancel`, {}); await load(); notice('Appointment cancelled. Pending work is stopped; already submitted messages cannot be recalled.'); }, 'small'));
    content.append(card);
  }
}
function assertFresh() {
  if (!state.loaded || state.stale) throw new Error('Refresh the workspace before making changes.');
}
function demoToggle() {
  const control = input('checkbox'); control.checked = state.demo;
  control.onchange = () => { state.demo = control.checked; render(); };
  return el('label', 'check-label', '', [control, el('span', '', 'Include fictional demo records')]);
}
function confirmation(text) {
  const control = input('checkbox'); control.required = true;
  return { control, label: el('label', 'check-label', '', [control, el('span', '', text)]) };
}
function rememberIntent(key, data) {
  const previous = state.intents[key];
  const signature = JSON.stringify(data);
  if (previous?.signature === signature) return previous.body;
  const body = { ...data, idempotency_key: crypto.randomUUID() };
  state.intents[key] = { signature, body }; return body;
}
function supportedWorkspace() {
  if (state.capabilities.client_workflow_activation_supported) return true;
  content.append(empty('SQLite workspace required', 'Client setup, tasks and monitoring require SQLite. Research remains available.'));
  return false;
}
async function changeAndRefresh(path, body, message) {
  assertFresh(); await post(path, body); await load(); notice(message);
}
function renderClients() {
  content.append(heading('CLIENTS', 'Clients', 'Record authorization, test a workflow, and review its sandbox setup.', button('Refresh client setup', load, 'small')));
  if (!supportedWorkspace()) return;
  content.append(el('div', 'row', '', [demoToggle(), button('Create fictional client example', async () => {
    assertFresh(); await post('/demo/reminder-workflow', {}); state.demo = true; await load();
    notice('Fictional lead and reminder workflow are ready. Record demo authorization to onboard it.');
  }, 'small')]));
  content.append(el('p', 'muted', 'Client profiles use this shared operator workspace. They do not create client logins or publish another server. Browser setup uses sandbox mode; previews remain unsent.'));
  const eligible = records().filter(b => qualification(b.id)?.prospect_status !== 'do_not_contact' && !state.clients.some(c => c.business_id === b.id && c.status !== 'archived'));
  if (eligible.length) {
    if (state.intents.onboarding && !eligible.some(b => b.id === state.intents.onboarding.body.business_id)) delete state.intents.onboarding;
    const pending = state.intents.onboarding?.body, form = el('form', 'card card-body workspace-card'); form.dataset.form = 'onboarding';
    const business = select(eligible.map(b => [b.id, `${b.business.name}${b.source === 'mock' ? ' · fictional' : ''}`]), eligible.some(b => b.id === pending?.business_id) ? pending.business_id : eligible[0].id); business.required = true;
    const contact = input('text', pending?.contact_name || ''); contact.required = true; contact.maxLength = 200;
    const email = input('email', pending?.contact_email || ''); email.maxLength = 254;
    const timezone = input('text', pending?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'); timezone.required = true; timezone.maxLength = 200;
    const reference = el('textarea'); reference.value = pending?.approval_reference || ''; reference.required = true; reference.maxLength = 2000;
    const consent = confirmation('Business authorization is recorded; fictional authorization is only for demo businesses.');
    form.append(el('h2', '', 'Onboard a client'), field('Client business', business), field('Client contact name', contact), field('Client contact email (optional)', email), field('Client timezone', timezone, 'Use an IANA timezone, such as Asia/Karachi or America/New_York.'), field('Authorization reference', reference, 'Record who agreed to the scope and where that authorization is documented.'), consent.label);
    submit(form, 'Create client profile', async () => {
      assertFresh(); const body = rememberIntent('onboarding', { business_id: business.value, contact_name: contact.value.trim(), contact_email: email.value.trim() || null, timezone: timezone.value.trim(), approval_reference: reference.value.trim(), confirm_business_authorization: consent.control.checked });
      await post('/clients', body); delete state.intents.onboarding; await load(); notice('Client profile saved. Review authorization before activating it.');
    }); content.append(form);
  }
  const clients = state.clients.filter(c => records().some(b => b.id === c.business_id));
  if (!clients.length) content.append(empty('No client profiles yet', 'Choose a business above or explicitly create the fictional example.'));
  for (const client of clients) {
    const record = state.businesses.find(b => b.id === client.business_id), card = el('section', 'card card-body workspace-card'); card.dataset.clientId = client.id;
    card.append(el('div', 'row space-between', '', [el('h2', '', record?.business.name || 'Saved client'), badge(human(client.status), client.status === 'active' ? 'good' : 'neutral')]), el('div', 'row', '', [client.is_demo ? badge('Demo client · fictional', 'demo') : needStatus(qualification(client.business_id))]), el('p', 'muted long-wrap', `${client.contact_name} · ${client.timezone}${client.contact_email ? ' · ' + client.contact_email : ''}`), el('p', 'long-wrap', client.approval_reference));
    const actions = el('div', 'row');
    if (client.status === 'onboarding' || client.status === 'paused') {
      const agreed = confirmation('I reviewed this client authorization.');
      const activate = button('Activate client', () => changeAndRefresh(`/clients/${client.id}/activate`, { confirm_authorization: agreed.control.checked }, 'Client activated. Validate a workflow before activating its sandbox setup.'), 'small');
      activate.disabled = true; agreed.control.onchange = () => { activate.disabled = !agreed.control.checked; };
      card.append(agreed.label); actions.append(activate);
    }
    if (client.status === 'active') actions.append(button('Pause client', () => changeAndRefresh(`/clients/${client.id}/pause`, {}, 'Client paused. Pending managed work will stop; submitted messages cannot be recalled.'), 'small'));
    actions.append(button('Download client handoff', async () => { assertFresh(); saveJSON(await api(`/clients/${client.id}/handoff`), `client-handoff-${client.id}.json`); }, 'small'));
    card.append(actions);
    const history = el('div'); card.append(button('View client history', async () => {
      const rows = await api(`/clients/${client.id}/history?limit=100`);
      if (!history.isConnected) return;
      history.replaceChildren(...rows.map(r => el('p', 'status-detail', `${date(r.at)} · ${human(r.outcome)}`)));
    }, 'small'), history);
    const workflows = state.workflows.filter(w => w.business_id === client.business_id && w.status === 'draft' && w.analysis_id === latest(client.business_id)?.id && !w.nodes.some(n => n.type === 'calendar'));
    if (client.status !== 'archived' && workflows.length) {
      const form = el('form', 'client-setup-form');
      const pendingWorkflow = state.intents['deployment:' + client.id]?.body.workflow_id;
      const selected = select(workflows.map(w => [w.id, w.name]), workflows.some(w => w.id === pendingWorkflow) ? pendingWorkflow : workflows[0].id); selected.required = true;
      form.append(field('Client workflow', selected));
      submit(form, 'Create sandbox setup', async () => {
        assertFresh(); const body = rememberIntent('deployment:' + client.id, { workflow_id: selected.value, channel: 'sandbox' });
        await post(`/clients/${client.id}/deployments`, body); delete state.intents['deployment:' + client.id]; await load(); notice('Sandbox setup saved. Run a sandbox proof, then validate it.');
      }); card.append(form);
    } else if (client.status !== 'archived') card.append(el('p', 'muted', 'No current supported message workflow. Confirm the scope with the business before generating one.'));
    for (const deployment of state.deployments.filter(d => d.client_id === client.id)) card.append(deploymentCard(deployment));
    content.append(card);
  }
}
function deploymentCard(deployment) {
  const card = el('section', 'deployment-card'); card.dataset.deploymentId = deployment.id;
  const workflow = state.workflows.find(w => w.id === deployment.workflow_id);
  card.append(el('div', 'row space-between', '', [el('h3', '', workflow?.name || 'Saved workflow'), badge(`${human(deployment.channel)} · ${human(deployment.status)}`)]));
  if (deployment.channel === 'email') card.append(el('p', 'muted', 'Email setup is managed through the API. Inspect provider outcomes; configuration alone does not verify live delivery.'));
  const report = el('div');
  const showReport = (result, label) => {
    report.replaceChildren(el('p', 'muted', `${label} · ${date(result.checked_at)}`));
    const list = el('ul', 'readiness-checks'); for (const check of result.checks) list.append(el('li', '', `${check.passed ? '✓' : 'Needs attention:'} ${check.message}`)); report.append(list);
  };
  if (deployment.validation) showReport(deployment.validation, 'Saved validation');
  const actions = el('div', 'row', '', [button('Check readiness', async () => { const result = await api(`/deployments/${deployment.id}/preflight`); if (report.isConnected) showReport(result, 'Current readiness check'); }, 'small')]);
  if (['draft', 'validated', 'paused'].includes(deployment.status)) actions.append(button('Validate sandbox setup', async () => {
    assertFresh(); const result = await post(`/deployments/${deployment.id}/validate`, {}); await load(); notice(result.validation.ready ? 'Sandbox setup validated. Review and confirm activation.' : 'Validation needs attention. Review the checks and run a successful sandbox proof.');
  }, 'small'));
  if (deployment.status === 'validated' && deployment.channel === 'sandbox') {
    const agreed = confirmation('I reviewed the checks and approve this sandbox setup.');
    const activate = button('Activate sandbox setup', () => changeAndRefresh(`/deployments/${deployment.id}/activate`, { confirm_activation: agreed.control.checked }, 'Sandbox setup activated. Client reminders can now use it.'), 'small');
    activate.disabled = true; agreed.control.onchange = () => { activate.disabled = !agreed.control.checked; }; card.append(agreed.label); actions.append(activate);
  }
  if (deployment.status === 'active') {
    actions.append(button('Pause setup', () => changeAndRefresh(`/deployments/${deployment.id}/pause`, {}, 'Setup paused. Pending managed reminders will stop.'), 'small'));
    if (deployment.channel === 'sandbox') actions.append(button('Schedule client reminder', () => { state.managedChoice = deployment.id; state.reminderIntent = null; location.hash = '#automation'; }, 'small'));
  }
  if (deployment.channel === 'sandbox') actions.append(button('Open sandbox lab for a proof →', () => { state.managedChoice = ''; state.proofChoice = deployment.workflow_id; state.reminderIntent = null; location.hash = '#automation'; }, 'small'));
  card.append(report, actions); return card;
}
function renderTasks() {
  content.append(heading('FOLLOW-UP TASKS', 'Follow-up tasks', 'These are manual tasks. Saving a task does not send a message.', button('Refresh tasks', load, 'small')));
  if (!supportedWorkspace()) return;
  content.append(demoToggle());
  const eligible = records().filter(b => qualification(b.id)?.prospect_status !== 'do_not_contact');
  if (eligible.length) {
    const entry = Object.entries(state.intents).find(([key]) => key.startsWith('task:') && eligible.some(b => key === 'task:' + b.id));
    const pending = entry?.[1].body, form = el('form', 'card card-body workspace-card'); form.dataset.form = 'task';
    const business = select(eligible.map(b => [b.id, b.business.name]), entry ? entry[0].slice(5) : eligible[0].id); business.required = true;
    const title = input('text', pending?.title || ''); title.required = true; title.maxLength = 200;
    const notes = el('textarea'); notes.value = pending?.notes || ''; notes.maxLength = 4000;
    const due = input('datetime-local', pending ? localDateTime(pending.due_at) : localDateTime(Date.now() + 86400000)); due.required = true; due.step = '1';
    form.append(el('h2', '', 'Add a follow-up task'), field('Task business', business), field('Task title', title), field('Task notes', notes), field('Task due time', due, 'Times use your browser timezone. Past dates represent overdue work.'));
    submit(form, 'Save follow-up task', async () => {
      assertFresh(); const key = 'task:' + business.value, body = rememberIntent(key, { title: title.value.trim(), notes: notes.value, due_at: new Date(due.value).toISOString() });
      await post(`/businesses/${business.value}/tasks`, body); delete state.intents[key]; await load(); notice('Follow-up task saved. No message was sent.');
    }); content.append(form);
  }
  const visible = state.tasks.filter(t => records().some(b => b.id === t.business_id));
  if (!visible.length) content.append(empty('No follow-up tasks yet', 'Save a manual next step for a business above.'));
  for (const task of visible) {
    const card = el('section', 'card card-body workspace-card'); card.dataset.taskId = task.id;
    const overdue = task.status === 'pending' && new Date(task.due_at).getTime() < Date.now();
    card.append(el('div', 'row space-between', '', [el('h2', 'long-wrap', task.title), badge(overdue ? 'Overdue' : human(task.status), overdue ? 'research' : 'neutral')]), el('p', 'muted', state.businesses.find(b => b.id === task.business_id)?.business.name || 'Saved business'), el('p', 'long-wrap', task.notes), el('p', 'status-detail', `Due ${date(task.due_at)}`));
    if (task.status === 'pending') card.append(el('div', 'row', '', [button('Complete task', async () => { assertFresh(); await api(`/tasks/${task.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: 'completed' }) }); await load(); notice('Task completed.'); }, 'small'), button('Cancel task', async () => { assertFresh(); await api(`/tasks/${task.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: 'cancelled' }) }); await load(); notice('Task cancelled.'); }, 'small')]));
    content.append(card);
  }
}
function renderOperations() {
  content.append(heading('OPERATIONS', 'Operations', 'Saved work, scheduler state, and pending issues. Provider delivery needs its own evidence.', button('Refresh operations', load, 'small')));
  if (!supportedWorkspace()) return;
  content.append(demoToggle());
  const region = el('div'); content.append(region);
  const show = summary => {
    if (!region.isConnected) return;
    region.replaceChildren(el('p', 'muted', `Checked ${date(summary.checked_at)} · ${summary.include_demo ? 'Fictional demo records included' : 'Fictional demo records excluded'}`), el('div', 'stats', '', [stat('Active clients', summary.counts.clients.active || 0, 'Recorded client status'), stat('Active setups', summary.counts.deployments.active || 0, 'Local workflow activation'), stat('Active runs', summary.active_runs, summary.scheduler_running ? 'Scheduler running' : 'Scheduler not running'), stat('Needs attention', summary.alert_count, summary.alerts_truncated ? 'Showing a limited list' : 'Saved issues and overdue work')]));
    if (!summary.alerts.length) region.append(empty('No recorded issues in this view', 'This does not establish live provider access or guaranteed delivery.'));
    for (const item of summary.alerts) {
      const card = el('section', 'card card-body workspace-card'); card.dataset.alertId = item.id;
      card.append(el('div', 'row space-between', '', [el('h2', '', human(item.type)), badge(human(item.status), 'research')]), el('p', 'muted', state.businesses.find(b => b.id === item.business_id)?.business.name || 'Discovery job'), el('p', 'long-wrap', item.reason ? human(item.reason) : ''), el('p', 'status-detail', date(item.at)));
      if (item.type === 'overdue_task') card.append(link('Open tasks →', '#tasks', 'button small'));
      else if (item.type === 'deployment_readiness') card.append(link('Review client setup →', '#clients', 'button small'));
      else if (item.type === 'discovery_job') card.append(link('Open discovery →', '#discovery', 'button small'));
      else if (item.type !== 'call_outcome') card.append(link('Open run history →', '#automation', 'button small'));
      if (item.leg) card.append(el('p', 'muted', 'Sales-agent call leg; prospect answering is unconfirmed.'));
      region.append(card);
    }
  };
  if (state.operations?.include_demo === state.demo) show(state.operations);
  else {
    region.append(el('p', 'muted', 'Loading operations…'));
    api(`/operations/summary?include_demo=${state.demo}`).then(summary => { if (region.isConnected) { state.operations = summary; show(summary); } }).catch(error => { if (region.isConnected) region.replaceChildren(el('p', 'error-text', error.message)); });
  }
}
$('#refresh').onclick = () => busy($('#refresh'), load);
$('#global-search').oninput = updateGlobalSearch;
$('#global-search-form').onsubmit = event => { event.preventDefault(); $('#global-search-results .search-result')?.click(); };
$('#global-search-form').onkeydown = event => {
  if (event.key === 'Escape') { clearGlobalSearch(); $('#global-search').focus(); }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    const matches = [...$('#global-search-results').querySelectorAll('.search-result')];
    if (!matches.length) return;
    event.preventDefault(); const current = matches.indexOf(document.activeElement);
    const next = current === -1 ? (event.key === 'ArrowDown' ? 0 : matches.length - 1) : (current + (event.key === 'ArrowDown' ? 1 : -1) + matches.length) % matches.length;
    matches[next].focus();
  }
};
document.addEventListener('click', event => { if (!$('#global-search-form').contains(event.target)) $('#global-search-results').hidden = true; });
$('#global-search').onfocus = updateGlobalSearch;
$('#lock').onclick = lock;
$('#auth-form').onsubmit = event => {
  event.preventDefault(); const form = event.currentTarget; if (!form.reportValidity()) return;
  const input = $('#api-token'), submitButton = $('button[type=submit]', form);
  busy(submitButton, async () => {
    sessionGeneration++; state.token = input.value; input.value = ''; $('#auth-error').textContent = '';
    try { await load(); authDialog.close(); } catch (error) { $('#auth-error').textContent = error.message; }
  });
};
authDialog.addEventListener('cancel', event => event.preventDefault());
const mobileSections = $('#mobile-sections');
for (const item of document.querySelectorAll('nav a[data-view]')) {
  const choice = link(item.textContent.trim(), item.getAttribute('href'));
  choice.dataset.mobileView = item.dataset.view;
  choice.addEventListener('click', () => { mobileSections.open = false; });
  $('#mobile-section-list').append(choice);
}
mobileSections.addEventListener('keydown', event => { if (event.key === 'Escape') { mobileSections.open = false; mobileSections.querySelector('summary').focus(); } });
document.addEventListener('click', event => { if (!mobileSections.contains(event.target)) mobileSections.open = false; });
window.addEventListener('hashchange', () => { mobileSections.open = false; if (leadDialog.open) { leadDialog.close(); state.selected = null; } render(); });
let polling = false;
setInterval(async () => {
  if (!state.loaded || polling || !state.jobs.some(job => ['queued', 'running'].includes(job.status))) return;
  polling = true;
  try {
    state.jobs = await api('/discovery/jobs'); renderJobs();
    const finished = state.jobs.find(job => job.id === state.pendingPilotId && !['queued', 'running'].includes(job.status));
    if (finished) {
      state.pendingPilotId = null;
      if (finished.status === 'succeeded' && view() === 'discovery' && !state.preview) {
        await showPilotPreview(finished);
        notice(`${finished.collected_count} listings captured. Review categories and details before importing; nothing was saved automatically.`);
      } else if (finished.status === 'failed' && view() === 'discovery') notice(finished.error || 'The pilot failed before producing a preview.', true);
    }
  }
  catch (error) { notice(error.message, true); }
  finally { polling = false; }
}, 3000);
load().catch(() => {});
