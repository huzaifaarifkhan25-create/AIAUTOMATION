import { NextRequest, NextResponse } from 'next/server';
import { accountCookieHeader, accountCookieNames, accountSession, backendURL, BackendAuthError, legacyAvailable, previewCookieName } from '@/lib/session';
import { sameOrigin } from '@/lib/request-origin';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function clearCookies(response: NextResponse) {
  for (const name of [...accountCookieNames, previewCookieName]) {
    response.cookies.set(name, '', { httpOnly: true, secure: name.startsWith('__Host-') || process.env.NODE_ENV === 'production', sameSite: 'strict', path: '/', maxAge: 0 });
  }
}

function error(message: string, status: number) {
  return NextResponse.json({ error: message }, { status, headers: { 'Cache-Control': 'no-store' } });
}

async function forward(request: NextRequest, context: { params: Promise<{ action: string }> }) {
  const { action } = await context.params;
  const permitted = request.method === 'GET' ? ['status', 'me'].includes(action) : ['login', 'register', 'logout'].includes(action);
  if (!permitted) return error('Unsupported account operation', 404);
  if (request.method !== 'GET' && (!sameOrigin(request) || ![null, 'same-origin', 'none'].includes(request.headers.get('sec-fetch-site')))) return error('Cross-origin request refused', 403);

  try {
    const target = backendURL(`auth/${action}`);
    const headers: Record<string, string> = { Accept: 'application/json' };
    const cookie = await accountCookieHeader();
    if (cookie) headers.Cookie = cookie;
    if (request.method === 'POST') {
      // The browser's origin was checked above. The upstream call is made by
      // this server using the backend's own origin and real account cookie.
      headers.Origin = target.origin;
      headers['Sec-Fetch-Site'] = 'same-origin';
      if (action === 'logout') {
        const session = await accountSession();
        if (!session) {
          const response = NextResponse.json({ signed_out: true }, { headers: { 'Cache-Control': 'no-store' } });
          clearCookies(response);
          return response;
        }
        headers['X-Workspace-CSRF'] = session.csrf_token;
      } else {
        headers['Content-Type'] = 'application/json';
      }
    }
    const body = request.method === 'POST' && action !== 'logout' ? await request.text() : undefined;
    if (body && body.length > 16384) return error('Account request is too large', 413);
    let upstream: Response;
    try { upstream = await fetch(target, { method: request.method, headers, body, cache: 'no-store', redirect: 'manual', signal: AbortSignal.timeout(15000) }); }
    catch { throw new BackendAuthError('Backend is unavailable', 502); }
    const data = await upstream.json().catch(() => ({ error: 'Invalid response from account server' }));
    if (action === 'status' && upstream.ok) data.legacy_available = legacyAvailable();
    const response = NextResponse.json(data, { status: upstream.status, headers: { 'Cache-Control': 'no-store' } });
    if (upstream.ok && ['login', 'register'].includes(action)) {
      const upstreamCookie = upstream.headers.getSetCookie().map(value => /^(aia_session|__Host-aia_session)=([A-Za-z0-9_-]{32,128});/.exec(value)).find(Boolean);
      if (!upstreamCookie) return error('Account server did not establish a session', 502);
      clearCookies(response);
      response.cookies.set(upstreamCookie[1], upstreamCookie[2], { httpOnly: true, secure: upstreamCookie[1].startsWith('__Host-') || process.env.NODE_ENV === 'production', sameSite: 'strict', path: '/', maxAge: 12 * 60 * 60 });
    }
    if (action === 'logout' && upstream.ok) clearCookies(response);
    return response;
  } catch (cause) {
    return error(cause instanceof BackendAuthError ? cause.message : 'Account operation is unavailable', cause instanceof BackendAuthError ? cause.status : 502);
  }
}

export { forward as GET, forward as POST };
