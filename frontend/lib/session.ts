import { createHmac, timingSafeEqual } from 'node:crypto';
import { cookies } from 'next/headers';

export const previewCookieName = 'preview_session';
export const accountCookieNames = ['__Host-aia_session', 'aia_session'] as const;

export class BackendAuthError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export function backendURL(path: string) {
  const value = process.env.BACKEND_URL;
  try {
    const base = new URL(value || '');
    if (!['http:', 'https:'].includes(base.protocol) || base.username || base.password || base.search || base.hash || !['', '/'].includes(base.pathname)) throw Error();
    const target = new URL(path.replace(/^\/+/, ''), base.origin + '/');
    if (target.origin !== base.origin) throw Error();
    return target;
  } catch { throw new BackendAuthError('Backend is not configured', 503); }
}

export function legacyAvailable() {
  return Boolean(process.env.DEMO_ACCESS_CODE && process.env.DEMO_ACCESS_CODE.length >= 12 && process.env.FRONTEND_SESSION_SECRET && process.env.FRONTEND_SESSION_SECRET.length >= 32 && process.env.APP_API_TOKEN);
}

function secret() {
  const value = process.env.FRONTEND_SESSION_SECRET;
  if (!value || value.length < 32) throw new Error('FRONTEND_SESSION_SECRET must contain at least 32 characters');
  return value;
}

function signature(value: string) { return createHmac('sha256', secret()).update(value).digest('hex'); }

export async function previewAllowed() {
  if (!legacyAvailable()) return false;
  const raw = (await cookies()).get(previewCookieName)?.value || '';
  const [expiry, mac] = raw.split('.');
  if (!expiry || !mac || !/^\d+$/.test(expiry) || Number(expiry) < Date.now() || !/^[a-f0-9]{64}$/.test(mac) || raw.split('.').length !== 2) return false;
  const expected = Buffer.from(signature(expiry), 'hex');
  const actual = Buffer.from(mac, 'hex');
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}

export async function accountCookieHeader() {
  const jar = await cookies();
  return accountCookieNames.map(name => {
    const value = jar.get(name)?.value;
    return value && /^[A-Za-z0-9_-]{32,128}$/.test(value) ? `${name}=${value}` : '';
  }).filter(Boolean).join('; ');
}

export async function accountSession() {
  const cookie = await accountCookieHeader();
  if (!cookie) return null;
  const target = backendURL('auth/me');
  let response: Response;
  try { response = await fetch(target, { headers: { Cookie: cookie, Accept: 'application/json' }, cache: 'no-store', redirect: 'manual', signal: AbortSignal.timeout(10000) }); }
  catch { throw new BackendAuthError('Backend is unavailable', 502); }
  if (response.status === 401) return null;
  if (!response.ok) throw new BackendAuthError('Account session could not be verified', response.status === 503 ? 503 : 502);
  const result = await response.json().catch(() => null);
  if (!result || typeof result.user?.id !== 'string' || typeof result.csrf_token !== 'string' || !/^[a-f0-9]{64}$/.test(result.csrf_token)) throw new BackendAuthError('Account session could not be verified', 502);
  return { cookie, user: result.user as { id: string; email: string; name: string }, csrf_token: result.csrf_token as string };
}

export async function allowed() {
  try { if (await accountSession()) return true; }
  catch { return false; }
  return previewAllowed();
}

// Accounts always retain their real backend identity. A signed legacy preview
// is the only path that may use the server's shared bearer token.
export async function backendAuthHeaders(method: string): Promise<Record<string, string>> {
  const session = await accountSession();
  if (session) {
    const headers: Record<string, string> = { Cookie: session.cookie };
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase())) {
      headers['X-Workspace-CSRF'] = session.csrf_token;
      headers.Origin = backendURL('').origin;
      headers['Sec-Fetch-Site'] = 'same-origin';
    }
    return headers;
  }
  if (await previewAllowed()) return { Authorization: `Bearer ${process.env.APP_API_TOKEN}` };
  throw new BackendAuthError('Sign in required', 401);
}

export function validateCode(code: string) {
  if (!legacyAvailable()) return false;
  const expected = process.env.DEMO_ACCESS_CODE;
  if (!expected || expected.length < 12) throw new Error('DEMO_ACCESS_CODE must contain at least 12 characters');
  const a = Buffer.from(code); const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

export async function openSession() {
  const expiry = String(Date.now() + 8 * 60 * 60 * 1000);
  (await cookies()).set(previewCookieName, `${expiry}.${signature(expiry)}`, { httpOnly: true, secure: process.env.NODE_ENV === 'production', sameSite: 'strict', path: '/', maxAge: 8 * 60 * 60 });
}

export async function closeSession() { (await cookies()).delete(previewCookieName); }
