# file: strategy.py
import pandas as pd
import numpy as np
from indicators import calculate_indicators
from candlestick_patterns import detect_candle_pattern


def generate_signals(df, ema_short=15, ema_mid=25, ema_long=50, bb_std=2.0, vol_mult=1.3, use_candles=True):
    """
    Sinh tín hiệu giao dịch nâng cao dựa trên:
      - EMA15 / EMA25 / EMA50 (xu hướng chính)
      - Bollinger Bands (2σ)
      - RSI xác nhận sức mạnh
      - Stochastic RSI hoặc MACD làm bộ lọc phụ
      - Volume breakout
      - (Tùy chọn) Mô hình nến Pin Bar / Engulfing làm xác nhận mạnh
    """

    if df is None or df.empty:
        print("⚠️ Không có dữ liệu đầu vào để sinh tín hiệu.")
        return pd.DataFrame()

    df = calculate_indicators(df, ema_short, ema_mid, ema_long, bb_std)

    signals = []
    min_index = max(ema_long, 50)

    for i in range(min_index, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i - 1]

        # --- Giá & EMA ---
        close = row["close"]
        ema_s, ema_m, ema_l = row["EMA_SHORT"], row["EMA_MID"], row["EMA_LONG"]

        # --- Bollinger Bands ---
        upper_bb, lower_bb = row["BB_upper"], row["BB_lower"]

        # --- Volume breakout ---
        avg_vol = df["volume"].iloc[i - 20:i].mean()
        volume = row["volume"]
        strong_volume = volume > avg_vol * vol_mult

        # --- RSI & bộ lọc phụ ---
        rsi = row.get("RSI", np.nan)
        stoch_k = row.get("StochRSI_K", np.nan)
        stoch_d = row.get("StochRSI_D", np.nan)
        macd = row.get("MACD", np.nan)
        macd_signal = row.get("MACD_signal", np.nan)

        # --- Mô hình nến ---
        candle_ok = True
        if use_candles:
            candle_ok = detect_candle_pattern(df, row["time"])

        # ======================
        # 🔹 Điều kiện MUA (BUY)
        # ======================
        buy_cond = (
            ema_s > ema_m > ema_l and          # EMA xác nhận xu hướng tăng
            close > ema_s and close < upper_bb and
            strong_volume and
            rsi > 50
        )

        # Bộ lọc phụ BUY (Stoch RSI hoặc MACD)
        filter_buy = (
            (not np.isnan(stoch_k) and not np.isnan(stoch_d) and stoch_k > stoch_d and stoch_k < 80)
            or
            (not np.isnan(macd) and not np.isnan(macd_signal) and macd > macd_signal)
        )

        # ======================
        # 🔻 Điều kiện BÁN (SELL)
        # ======================
        sell_cond = (
            ema_s < ema_m < ema_l and          # EMA xác nhận xu hướng giảm
            close < ema_s and close > lower_bb and
            strong_volume and
            rsi < 50
        )

        # Bộ lọc phụ SELL (Stoch RSI hoặc MACD)
        filter_sell = (
            (not np.isnan(stoch_k) and not np.isnan(stoch_d) and stoch_k < stoch_d and stoch_k > 20)
            or
            (not np.isnan(macd) and not np.isnan(macd_signal) and macd < macd_signal)
        )

        # ======================
        # 🧩 Kết hợp tín hiệu
        # ======================
        if buy_cond and filter_buy and candle_ok:
            entry = close
            tp = entry * 1.03   # TP 3%
            sl = entry * 0.90   # SL 10%
            signals.append({
                "time": row["time"],
                "Signal": "BUY",
                "Entry": entry,
                "TP": tp,
                "SL": sl,
                "RSI": rsi,
                "Volume": volume,
                "Candle": candle_ok,
                "MACD": macd,
                "MACD_signal": macd_signal,
                "StochRSI_K": stoch_k,
                "StochRSI_D": stoch_d
            })

        elif sell_cond and filter_sell and candle_ok:
            entry = close
            tp = entry * 0.97   # TP 3%
            sl = entry * 1.1   # SL 10%
            signals.append({
                "time": row["time"],
                "Signal": "SELL",
                "Entry": entry,
                "TP": tp,
                "SL": sl,
                "RSI": rsi,
                "Volume": volume,
                "Candle": candle_ok,
                "MACD": macd,
                "MACD_signal": macd_signal,
                "StochRSI_K": stoch_k,
                "StochRSI_D": stoch_d
            })

    df_signals = pd.DataFrame(signals)
    if not df_signals.empty:
        print(f"✅ Đã sinh {len(df_signals)} tín hiệu (BUY/SELL).")
    else:
        print("⚠️ Không phát hiện tín hiệu đủ mạnh.")

    return df_signals


# =======================================================
# 🔍 PHÂN TÍCH TỔNG HỢP 1 COIN (cho main.py)
# =======================================================

def analyze_coin(symbol, df, interval):
    """
    Phân tích 1 coin cụ thể:
    - Tính toàn bộ chỉ báo kỹ thuật
    - Sinh tín hiệu mới nhất (BUY/SELL)
    - Trả về dict sẵn sàng gửi lên Discord
    """
    try:
        df = calculate_indicators(df)
        signals = generate_signals(df)

        if signals is None or signals.empty:
            return None

        last_signal = signals.iloc[-1]
        return {
            "symbol": symbol,
            "interval": interval,
            "type": last_signal["Signal"],
            "entry": last_signal["Entry"],
            "tp": last_signal["TP"],
            "sl": last_signal["SL"],
            "rsi": round(last_signal["RSI"], 2),
            "volume": round(last_signal["Volume"], 2),
            "macd": round(last_signal["MACD"], 4),
            "macd_signal": round(last_signal["MACD_signal"], 4),
            "stoch_k": round(last_signal["StochRSI_K"], 2),
            "stoch_d": round(last_signal["StochRSI_D"], 2),
            "time": str(last_signal["time"])
        }
    except Exception as e:
        print(f"❌ Lỗi analyze_coin({symbol}): {e}")
        return None
