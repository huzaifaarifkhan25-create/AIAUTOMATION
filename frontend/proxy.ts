import { NextRequest, NextResponse } from 'next/server';

// Account sessions survive document navigation and are verified by the page.
// Only the legacy shared-code preview locks on a fresh document load.
export function proxy(request: NextRequest) {
  const documentRequest = request.headers.get('sec-fetch-dest') === 'document' ||
    request.headers.get('accept')?.includes('text/html');
  if (request.method !== 'GET' || !documentRequest)
    return NextResponse.next();

  if (request.cookies.has('aia_session') || request.cookies.has('__Host-aia_session'))
    return NextResponse.next();

  const response = NextResponse.redirect(new URL('/login', request.url));
  response.cookies.delete('preview_session');
  response.headers.set('Cache-Control', 'no-store');
  return response;
}

export const config = {
  matcher: ['/', '/dashboard', '/discover', '/leads', '/tasks', '/workflows', '/lab', '/chat', '/settings', '/automations', '/inquiries', '/outcomes'],
};
