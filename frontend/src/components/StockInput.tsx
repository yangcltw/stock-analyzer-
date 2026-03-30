"use client";

import { useState } from "react";

interface StockInputProps {
  onSearch: (symbol: string) => void;
  loading: boolean;
  error: string | null;
}

export default function StockInput({ onSearch, loading, error }: StockInputProps) {
  const [symbol, setSymbol] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = symbol.trim();
    if (trimmed) {
      onSearch(trimmed);
    }
  };

  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="台股代號 (例: 2330)"
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm sm:text-base w-full sm:w-44 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !symbol.trim()}
          className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm sm:text-base font-medium hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
        >
          {loading ? "查詢中..." : "查詢"}
        </button>
      </form>
      {error && (
        <span className="text-red-500 text-xs sm:text-sm bg-red-50 px-2 py-1 rounded">
          {error}
        </span>
      )}
    </div>
  );
}
