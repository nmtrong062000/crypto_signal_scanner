from indicators import ema, bollinger_bands, volume_filter
import pandas as pd

def generate_signals(df, ema_short, ema_mid, ema_long, bb_std, vol_mult):
    df['EMA_S'] = ema(df['close'], ema_short)
    df['EMA_M'] = ema(df['close'], ema_mid)
    df['EMA_L'] = ema(df['close'], ema_long)
    df['BB_M'], df['BB_U'], df['BB_L'] = bollinger_bands(df['close'], 20, bb_std)
    df['Vol_OK'] = volume_filter(df['volume'], vol_mult)

    df['Signal'] = None
    df['Entry'] = None
    df['TP'] = None
    df['SL'] = None

    for i in range(1, len(df)):
        if (
            df['EMA_S'][i] > df['EMA_M'][i] > df['EMA_L'][i] and
            df['close'][i] > df['EMA_S'][i] and
            df['close'][i] > df['BB_U'][i] and
            df['Vol_OK'][i]
        ):
            df.at[i, 'Signal'] = 'BUY'
            df.at[i, 'Entry'] = df['close'][i]
            df.at[i, 'TP'] = df['close'][i] * 1.02
            df.at[i, 'SL'] = df['close'][i] * 0.99

        elif (
            df['EMA_S'][i] < df['EMA_M'][i] < df['EMA_L'][i] and
            df['close'][i] < df['EMA_S'][i] and
            df['close'][i] < df['BB_L'][i] and
            df['Vol_OK'][i]
        ):
            df.at[i, 'Signal'] = 'SELL'
            df.at[i, 'Entry'] = df['close'][i]
            df.at[i, 'TP'] = df['close'][i] * 0.98
            df.at[i, 'SL'] = df['close'][i] * 1.01

    return df[df['Signal'].notnull()][['time', 'Signal', 'Entry', 'TP', 'SL']]
