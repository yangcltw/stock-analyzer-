export interface StockDailyData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface StockResponse {
  symbol: string;
  name: string | null;
  data: StockDailyData[];
  ma5: (number | null)[];
  ma20: (number | null)[];
}
