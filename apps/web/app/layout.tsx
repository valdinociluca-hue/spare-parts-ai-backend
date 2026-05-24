import type { Metadata } from 'next';

import { brandStyleTag, getCurrentTenant } from '@/lib/tenant';

import './globals.css';

export const metadata: Metadata = {
  title: 'PartsAI',
  description: 'AI-powered spare-parts platform',
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const tenant = await getCurrentTenant();
  const lang = tenant?.language ?? 'en';
  return (
    <html lang={lang}>
      <head>
        {tenant ? (
          <style dangerouslySetInnerHTML={{ __html: brandStyleTag(tenant.brandColor) }} />
        ) : null}
      </head>
      <body>{children}</body>
    </html>
  );
}
