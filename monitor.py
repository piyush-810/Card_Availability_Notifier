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
TARGET_URL = urljoin(BASE_URL, "SeasonalPortal/DataEntry")
ERROR_TEXT = "There was an error"
TARGET_TEXT = "There are no cards to type. Try again soon!"

def get_authenticated_session():
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Origin': BASE_URL,
        'Referer': LOGIN_URL
    }
    
    try:
        # Step 1: Initial Login
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
        
        # Step 2: Handle Enrollment Page
        print("🔄 Step 2/3: Processing enrollment...")
        enroll_response = session.post(LOGIN_URL, data=payload, headers=headers)
        enroll_response.raise_for_status()
        
        # Step 3: Direct Access to Target (Skip NoAccess)
        print("🎯 Step 3/3: Accessing target directly...")
        target_response = session.get(TARGET_URL, headers={
            **headers,
            'Referer': ENROLL_URL
        })
        target_response.raise_for_status()
        
        return session
        
    except Exception as e:
        raise Exception(f"Authentication failed: {str(e)}")

def check_for_change():
    try:
        session = get_authenticated_session()
        
        # Retry logic for error page
        max_retries = 3
        for attempt in range(max_retries):
            response = session.get(TARGET_URL)
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            print(f"🔍 Attempt {attempt + 1}: Page preview:\n{page_text[:200]}...")
            
            if ERROR_TEXT in page_text:
                print("⚠️ Error page detected, retrying...")
                time.sleep(2)
                continue
                
            if TARGET_TEXT not in page_text:
                send_telegram_alert("🚨 CARDS AVAILABLE! Message disappeared!")
                return True
                
            print("ℹ️ No changes detected")
            return False
            
        raise Exception("Max retries reached with error page")
        
    except Exception as e:
        error_msg = f"⚠️ Monitoring failed: {str(e)}"
        print(error_msg)
        send_telegram_alert(error_msg)
        return False

# [Rest of your existing send_telegram_alert() and __main__ code]
