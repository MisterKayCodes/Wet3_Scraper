import os
import sys
import time
from playwright.sync_api import sync_playwright

# Example monetized link (normally we'd get this from the scraper output)
# For research, I'll just pick the first link from the subagent's previous attempt if I had it.
# Since I don't have a specific ID right now, I'll first scrape one link.

TARGET_PROFILE = "https://nelb6o.wet3.click/user-v2/Maliyaofficial/"

def research():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        print(f"[*] Navigating to {TARGET_PROFILE} to get a link...", flush=True)
        page.goto(TARGET_PROFILE)
        
        # Bypass modal
        try:
            page.wait_for_selector("button:has-text('Understand')", timeout=3000)
            page.click("button:has-text('Understand')")
        except:
            pass
            
        page.wait_for_selector("a.media-card", timeout=5000)
        first_video = page.query_selector("a.media-card")
        link = first_video.get_attribute("href")
        if not link.startswith("http"):
            link = "https://nelb6o.wet3.click" + link
            
        print(f"[*] Analyzing monetized link: {link}", flush=True)
        page.goto(link)
        
        # Take a series of screenshots to see the progression
        for i in range(1, 11):
            time.sleep(2)
            screenshot_path = f"research_step_{i}.png"
            page.screenshot(path=screenshot_path)
            print(f"[+] Saved {screenshot_path}", flush=True)
            
            # Check for common "Get Link" or "Continue" buttons
            # We can also check page title or URL changes
            print(f"    URL: {page.url}", flush=True)
            
        # Try to find the video tag in the end
        video_tag = page.query_selector("video")
        if video_tag:
            print("[!!!] Found video tag!", flush=True)
            print(f"    Source: {video_tag.get_attribute('src', flush=True)}")
        else:
            # Check for iframe
            iframe = page.query_selector("iframe")
            if iframe:
                print(f"[!] Found iframe: {iframe.get_attribute('src', flush=True)}")
        
        browser.close()

if __name__ == "__main__":
    research()
