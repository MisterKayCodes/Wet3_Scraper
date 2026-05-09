import os
import json
import time
from playwright.sync_api import sync_playwright

# Calculate project root (one level up from core/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_FILE = os.path.join(PROJECT_ROOT, "data", "session.json")

DOMAINS = [
    {"name": "Misnympho Profile", "url": "https://wet3.click/user/misnympho"},
    {"name": "Zelda Profile", "url": "https://wet3.click/user/zelda"},
    {"name": "Host Site", "url": "https://send.now/"}
]

def authorize_session():
    """
    Launches a headed browser for the user to solve Cloudflare challenges on multiple domains.
    """
    print("\n" + "="*50, flush=True)
    print("   DUAL-DOMAIN SESSION AUTHORIZATION", flush=True)
    print("="*50, flush=True)
    print("\n[*] INSTRUCTIONS:", flush=True)
    print("1. A browser window will open.", flush=True)
    print("2. We will visit TWO sites one after the other.", flush=True)
    print("3. On EACH site, solve the 'Verify you are human' checkbox if it appears.", flush=True)
    print("4. Come back here and press ENTER after EACH check is solved.", flush=True)
    
    with sync_playwright() as p:
        # Launch headed browser
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        all_cookies = []
        
        for site in DOMAINS:
            print(f"\n[*] Navigating to {site['name']} ({site['url']}, flush=True)...")
            try:
                # Use domcontentloaded and 90s timeout for flaky connection
                page.goto(site['url'], wait_until="domcontentloaded", timeout=90000)
                input(f"[WAITING] Solve the check on {site['name']} in the browser, then press ENTER here...")
                # Capture cookies for this domain
                all_cookies.extend(context.cookies())
            except Exception as e:
                print(f"[!] Warning: Navigation to {site['name']} timed out, but continuing... {e}", flush=True)
                input(f"[WAITING] Site is slow, but if it loaded in browser, solve check and press ENTER here...")
                all_cookies.extend(context.cookies())
            
        user_agent = page.evaluate("navigator.userAgent")
        
        session_data = {
            "cookies": all_cookies,
            "user_agent": user_agent,
            "timestamp": time.time()
        }
        
        with open(SESSION_FILE, "w") as f:
            json.dump(session_data, f, indent=4)
            
        print(f"\n[SUCCESS] Multi-domain session saved to {SESSION_FILE}!", flush=True)
        print("[*] You can now close the browser window.", flush=True)
        
        browser.close()

if __name__ == "__main__":
    authorize_session()
