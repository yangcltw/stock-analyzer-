"use client";

import { useState } from "react";
import StockInput from "@/components/StockInput";
import StockChart from "@/components/StockChart";
import AIAnalysis from "@/components/AIAnalysis";
import { fetchStock } from "@/services/stockApi";
import { StockResponse } from "@/types/stock";

export default function Home() {
  const [data, setData] = useState<StockResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (symbol: string) => {
    setLoading(true);
    setError(null);
    setData(null);

    try {
      const result = await fetchStock(symbol);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "查詢失敗");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">台股技術分析</h1>
      <StockInput onSearch={handleSearch} loading={loading} error={error} />
      {data && (
        <div className="mt-6">
          <h2 className="text-xl font-semibold mb-2">
            {data.name ? `${data.symbol} ${data.name}` : data.symbol} 近 30 個交易日
          </h2>
          <StockChart data={data} />
          <AIAnalysis analysis={data.ai_analysis} loading={loading} />
        </div>
      )}
    </main>
  );
}
