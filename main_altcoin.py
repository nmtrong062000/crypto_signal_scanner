# file: main.py
import pandas as pd
from datetime import datetime, timedelta, timezone
import time
import os
import json
import traceback
import random

from config import (
    COIN_LIST, INTERVALS,
    EMA_SHORT, EMA_MID, EMA_LONG,
    BB_STD, VOL_MULT
)
from data_fetcher import get_binance_data
from strategy import generate_signals
from alert import send_discord_alert

# --- ƯU TIÊN KHUNG THỜI GIAN ---
TIMEFRAME_PRIORITY = {"15m": 1, "30m": 2, "1h": 3}

# --- GIỚI HẠN TÍN HIỆU MỚI (≤ 2 cây nến gần nhất) ---
FRESH_SIGNAL_LIMIT = {
    "15m": 15 * 60 * 1,
    "30m": 30 * 60 * 1,
    "1h": 60 * 60 * 1
}

# --- TỆP LƯU TÍN HIỆU ĐÃ GỬI ---
SENT_FILE = "sent_signals.json"

# --- GIỜ VIỆT NAM (UTC+7) ---
VIETNAM_TZ = timezone(timedelta(hours=7))

# --- TẠO THƯ MỤC LOG ---
os.makedirs("logs", exist_ok=True)

url_discord = "https://discord.com/api/webhooks/1385982868769083402/L0tcoXRMh-top1zZ1dPWjthYXYCb9GUcDUC2eUplgME8JdHOJr8YtfIrxk1c6utgnzgI"

# ==========================================================
# 📂 HÀM HỖ TRỢ
# ==========================================================
def load_sent_signals():
    """Đọc danh sách tín hiệu đã gửi"""
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_sent_signals(sent_signals):
    """Lưu danh sách tín hiệu đã gửi"""
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent_signals), f)

def log_message(msg):
    """Ghi log ra file và in ra console"""
    print(msg)
    with open("logs/runtime.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(VIETNAM_TZ).strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")

# ==========================================================
# 🔍 QUÉT TOÀN BỘ COIN
# ==========================================================
def scan_all():
    all_signals = []
    coin_signals = {}
    sent_signals = load_sent_signals()

    now_vn = datetime.now(VIETNAM_TZ)
    log_message(f"\n⏳ Bắt đầu quét lúc: {now_vn.strftime('%Y-%m-%d %H:%M:%S')} (Giờ Việt Nam)")

    #random 100 đồng coin khi chạy
    sample_size = 100
    coins = COIN_LIST
    coins = random.sample(coins, min(sample_size, len(coins)))

    # coins = [
    #     "BTCUSDT",
    #     "ETHUSDT",
    #     "BNBUSDT",
    #     "SUIUSDT",
    #     "SOLUSDT",
    # ]

    intervals = ["30m"]

    for symbol in COIN_LIST:
        for interval in intervals:
            try:
                df = get_binance_data(symbol, interval, limit=500)
                if len(df) < 100:
                    log_message(f"⚠️ {symbol} ({interval}) - Không đủ dữ liệu, bỏ qua.")
                    continue

                # Tạo tín hiệu
                signals = generate_signals(df, EMA_SHORT, EMA_MID, EMA_LONG, BB_STD, VOL_MULT)
                if signals.empty:
                    continue

                latest = signals.iloc[-1]
                signal_time_utc = pd.to_datetime(latest["time"], utc=True)
                signal_time_vn = signal_time_utc.astimezone(VIETNAM_TZ)
                now = datetime.now(timezone.utc)
                time_diff = (now - signal_time_utc).total_seconds()

                # Chỉ lấy tín hiệu mới trong 1 nến gần nhất
                if time_diff > FRESH_SIGNAL_LIMIT[interval]:
                    continue

                # Ưu tiên khung lớn hơn
                if (
                    symbol not in coin_signals
                    or TIMEFRAME_PRIORITY[interval] > TIMEFRAME_PRIORITY[coin_signals[symbol]["interval"]]
                ):
                    coin_signals[symbol] = {
                        "interval": interval,
                        "signal": latest["Signal"],
                        "entry": latest["Entry"],
                        "tp": latest["TP"],
                        "sl": latest["SL"],
                        "time": signal_time_vn.strftime('%Y-%m-%d %H:%M:%S'),
                    }

                    signal_id = f"{symbol}_{coin_signals[symbol]['interval']}_{coin_signals[symbol]['time']}"

                    if signal_id not in sent_signals:
                        msg = (
                            f"🔔 **{symbol}** ({coin_signals[symbol]['interval']})\n"
                            f"➡️ {coin_signals[symbol]['signal']} @ {coin_signals[symbol]['entry']}\n"
                            f"🎯 TP: {coin_signals[symbol]['tp']}\n"
                            f"🛑 SL: {coin_signals[symbol]['sl']}\n"
                            f"🕒 Thời gian: {coin_signals[symbol]['time']} (VN)"
                        )
                        log_message(msg)
                        send_discord_alert(
                            symbol,
                            coin_signals[symbol]["interval"],
                            coin_signals[symbol]["signal"],
                            coin_signals[symbol]["entry"],
                            coin_signals[symbol]["tp"],
                            coin_signals[symbol]["sl"],
                            coin_signals[symbol]["time"],
                            url_discord
                        )

                        sent_signals.add(signal_id)
                        all_signals.append([
                            symbol, coin_signals[symbol]["interval"], coin_signals[symbol]["time"], coin_signals[symbol]["signal"], coin_signals[symbol]["entry"], coin_signals[symbol]["tp"],
                            coin_signals[symbol]["sl"]
                        ])
                    else:
                        log_message(f"⏩ {symbol} ({coin_signals[symbol]['interval']}) - Đã gửi trước đó, bỏ qua.")

            except Exception as e:
                error_msg = f"❌ Lỗi khi quét {symbol} ({interval}): {e}"
                log_message(error_msg)
                traceback.print_exc()

    # ======================================================
    # 🔔 GỬI TÍN HIỆU MỚI LÊN DISCORD
    # ======================================================
    if coin_signals:
        # for symbol, data in coin_signals.items():
        #     signal_id = f"{symbol}_{data['interval']}_{data['time']}"
        #
        #     if signal_id not in sent_signals:
        #         msg = (
        #             f"🔔 **{symbol}** ({data['interval']})\n"
        #             f"➡️ {data['signal']} @ {data['entry']}\n"
        #             f"🎯 TP: {data['tp']}\n"
        #             f"🛑 SL: {data['sl']}\n"
        #             f"🕒 Thời gian: {data['time']} (VN)"
        #         )
        #         log_message(msg)
        #         send_discord_alert(
        #             symbol,
        #             data["interval"],
        #             data["signal"],
        #             data["entry"],
        #             data["tp"],
        #             data["sl"],
        #             data["time"],
        #             url_discord
        #         )
        #
        #         sent_signals.add(signal_id)
        #         all_signals.append([
        #             symbol, data["interval"], data["time"], data["signal"], data["entry"], data["tp"], data["sl"]
        #         ])
        #     else:
        #         log_message(f"⏩ {symbol} ({data['interval']}) - Đã gửi trước đó, bỏ qua.")

        # Lưu log CSV & JSON
        if all_signals:
            pd.DataFrame(
                all_signals, columns=["Symbol", "Interval", "Time (VN)", "Signal", "Entry", "TP", "SL"]
            ).to_csv("signals.csv", index=False)
            save_sent_signals(sent_signals)
            log_message("✅ Đã lưu signals.csv và cập nhật danh sách đã gửi.")
        else:
            log_message("ℹ️ Không có tín hiệu mới nào cần gửi Discord.")
    else:
        log_message("❌ Không phát hiện tín hiệu mới.")

    log_message(f"✅ Quét hoàn tất lúc: {datetime.now(VIETNAM_TZ).strftime('%Y-%m-%d %H:%M:%S')} (Giờ Việt Nam)")

# ==========================================================
# 🧠 LOOP CHÍNH (THỰC CHIẾN)
# ==========================================================
if __name__ == "__main__":
    while True:
        try:
            scan_all()
            log_message("🕔 Chờ 5 phút trước lần quét tiếp theo...\n")
            time.sleep(5*60)
        except KeyboardInterrupt:
            log_message("🛑 Dừng bot theo yêu cầu người dùng.")
            break
        except Exception as e:
            log_message(f"⚠️ Lỗi ngoài dự kiến: {e}")
            time.sleep(60)
