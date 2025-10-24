# backtest.py
import pandas as pd
import numpy as np
from datetime import timedelta, timezone
from multiprocessing import Pool, cpu_count
from typing import List, Dict, Optional

import config  # Import constants from config.py
from data_fetcher import get_historical_data
from strategy import generate_signals
import traceback
import random
import os

# Thiết lập múi giờ Việt Nam (nếu cần, nhưng hiện không dùng trực tiếp)
VIETNAM_TZ = timezone(timedelta(hours=7))

RESULT_FILE = "backtest_results.csv"
TRADES_FILE = "backtest_trades.csv"


def backtest_coin(args: tuple) -> List[Dict]:
    """Chạy backtest cho 1 đồng coin trên các khung thời gian."""
    symbol, intervals = args
    all_trades = []
    print(f"\n🔍 Bắt đầu backtest {symbol}")

    for interval in intervals:
        try:
            # === Lấy dữ liệu giá ===
            df = get_historical_data(symbol, interval, days=365)
            if df.empty:
                print(f"⚠️ Không có dữ liệu {symbol} ({interval})")
                continue

            # === Sinh tín hiệu giao dịch ===
            signals = generate_signals(df)
            if signals.empty:
                print(f"⚠️ Không có tín hiệu cho {symbol} ({interval})")
                continue

            # === Duyệt từng tín hiệu (vectorized hit check) ===
            for _, s in signals.iterrows():
                entry_price = s["Entry"]
                tp = s["TP"]
                sl = s["SL"]
                signal = s["Signal"]
                entry_time = s["time"]

                # Lấy dữ liệu tương lai sau thời điểm vào lệnh (giới hạn 50 nến)
                future_df = df[df["time"] > entry_time].head(50)
                if future_df.empty:
                    continue

                result = "NONE"
                profit = 0.0

                # Vectorized check for TP/SL hit
                if signal == "BUY":
                    hit_tp = future_df["high"] >= tp
                    hit_sl = future_df["low"] <= sl
                else:  # SELL
                    hit_tp = future_df["low"] <= tp
                    hit_sl = future_df["high"] >= sl

                first_hit_idx = np.inf
                if hit_tp.any():
                    first_hit_idx = hit_tp.idxmin()
                    result = "TP"
                #ưu tiên TP
                # if hit_sl.any():
                #     sl_idx = hit_sl.idxmin()
                #     if sl_idx < first_hit_idx:
                #         first_hit_idx = sl_idx
                #         result = "SL"

                # ưu tiên SL
                if hit_sl.any():
                    sl_idx = hit_sl.idxmin()
                    if sl_idx <= first_hit_idx:  # dùng <= thay vì <
                        first_hit_idx = sl_idx
                        result = "SL"

                if result != "NONE":
                    if signal == "BUY":
                        exit_price = tp if result == "TP" else sl
                        profit = (exit_price - entry_price) / entry_price
                    else:
                        exit_price = tp if result == "TP" else sl
                        profit = (entry_price - exit_price) / entry_price
                else:
                    continue  # Bỏ nếu không hit trong 50 nến

                all_trades.append({
                    "Symbol": symbol,
                    "Interval": interval,
                    "Signal": signal,
                    "Result": result,
                    "Profit": profit,
                    "Entry": entry_price,
                    "TP": tp,
                    "SL": sl,
                    "Time": entry_time
                })

        except Exception as e:
            print(f"❌ Lỗi backtest {symbol} ({interval}): {e}")
            traceback.print_exc()

    return all_trades


def run_backtest(sample_size: Optional[int] = None):
    """Chạy backtest toàn bộ danh sách coin trong COIN_LIST (đa luồng)."""
    all_trades = []
    intervals = config.INTERVALS  # ["15m", "30m", "1h"]
    intervals = ["30m"]
    # Sample nếu cần test nhanh
    coins = config.COIN_LIST
    if sample_size:
        coins = random.sample(coins, min(sample_size, len(coins)))

    print(f"\n🚀 Bắt đầu backtest cho {len(coins)} đồng coin...")

    coins = [
        "BTCUSDT",
        "ETHUSDT",
        "BNBUSDT",
        "XRPUSDT",
        "SOLUSDT",
        "TRXUSDT",
        "DOGEUSDT",
        "ADAUSDT",
        "HYPEUSDT",
        "LINKUSDT",
        "XLMUSDT",
        "BCHUSDT",
        "SUIUSDT",
        "AVAXUSDT",
        "LTCUSDT",
        "HBARUSDT",
        "XMRUSDT",
        "TAOUSDT",
        "TONUSDT",
        "DOTUSDT",
    ]

    coins = [
        "BTCUSDT",
        "ETHUSDT",
        "BNBUSDT",
        "XRPUSDT",
        "SOLUSDT",
        "SUIUSDT",
        "DOGEUSDT",
        "ADAUSDT",
        "HYPEUSDT",
        "LINKUSDT",
    ]

    # Đa luồng với multiprocessing
    num_processes = min(cpu_count(), config.MAX_THREADS)
    with Pool(processes=num_processes) as pool:
        args = [(coin, intervals) for coin in coins]
        results = pool.map(backtest_coin, args)
        for trades in results:
            all_trades.extend(trades)

    if not all_trades:
        print("❌ Không có dữ liệu backtest.")
        return

    # === Tổng hợp kết quả ===
    df = pd.DataFrame(all_trades)
    df["Profit %"] = df["Profit"] * 100

    total_trades = len(df)
    tp_trades = df[df["Result"] == "TP"]
    sl_trades = df[df["Result"] == "SL"]
    win_rate = len(tp_trades) / total_trades * 100 if total_trades > 0 else 0
    avg_profit = df["Profit"].mean() * 100
    total_profit = df["Profit"].sum() * 100

    summary = {
        "Tổng lệnh": total_trades,
        "TP": len(tp_trades),
        "SL": len(sl_trades),
        "NONE": len(df[df["Result"] == "NONE"]),
        "Tỷ lệ thắng (%)": round(win_rate, 2),
        "Lợi nhuận trung bình (%)": round(avg_profit, 2),
        "Tổng lợi nhuận (%)": round(total_profit, 2)
    }

    # === In kết quả ===
    print("\n📊 KẾT QUẢ BACKTEST TỔNG HỢP")
    for k, v in summary.items():
        print(f"{k}: {v}")

    # === Lưu file ===
    df.to_csv(TRADES_FILE, index=False)
    pd.DataFrame([summary]).to_csv(RESULT_FILE, index=False)

    print(f"\n✅ Đã lưu kết quả vào '{RESULT_FILE}' và '{TRADES_FILE}'.")


if __name__ == "__main__":
    run_backtest(sample_size=50)
    # run_backtest()  # Hoặc run_backtest(sample_size=50) để test nhanh