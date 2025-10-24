# file: signal_stats.py
import pandas as pd
import numpy as np

def calculate_signal_stats(df: pd.DataFrame):
    """
    Tính toán hiệu suất các tín hiệu giao dịch.
    Đầu vào: DataFrame chứa các cột ['time', 'Signal', 'Entry', 'TP', 'SL', 'close', 'high', 'low']
    """

    if df is None or df.empty:
        print("⚠️ Không có tín hiệu để thống kê.")
        return {
            'total_signals': 0,
            'winrate': 0,
            'avg_profit': 0,
            'total_profit': 0,
            'details': pd.DataFrame()
        }

    required_cols = {'time', 'Signal', 'Entry', 'TP', 'SL', 'close'}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"❌ Thiếu các cột bắt buộc: {missing_cols}")

    df = df.copy().reset_index(drop=True)
    results = []

    for i, row in df.iterrows():
        signal = row['Signal']
        entry = row['Entry']
        tp = row['TP']
        sl = row['SL']

        # Nếu không có giá high/low, dùng close thay thế
        if i + 1 < len(df):
            next_candle = df.iloc[i + 1]
            high = next_candle.get('high', row['close'])
            low = next_candle.get('low', row['close'])
            close = next_candle.get('close', row['close'])
        else:
            high = low = close = row['close']

        # --- Xử lý BUY ---
        if signal.upper() == 'BUY':
            if high >= tp:
                result = "TP"
                profit = (tp - entry) / entry
            elif low <= sl:
                result = "SL"
                profit = (sl - entry) / entry
            else:
                result = "CLOSE"
                profit = (close - entry) / entry

        # --- Xử lý SELL ---
        elif signal.upper() == 'SELL':
            if low <= tp:
                result = "TP"
                profit = (entry - tp) / entry
            elif high >= sl:
                result = "SL"
                profit = (entry - sl) / entry
            else:
                result = "CLOSE"
                profit = (entry - close) / entry

        else:
            continue  # Bỏ qua nếu không có tín hiệu hợp lệ

        results.append({
            'time': row['time'],
            'Signal': signal,
            'Entry': entry,
            'TP': tp,
            'SL': sl,
            'Exit': close,
            'Result': result,
            'Profit(%)': round(profit * 100, 2)
        })

    # --- Tổng hợp thống kê ---
    result_df = pd.DataFrame(results)
    total_signals = len(result_df)
    winrate = (result_df['Profit(%)'] > 0).mean() if total_signals > 0 else 0
    avg_profit = result_df['Profit(%)'].mean() if total_signals > 0 else 0
    total_profit = result_df['Profit(%)'].sum() if total_signals > 0 else 0

    # --- In kết quả ---
    print("\n📊 ===== THỐNG KÊ TÍN HIỆU =====")
    print(f"📈 Tổng số tín hiệu: {total_signals}")
    print(f"✅ Winrate: {winrate * 100:.2f}%")
    print(f"💰 Lợi nhuận trung bình: {avg_profit:.2f}%")
    print(f"💹 Tổng lợi nhuận: {total_profit:.2f}%")

    # --- Gắn màu kết quả để dễ nhìn khi in log ---
    result_df['Color'] = np.where(
        result_df['Result'] == 'TP', '🟢',
        np.where(result_df['Result'] == 'SL', '🔴', '🟡')
    )

    return {
        'total_signals': total_signals,
        'winrate': winrate,
        'avg_profit': avg_profit,
        'total_profit': total_profit,
        'details': result_df
    }
