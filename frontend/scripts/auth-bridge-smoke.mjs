// Run only against a fresh isolated fixture. Never point this at a user's DB.
import assert from 'node:assert/strict';

if (process.env.AUTH_BRIDGE_FIXTURE !== 'true') throw Error('Set AUTH_BRIDGE_FIXTURE=true only for an isolated disposable test server');
const origin = process.env.AUTH_TEST_FRONTEND_URL || 'http://127.0.0.1:18582';
const backend = process.env.AUTH_TEST_BACKEND_URL || 'http://127.0.0.1:18581';
const invite = process.env.AUTH_TEST_INVITE || 'synthetic-account-bridge-token-2026';
const code = process.env.AUTH_TEST_ACCESS_CODE || 'synthetic-account-bridge-preview';
const password = 'Synthetic-account-password-2026';
const checks = [];
let cookie = '';
async function request(path, method = 'GET', body, extraHeaders = {}) {
  const response = await fetch(origin + path, { method, redirect: 'manual', headers: { ...(cookie ? { Cookie: cookie } : {}), ...(body ? { 'Content-Type': 'application/json', Origin: origin } : {}), ...extraHeaders }, body: body ? JSON.stringify(body) : undefined });
  const data = await response.json().catch(() => null);
  return { response, data };
}
function check(label, condition) { assert.ok(condition, label); checks.push(label); }
let result = await request('/api/auth/status');
check('Invited shared accounts available', result.response.status === 200 && result.data.supported && result.data.access_code_required && result.data.legacy_available);
result = await request('/api/backend/tasks');
check('Anonymous API denied', result.response.status === 401);
result = await request('/api/auth/register', 'POST', { name: 'Synthetic Bridge Operator', email: 'bridge@example.test', password, access_code: invite, confirm_shared_workspace: true }, { Origin: 'https://other.example.test' });
check('Cross-origin registration rejected', result.response.status === 403);
result = await request('/api/auth/register', 'POST', { name: 'Synthetic Bridge Operator', email: 'bridge@example.test', password, access_code: invite, confirm_shared_workspace: true });
check('Account registration established a backend session', result.response.status === 201 && result.data.user.email === 'bridge@example.test' && typeof result.data.csrf_token === 'string');
cookie = result.response.headers.getSetCookie().find(value => value.startsWith('aia_session=') && !value.startsWith('aia_session=;'))?.split(';')[0] || '';
check('Real account cookie is distinct from legacy preview', cookie.startsWith('aia_session='));
result = await request('/api/auth/me');
check('Account identity read back', result.response.status === 200 && result.data.user.email === 'bridge@example.test');
const document = await fetch(origin + '/tasks', { headers: { Cookie: cookie, Accept: 'text/html' }, redirect: 'manual' });
check('Account session survives a full page load', document.status === 200 && !document.headers.get('location') && !document.headers.getSetCookie().some(value => value.startsWith('aia_session=;')));
// Bootstrap one fictional retained record through the explicit fixture bearer.
const imported = await fetch(backend + '/businesses/import-csv?dry_run=false', { method: 'POST', headers: { Authorization: `Bearer ${invite}`, 'Content-Type': 'text/csv' }, body: 'name,address,category,place_id\nFictional Auth Bridge Spa,Fixture Road,Medical spa,auth-bridge-fixture\n' });
assert.equal(imported.status, 200);
result = await request('/api/backend/businesses');
check('Account cookie authorizes protected read', result.response.status === 200 && result.data.length === 1);
const business = result.data[0].id;
result = await request(`/api/backend/businesses/${business}/tasks`, 'POST', { idempotency_key: 'auth-bridge-fixture-task', title: 'Synthetic bridge follow-up', due_at: new Date(Date.now() + 3600000).toISOString() });
check('Backend CSRF is supplied for account writes', result.response.status === 201 && result.data.title === 'Synthetic bridge follow-up');
result = await request(`/api/backend/businesses/${business}/tasks`, 'POST', { idempotency_key: 'auth-bridge-cross-origin', title: 'Must be refused', due_at: new Date(Date.now() + 3600000).toISOString() }, { Origin: 'https://other.example.test' });
check('Cross-origin account write is refused', result.response.status === 403);
if (process.env.AUTH_TEST_HEADER_PROOF === 'true') {
  const proof = await fetch(backend + '/fixture/auth-header-proof');
  assert.equal(proof.status, 200);
  const events = await proof.json();
  check('Account write forwards cookie and CSRF without owner bearer', events.some(event => event.method === 'POST' && event.path === `/businesses/${business}/tasks` && event.account_cookie_present && event.csrf_present && !event.authorization_present));
  check('Cross-origin write never reached backend', events.filter(event => event.method === 'POST' && event.path === `/businesses/${business}/tasks`).length === 1);
}
const old = cookie;
result = await request('/api/auth/logout', 'POST');
check('Logout revokes backend session', result.response.status === 200 && result.data.signed_out === true);
result = await request('/api/backend/tasks');
check('Revoked cookie cannot fall back to server bearer', result.response.status === 401);
const revoked = await fetch(backend + '/auth/me', { headers: { Cookie: old } });
check('Logout revocation is confirmed directly in backend', revoked.status === 401);
cookie = '';
result = await request('/api/auth/login', 'POST', { email: 'bridge@example.test', password });
check('Existing account can log in again', result.response.status === 200 && result.data.user.email === 'bridge@example.test');
result = await request('/api/access', 'POST', { code });
cookie = result.response.headers.getSetCookie().find(value => value.startsWith('preview_session='))?.split(';')[0] || '';
check('Legacy preview uses separate cookie', result.response.status === 200 && cookie.startsWith('preview_session='));
result = await request('/api/backend/tasks');
check('Explicit legacy preview remains usable', result.response.status === 200 && result.data.length === 1);
const reload = await fetch(origin + '/tasks', { headers: { Cookie: cookie, Accept: 'text/html' }, redirect: 'manual' });
check('Legacy reload retains its lock behavior', reload.status === 307 && reload.headers.get('location')?.endsWith('/login') && reload.headers.getSetCookie().some(value => value.startsWith('preview_session=;')));
console.log(JSON.stringify({ checks: checks.length, passed: checks, real_provider_operations: false, fixture: true }, null, 2));
