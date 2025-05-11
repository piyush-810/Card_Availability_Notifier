import requests
from bs4 import BeautifulSoup
import os
import sys
from urllib.parse import urljoin

# Configuration
BASE_URL = "https://gts.gradtrak.com/"
LOGIN_URL = urljoin(BASE_URL, "GTO/Profiles/SignIn.aspx")
TARGET_URL = urljoin(BASE_URL, "SeasonalPortal/DataEntry")
TARGET_ELEMENT = {'class': 'alert alert-danger'}  # Changed to danger per your screenshot

def get_authenticated_session():
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        # Get login page for ASP.NET tokens
        login_page = session.get(LOGIN_URL, headers=headers)
        login_page.raise_for_status()
        soup = BeautifulSoup(login_page.text, 'html.parser')
        
        # Prepare ASP.NET form data
        payload = {
            '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'})['value'],
            '__VIEWSTATEGENERATOR': soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'],
            '__EVENTVALIDATION': soup.find('input', {'name': '__EVENTVALIDATION'})['value'],
            'ctl00$ContentPlaceHolder1$Login1$UserName': os.getenv("PORTAL_USERNAME"),
            'ctl00$ContentPlaceHolder1$Login1$Password': os.getenv("PORTAL_PASSWORD"),
            'ctl00$ContentPlaceHolder1$Login1$LoginButton': 'Sign In'
        }
        
        # Submit login
        login_response = session.post(LOGIN_URL, data=payload, headers=headers)
        login_response.raise_for_status()
        
        # Verify login success
        if "SignOut" not in login_response.text:
            raise Exception("Login failed - check credentials or page structure")
            
        return session
        
    except Exception as e:
        send_telegram_alert(f"🔐 Login failed: {str(e)}")
        raise

def check_for_change():
    try:
        session = get_authenticated_session()
        response = session.get(TARGET_URL)
        response.raise_for_status()
        
        # Save page content for debugging
        with open("page.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for specific element
        target_div = soup.find('div', TARGET_ELEMENT)
        
        if target_div:  # Element exists (no cards available)
            print(f"ℹ️ Target element found: {target_div.get_text(strip=True)[:50]}...")
            return False
        else:  # Element disappeared (cards available)
            send_telegram_alert("🚨 CARDS AVAILABLE! The alert div disappeared!")
            return True
            
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
    required_vars = ["PORTAL_USERNAME", "PORTAL_PASSWORD", "BOT_TOKEN", "CHAT_ID"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        error_msg = f"❌ Missing environment variables: {', '.join(missing_vars)}"
        print(error_msg)
        if "BOT_TOKEN" in os.environ and "CHAT_ID" in os.environ:
            send_telegram_alert(error_msg)
        sys.exit(1)
        
    check_for_change()
