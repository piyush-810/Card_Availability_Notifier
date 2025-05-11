import requests
from bs4 import BeautifulSoup
import os
import sys

# Configuration
URL = "https://gts.gradtrak.com/SeasonalPortal/DataEntry"
TARGET_TEXT = "There are no cards to type. Try again soon!"
BOT_TOKEN = os.getenv("BOT_TOKEN", "")  # Second parameter is default value
CHAT_ID = os.getenv("CHAT_ID", "")

# Validate critical variables
if not all([BOT_TOKEN, CHAT_ID]):
    print("❌ ERROR: Missing required environment variables")
    print(f"BOT_TOKEN present: {bool(BOT_TOKEN)}")
    print(f"CHAT_ID present: {bool(CHAT_ID)}")
    sys.exit(1)

def check_for_change():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        response = requests.get(URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text()
        
        print(f"🔍 Page content preview:\n{page_text[:200]}...")
        
        if TARGET_TEXT not in page_text:
            send_telegram_alert("🚨 CARDS AVAILABLE! The message disappeared!")
            return True
            
        print("ℹ️ No changes detected - target text still present")
        return False
        
    except Exception as e:
        error_msg = f"⚠️ Monitoring error: {str(e)}"
        print(error_msg)
        send_telegram_alert(error_msg)
        return False

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        params = {
            "chat_id": CHAT_ID,
            "text": message,
        }
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        print("✅ Telegram alert sent successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to send Telegram alert: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting monitoring check")
    check_for_change()
    print("🏁 Monitoring check completed")
