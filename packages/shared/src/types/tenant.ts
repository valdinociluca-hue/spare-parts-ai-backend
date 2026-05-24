export type Region = 'RU' | 'GLOBAL';
export type LlmProvider = 'yandex' | 'claude';
export type TenantPlan = 'starter' | 'pro' | 'enterprise';

export interface Tenant {
  id: string;
  slug: string;
  name: string;
  region: Region;
  llmProvider: LlmProvider;
  brandColor: string;
  logoUrl: string | null;
  language: string;
  widgetApiKey: string;
  plan: TenantPlan;
  createdAt: string;
}

export interface TenantUser {
  id: string;
  tenantId: string;
  email: string;
  role: 'admin' | 'viewer';
  createdAt: string;
}
