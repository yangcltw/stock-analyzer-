"use client";

import { useState, useRef, useCallback } from "react";
import StockInput from "@/components/StockInput";
import StockChart from "@/components/StockChart";
import AIAnalysis from "@/components/AIAnalysis";
import { fetchStock, streamAIAnalysis } from "@/services/stockApi";
import { StockResponse } from "@/types/stock";

export default function Home() {
  const [data, setData] = useState<StockResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // AI streaming state
  const [aiText, setAiText] = useState("");
  const [aiStreaming, setAiStreaming] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const sseRef = useRef<AbortController | null>(null);

  const cleanupSSE = useCallback(() => {
    if (sseRef.current) {
      sseRef.current.abort();
      sseRef.current = null;
    }
  }, []);

  const handleSearch = async (symbol: string) => {
    // Cleanup previous SSE connection
    cleanupSSE();

    setLoading(true);
    setError(null);
    setData(null);
    setAiText("");
    setAiStreaming(false);
    setAiError(null);

    try {
      // Step 1: Fetch data (fast — chart renders immediately)
      const result = await fetchStock(symbol);
      setData(result);
      setLoading(false);

      // Step 2: Start AI streaming (non-blocking)
      setAiStreaming(true);
      const controller = streamAIAnalysis(
        symbol,
        (token) => setAiText((prev) => prev + token),
        (_fullText) => setAiStreaming(false),
        (message) => {
          setAiError(message);
          setAiStreaming(false);
        },
      );
      sseRef.current = controller;
    } catch (e) {
      setError(e instanceof Error ? e.message : "查詢失敗");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="w-full px-4 sm:px-6 lg:px-8 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 shrink-0">
            台股技術分析
          </h1>
          <StockInput onSearch={handleSearch} loading={loading} error={error} />
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 w-full">
        {!data && !loading && (
          <div className="flex items-center justify-center h-[calc(100vh-80px)]">
            <div className="text-center text-gray-400">
              <svg className="mx-auto h-16 w-16 sm:h-24 sm:w-24 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
              </svg>
              <p className="text-lg sm:text-xl">輸入台股代號開始分析</p>
              <p className="text-sm mt-1">例如：2330（台積電）、2317（鴻海）</p>
            </div>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center h-[calc(100vh-80px)]">
            <div className="text-center">
              <div className="inline-block h-10 w-10 animate-spin rounded-full border-4 border-blue-600 border-r-transparent" />
              <p className="mt-4 text-gray-500">載入中...</p>
            </div>
          </div>
        )}

        {data && (
          <div className="w-full px-4 sm:px-6 lg:px-8 py-4 space-y-4">
            {/* Stock Info Bar */}
            <div className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-4">
              <h2 className="text-lg sm:text-2xl font-bold text-gray-900">
                {data.symbol}
                {data.name && (
                  <span className="ml-2 text-base sm:text-lg font-normal text-gray-500">
                    {data.name}
                  </span>
                )}
              </h2>
              <div className="flex items-baseline gap-3 text-sm text-gray-500">
                <span>
                  收盤 <span className="text-lg font-semibold text-gray-900">{data.data[data.data.length - 1].close}</span>
                </span>
                <span>MA5 <span className="font-medium text-blue-600">{data.ma5[data.ma5.length - 1]}</span></span>
                <span>MA20 <span className="font-medium text-orange-500">{data.ma20[data.ma20.length - 1]}</span></span>
              </div>
            </div>

            {/* Chart — full width */}
            <div className="bg-white rounded-lg border border-gray-200 p-2 sm:p-4">
              <StockChart data={data} />
            </div>

            {/* AI Analysis — streaming */}
            <AIAnalysis text={aiText} streaming={aiStreaming} error={aiError} />

            {/* Data Table — collapsible on mobile */}
            <details className="bg-white rounded-lg border border-gray-200">
              <summary className="px-4 py-3 cursor-pointer text-sm font-medium text-gray-700 hover:bg-gray-50">
                近 30 個交易日明細
              </summary>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-gray-600">
                    <tr>
                      <th className="px-3 py-2 text-left">日期</th>
                      <th className="px-3 py-2 text-right">開盤</th>
                      <th className="px-3 py-2 text-right">最高</th>
                      <th className="px-3 py-2 text-right">最低</th>
                      <th className="px-3 py-2 text-right">收盤</th>
                      <th className="px-3 py-2 text-right text-blue-600">MA5</th>
                      <th className="px-3 py-2 text-right text-orange-500">MA20</th>
                      <th className="px-3 py-2 text-right hidden sm:table-cell">成交量</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.data.slice().reverse().map((d, i) => {
                      const revIndex = data.data.length - 1 - i;
                      const prev = data.data.slice().reverse()[i + 1];
                      const isUp = prev ? d.close >= prev.close : true;
                      const ma5Val = data.ma5[revIndex];
                      const ma20Val = data.ma20[revIndex];
                      return (
                        <tr key={d.date} className="hover:bg-gray-50">
                          <td className="px-3 py-1.5 text-gray-600 whitespace-nowrap">{d.date}</td>
                          <td className="px-3 py-1.5 text-right">{d.open}</td>
                          <td className="px-3 py-1.5 text-right">{d.high}</td>
                          <td className="px-3 py-1.5 text-right">{d.low}</td>
                          <td className={`px-3 py-1.5 text-right font-medium ${isUp ? "text-red-600" : "text-green-600"}`}>
                            {d.close}
                          </td>
                          <td className="px-3 py-1.5 text-right text-blue-600">{ma5Val ?? "-"}</td>
                          <td className="px-3 py-1.5 text-right text-orange-500">{ma20Val ?? "-"}</td>
                          <td className="px-3 py-1.5 text-right text-gray-500 hidden sm:table-cell">
                            {d.volume.toLocaleString()}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </details>
          </div>
        )}
      </main>
    </div>
  );
}
