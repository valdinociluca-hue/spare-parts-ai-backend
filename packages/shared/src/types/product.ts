export interface Product {
  id: string;
  tenantId: string;
  sku: string;
  name: string | null;
  description: string | null;
  brand: string | null;
  category: string | null;
  compatibleModels: string[];
  qtyStock: number;
  priceBase: number | null;
  currency: string;
  embeddingId: string | null;
  metadata: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface ProductMatch {
  sku: string;
  name: string;
  score: number;
  stock: number;
  price: number | null;
  currency: string;
  imageUrl: string | null;
  reasoning: string;
}

export interface ErrorCode {
  id: string;
  tenantId: string;
  brand: string;
  modelPattern: string | null;
  errorCode: string;
  description: string | null;
  likelyParts: string[];
  severity: 'low' | 'medium' | 'high' | 'critical' | null;
  solution: string | null;
}
