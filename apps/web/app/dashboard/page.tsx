import { getCurrentTenant } from '@/lib/tenant';

export default async function DashboardPage() {
  const tenant = await getCurrentTenant();
  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      {tenant ? (
        <p className="mt-2 text-slate-600">
          Welcome, {tenant.name}. Metrics wire in Week 3 step 13.
        </p>
      ) : (
        <p className="mt-2 text-red-600">No tenant resolved.</p>
      )}
    </main>
  );
}
