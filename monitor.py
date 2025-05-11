import requests
from bs4 import BeautifulSoup
import os
import sys

# Configuration
URL = "https://gts.gradtrak.com/SeasonalPortal/DataEntry"
TARGET_TEXT = "There are no cards to type. Try again soon!"
BOT_TOKEN = os.getenv("BOT_TOKEN")  # os.environ works too
CHAT_ID = os.getenv("CHAT_ID")

# Mimic a browser to avoid blocking
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def check_for_change():
    try:
        response = requests.get(URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code} received")
            
        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text()
        
        print(f"Current page content preview: {page_text[:200]}...")  # Debug
        
        if TARGET_TEXT not in page_text:
            send_telegram_alert("🚨 CARDS AVAILABLE! The message disappeared!")
            return True
            
        print("Target text still present - no changes detected")
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
        
        if response.status_code != 200:
            print(f"Telegram API error: {response.json()}")
            return False
            
        return True
        
    except Exception as e:
        print(f"Failed to send Telegram alert: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting monitoring check...")
    if not all([BOT_TOKEN, CHAT_ID]):
        print("ERROR: Missing BOT_TOKEN or CHAT_ID")
        sys.exit(1)
        
    check_for_change()
    print("Monitoring check completed")
