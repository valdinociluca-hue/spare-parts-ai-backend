function required(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

export const env = {
  NEXT_PUBLIC_API_URL:
    process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000',
  NEXT_PUBLIC_APP_DOMAIN:
    process.env.NEXT_PUBLIC_APP_DOMAIN ?? 'partsai.local',
  NEXT_PUBLIC_DEFAULT_TENANT_SLUG:
    process.env.NEXT_PUBLIC_DEFAULT_TENANT_SLUG ?? 'lvtrade',
  NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL ?? '',
  NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '',
  SUPABASE_SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY ?? '',
};

export function requireServerEnv(name: keyof typeof env): string {
  return required(name, env[name]);
}
