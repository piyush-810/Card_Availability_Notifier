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

def send_telegram_update(message, is_alert=False):
    """Send formatted Telegram updates with alert formatting"""
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        icon = "🚨" if is_alert else "ℹ️"
        formatted_msg = f"{icon} <b>{timestamp}</b>\n{message}"
        
        requests.post(
            f"https://api.telegram.org/bot{os.getenv('BOT_TOKEN')}/sendMessage",
            params={
                'chat_id': os.getenv('CHAT_ID'),
                'text': formatted_msg,
                'parse_mode': 'HTML',
                'disable_notification': not is_alert
            },
            timeout=10
        )
    except Exception as e:
        print(f"Telegram send failed: {e}")

def follow_website_flow():
    """Exactly follows the specified website navigation flow"""
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Origin': BASE_URL
    }

    try:
        # --- STEP 1: Login ---
        send_telegram_update("Starting authentication at signin.aspx")
        headers['Referer'] = LOGIN_URL
        login_page = session.get(LOGIN_URL, headers=headers)
        login_page.raise_for_status()

        # Build login payload
        soup = BeautifulSoup(login_page.text, 'html.parser')
        login_payload = {
            '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'})['value'],
            '__VIEWSTATEGENERATOR': soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'],
            '__EVENTVALIDATION': soup.find('input', {'name': '__EVENTVALIDATION'})['value'],
            'txtEmail': os.getenv("PORTAL_USERNAME"),
            'txtPassword': os.getenv("PORTAL_PASSWORD"),
            'btnSignIn': 'Sign In'
        }

        # --- STEP 2: Enroll Page ---
        send_telegram_update("Submitting login, expecting enroll.aspx")
        headers['Referer'] = LOGIN_URL
        enroll_response = session.post(LOGIN_URL, data=login_payload, headers=headers)
        enroll_response.raise_for_status()

        if ENROLL_URL not in enroll_response.url:
            raise Exception(f"Expected {ENROLL_URL} but got {enroll_response.url}")

        # --- STEP 3: Handle Next Button ---
        send_telegram_update("Processing enroll.aspx next button")
        soup = BeautifulSoup(enroll_response.text, 'html.parser')
        next_button_payload = {
            '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'})['value'],
            '__VIEWSTATEGENERATOR': soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'],
            '__EVENTVALIDATION': soup.find('input', {'name': '__EVENTVALIDATION'})['value'],
            'ctl00$cphContent$Wizard1$StepNavigationTemplateContainerID$StepNextButton': 'Next >>'
        }

        # --- STEP 4: NoAccess Page ---
        headers['Referer'] = ENROLL_URL
        noaccess_response = session.post(ENROLL_URL, data=next_button_payload, headers=headers)
        noaccess_response.raise_for_status()

        if NOACCESS_URL not in noaccess_response.url:
            raise Exception(f"Expected {NOACCESS_URL} but got {noaccess_response.url}")

        # --- STEP 5: Final Target Page ---
        send_telegram_update("Navigating to target DataEntry page")
        headers['Referer'] = NOACCESS_URL
        target_response = session.get(TARGET_URL, headers=headers)
        target_response.raise_for_status()

        return session, target_response.text

    except Exception as e:
        send_telegram_update(f"Flow interrupted: {str(e)}", is_alert=True)
        raise

def check_for_changes():
    """Main monitoring function"""
    try:
        # Follow exact website flow
        session, page_content = follow_website_flow()
        soup = BeautifulSoup(page_content, 'html.parser')
        
        # Check for target text
        if TARGET_TEXT not in soup.get_text():
            send_telegram_update("CARDS AVAILABLE! Target message missing", is_alert=True)
            return True
            
        send_telegram_update("No changes detected - monitoring active")
        return False

    except Exception as e:
        send_telegram_update(f"Monitoring failed: {str(e)}", is_alert=True)
        return False

if __name__ == "__main__":
    # Validate credentials
    if not all(os.getenv(var) for var in ["BOT_TOKEN", "CHAT_ID", "PORTAL_USERNAME", "PORTAL_PASSWORD"]):
        send_telegram_update("❌ Missing environment variables", is_alert=True)
        sys.exit(1)

    try:
        check_for_changes()
    except Exception as e:
        send_telegram_update(f"💀 Critical failure: {str(e)}", is_alert=True)
        sys.exit(1)
