import { headers } from 'next/headers';

import type { Tenant } from '@partsai/shared';

import { env } from './env';
import { hexToRgb } from './utils';

export const TENANT_SLUG_HEADER = 'x-partsai-tenant-slug';

/** Read the tenant slug that the Next.js middleware put on the request. */
export function getTenantSlugFromHeaders(): string {
  const slug = headers().get(TENANT_SLUG_HEADER);
  return slug ?? env.NEXT_PUBLIC_DEFAULT_TENANT_SLUG;
}

/** Fetch the current tenant from the API. Cached for the request via Next.js fetch cache. */
export async function getCurrentTenant(): Promise<Tenant | null> {
  const slug = getTenantSlugFromHeaders();
  const url = `${env.NEXT_PUBLIC_API_URL}/api/v1/tenants/me`;
  const response = await fetch(url, {
    headers: { 'X-Tenant-Slug': slug },
    next: { revalidate: 60, tags: [`tenant:${slug}`] },
  });
  if (!response.ok) return null;
  return (await response.json()) as Tenant;
}

/** Inline <style> that paints the tenant's brand color as CSS variables. */
export function brandStyleTag(brandColor: string): string {
  return `:root { --brand: ${hexToRgb(brandColor)}; }`;
}
