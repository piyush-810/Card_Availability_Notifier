import requests
from bs4 import BeautifulSoup
import os
import sys
import time
from urllib.parse import urljoin

# Configuration
BASE_URL = "https://gts.gradtrak.com/"
LOGIN_URL = urljoin(BASE_URL, "GTO/Profiles/SignIn.aspx")
ENROLL_URL = urljoin(BASE_URL, "GTO/Profiles/Enroll.aspx")
NOACCESS_URL = urljoin(BASE_URL, "GTO/Profiles/NoAccess.aspx")
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
        # Step 1: Initial login
        print("🔐 Step 1/3: Authenticating...")
        login_page = session.get(LOGIN_URL, headers=headers)
        login_page.raise_for_status()
        
        soup = BeautifulSoup(login_page.text, 'html.parser')
        payload = {
            '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'})['value'],
            '__VIEWSTATEGENERATOR': soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'],
            '__EVENTVALIDATION': soup.find('input', {'name': '__EVENTVALIDATION'})['value'],
            'txtEmail': os.getenv("PORTAL_USERNAME"),
            'txtPassword': os.getenv("PORTAL_PASSWORD"),
            'btnSignIn': 'Sign In'
        }
        
        # Step 2: Handle enrollment page
        print("🔄 Step 2/3: Processing enrollment...")
        enroll_response = session.post(LOGIN_URL, data=payload, headers=headers)
        enroll_response.raise_for_status()
        
        if ENROLL_URL not in enroll_response.url:
            raise Exception(f"Unexpected redirect after login: {enroll_response.url}")
        
        # Extract Next button payload
        soup = BeautifulSoup(enroll_response.text, 'html.parser')
        enroll_payload = {
            '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'})['value'],
            '__VIEWSTATEGENERATOR': soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'],
            '__EVENTVALIDATION': soup.find('input', {'name': '__EVENTVALIDATION'})['value'],
            'ctl00$cphContent$Wizard1$StepNavigationTemplateContainerID$StepNextButton': 'Next >>'
        }
        
        # Step 3: Navigate through NoAccess page
        print("⏩ Step 3/3: Bypassing access page...")
        noaccess_response = session.post(ENROLL_URL, data=enroll_payload, headers={
            **headers,
            'Referer': ENROLL_URL
        })
        noaccess_response.raise_for_status()
        
        if NOACCESS_URL not in noaccess_response.url:
            raise Exception(f"Unexpected redirect after enrollment: {noaccess_response.url}")
        
        # Manually navigate to target URL
        print("🎯 Accessing target page...")
        target_response = session.get(TARGET_URL, headers={
            **headers,
            'Referer': NOACCESS_URL
        })
        target_response.raise_for_status()
        
        return session
        
    except Exception as e:
        error_msg = f"🔴 Authentication failed at step: {str(e)}"
        print(error_msg)
        raise Exception(error_msg)

def check_for_change():
    try:
        session = get_authenticated_session()
        response = session.get(TARGET_URL)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        print("🔍 Current page status:")
        print(page_text[:200] + "...")
        
        if TARGET_TEXT not in page_text:
            send_telegram_alert("🟢 CARDS AVAILABLE! The message disappeared!")
            return True
            
        print("🟡 No changes detected")
        return False
        
    except Exception as e:
        error_msg = f"🔴 Monitoring failed: {str(e)}"
        print(error_msg)
        send_telegram_alert(error_msg)
        return False

def send_telegram_alert(message):
    try:
        requests.post(
            f"https://api.telegram.org/bot{os.getenv('BOT_TOKEN')}/sendMessage",
            params={
                'chat_id': os.getenv('CHAT_ID'),
                'text': message,
                'parse_mode': 'HTML'
            },
            timeout=10
        )
    except Exception as e:
        print(f"❌ Telegram alert failed: {str(e)}")

if __name__ == "__main__":
    try:
        if not all([os.getenv("PORTAL_USERNAME"), os.getenv("PORTAL_PASSWORD")]):
            raise Exception("Missing credentials")
            
        check_for_change()
    except Exception as e:
        print(f"🔥 Critical error: {str(e)}")
        sys.exit(1)
