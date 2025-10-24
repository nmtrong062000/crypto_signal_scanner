# file: getCoinsBinanceFuture.py

import requests
import json
import os

CONFIG_FILE = "config.py"
BINANCE_FUTURES_EXCHANGE_INFO = "https://fapi.binance.com/fapi/v1/exchangeInfo"

def get_all_futures_symbols():
    """Lấy toàn bộ các cặp giao dịch futures đang active trên Binance"""
    try:
        response = requests.get(BINANCE_FUTURES_EXCHANGE_INFO, timeout=10)
        response.raise_for_status()
        data = response.json()

        symbols = [
            s["symbol"] for s in data["symbols"]
            if s["status"] == "TRADING" and s["contractType"] in ("PERPETUAL", "CURRENT_MONTH")
        ]

        # Lọc chỉ các cặp USDT (ví dụ BTCUSDT, ETHUSDT, 1000SHIBUSDT)
        usdt_symbols = [s for s in symbols if s.endswith("USDT")]
        usdt_symbols.sort()
        return usdt_symbols

    except Exception as e:
        print(f"❌ Lỗi khi lấy danh sách futures: {e}")
        return []


def update_config_coin_list(symbols):
    """Cập nhật danh sách COIN_LIST trong config.py"""
    if not symbols:
        print("⚠️ Không có symbol nào để cập nhật.")
        return

    if not os.path.exists(CONFIG_FILE):
        print(f"⚠️ Không tìm thấy file {CONFIG_FILE}. Tạo mới...")
        with open(CONFIG_FILE, "w") as f:
            f.write("COIN_LIST = []\n")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    replaced = False
    for line in lines:
        if line.strip().startswith("COIN_LIST"):
            line = f"COIN_LIST = {json.dumps(symbols, indent=4, ensure_ascii=False)}\n"
            replaced = True
        new_lines.append(line)

    if not replaced:
        new_lines.append(f"\nCOIN_LIST = {json.dumps(symbols, indent=4, ensure_ascii=False)}\n")

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"✅ Đã cập nhật {len(symbols)} cặp Futures vào {CONFIG_FILE}")


if __name__ == "__main__":
    print("⏳ Đang lấy danh sách coin Futures từ Binance...")
    futures_symbols = get_all_futures_symbols()
    if futures_symbols:
        update_config_coin_list(futures_symbols)
        print("✅ Hoàn tất cập nhật danh sách COIN_LIST trong config.py")
    else:
        print("❌ Không lấy được danh sách coin Futures nào.")
