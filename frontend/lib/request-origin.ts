import { NextRequest } from 'next/server';

export function sameOrigin(request: NextRequest) {
  const origin = request.headers.get('origin');
  if (!origin) return true;
  const host = request.headers.get('host');
  if (!host) return false;
  try {
    const source = new URL(origin);
    if (source.host !== host) return false;
    const forwardedProtocol = request.headers.get('x-forwarded-proto');
    const protocol = forwardedProtocol?.split(',')[0]?.trim() || request.nextUrl.protocol.slice(0, -1);
    return source.protocol === `${protocol}:`;
  } catch {
    return false;
  }
}
