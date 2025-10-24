# file: alert.py
import requests
import time
from config import DISCORD_WEBHOOK_URL


def send_discord_alert(symbol, interval, signal, entry, tp, sl, timestamp,url_discord=DISCORD_WEBHOOK_URL, retry=3):
    """
    Gửi tín hiệu cảnh báo đến Discord Webhook.
    Tự động retry nếu thất bại (do lỗi mạng hoặc Discord rate limit).
    """
    if not url_discord:
        print("⚠️ Chưa cấu hình DISCORD_WEBHOOK_URL trong config.py")
        return

    content = (
        f"🔔 **{symbol} ({interval})**\n"
        f"➡️ Signal: **{signal}**\n"
        f"💰 Entry: `{entry}`\n"
        f"🎯 TP: `{tp}`\n"
        f"🛑 SL: `{sl}`\n"
        f"🕒 Time: {timestamp} (VN)\n"
        f"-----------------------------"
    )

    payload = {"content": content}

    for attempt in range(1, retry + 1):
        try:
            response = requests.post(
                url_discord,
                json=payload,
                timeout=10
            )
            if response.status_code == 204:
                print(f"✅ Gửi tín hiệu {symbol} ({interval}) thành công!")
                return
            else:
                print(f"⚠️ Lỗi gửi Discord ({response.status_code}): {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Lỗi mạng Discord: {e}")

        if attempt < retry:
            print(f"🔁 Thử lại lần {attempt + 1} sau 3s...")
            time.sleep(3)
        else:
            print(f"🚫 Gửi tín hiệu {symbol} ({interval}) thất bại sau {retry} lần thử.")
