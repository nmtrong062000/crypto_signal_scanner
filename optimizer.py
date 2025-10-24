# file: optimizer.py
import itertools
import json
import pandas as pd
import os
import traceback
from data_fetcher import get_historical_data
from strategy import generate_signals
from config import COIN_LIST, EMA_SHORT, EMA_MID, EMA_LONG, BB_STD, VOL_MULT
import numpy as np

# ============================
# 🎯 ĐÁNH GIÁ CHIẾN LƯỢC
# ============================

def evaluate_strategy(df, ema_s, ema_m, ema_l, bb_std, vol_mult):
    """
    Đánh giá chiến lược với bộ tham số.
    Trả về: (winrate %, lợi nhuận trung bình %)
    """
    try:
        if df is None or df.empty:
            return 0, 0

        signals = generate_signals(df, ema_s, ema_m, ema_l, bb_std, vol_mult)
        if signals is None or signals.empty:
            return 0, 0

        total, wins, profit_sum = 0, 0, 0

        for _, s in signals.iterrows():
            entry, tp, sl, signal = s.get("Entry"), s.get("TP"), s.get("SL"), s.get("Signal")
            entry_time = s.get("time")

            if pd.isna(entry) or pd.isna(tp) or pd.isna(sl):
                continue

            after = df[df["time"] > entry_time].head(30)
            if after.empty:
                continue

            result = None
            profit = 0

            for _, r in after.iterrows():
                if signal == "BUY":
                    if r["high"] >= tp:
                        result, profit = "TP", (tp - entry) / entry
                        break
                    elif r["low"] <= sl:
                        result, profit = "SL", (sl - entry) / entry
                        break
                elif signal == "SELL":
                    if r["low"] <= tp:
                        result, profit = "TP", (entry - tp) / entry
                        break
                    elif r["high"] >= sl:
                        result, profit = "SL", (entry - sl) / entry
                        break

            if result:
                total += 1
                profit_sum += profit
                if result == "TP":
                    wins += 1

        if total == 0:
            return 0, 0

        winrate = wins / total * 100
        avg_profit = profit_sum / total * 100
        return winrate, avg_profit

    except Exception as e:
        print(f"❌ Lỗi evaluate_strategy: {e}")
        traceback.print_exc()
        return 0, 0


# ============================
# 🔍 TỐI ƯU THAM SỐ CHIẾN LƯỢC
# ============================

def optimize_params():
    """
    Thử nhiều bộ tham số khác nhau để tìm ra cấu hình có Winrate & lợi nhuận tốt nhất.
    """
    rangeNum = 3
    rangeNumFloat = 0.3
    stepFloat = 0.1

    ema_short_list = list(range(max(1, EMA_SHORT - rangeNum), EMA_SHORT + rangeNum + 1))
    ema_mid_list = list(range(max(1, EMA_MID - rangeNum), EMA_MID + rangeNum + 1))
    ema_long_list = list(range(max(1, EMA_LONG - rangeNum), EMA_LONG + rangeNum + 1))
    bb_std_list = [round(x, 2) for x in np.arange(BB_STD - rangeNumFloat, BB_STD + rangeNumFloat + stepFloat, stepFloat)]
    vol_mult_list = [round(x, 2) for x in np.arange(VOL_MULT - 0.4, VOL_MULT + 0.4 + 0.1, 0.1)]

    best = {
        "ema_short": None,
        "ema_mid": None,
        "ema_long": None,
        "bb_std": None,
        "vol_mult": None,
        "win_rate": 0,
        "avg_profit": 0
    }

    total_combos = len(ema_short_list) * len(ema_mid_list) * len(ema_long_list) * len(bb_std_list) * len(vol_mult_list)
    print(f"🚀 Bắt đầu tối ưu ({total_combos} tổ hợp)...")

    combos = itertools.product(ema_short_list, ema_mid_list, ema_long_list, bb_std_list, vol_mult_list)

    for i, (ema_s, ema_m, ema_l, bb_std, vol_mult) in enumerate(combos, 1):
        print(f"\n🧩 [{i}/{total_combos}] Testing: EMA({ema_s},{ema_m},{ema_l}), BB={bb_std}, VOL={vol_mult}")
        all_wr, all_profit = [], []

        coins = [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
        ]
        # Dùng 3 coin đầu tiên để giảm thời gian tối ưu
        # for coin in COIN_LIST[:3]:
        for coin in coins:
            try:
                df = get_historical_data(coin, "30m", days=180)
                if df is None or df.empty:
                    continue

                wr, prof = evaluate_strategy(df, ema_s, ema_m, ema_l, bb_std, vol_mult)
                if wr > 0:
                    all_wr.append(wr)
                    all_profit.append(prof)
            except Exception as e:
                print(f"⚠️ Lỗi xử lý {coin}: {e}")

        if not all_wr:
            continue

        avg_wr = np.mean(all_wr)
        avg_prof = np.mean(all_profit)

        print(f"   → ✅ Winrate: {avg_wr:.2f}%, Avg Profit: {avg_prof:.2f}%")

        # Ưu tiên Winrate cao, sau đó đến lợi nhuận
        if (avg_wr > best["win_rate"]) or (avg_wr == best["win_rate"] and avg_prof > best["avg_profit"]):
            best.update({
                "ema_short": ema_s,
                "ema_mid": ema_m,
                "ema_long": ema_l,
                "bb_std": bb_std,
                "vol_mult": vol_mult,
                "win_rate": avg_wr,
                "avg_profit": avg_prof
            })

    # Lưu kết quả tối ưu
    os.makedirs("results", exist_ok=True)
    best_path = os.path.join("results", "best_config.json")
    with open(best_path, "w", encoding="utf-8") as f:
        json.dump(best, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Cấu hình tốt nhất: {best}")
    print(f"📁 Đã lưu vào {best_path}")

    update_config(best)


# ============================
# 🧠 CẬP NHẬT CONFIG.PY
# ============================

def update_config(best):
    """Cập nhật config.py với các giá trị tối ưu."""
    try:
        lines = []
        with open("config.py", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("EMA_SHORT"):
                    line = f"EMA_SHORT = {best['ema_short']}\n"
                elif line.startswith("EMA_MID"):
                    line = f"EMA_MID = {best['ema_mid']}\n"
                elif line.startswith("EMA_LONG"):
                    line = f"EMA_LONG = {best['ema_long']}\n"
                elif line.startswith("BB_STD"):
                    line = f"BB_STD = {best['bb_std']}\n"
                elif line.startswith("VOL_MULT"):
                    line = f"VOL_MULT = {best['vol_mult']}\n"
                lines.append(line)

        with open("config.py", "w", encoding="utf-8") as f:
            f.writelines(lines)

        print("🧠 Đã cập nhật config.py với thông số tối ưu!")

    except Exception as e:
        print(f"❌ Lỗi khi cập nhật config.py: {e}")


if __name__ == "__main__":
    optimize_params()
