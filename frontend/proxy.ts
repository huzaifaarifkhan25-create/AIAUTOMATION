import { NextRequest, NextResponse } from 'next/server';

// A fresh document load (reload, new tab, or typed URL) locks the local preview.
// In-app navigation uses client-side routing and keeps the active session.
export function proxy(request: NextRequest) {
  const documentRequest = request.headers.get('sec-fetch-dest') === 'document' ||
    request.headers.get('accept')?.includes('text/html');
  if (request.method !== 'GET' || !documentRequest)
    return NextResponse.next();

  const response = NextResponse.redirect(new URL('/login', request.url));
  response.cookies.delete('aia_session');
  response.headers.set('Cache-Control', 'no-store');
  return response;
}

export const config = {
  matcher: ['/', '/dashboard', '/discover', '/leads', '/tasks', '/workflows', '/lab', '/chat', '/settings'],
};
