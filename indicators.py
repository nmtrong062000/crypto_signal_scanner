# file: indicators.py
import pandas as pd
import numpy as np


def calculate_indicators(df, ema_short=15, ema_mid=25, ema_long=50, bb_std=2.0):
    """
    Tính toán toàn bộ chỉ báo kỹ thuật cần cho chiến lược:
    EMA15 / EMA25 / EMA50, Bollinger Bands, RSI, StochRSI, MACD, Volume trend.
    Trả về DataFrame gốc + các cột chỉ báo.
    """

    if df is None or df.empty:
        raise ValueError("❌ DataFrame rỗng — không thể tính chỉ báo.")

    df = df.copy().reset_index(drop=True)

    # --- EMA ---
    df["EMA_SHORT"] = df["close"].ewm(span=ema_short, adjust=False).mean()
    df["EMA_MID"] = df["close"].ewm(span=ema_mid, adjust=False).mean()
    df["EMA_LONG"] = df["close"].ewm(span=ema_long, adjust=False).mean()

    # --- Bollinger Bands ---
    window = 20
    df["BB_MA"] = df["close"].rolling(window=window).mean()
    df["BB_STD"] = df["close"].rolling(window=window).std()
    df["BB_upper"] = df["BB_MA"] + bb_std * df["BB_STD"]
    df["BB_lower"] = df["BB_MA"] - bb_std * df["BB_STD"]

    # --- RSI ---
    delta = df["close"].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    roll_up = pd.Series(gain).rolling(window=14).mean()
    roll_down = pd.Series(loss).rolling(window=14).mean()

    rs = roll_up / (roll_down + 1e-10)
    df["RSI"] = 100 - (100 / (1 + rs))

    # --- Stochastic RSI ---
    rsi_min = df["RSI"].rolling(window=14).min()
    rsi_max = df["RSI"].rolling(window=14).max()
    df["StochRSI"] = (df["RSI"] - rsi_min) / (rsi_max - rsi_min + 1e-10)
    df["StochRSI_K"] = df["StochRSI"].rolling(window=3).mean() * 100
    df["StochRSI_D"] = df["StochRSI_K"].rolling(window=3).mean()

    # --- MACD ---
    ema_fast = df["close"].ewm(span=12, adjust=False).mean()
    ema_slow = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    # --- Volume trend (OBV-like) ---
    df["VOL_trend"] = np.where(df["close"].diff() > 0, df["volume"], -df["volume"])
    df["VOL_trend"] = df["VOL_trend"].cumsum()

    # --- Làm sạch NaN đầu chuỗi ---
    df = df.dropna().reset_index(drop=True)

    return df


def detect_cross(df, short_col, long_col):
    """
    Phát hiện giao cắt giữa hai đường (ví dụ EMA15 cắt EMA25).
    Trả về 1 nếu cross up, -1 nếu cross down, 0 nếu không có tín hiệu.
    """
    if df is None or len(df) < 2:
        return 0

    prev_short = df[short_col].iloc[-2]
    prev_long = df[long_col].iloc[-2]
    curr_short = df[short_col].iloc[-1]
    curr_long = df[long_col].iloc[-1]

    if prev_short < prev_long and curr_short > curr_long:
        return 1  # Cross up
    elif prev_short > prev_long and curr_short < curr_long:
        return -1  # Cross down
    return 0


def get_latest_indicators(df):
    """
    Trả về dict chứa các chỉ báo gần nhất (hỗ trợ main.py hoặc alert.py).
    """
    if df is None or df.empty:
        return {}

    last = df.iloc[-1]
    return {
        "time": str(last["time"]),
        "close": float(last["close"]),
        "EMA_SHORT": float(last["EMA_SHORT"]),
        "EMA_MID": float(last["EMA_MID"]),
        "EMA_LONG": float(last["EMA_LONG"]),
        "BB_upper": float(last["BB_upper"]),
        "BB_lower": float(last["BB_lower"]),
        "RSI": float(last["RSI"]),
        "StochRSI_K": float(last["StochRSI_K"]),
        "StochRSI_D": float(last["StochRSI_D"]),
        "MACD": float(last["MACD"]),
        "MACD_signal": float(last["MACD_signal"]),
        "MACD_hist": float(last["MACD_hist"]),
        "Volume": float(last["volume"]),
    }
