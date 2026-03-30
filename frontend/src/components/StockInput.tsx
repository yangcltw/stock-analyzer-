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
    <form onSubmit={handleSubmit} className="flex gap-2 items-center">
      <input
        type="text"
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
        placeholder="輸入台股代號 (例: 2330)"
        className="border rounded px-3 py-2 text-lg w-48"
        disabled={loading}
      />
      <button
        type="submit"
        disabled={loading || !symbol.trim()}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? "查詢中..." : "查詢"}
      </button>
      {error && <span className="text-red-500 text-sm">{error}</span>}
    </form>
  );
}
