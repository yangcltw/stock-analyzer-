"use client";

import { useEffect, useRef } from "react";
import { createChart, IChartApi, LineSeries, CandlestickSeries } from "lightweight-charts";
import { StockResponse } from "@/types/stock";

interface StockChartProps {
  data: StockResponse;
}

export default function StockChart({ data }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: "#ffffff" },
        textColor: "#333",
      },
      grid: {
        vertLines: { color: "#e0e0e0" },
        horzLines: { color: "#e0e0e0" },
      },
      timeScale: {
        timeVisible: false,
        borderColor: "#ccc",
      },
    });
    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#ef5350",
      downColor: "#26a69a",
      wickUpColor: "#ef5350",
      wickDownColor: "#26a69a",
    });

    candleSeries.setData(
      data.data.map((d) => ({
        time: d.date,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    );

    const ma5Series = chart.addSeries(LineSeries, {
      color: "#2196F3",
      lineWidth: 2,
      title: "MA5",
    });

    ma5Series.setData(
      data.data
        .map((d, i) => ({
          time: d.date,
          value: data.ma5[i],
        }))
        .filter((p): p is { time: string; value: number } => p.value !== null)
    );

    const ma20Series = chart.addSeries(LineSeries, {
      color: "#FF9800",
      lineWidth: 2,
      title: "MA20",
    });

    ma20Series.setData(
      data.data
        .map((d, i) => ({
          time: d.date,
          value: data.ma20[i],
        }))
        .filter((p): p is { time: string; value: number } => p.value !== null)
    );

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data]);

  return <div ref={chartContainerRef} className="w-full" />;
}
