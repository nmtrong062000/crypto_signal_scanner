# file: data_fetcher.py
import os
import time
import requests
import pandas as pd

BASE_URL = "https://fapi.binance.com"  # Binance Futures API


# =========================================================
# 🔹 Hàm 1: Lấy dữ liệu mới nhất và tự động cập nhật file CSV
# =========================================================
def get_binance_data(symbol="BTCUSDT", interval="1h", limit=500, save=True):
    """
    Lấy dữ liệu nến đã đóng từ Binance Futures (klines).
    - Không bao gồm nến đang chạy.
    - Nếu save=True → cập nhật hoặc tạo file CSV trong /data.
    - Trả về DataFrame gồm: [time, open, high, low, close, volume]
    """
    try:
        symbol = symbol.upper()
        endpoint = f"/fapi/v1/klines"
        url = f"{BASE_URL}{endpoint}?symbol={symbol}&interval={interval}&limit={limit}"

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data or (isinstance(data, dict) and "code" in data):
            raise ValueError(data.get("msg", "Không có dữ liệu từ Binance."))

        # Tạo DataFrame
        df_new = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_vol", "num_trades",
            "taker_base_vol", "taker_quote_vol", "ignore"
        ])

        # 👉 Chỉ giữ các nến đã đóng
        current_ts = int(time.time() * 1000)
        df_new = df_new[df_new["close_time"] < current_ts]

        # Chuyển kiểu dữ liệu
        df_new["time"] = pd.to_datetime(df_new["open_time"], unit="ms")
        df_new[["open", "high", "low", "close", "volume"]] = df_new[
            ["open", "high", "low", "close", "volume"]
        ].astype(float)
        df_new = df_new[["time", "open", "high", "low", "close", "volume"]]

        # --- Lưu trữ dữ liệu ---
        if save:
            os.makedirs("data", exist_ok=True)
            file_path = f"data/{symbol}_{interval}.csv"

            if os.path.exists(file_path):
                df_old = pd.read_csv(file_path, parse_dates=["time"])
                last_time = df_old["time"].iloc[-1]
                df_append = df_new[df_new["time"] > last_time]

                if not df_append.empty:
                    df_updated = pd.concat([df_old, df_append], ignore_index=True)
                    df_updated.drop_duplicates(subset=["time"], inplace=True)
                    df_updated.to_csv(file_path, index=False)
                    print(f"🟢 {symbol} ({interval}): +{len(df_append)} nến mới (đã đóng).")
                else:
                    print(f"✅ {symbol} ({interval}): Không có nến mới.")
                    df_updated = df_old
            else:
                df_new.to_csv(file_path, index=False)
                print(f"📁 Tạo mới file dữ liệu: {file_path}")
                df_updated = df_new

            return df_updated
        else:
            return df_new

    except Exception as e:
        raise Exception(f"❌ Lỗi khi lấy dữ liệu {symbol} ({interval}): {e}")


# =========================================================
# 🔹 Hàm 2: Lấy dữ liệu lịch sử có cache (tốc độ cao)
# =========================================================
def get_historical_data(symbol, interval="1h", days=365, isgetdatanew=False):
    """
    Lấy dữ liệu lịch sử X ngày gần nhất.
    - Nếu isgetdatanew=False → đọc từ cache (nếu có).
    - Nếu isgetdatanew=True → tải mới toàn bộ và ghi đè cache.
    Cache lưu tại: data_cache/{symbol}_{interval}_{days}.csv
    """
    try:
        os.makedirs("data_cache", exist_ok=True)
        cache_path = f"data_cache/{symbol}_{interval}_{days}.csv"

        # --- Ưu tiên đọc cache nếu có ---
        if not isgetdatanew and os.path.exists(cache_path):
            df = pd.read_csv(cache_path)
            if not df.empty:
                df["time"] = pd.to_datetime(df["time"])
                return df

        # --- Gọi API Binance ---
        symbol = symbol.upper()
        end_time = int(time.time() * 1000)
        start_time = end_time - days * 24 * 60 * 60 * 1000
        batch = 1500  # số nến mỗi lần
        all_data = []

        print(f"🌐 Đang tải dữ liệu mới: {symbol} ({interval}, {days} ngày)")

        while True:
            url = (
                f"{BASE_URL}/fapi/v1/klines"
                f"?symbol={symbol}&interval={interval}&limit={batch}"
                f"&startTime={start_time}&endTime={end_time}"
            )
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                print(f"⚠️ Lỗi tải batch, retry sau 5s... ({e})")
                time.sleep(5)
                continue

            if not data:
                break

            all_data += data
            last_time = data[-1][6]  # close_time
            if last_time >= end_time or len(data) < batch:
                break

            start_time = last_time + 1
            time.sleep(0.3)  # tránh rate limit

        if not all_data:
            raise Exception(f"Không lấy được dữ liệu {symbol} ({interval}).")

        df = pd.DataFrame(all_data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_vol", "num_trades",
            "taker_base_vol", "taker_quote_vol", "ignore"
        ])

        df["time"] = pd.to_datetime(df["open_time"], unit="ms")
        df[["open", "high", "low", "close", "volume"]] = df[
            ["open", "high", "low", "close", "volume"]
        ].astype(float)

        df = df[["time", "open", "high", "low", "close", "volume"]]
        df = df.drop_duplicates(subset=["time"]).reset_index(drop=True)
        df.to_csv(cache_path, index=False)

        print(f"💾 Đã lưu dữ liệu: {cache_path}")
        return df

    except Exception as e:
        raise Exception(f"❌ Lỗi khi lấy dữ liệu lịch sử {symbol} ({interval}): {e}")


# =========================================================
# 🔹 Hàm 3: Chuẩn hóa gọi trong main.py
# =========================================================
def get_klines(symbol, interval="1h", limit=500):
    """
    Hàm rút gọn cho main.py → trả về DataFrame chứa dữ liệu nến mới nhất.
    """
    try:
        return get_binance_data(symbol, interval, limit, save=False)
    except Exception as e:
        print(f"⚠️ Lỗi get_klines {symbol} ({interval}): {e}")
        return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])
