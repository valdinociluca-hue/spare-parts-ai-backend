import { cookies } from 'next/headers';

import { createServerClient } from '@supabase/ssr';

import { env } from '../env';

export function createSupabaseServerClient() {
  const cookieStore = cookies();
  return createServerClient(env.NEXT_PUBLIC_SUPABASE_URL, env.NEXT_PUBLIC_SUPABASE_ANON_KEY, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(items) {
        try {
          items.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options);
          });
        } catch {
          // Read-only server components cannot set cookies — middleware handles it.
        }
      },
    },
  });
}
