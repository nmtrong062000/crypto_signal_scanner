import pandas as pd
from config import COIN_LIST, TIMEFRAMES, EMA_SHORT, EMA_MID, EMA_LONG, BB_STD, VOL_MULT
from data_fetcher import get_binance_data
from strategy import generate_signals
from alert import send_discord_alert

def scan_all():
    all_signals = []
    for symbol in COIN_LIST:
        for interval in TIMEFRAMES:
            try:
                df = get_binance_data(symbol, interval, limit=500)
                signals = generate_signals(df, EMA_SHORT, EMA_MID, EMA_LONG, BB_STD, VOL_MULT)
                if not signals.empty:
                    latest = signals.iloc[-1]
                    print(f"🔔 {symbol} ({interval}) -> {latest['Signal']} @ {latest['Entry']:.2f}")
                    send_discord_alert(symbol, interval, latest['Signal'], latest['Entry'], latest['TP'], latest['SL'], str(latest['time']))
                    all_signals.append([symbol, interval, latest['time'], latest['Signal'], latest['Entry'], latest['TP'], latest['SL']])
            except Exception as e:
                print(f"Error scanning {symbol} {interval}: {e}")

    if all_signals:
        pd.DataFrame(all_signals, columns=['Symbol','Interval','Time','Signal','Entry','TP','SL']).to_csv('signals.csv', index=False)
        print("✅ Signals saved to signals.csv")

if __name__ == '__main__':
    scan_all()
