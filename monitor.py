import requests
from bs4 import BeautifulSoup
import os
import sys
import time
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
        # Step 1: Get login page
        print("🔄 Loading login page...")
        login_page = session.get(LOGIN_URL, headers=headers)
        login_page.raise_for_status()
        
        # Save login page for debugging
        with open("login_page_source.html", "w", encoding="utf-8") as f:
            f.write(login_page.text)
        print("💾 Saved login page source")

        soup = BeautifulSoup(login_page.text, 'html.parser')

        # Step 2: Prepare payload with dynamic field detection
        payload = {
            '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'})['value'],
            '__VIEWSTATEGENERATOR': soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'],
            '__EVENTVALIDATION': soup.find('input', {'name': '__EVENTVALIDATION'})['value'],
            'txtEmail': os.getenv("PORTAL_USERNAME"),
            'txtPassword': os.getenv("PORTAL_PASSWORD"),
            'btnSignIn': 'Sign In'
        }

        # Add delay to prevent brute-force detection
        time.sleep(5)

        # Step 3: Submit login
        print("🔐 Attempting login...")
        response = session.post(LOGIN_URL, data=payload, headers=headers)
        response.raise_for_status()
        
        # Save login response for debugging
        with open("login_response.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        # Step 4: Verify login success
        success_markers = ["SignOut", "Dashboard", "Welcome"]
        if not any(marker in response.text for marker in success_markers):
            raise Exception("Login failed - no success markers detected")
            
        print("✅ Login successful")
        return session
        
    except Exception as e:
        error_msg = f"❌ Login failed: {str(e)}"
        print(error_msg)
        if 'login_response.html' in os.listdir():
            print("📁 See login_response.html for details")
        raise Exception(error_msg)

def check_for_change():
    try:
        session = get_authenticated_session()
        
        print("🌐 Loading target page...")
        response = session.get(TARGET_URL)
        response.raise_for_status()
        
        # Save target page for debugging
        with open("target_page.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        # Debug output
        print("🔍 Page content preview:")
        print(page_text[:200] + "...")
        
        if TARGET_TEXT not in page_text:
            send_telegram_alert("🚨 CARDS AVAILABLE! The message disappeared!")
            print("⚠️ Change detected - notification sent")
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
        print("📤 Telegram alert sent successfully")
    except Exception as e:
        print(f"❌ Failed to send Telegram alert: {str(e)}")

if __name__ == "__main__":
    try:
        # Validate environment variables
        required_vars = {
            "BOT_TOKEN": os.getenv("BOT_TOKEN"),
            "CHAT_ID": os.getenv("CHAT_ID"),
            "PORTAL_USERNAME": os.getenv("PORTAL_USERNAME"),
            "PORTAL_PASSWORD": os.getenv("PORTAL_PASSWORD")
        }
        
        missing_vars = [k for k, v in required_vars.items() if not v]
        if missing_vars:
            error_msg = f"❌ Missing environment variables: {', '.join(missing_vars)}"
            print(error_msg)
            if required_vars.get("BOT_TOKEN") and required_vars.get("CHAT_ID"):
                send_telegram_alert(error_msg)
            sys.exit(1)
            
        print("🚀 Starting monitoring check")
        check_for_change()
        print("🏁 Monitoring complete")
        
    except Exception as e:
        print(f"🔥 Critical error: {str(e)}")
        sys.exit(1)
