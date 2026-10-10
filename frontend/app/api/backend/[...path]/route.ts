import { NextRequest, NextResponse } from 'next/server';
import { allowed } from '@/lib/session';
import { sameOrigin } from '@/lib/request-origin';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const roots = new Set(['capabilities', 'ready', 'businesses', 'analyses', 'prospects', 'opportunities', 'tasks', 'appointments', 'discovery', 'workflows', 'workflow-runs', 'workflow-outbox', 'ai', 'operations', 'demo']);
const safePart = /^[A-Za-z0-9_-]{1,120}$/;
const getPaths = [
  /^(capabilities|ready|prospects|opportunities|tasks|appointments|analyses|businesses|workflows|workflow-runs|workflow-outbox)$/,
  /^(businesses|analyses|workflows|appointments)\/[A-Za-z0-9_-]+$/,
  /^businesses\/[A-Za-z0-9_-]+\/(activities|contact)$/,
  /^ai\/businesses\/[A-Za-z0-9_-]+\/insights$/,
  /^discovery\/(collector-status|jobs)$/,
  /^discovery\/jobs\/[A-Za-z0-9_-]+\/(csv|spreadsheet.csv)$/,
];
const postPaths = [
  /^businesses\/[A-Za-z0-9_-]+\/analyze$/,
  /^businesses\/[A-Za-z0-9_-]+\/tasks$/,
  /^businesses\/[A-Za-z0-9_-]+\/activities$/,
  /^businesses\/import-csv$/,
  /^discovery\/jobs$/,
  /^discovery\/jobs\/[A-Za-z0-9_-]+\/(preview|import)$/,
  /^ai\/businesses\/[A-Za-z0-9_-]+\/(analysis|pitch|call-script)$/,
  /^ai\/chat$/,
  /^workflows$/,
  /^demo\/reminder-workflow$/,
  /^appointments$/,
  /^appointments\/[A-Za-z0-9_-]+\/cancel$/,
];

async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  if (!(await allowed())) return NextResponse.json({ error: 'Access required' }, { status: 401 });
  const { path } = await context.params;
  if (!path.length || path.length > 6 || !roots.has(path[0]) || path.some(p => !safePart.test(p)))
    return NextResponse.json({ error: 'Unsupported API path' }, { status: 404 });
  const joined = path.join('/');
  const permitted = request.method === 'GET' ? getPaths.some(re => re.test(joined)) : request.method === 'POST' && postPaths.some(re => re.test(joined));
  if (!permitted) return NextResponse.json({ error: 'API operation is not exposed in this workspace' }, { status: 405 });
  if (request.method !== 'GET' && !sameOrigin(request))
    return NextResponse.json({ error: 'Cross-origin request refused' }, { status: 403 });
  const base = process.env.BACKEND_URL;
  const token = process.env.APP_API_TOKEN;
  if (!base || !token || !/^https?:\/\//.test(base)) return NextResponse.json({ error: 'Backend is not configured' }, { status: 503 });
  const target = new URL(path.join('/'), base.endsWith('/') ? base : base + '/');
  target.search = request.nextUrl.search;
  const headers: Record<string, string> = { Authorization: `Bearer ${token}`, Accept: 'application/json' };
  if (request.headers.get('content-type')) headers['Content-Type'] = request.headers.get('content-type')!;
  try {
    const response = await fetch(target, { method: request.method, headers, body: ['GET', 'HEAD'].includes(request.method) ? undefined : await request.arrayBuffer(), cache: 'no-store', redirect: 'manual', signal: AbortSignal.timeout(30000) });
    const data = await response.arrayBuffer();
    return new NextResponse(data, { status: response.status, headers: { 'Content-Type': response.headers.get('content-type') || 'application/json', 'Cache-Control': 'no-store', 'Content-Disposition': response.headers.get('content-disposition') || 'inline' } });
  } catch {
    return NextResponse.json({ error: 'Backend is unavailable' }, { status: 502 });
  }
}

export { forward as GET, forward as POST };
