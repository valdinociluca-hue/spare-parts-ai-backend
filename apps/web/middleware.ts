import { NextResponse, type NextRequest } from 'next/server';

import { TENANT_SLUG_HEADER } from '@/lib/tenant';

const APP_DOMAIN = process.env.NEXT_PUBLIC_APP_DOMAIN ?? 'partsai.local';
const DEFAULT_SLUG = process.env.NEXT_PUBLIC_DEFAULT_TENANT_SLUG ?? 'lvtrade';
const RESERVED_SUBDOMAINS = new Set(['www', 'admin', 'api', 'widget', 'app']);

/**
 * Subdomain-based tenant resolution.
 *
 * Production: <slug>.partsai.com → header X-PartsAI-Tenant-Slug = <slug>
 * Localhost dev: anything (no subdomain) → use NEXT_PUBLIC_DEFAULT_TENANT_SLUG
 * Reserved subdomains (admin, api, widget) are passed through without tenant scope.
 */
export function middleware(request: NextRequest) {
  const host = request.headers.get('host') ?? '';
  const hostname = host.split(':')[0];

  let slug = DEFAULT_SLUG;

  if (hostname.endsWith(`.${APP_DOMAIN}`)) {
    const sub = hostname.slice(0, -(APP_DOMAIN.length + 1));
    const first = sub.split('.')[0] ?? '';
    if (RESERVED_SUBDOMAINS.has(first)) {
      // Pass through — admin / api / widget have their own concerns.
      return NextResponse.next();
    }
    if (first.length > 0) {
      slug = first;
    }
  }

  const headers = new Headers(request.headers);
  headers.set(TENANT_SLUG_HEADER, slug);

  return NextResponse.next({ request: { headers } });
}

export const config = {
  // Skip static assets and Next internals.
  matcher: ['/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)'],
};
