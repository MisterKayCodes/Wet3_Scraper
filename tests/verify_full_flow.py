import os
import sys
import json
import time # Fixed missing import
from scraper import scrape_video_cards
from downloader import process_video_queue
from playwright.sync_api import sync_playwright

# Non-interactive test to verify the full flow
TEST_URL = "https://nelb6o.wet3.click/user-v2/Maliyaofficial/"

def verify_full_flow():
    print("--- Verification: Full Flow Test ---", flush=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # 1. Scrape 1 page for just 1 video to test
        print("[*] Scraping 1 test video (with retries and long timeout, flush=True)...")
        success_nav = False
        for attempt in range(3):
            try:
                # Use wait_until="domcontentloaded" to avoid timing out on slow external ad scripts
                page.goto(TEST_URL, wait_until="domcontentloaded", timeout=60000)
                success_nav = True
                break
            except Exception as e:
                print(f"[!] Attempt {attempt+1} failed: {e}", flush=True)
                time.sleep(5)
        
        if not success_nav:
            print("[!] Could not navigate to profile. Site might be throttled.", flush=True)
            browser.close()
            return

        # Bypass modal
        try:
            page.wait_for_selector("button:has-text('Understand')", timeout=10000)
            page.click("button:has-text('Understand')")
            print("[x] Modal bypassed.", flush=True)
        except:
            print("[ ] No modal found.", flush=True)
            
        page.wait_for_selector("a.media-card", timeout=20000)
        cards = page.query_selector_all("a.media-card")
        
        if not cards:
            print("[!] No videos found.", flush=True)
            browser.close()
            return

        # Just take the first one
        card = cards[0]
        title = card.inner_text().strip()
        link = card.get_attribute("href")
        if not link.startswith("http"):
            link = "https://nelb6o.wet3.click" + link
            
        test_video = [{"title": title, "link": link}]
        print(f"[+] Found test video: {title}", flush=True)
        
        browser.close()
        
    # 2. Trigger downloader
    print("[*] Starting downloader for test video...", flush=True)
    # This will decode the token and then use the stealth downloader
    process_video_queue(test_video)
    
    # 3. Check if file exists
    if os.path.exists("videos"):
        videos = os.listdir("videos")
        print(f"[*] Files in videos/ folder: {videos}", flush=True)
        if len(videos) > 0:
            print("\n[VERIFICATION SUCCESS] Video file found in 'videos/' folder!", flush=True)
        else:
            print("\n[VERIFICATION FAILURE] videos/ folder is empty.", flush=True)
    else:
        print("\n[VERIFICATION FAILURE] 'videos/' folder was not created.", flush=True)

if __name__ == "__main__":
    verify_full_flow()
