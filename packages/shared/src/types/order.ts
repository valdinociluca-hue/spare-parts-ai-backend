export interface OrderItem {
  sku: string;
  qty: number;
  price: number;
}

export type OrderStatus = 'draft' | 'submitted' | 'confirmed';

export interface Order {
  id: string;
  tenantId: string;
  sessionId: string | null;
  clientId: string | null;
  items: OrderItem[];
  total: number | null;
  status: OrderStatus;
  createdAt: string;
}
