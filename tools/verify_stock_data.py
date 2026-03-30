#!/usr/bin/env python3
"""
台股資料驗證工具

資料源：TWSE 官方 API（證交所每日收盤行情）
功能：
  1. 從 TWSE 抓取指定股票最近 N 個交易日資料
  2. 獨立計算 MA5 / MA20
  3. 可選：與後端 API 回傳結果比對，輸出驗證報告

用法：
  python verify_stock_data.py 2330
  python verify_stock_data.py 2330 --compare http://localhost:8000/api/stock/2330
  python verify_stock_data.py 2330 --days 30 --json
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class DailyData:
    date: str       # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: int


# ---------------------------------------------------------------------------
# TWSE Data Fetcher
# ---------------------------------------------------------------------------

def _twse_date_to_iso(roc_date: str) -> str:
    """民國日期 '115/03/02' -> ISO '2026-03-02'"""
    parts = roc_date.strip().split("/")
    year = int(parts[0]) + 1911
    return f"{year}-{parts[1]}-{parts[2]}"


def _parse_number(s: str) -> float:
    """移除逗號後轉數字: '1,940.00' -> 1940.0, '--' -> 0.0"""
    cleaned = s.replace(",", "").strip()
    if cleaned in ("--", "-", ""):
        return 0.0
    return float(cleaned)


def _parse_volume(s: str) -> int:
    return int(s.replace(",", "").strip())


def fetch_twse_month(symbol: str, year: int, month: int) -> list[DailyData]:
    """從 TWSE 抓取指定月份的日成交資訊"""
    roc_year = year - 1911
    date_str = f"{year}{month:02d}01"
    url = (
        f"https://www.twse.com.tw/exchangeReport/STOCK_DAY"
        f"?response=json&date={date_str}&stockNo={symbol}"
    )

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  [WARN] TWSE HTTP {e.code} for {year}/{month:02d}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [WARN] TWSE request failed for {year}/{month:02d}: {e}", file=sys.stderr)
        return []

    if body.get("stat") != "OK" or "data" not in body:
        return []

    results = []
    for row in body["data"]:
        # fields: 日期, 成交股數, 成交金額, 開盤價, 最高價, 最低價, 收盤價, 漲跌價差, 成交筆數
        try:
            results.append(DailyData(
                date=_twse_date_to_iso(row[0]),
                open=_parse_number(row[3]),
                high=_parse_number(row[4]),
                low=_parse_number(row[5]),
                close=_parse_number(row[6]),
                volume=_parse_volume(row[1]),
            ))
        except (ValueError, IndexError) as e:
            print(f"  [WARN] Skip row {row[0]}: {e}", file=sys.stderr)
            continue

    return results


def fetch_twse_data(symbol: str, trading_days: int = 49) -> list[DailyData]:
    """
    從 TWSE 抓取足夠的交易日資料。
    往回抓取多個月份，直到累積足夠天數。
    """
    all_data: list[DailyData] = []
    now = datetime.now()
    year, month = now.year, now.month

    # 最多往回抓 6 個月（應足夠 49 個交易日）
    for _ in range(6):
        print(f"  抓取 TWSE {symbol} {year}/{month:02d} ...", file=sys.stderr)
        month_data = fetch_twse_month(symbol, year, month)
        all_data = month_data + all_data  # 舊月份放前面
        time.sleep(0.5)  # 避免被 TWSE 限流

        if len(all_data) >= trading_days:
            break

        month -= 1
        if month < 1:
            month = 12
            year -= 1

    # 按日期排序，取最近 N 天
    all_data.sort(key=lambda d: d.date)
    return all_data[-trading_days:]


# ---------------------------------------------------------------------------
# MA Calculation
# ---------------------------------------------------------------------------

def calculate_ma(prices: list[float], period: int) -> list[Optional[float]]:
    """計算簡單移動平均線，資料不足的位置回傳 None"""
    result: list[Optional[float]] = []
    for i in range(len(prices)):
        if i < period - 1:
            result.append(None)
        else:
            window = prices[i - period + 1 : i + 1]
            result.append(round(sum(window) / period, 2))
    return result


# ---------------------------------------------------------------------------
# Comparison with Backend API
# ---------------------------------------------------------------------------

def fetch_backend(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def compare_data(
    twse_data: list[DailyData],
    twse_ma5: list[Optional[float]],
    twse_ma20: list[Optional[float]],
    backend: dict,
    tolerance: float = 0.5,
) -> list[str]:
    """比對 TWSE 驗證資料與後端 API 回傳值，回傳差異列表"""
    issues: list[str] = []

    backend_data = backend.get("data", [])
    backend_ma5 = backend.get("ma5", [])
    backend_ma20 = backend.get("ma20", [])

    # 建立 TWSE 資料的 date -> index 對照
    twse_by_date = {d.date: (i, d) for i, d in enumerate(twse_data)}

    matched = 0
    for bi, bd in enumerate(backend_data):
        date = bd.get("date", "")
        if date not in twse_by_date:
            issues.append(f"[MISSING] 後端日期 {date} 不在 TWSE 資料中")
            continue

        ti, td = twse_by_date[date]
        matched += 1

        # 比對 OHLCV
        for field in ["open", "high", "low", "close"]:
            tv = getattr(td, field)
            bv = bd.get(field, 0)
            if abs(tv - bv) > tolerance:
                issues.append(
                    f"[DIFF] {date} {field}: TWSE={tv} vs Backend={bv} (差={abs(tv-bv):.2f})"
                )

        tv_vol = td.volume
        bv_vol = bd.get("volume", 0)
        if tv_vol != bv_vol and abs(tv_vol - bv_vol) / max(tv_vol, 1) > 0.01:
            issues.append(
                f"[DIFF] {date} volume: TWSE={tv_vol} vs Backend={bv_vol}"
            )

        # 比對 MA
        if bi < len(backend_ma5) and ti < len(twse_ma5):
            bma5 = backend_ma5[bi]
            tma5 = twse_ma5[ti]
            if bma5 is not None and tma5 is not None and abs(bma5 - tma5) > tolerance:
                issues.append(
                    f"[DIFF] {date} MA5: TWSE={tma5} vs Backend={bma5} (差={abs(bma5-tma5):.2f})"
                )

        if bi < len(backend_ma20) and ti < len(twse_ma20):
            bma20 = backend_ma20[bi]
            tma20 = twse_ma20[ti]
            if bma20 is not None and tma20 is not None and abs(bma20 - tma20) > tolerance:
                issues.append(
                    f"[DIFF] {date} MA20: TWSE={tma20} vs Backend={bma20} (差={abs(bma20-tma20):.2f})"
                )

    if matched == 0 and len(backend_data) > 0:
        issues.append("[ERROR] 沒有任何日期匹配，可能日期格式不同")

    return issues


# ---------------------------------------------------------------------------
# Report Output
# ---------------------------------------------------------------------------

def print_report(
    symbol: str,
    data: list[DailyData],
    ma5: list[Optional[float]],
    ma20: list[Optional[float]],
    display_days: int = 30,
    output_json: bool = False,
):
    """輸出驗證資料報告"""
    # 取最後 display_days 天
    start = max(0, len(data) - display_days)
    show_data = data[start:]
    show_ma5 = ma5[start:]
    show_ma20 = ma20[start:]

    if output_json:
        result = {
            "symbol": symbol,
            "source": "TWSE",
            "fetched_at": datetime.now().isoformat(),
            "trading_days": len(show_data),
            "data": [asdict(d) for d in show_data],
            "ma5": show_ma5,
            "ma20": show_ma20,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"\n{'='*80}")
    print(f"  台股資料驗證報告 — {symbol}")
    print(f"  資料來源：TWSE 證交所官方 API")
    print(f"  抓取時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  交易日數：{len(show_data)} 天")
    print(f"{'='*80}\n")

    # 表頭
    header = f"{'日期':>12} {'開盤':>10} {'最高':>10} {'最低':>10} {'收盤':>10} {'成交量':>14} {'MA5':>10} {'MA20':>10}"
    print(header)
    print("-" * len(header))

    for i, d in enumerate(show_data):
        m5 = f"{show_ma5[i]:.2f}" if show_ma5[i] is not None else "---"
        m20 = f"{show_ma20[i]:.2f}" if show_ma20[i] is not None else "---"
        print(
            f"{d.date:>12} {d.open:>10.2f} {d.high:>10.2f} {d.low:>10.2f} "
            f"{d.close:>10.2f} {d.volume:>14,} {m5:>10} {m20:>10}"
        )

    # 摘要
    closes = [d.close for d in show_data]
    print(f"\n--- 摘要 ---")
    print(f"  期間：{show_data[0].date} ~ {show_data[-1].date}")
    print(f"  最高收盤：{max(closes):.2f}")
    print(f"  最低收盤：{min(closes):.2f}")
    print(f"  期間漲跌：{closes[-1] - closes[0]:+.2f} ({(closes[-1]/closes[0]-1)*100:+.2f}%)")

    if show_ma5[-1] is not None and show_ma20[-1] is not None:
        last_ma5 = show_ma5[-1]
        last_ma20 = show_ma20[-1]
        print(f"  最新 MA5：{last_ma5:.2f}")
        print(f"  最新 MA20：{last_ma20:.2f}")
        if last_ma5 > last_ma20:
            print(f"  MA5 > MA20（短期均線在上，偏多排列）")
        else:
            print(f"  MA5 < MA20（短期均線在下，偏空排列）")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="台股資料驗證工具（TWSE 官方資料源）")
    parser.add_argument("symbol", help="股票代號，例如 2330")
    parser.add_argument("--days", type=int, default=30, help="顯示天數（預設 30）")
    parser.add_argument("--compare", help="後端 API URL，用於比對驗證")
    parser.add_argument("--json", action="store_true", help="輸出 JSON 格式")
    parser.add_argument("--tolerance", type=float, default=0.5, help="比對容許誤差（預設 0.5）")
    args = parser.parse_args()

    # 抓取 TWSE 資料（多抓 19 天確保 MA20 從第一天就有值）
    fetch_days = args.days + 19
    print(f"\n抓取 TWSE 資料中（{args.symbol}，需要 {fetch_days} 個交易日）...", file=sys.stderr)

    data = fetch_twse_data(args.symbol, trading_days=fetch_days)
    if len(data) < 20:
        print(f"[ERROR] 資料不足：僅取得 {len(data)} 天，至少需要 20 天", file=sys.stderr)
        sys.exit(1)

    print(f"  共取得 {len(data)} 個交易日資料\n", file=sys.stderr)

    # 計算 MA
    closes = [d.close for d in data]
    ma5 = calculate_ma(closes, 5)
    ma20 = calculate_ma(closes, 20)

    # 輸出報告
    print_report(args.symbol, data, ma5, ma20, display_days=args.days, output_json=args.json)

    # 比對後端 API
    if args.compare:
        print(f"\n比對後端 API: {args.compare}", file=sys.stderr)
        try:
            backend = fetch_backend(args.compare)
            issues = compare_data(data, ma5, ma20, backend, tolerance=args.tolerance)
            if issues:
                print(f"\n{'='*80}")
                print(f"  比對結果：發現 {len(issues)} 個差異")
                print(f"{'='*80}")
                for issue in issues:
                    print(f"  {issue}")
            else:
                print(f"\n  ✓ 比對通過：TWSE 資料與後端 API 完全一致")
        except Exception as e:
            print(f"\n  [ERROR] 無法連線後端 API: {e}", file=sys.stderr)

    print()


if __name__ == "__main__":
    main()
