import requests
from bs4 import BeautifulSoup
import os
import sys
from urllib.parse import urljoin

# Configuration
BASE_URL = "https://gts.gradtrak.com/"
LOGIN_URL = urljoin(BASE_URL, "GTO/Profiles/SignIn.aspx")
TARGET_URL = urljoin(BASE_URL, "SeasonalPortal/DataEntry")
TARGET_ELEMENT = {'class': 'alert alert-danger'}  # More specific than text search

def get_authenticated_session():
    session = requests.Session()
    
    # Get login page for ASP.NET tokens
    login_page = session.get(LOGIN_URL)
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
    session.post(LOGIN_URL, data=payload)
    return session

def check_for_change():
    try:
        session = get_authenticated_session()
        response = session.get(TARGET_URL)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for specific element instead of raw text
        target_div = soup.find('div', TARGET_ELEMENT)
        
        if not target_div:  # Element disappeared
            send_telegram_alert("🚨 CARDS AVAILABLE! The alert div disappeared!")
            return True
            
        print("ℹ️ Target element still present")
        return False
        
    except Exception as e:
        send_telegram_alert(f"⚠️ Monitoring failed: {str(e)}")
        return False

def send_telegram_alert(message):
    requests.post(
        f"https://api.telegram.org/bot{os.getenv('BOT_TOKEN')}/sendMessage",
        params={'chat_id': os.getenv('CHAT_ID'), 'text': message}
    )

if __name__ == "__main__":
    if not all([os.getenv("PORTAL_USERNAME"), os.getenv("PORTAL_PASSWORD")]):
        print("❌ Missing login credentials")
        sys.exit(1)
        
    check_for_change()
