import pandas as pd

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def bollinger_bands(series, window=20, std=1.6):
    mid = series.rolling(window).mean()
    std_dev = series.rolling(window).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return mid, upper, lower

def volume_filter(volume, multiplier=1.3, window=20):
    vol_ma = volume.rolling(window).mean()
    return volume > vol_ma * multiplier
