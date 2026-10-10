const origin = 'http://127.0.0.1:3011';
const login = await fetch(origin + '/api/access', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: 'synthetic-demo-access' }) });
if (!login.ok) throw Error('Access gate failed');
const cookie = (login.headers.get('set-cookie') || '').split(';')[0];
if (!cookie.startsWith('aia_session=')) throw Error('Access session cookie missing');
async function request(path, init = {}) {
  const response = await fetch(origin + '/api/backend/' + path, { ...init, headers: { Cookie: cookie, ...(init.headers || {}) } });
  const body = await response.json();
  return { status: response.status, body };
}
const cap = await request('capabilities');
if (cap.status !== 200 || cap.body.persistence !== 'sqlite') throw Error('Backend proxy failed');
const csv = 'name,address,category,place_id\nFictional Med Spa,Demo Road,Medical spa,fixture-1\nInvalid Demo,,Spa,fixture-2\n';
const preview = await request('businesses/import-csv?dry_run=true', { method: 'POST', headers: { 'Content-Type': 'text/csv' }, body: csv });
if (preview.status !== 200 || preview.body.valid_rows !== 1 || preview.body.invalid_rows !== 1) throw Error('CSV preview failed');
const before = await request('businesses');
if (before.status !== 200 || before.body.length !== 0) throw Error('Preview unexpectedly imported records');
const imported = await request('businesses/import-csv?dry_run=false', { method: 'POST', headers: { 'Content-Type': 'text/csv' }, body: csv });
if (imported.status !== 200 || imported.body.imported_rows !== 1) throw Error('CSV import failed');
const duplicate = await request('businesses/import-csv?dry_run=false', { method: 'POST', headers: { 'Content-Type': 'text/csv' }, body: csv });
if (duplicate.status !== 200 || duplicate.body.duplicate_rows !== 1) throw Error('CSV duplicate skipping failed');
const rows = await request('businesses');
const businessId = rows.body[0]?.id;
if (!businessId) throw Error('Fixture business missing');
const pitch = await request(`ai/businesses/${businessId}/pitch`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ language: 'en', sender: { name: 'Ayesha', company: 'Example Studio', offer: 'a review of inquiry follow-up options' } }) });
if (pitch.status !== 200 || pitch.body.origin !== 'rules' || pitch.body.sent !== false || pitch.body.kind !== 'pitch') throw Error('Unsent email fallback failed through proxy');
const script = await request(`ai/businesses/${businessId}/call-script`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ language: 'en', sender: { name: 'Ayesha', company: 'Example Studio', offer: 'a review of inquiry follow-up options' } }) });
if (script.status !== 503) throw Error('Call script should report missing Gemini key');
const note = await request(`businesses/${businessId}/activities`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ idempotency_key: 'synthetic-manual-contact', kind: 'email', direction: 'outgoing', notes: 'Fictional operator note; delivery unverified.', occurred_at: new Date(Date.now() - 1000).toISOString() }) });
if (note.status !== 201 || note.body.origin !== 'operator' || 'delivered' in note.body || 'evidence' in note.body) throw Error('Manual activity provenance failed through proxy');
const insights = await request(`ai/businesses/${businessId}/insights`);
if (insights.status !== 200 || !insights.body.some(row => row.kind === 'pitch' && row.sent === false)) throw Error('Saved draft readback failed');
const forbidden = await request('businesses/fixture/calls', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
if (forbidden.status !== 405) throw Error('Proxy exposed call route');
const reload = await fetch(origin + '/workflows', { headers: { Cookie: cookie, Accept: 'text/html' }, redirect: 'manual' });
if (reload.status !== 307 || !reload.headers.get('location')?.endsWith('/login') || !reload.headers.get('set-cookie')?.startsWith('aia_session=;'))
  throw Error('Full page reload did not clear the preview session');
console.log('PASS: access gate, reload lock, authenticated proxy, CSV import, unsent email fallback, manual activity, saved draft readback, call route blocked (isolated fixture).');
