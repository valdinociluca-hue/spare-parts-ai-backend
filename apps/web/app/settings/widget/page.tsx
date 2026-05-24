import { getCurrentTenant } from '@/lib/tenant';

export default async function WidgetSettingsPage() {
  const tenant = await getCurrentTenant();
  if (!tenant) {
    return <main className="p-8">No tenant resolved.</main>;
  }
  const snippet =
    `<script\n` +
    `  src="https://widget.partsai.com/widget.js"\n` +
    `  data-key="${tenant.widgetApiKey}"\n` +
    `  data-module="parts_id"\n` +
    `  data-language="${tenant.language}">\n` +
    `</script>`;
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">Widget embed</h1>
      <p className="mt-2 text-slate-600">
        Paste this on any page of your site (right before <code>&lt;/body&gt;</code>):
      </p>
      <pre className="mt-4 overflow-x-auto rounded-lg bg-slate-900 p-4 text-sm text-slate-100">
        <code>{snippet}</code>
      </pre>
    </main>
  );
}
