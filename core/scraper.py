
import os
import re
import time
import json
import requests
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from .downloader import resolve_monetized_link
try:
    from playwright_stealth import stealth
except ImportError:
    stealth = None

BASE_URL = "https://wet3.click"

def get_profile_data(target_url, max_pages=None, headless=False, status_callback=None):
    """
    EVIDENCE-BASED SCRAPER: 
    - Verified Pagination (reads text from UI)
    - 100% Media Tagging (checks server headers)
    """
    print(f"[*] Starting Evidence-Based Scrape for: {target_url}", flush=True)
    all_content = []
    
    with sync_playwright() as p:
        # Full Viewport for better button detection
        # Using Chromium (Visible Mode for Debugging)
        browser = p.chromium.launch(headless=headless, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        context = browser.new_context(viewport={'width': 1920, 'height': 1080}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        page = context.new_page()
        if stealth:
            try: stealth(page)
            except: pass
        
        try:
            # Switch to 'commit' to bypass slow ad-scripts hanging the page
            page.goto(target_url, wait_until="commit", timeout=90000)
            print("[*] Initial commit reached. Waiting for dynamic content...", flush=True)
            time.sleep(15) # Manual wait for the UI to settle
            
            def get_page_evidence():
                try:
                    text = page.locator("body").text_content()
                    match = re.search(r"Page\s*(\d+)\s*(?:of|/)\s*(\d+)", text)
                    if match:
                        return int(match.group(1)), int(match.group(2))
                except: pass
                return 1, 1

            current_p, total_p = get_page_evidence()
            print(f"[*] INITIAL EVIDENCE: Page {current_p} of {total_p}", flush=True)

            while True:
                if status_callback: status_callback(f"📄 <b>Processing Page:</b> {current_p} of {total_p}")
                print(f"\n[*] --- PROCESSING PAGE {current_p} ---", flush=True)
                
                # Scroll to reveal content
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                time.sleep(3)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)
                
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                links = soup.find_all("a", href=re.compile(r"swipe|get-monetized-link"))
                
                page_items = 0
                for link_tag in links:
                    link = link_tag['href']
                    if not link.startswith("http"): link = BASE_URL + link
                    
                    if not any(v['link'] == link for v in all_content):
                        media_type = "unknown"
                        real_url = resolve_monetized_link(link)
                        
                        if real_url:
                            try:
                                h = requests.head(real_url, timeout=5)
                                c_type = h.headers.get('Content-Type', '').lower()
                                if "video" in c_type: media_type = "video"
                                elif "image" in c_type: media_type = "image"
                            except: pass
                        
                        if media_type == "unknown" and "swipe?id=" in link:
                            media_type = "video"

                        if media_type != "unknown":
                            all_content.append({
                                "title": f"{media_type.upper()}_{len(all_content)}",
                                "link": link,
                                "type": media_type,
                                "page": current_p
                            })
                            page_items += 1
                
                print(f"[+] Evidence: Found {page_items} items on Page {current_p}.", flush=True)

                if max_pages and current_p >= max_pages: break
                if current_p >= total_p: break
                
                # SURGICAL PAGING: Use the specific #next-btn selector
                print(f"[*] Attempting to click #next-btn...", flush=True)
                clicked = page.evaluate("""() => {
                    const nextBtn = document.querySelector('#next-btn');
                    if (nextBtn) {
                        nextBtn.click();
                        return true;
                    }
                    return false;
                }""")

                if clicked:
                    print(f"[*] Event sent. Waiting for Page {current_p + 1} evidence...", flush=True)
                    # Wait for UI text to change
                    start_time = time.time()
                    page_changed = False
                    while time.time() - start_time < 20:
                        new_p, _ = get_page_evidence()
                        if new_p == current_p + 1:
                            current_p = new_p
                            print(f"[VERIFIED] Now on Page {current_p}.", flush=True)
                            page_changed = True
                            break
                        time.sleep(2)
                    
                    if not page_changed:
                        print("[!] Page stuck. Attempting Hard Refresh to Page URL...", flush=True)
                        # Fallback: Construct the page URL directly if possible
                        # Some sites use ?page=2. We'll try to find a pattern.
                        break # For now, stop to avoid infinite loops
                else:
                    print("[!] No paging trigger found. Stopping.", flush=True)
                    break
                
        finally:
            browser.close()
            
    return all_content
