import requests
from config import DISCORD_WEBHOOK_URL

def send_discord_alert(symbol, interval, signal, entry, tp, sl, timestamp):
    data = {
        "content": f"🔔 **{symbol} ({interval})**\nSignal: **{signal}**\nEntry: {entry:.2f}\nTP: {tp:.2f}\nSL: {sl:.2f}\nTime: {timestamp}"
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=data)
    except Exception as e:
        print(f"Discord alert error: {e}")
