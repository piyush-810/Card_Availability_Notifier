import requests
from bs4 import BeautifulSoup
import os
import sys
from urllib.parse import urljoin

# Configuration
BASE_URL = "https://gts.gradtrak.com/"
LOGIN_URL = urljoin(BASE_URL, "GTO/Profiles/SignIn.aspx")
TARGET_URL = urljoin(BASE_URL, "SeasonalPortal/DataEntry")
TARGET_TEXT = "There are no cards to type. Try again soon!"

def get_authenticated_session():
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Origin': BASE_URL,
        'Referer': LOGIN_URL
    }
    
    try:
        # Initial GET to capture tokens
        login_page = session.get(LOGIN_URL, headers=headers)
        login_page.raise_for_status()
        soup = BeautifulSoup(login_page.text, 'html.parser')

        # Prepare payload with EXACT field names
        payload = {
            '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'})['value'],
            '__VIEWSTATEGENERATOR': soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'],
            '__EVENTVALIDATION': soup.find('input', {'name': '__EVENTVALIDATION'})['value'],
            'txtEmail': os.getenv("PORTAL_USERNAME"),  # Email field
            'txtPassword': os.getenv("PORTAL_PASSWORD"),  # Password field
            'btnSignIn': 'Sign In'  # Login button ID from your screenshot
        }

        # Submit login
        response = session.post(LOGIN_URL, data=payload, headers=headers)
        response.raise_for_status()
        
        # Verify login success
        if "SignOut" not in response.text:
            with open("login_failure.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            raise Exception("Login failed - check login_failure.html")
            
        return session
        
    except Exception as e:
        raise Exception(f"Login error: {str(e)}")

def check_for_change():
    try:
        print("🔐 Authenticating...")
        session = get_authenticated_session()
        
        print("🌐 Fetching target page...")
        response = session.get(TARGET_URL)
        response.raise_for_status()
        
        # Save page for debugging
        with open("page.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        print(f"🔍 Page content preview:\n{page_text[:200]}...")
        
        if TARGET_TEXT not in page_text:
            send_telegram_alert("🚨 CARDS AVAILABLE! The message disappeared!")
            return True
            
        print("ℹ️ No changes detected")
        return False
        
    except Exception as e:
        error_msg = f"⚠️ Monitoring failed: {str(e)}"
        print(error_msg)
        send_telegram_alert(error_msg)
        return False

def send_telegram_alert(message):
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{os.getenv('BOT_TOKEN')}/sendMessage",
            params={
                'chat_id': os.getenv('CHAT_ID'),
                'text': message,
                'parse_mode': 'HTML'
            },
            timeout=10
        )
        response.raise_for_status()
        print("✅ Telegram alert sent")
    except Exception as e:
        print(f"❌ Failed to send Telegram alert: {str(e)}")

if __name__ == "__main__":
    # Validate environment variables
    required_vars = {
        "PORTAL_USERNAME": os.getenv("PORTAL_USERNAME"),
        "PORTAL_PASSWORD": os.getenv("PORTAL_PASSWORD"),
        "BOT_TOKEN": os.getenv("BOT_TOKEN"),
        "CHAT_ID": os.getenv("CHAT_ID")
    }
    
    missing_vars = [k for k, v in required_vars.items() if not v]
    if missing_vars:
        error_msg = f"❌ Missing environment variables: {', '.join(missing_vars)}"
        print(error_msg)
        if required_vars["BOT_TOKEN"] and required_vars["CHAT_ID"]:
            send_telegram_alert(error_msg)
        sys.exit(1)
        
    check_for_change()
