import Link from 'next/link';

import { getCurrentTenant } from '@/lib/tenant';

export default async function HomePage() {
  const tenant = await getCurrentTenant();

  if (!tenant) {
    return (
      <main className="mx-auto max-w-2xl p-8">
        <h1 className="text-2xl font-semibold">PartsAI</h1>
        <p className="mt-2 text-slate-600">
          No tenant resolved for this hostname. Visit <code>lvtrade.partsai.com</code> or{' '}
          <code>equipart.partsai.com</code>, or set
          <code>NEXT_PUBLIC_DEFAULT_TENANT_SLUG</code> in development.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-2xl font-semibold text-brand">{tenant.name}</h1>
      <p className="mt-2 text-slate-600">
        Tenant: <code>{tenant.slug}</code> · Region: {tenant.region} · LLM: {tenant.llmProvider}
      </p>
      <nav className="mt-6 flex gap-4 text-sm">
        <Link className="underline" href="/login">Sign in</Link>
        <Link className="underline" href="/dashboard">Dashboard</Link>
      </nav>
    </main>
  );
}
