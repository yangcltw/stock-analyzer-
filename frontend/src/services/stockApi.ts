import { StockResponse } from "@/types/stock";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchStock(symbol: string): Promise<StockResponse> {
  const res = await fetch(`${API_URL}/api/stock/${symbol}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
