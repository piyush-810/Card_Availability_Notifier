import requests
from bs4 import BeautifulSoup
import time

# Configuration
URL = "https://gts.gradtrak.com/SeasonalPortal/DataEntry"  
CHECK_INTERVAL = 60  # Seconds between checks (e.g., 60 = 1 minute)
TARGET_TEXT = "There are no cards to type. Try again soon!"
BOT_TOKEN = "7350093859:AAF5uqLs1xcalkpzqx1SnMvO2RUVZajGzXw"  # Replace with your bot token
CHAT_ID = "6473440321"  # Your chat ID

def check_for_change():
    try:
        response = requests.get(URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Check if the target text is MISSING (meaning cards are available)
        if TARGET_TEXT not in soup.get_text():
            send_telegram_alert("🚨 CARDS AVAILABLE! The message disappeared!")
            return True
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {
        "chat_id": CHAT_ID,
        "text": message,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        print("Telegram alert sent!")
    else:
        print(f"Failed to send alert. Response: {response.json()}")

def monitor():
    print(f"Monitoring for disappearance of: '{TARGET_TEXT}'...")
    while True:
        if check_for_change():
            break  # Exit after first alert (remove this line to keep monitoring)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    monitor()
