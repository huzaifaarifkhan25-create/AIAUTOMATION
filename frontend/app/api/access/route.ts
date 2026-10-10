import { NextRequest, NextResponse } from 'next/server';
import { closeSession, openSession, validateCode } from '@/lib/session';
import { sameOrigin } from '@/lib/request-origin';

export async function POST(request: NextRequest) {
  if (!sameOrigin(request)) return NextResponse.json({ error: 'Cross-origin request refused' }, { status: 403 });
  const body = await request.json().catch(() => ({}));
  if (typeof body.code !== 'string' || !validateCode(body.code)) return NextResponse.json({ error: 'Invalid access code' }, { status: 401 });
  await openSession();
  return NextResponse.json({ ok: true });
}

export async function DELETE(request: NextRequest) { if (!sameOrigin(request)) return NextResponse.json({ error: 'Cross-origin request refused' }, { status: 403 }); await closeSession(); return NextResponse.json({ ok: true }); }
