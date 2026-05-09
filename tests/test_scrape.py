import os
import sys
import time
import json
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE_URL = "https://nelb6o.wet3.click"
TARGET_URL = "https://nelb6o.wet3.click/user-v2/Maliyaofficial/"

def test_scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"[*] Testing connection to {TARGET_URL}...", flush=True)
        page.goto(TARGET_URL)
        
        # Check for modal
        try:
            page.wait_for_selector("button:has-text('Understand')", timeout=5000)
            page.click("button:has-text('Understand')")
            print("[x] Bypassed modal.", flush=True)
        except:
            print("[ ] No modal found.", flush=True)
            
        # Wait for videos
        page.wait_for_selector("a.media-card", timeout=10000)
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.select("a.media-card")
        
        print(f"[+] Found {len(cards, flush=True)} videos on first page.")
        
        if len(cards) > 0:
            first_title = cards[0].get_text(strip=True)
            first_link = cards[0]['href']
            print(f"[*] First Video: {first_title}", flush=True)
            print(f"[*] Link: {first_link}", flush=True)
            
        browser.close()

if __name__ == "__main__":
    test_scrape()
