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

    const container = chartContainerRef.current;
    const isMobile = container.clientWidth < 640;

    const chart = createChart(container, {
      width: container.clientWidth,
      height: isMobile ? 300 : 500,
      layout: {
        background: { color: "#ffffff" },
        textColor: "#333",
        fontSize: isMobile ? 10 : 12,
      },
      grid: {
        vertLines: { color: "#f0f0f0" },
        horzLines: { color: "#f0f0f0" },
      },
      timeScale: {
        timeVisible: false,
        borderColor: "#e0e0e0",
        fixLeftEdge: true,
        fixRightEdge: true,
      },
      rightPriceScale: {
        borderColor: "#e0e0e0",
      },
      crosshair: {
        vertLine: { labelVisible: true },
        horzLine: { labelVisible: true },
      },
    });
    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#ef5350",
      downColor: "#26a69a",
      borderUpColor: "#ef5350",
      borderDownColor: "#26a69a",
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
      crosshairMarkerVisible: false,
      priceLineVisible: false,
      lastValueVisible: false,
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
      crosshairMarkerVisible: false,
      priceLineVisible: false,
      lastValueVisible: false,
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
        const w = chartContainerRef.current.clientWidth;
        const h = w < 640 ? 300 : 500;
        chart.applyOptions({ width: w, height: h });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data]);

  return (
    <div className="relative">
      <div ref={chartContainerRef} className="w-full" />
      {/* Legend */}
      <div className="flex gap-4 mt-2 text-xs sm:text-sm text-gray-500 px-1">
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-0.5 bg-blue-500" /> MA5
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-0.5 bg-orange-500" /> MA20
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 bg-red-500 rounded-sm" /> 上漲
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 bg-teal-500 rounded-sm" /> 下跌
        </span>
      </div>
    </div>
  );
}
