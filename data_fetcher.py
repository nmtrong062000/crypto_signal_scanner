import pandas as pd
from binance.client import Client

def get_binance_data(symbol="BTCUSDT", interval="1h", limit=500):
    client = Client()
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        'time','open','high','low','close','volume','close_time',
        'quote_asset_vol','num_trades','taker_base_vol','taker_quote_vol','ignore'
    ])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    df[['open','high','low','close','volume']] = df[['open','high','low','close','volume']].astype(float)
    return df[['time','open','high','low','close','volume']]
