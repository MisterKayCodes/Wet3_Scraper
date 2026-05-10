
import os
import json
import time
from playwright.sync_api import sync_playwright

# Define paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SESSION_FILE = os.path.join(DATA_DIR, "session.json")

def capture_session():
    print("🚀 --- WET3 SESSION CAPTURER --- 🚀")
    print("This tool will help you log in manually and save your session cookies.")
    print("This allows the bot to bypass ad-walls and anti-bot measures.\n")
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    with sync_playwright() as p:
        # Launch a VISIBLE browser
        print("[*] Launching visible browser...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("[*] Navigating to wet3.click (Increased timeout)...")
        # Increase timeout to 90s and wait for DOM instead of full load to bypass slow ads
        page.goto("https://wet3.click/", timeout=90000, wait_until="domcontentloaded")
        
        print("\n✅ ACTION REQUIRED:")
        print("1. Log in to your account if needed.")
        print("2. Navigate to a profile page (e.g., https://wet3.click/user/chika1).")
        print("3. Solve any Cloudflare or Ad-Walls that appear.")
        print("4. When you are fully logged in and seeing the content, come back here.")
        
        input("\nPress ENTER when you have successfully logged in and are ready to save the session...")
        
        # Capture cookies and UA
        cookies = context.cookies()
        ua = page.evaluate("navigator.userAgent")
        
        session_data = {
            "cookies": cookies,
            "user_agent": ua,
            "timestamp": time.time()
        }
        
        with open(SESSION_FILE, "w") as f:
            json.dump(session_data, f, indent=4)
            
        print(f"\nâœ¨ SUCCESS! Session saved locally to: {SESSION_FILE}")
        
        # --- TELEGRAM COMMAND GENERATION ---
        print("\nâš¡ï¸  REMOTE UPDATE COMMAND (For VPS):")
        print("-" * 50)
        print("Copy the line below and paste it into your Telegram Bot to update the VPS:")
        print(f"\n/set_session {json.dumps(session_data)}")
        print("-" * 50)
        
        print("\nYou can now restart your bot, and it will use these hijacked cookies.")
        
        browser.close()

if __name__ == "__main__":
    capture_session()
