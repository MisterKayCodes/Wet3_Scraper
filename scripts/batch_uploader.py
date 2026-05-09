import os
import asyncio
import json
import time
from dotenv import load_dotenv
from playwright.async_api import async_playwright

from scraper import async_get_profile_videos, DEFAULT_PROFILE
from downloader import async_decode_token, async_download_via_requests, get_cookies_and_ua
from telegram_utils import TelegramService

# Load environment variables
load_dotenv()

HISTORY_FILE = "history.json"
TEMP_DIR = "temp"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

async def run_batch_upload():
    # 1. Initialize
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        
    history = load_history()
    
    print("\n" + "="*50, flush=True)
    print("   TELEGRAM BATCH UPLOADER (ASYNC, flush=True)")
    print("="*50, flush=True)
    
    target_url = os.getenv("TARGET_PROFILE", DEFAULT_PROFILE)
    creator_name = target_url.strip("/").split("/")[-1]
    
    # 2. Setup Telegram
    tg = TelegramService()
    await tg.start()
    await tg.resolve_channel(os.getenv("CHANNEL_LINK"))
    
    # 3. Scrape Videos
    print(f"[*] Scraping profile (Async, flush=True): {creator_name}...")
    videos = await async_get_profile_videos(target_url)
    
    if not videos:
        print("[!] No videos found to upload.", flush=True)
        return

    # Filter out already processed videos
    new_videos = [v for v in videos if v['link'] not in history]
    
    if not new_videos:
        print("[+] All discovered videos have already been uploaded.", flush=True)
        return
        
    print(f"[*] Found {len(new_videos, flush=True)} new videos to process.")
    
    # Reverse to post oldest first
    new_videos.reverse()
    
    start_num = len(history) + 1
    
    # 4. Process Loop
    session_data = get_cookies_and_ua()
    ua = session_data.get('user_agent') if session_data else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    cookies = session_data.get('cookies', []) if session_data else []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=ua)
        await context.add_cookies(cookies)
        page = await context.new_page()
        
        for i, video in enumerate(new_videos):
            video_num = start_num + i
            caption = f"{creator_name} - Video #{video_num}"
            filename = f"{creator_name}_{video_num}.mp4"
            file_path = os.path.join(TEMP_DIR, filename)
            
            print(f"\n[{i+1}/{len(new_videos, flush=True)}] Processing: {caption}")
            
            # Step A: Resolve Link
            sd_link = await async_decode_token(page, video['link'])
            
            if not sd_link:
                print(f"[!] Could not resolve link for: {video['title']}", flush=True)
                continue
                
            # Step B: Download
            print(f"[*] Downloading to local temp (Async/Threaded, flush=True)...")
            success = await async_download_via_requests(sd_link, await context.cookies(), ua, file_path)
            
            if success:
                # Step C: Upload to Telegram
                upload_success = await tg.upload_video(file_path, caption)
                
                if upload_success:
                    # Step D: Update History
                    history.append(video['link'])
                    save_history(history)
                    
                    # Step E: Cleanup
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            print(f"[*] Cleaned up local file: {filename}", flush=True)
                        except:
                            print(f"[!] Warning: Could not delete {filename}", flush=True)
                else:
                    print(f"[!] Failed to upload to Telegram: {video['title']}", flush=True)
            else:
                print(f"[!] Failed to download video: {video['title']}", flush=True)
            
            # Small cooldown between videos
            await asyncio.sleep(5)
            
        await browser.close()

    print("\n" + "="*50, flush=True)
    print("   BATCH UPLOAD FINISHED", flush=True)
    print("="*50, flush=True)
    await tg.client.disconnect()

if __name__ == "__main__":
    asyncio.run(run_batch_upload())
