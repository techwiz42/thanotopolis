import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// For now, we'll handle authentication client-side
// This middleware is a placeholder for future server-side auth checks

export function middleware(request: NextRequest) {
  // Allow all requests for now
  // Authentication is handled client-side in the components
  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
