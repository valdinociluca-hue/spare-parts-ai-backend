export type ChatModule = 'parts_id' | 'technician' | 'order';
export type ChatRole = 'user' | 'assistant' | 'system';

export interface ChatSession {
  id: string;
  tenantId: string;
  sessionToken: string;
  clientId: string | null;
  module: ChatModule;
  createdAt: string;
  lastActivity: string;
}

export interface ChatMessage {
  id: string;
  sessionId: string;
  tenantId: string;
  role: ChatRole;
  content: string;
  skusMentioned: string[];
  module: ChatModule | null;
  tokensUsed: number | null;
  llmProvider: 'yandex' | 'claude' | null;
  createdAt: string;
}
