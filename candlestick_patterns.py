# file: candlestick_patterns.py
import pandas as pd

def detect_candle_pattern(df: pd.DataFrame, time):
    """
    Phát hiện các mô hình nến mạnh tại thời điểm 'time'.
    Bao gồm:
      - Pin Bar (đuôi dài)
      - Bullish/Bearish Engulfing
      - Doji (thân nhỏ)
      - Morning Star / Evening Star (3 nến đảo chiều)
    Trả về:
      { 'pattern': <tên mô hình>, 'direction': 'bullish'/'bearish'/'neutral' }
    """

    idx = df.index[df["time"] == time]
    if len(idx) == 0 or idx[0] < 2:
        return {'pattern': None, 'direction': 'neutral'}

    i = idx[0]
    o, h, l, c = df.loc[i, ["open", "high", "low", "close"]]
    prev_o, prev_c = df.loc[i - 1, ["open", "close"]]
    prev2_o, prev2_c = df.loc[i - 2, ["open", "close"]]

    body = abs(c - o)
    candle_len = h - l
    upper_shadow = h - max(o, c)
    lower_shadow = min(o, c) - l

    # --- 1️⃣ Pin Bar ---
    if body > 0 and (upper_shadow > 2 * body or lower_shadow > 2 * body):
        if lower_shadow > 2 * body and c > o:  # Đuôi dưới dài, thân tăng
            return {'pattern': 'Bullish Pin Bar', 'direction': 'bullish'}
        elif upper_shadow > 2 * body and c < o:  # Đuôi trên dài, thân giảm
            return {'pattern': 'Bearish Pin Bar', 'direction': 'bearish'}

    # --- 2️⃣ Bullish Engulfing ---
    if c > o and prev_c < prev_o and c > prev_o and o < prev_c:
        return {'pattern': 'Bullish Engulfing', 'direction': 'bullish'}

    # --- 3️⃣ Bearish Engulfing ---
    if c < o and prev_c > prev_o and o > prev_c and c < prev_o:
        return {'pattern': 'Bearish Engulfing', 'direction': 'bearish'}

    # --- 4️⃣ Doji ---
    if candle_len > 0 and (body / candle_len) < 0.1:
        return {'pattern': 'Doji', 'direction': 'neutral'}

    # --- 5️⃣ Morning Star (3 nến) ---
    if i >= 2:
        # n-2: giảm, n-1: thân nhỏ, n: tăng mạnh
        if prev2_c < prev2_o and abs(prev_c - prev_o) < abs(prev2_c - prev2_o) * 0.5 and c > o and c > ((prev2_o + prev2_c) / 2):
            return {'pattern': 'Morning Star', 'direction': 'bullish'}

        # --- 6️⃣ Evening Star (3 nến) ---
        # n-2: tăng, n-1: thân nhỏ, n: giảm mạnh
        if prev2_c > prev2_o and abs(prev_c - prev_o) < abs(prev2_c - prev2_o) * 0.5 and c < o and c < ((prev2_o + prev2_c) / 2):
            return {'pattern': 'Evening Star', 'direction': 'bearish'}

    # --- Không có mô hình rõ ---
    return {'pattern': None, 'direction': 'neutral'}


def detect_recent_patterns(df: pd.DataFrame, lookback: int = 5):
    """
    Quét mô hình nến trong vài cây gần nhất để phát hiện tín hiệu đảo chiều mạnh.
    Trả về list chứa các dict {time, pattern, direction}
    """
    patterns = []
    for i in range(max(2, len(df) - lookback), len(df)):
        time = df.iloc[i]['time']
        result = detect_candle_pattern(df, time)
        if result['pattern']:
            patterns.append({'time': time, **result})
    return patterns
